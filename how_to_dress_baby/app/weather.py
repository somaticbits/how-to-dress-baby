"""Home Assistant adapter with finite timeouts and no direct weather API calls."""

import json
import math
import os
from datetime import UTC, datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.config import Config
from app.models import Room, Snapshot, Weather


def number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def timestamp(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timestamps must include a timezone")
    return result


def celsius(value: object, unit: str) -> float | None:
    result = number(value)
    if result is None:
        return None
    if unit in {"°C", "C"}:
        return result
    if unit in {"°F", "F"}:
        return (result - 32) * 5 / 9
    if unit == "K":
        return result - 273.15
    return None


def wind_kmh(value: object, unit: str) -> float | None:
    result = number(value)
    factors = {"km/h": 1, "m/s": 3.6, "mph": 1.609344, "kn": 1.852, "kt": 1.852}
    return result * factors[unit] if result is not None and unit in factors else None


def demo_snapshot(now: datetime) -> Snapshot:
    return Snapshot(
        weather=Weather(
            temperature=12,
            apparent_temperature=10,
            condition="rainy",
            wind_kmh=18,
            rain_probability=70,
            uv=1,
            forecast_low=10,
            forecast_high=15,
            forecast_conditions=("rainy", "cloudy"),
            observed_at=now,
        ),
        living_room=Room(19, now),
        bedroom=Room(19, now),
        fetched_at=now,
        demo=True,
    )


class HAClient:
    def __init__(self, config: Config):
        self.config = config
        self.token = os.environ.get("SUPERVISOR_TOKEN") or os.environ.get("HA_TOKEN")

    def request(self, path: str, body: dict | None = None) -> dict:
        if not self.token:
            raise ValueError("Home Assistant token missing")
        request = Request(
            f"{self.config.ha_url.rstrip('/')}/api/{path}",
            data=json.dumps(body).encode() if body is not None else None,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
        )
        with urlopen(request, timeout=10) as response:
            raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError("HA response too large")
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError("HA response must be an object")
        return result

    def state(self, entity: str) -> dict:
        result = self.request(f"states/{quote(entity, safe='')}")
        if result.get("state") in {None, "unknown", "unavailable"}:
            raise ValueError("Entity unavailable")
        return result

    def room(self, entity: str) -> Room | None:
        if not entity:
            return None
        state = self.state(entity)
        value = celsius(state["state"], state.get("attributes", {}).get("unit_of_measurement"))
        if value is None:
            raise ValueError("Room sensor has unsupported units or invalid value")
        # last_updated changes on state/attribute changes; last_reported also
        # reflects unchanged readings on recent HA versions. Never use fetch time.
        observed = timestamp(state.get("last_reported") or state["last_updated"])
        return Room(value, observed)

    def fetch(self, now: datetime) -> Snapshot:
        warnings = []
        rooms: list[Room | None] = []
        for entity in (
            self.config.living_room_entity,
            self.config.bedroom_entity,
            self.config.parents_bedroom_entity,
        ):
            try:
                rooms.append(self.room(entity))
            except (HTTPError, URLError, TimeoutError, ValueError, KeyError, TypeError):
                rooms.append(None)
                warnings.append("Une température de pièce est indisponible.")
        try:
            weather = self.fetch_weather(now, warnings)
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError, TypeError):
            weather = None
            warnings.append("Météo indisponible : vérifier dehors avant de sortir.")
        if weather is None and all(room is None for room in rooms):
            raise ValueError("No usable Home Assistant data")
        return Snapshot(
            weather,
            rooms[0],
            rooms[1],
            now,
            warnings=tuple(warnings),
            parents_bedroom=rooms[2],
        )

    def fetch_weather(self, now: datetime, warnings: list[str]) -> Weather:
        state = self.state(self.config.weather_entity)
        attributes = state.get("attributes", {})
        unit = attributes.get("temperature_unit")
        temperature = celsius(attributes.get("temperature"), unit)
        if temperature is None:
            raise ValueError("Weather temperature missing or unsupported units")
        forecast: list[dict] = []
        try:
            result = self.request(
                "services/weather/get_forecasts?return_response",
                {"entity_id": self.config.weather_entity, "type": "hourly"},
            )
            forecast = result["service_response"][self.config.weather_entity]["forecast"]
            if not isinstance(forecast, list):
                raise ValueError("Invalid forecast")
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError, TypeError):
            warnings.append("Prévisions horaires indisponibles ; conditions actuelles seules.")
        selected = []
        for entry in forecast:
            try:
                at = timestamp(entry["datetime"])
                if now <= at < now + timedelta(hours=self.config.forecast_hours):
                    selected.append(entry)
            except (KeyError, TypeError, ValueError):
                continue
        temperatures = [
            value
            for entry in selected
            if (value := celsius(entry.get("temperature"), unit)) is not None
        ]
        if forecast and not selected:
            warnings.append("Aucune prévision disponible pour cette fenêtre.")
        alert = None
        if self.config.alert_entity:
            try:
                alert = str(self.state(self.config.alert_entity)["state"])
            except (HTTPError, URLError, TimeoutError, ValueError, KeyError, TypeError):
                warnings.append("Vigilance indisponible : consulter Météo-France.")
        probabilities = [
            value
            for entry in selected
            if (value := number(entry.get("precipitation_probability"))) is not None
            and 0 <= value <= 100
        ]
        weather = Weather(
            temperature=temperature,
            condition=str(state["state"]),
            apparent_temperature=celsius(attributes.get("apparent_temperature"), unit),
            wind_kmh=wind_kmh(attributes.get("wind_speed"), attributes.get("wind_speed_unit")),
            uv=number(attributes.get("uv_index")),
            rain_probability=max(probabilities) if probabilities else None,
            forecast_low=min(temperatures) if temperatures else None,
            forecast_high=max(temperatures) if temperatures else None,
            forecast_conditions=tuple(str(entry.get("condition", "unknown")) for entry in selected),
            observed_at=timestamp(state.get("last_reported") or state["last_updated"]),
            alert=alert,
        )
        return weather


def utc_now() -> datetime:
    return datetime.now(UTC)
