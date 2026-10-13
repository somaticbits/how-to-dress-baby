"""Read local JSON or Home Assistant add-on options; keep secrets server-side."""

import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class Config:
    demo: bool = True
    location: str = "Chez nous"
    timezone: str = "Europe/Paris"
    day_start: str = "07:00"
    night_start: str = "19:00"
    port: int = 8000
    refresh_seconds: int = 900
    max_age_minutes: int = 120
    forecast_hours: int = 4
    weather_entity: str = ""
    living_room_entity: str = ""
    bedroom_entity: str = ""
    parents_bedroom_entity: str = ""
    alert_entity: str = ""
    ha_url: str = "http://supervisor/core"
    cold_below: float = 10.0
    cool_below: float = 18.0
    mild_below: float = 22.0
    warm_from: float = 25.0
    indoor_cool_below: float = 18.0
    indoor_warm_from: float = 25.0
    extreme_cold_below: float = 0.0
    extreme_heat_from: float = 32.0
    cache_dir: str = "cache"

    def __post_init__(self) -> None:
        ZoneInfo(self.timezone)
        for name in ("day_start", "night_start"):
            if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", getattr(self, name)):
                raise ValueError(f"{name} must be HH:MM")
        if self.day_start >= self.night_start:
            raise ValueError("day_start must be earlier than night_start")
        if not isinstance(self.demo, bool):
            raise ValueError("demo must be true or false")
        if not 1 <= self.port <= 65535:
            raise ValueError("port must be between 1 and 65535")
        if self.refresh_seconds < 60 or self.max_age_minutes < 1:
            raise ValueError("refresh must be >= 60 seconds; max age must be positive")
        if not 1 <= self.forecast_hours <= 24:
            raise ValueError("forecast_hours must be between 1 and 24")
        bands = (
            self.extreme_cold_below,
            self.cold_below,
            self.cool_below,
            self.mild_below,
            self.warm_from,
            self.extreme_heat_from,
        )
        if not all(math.isfinite(value) for value in bands):
            raise ValueError("temperature bands must be finite")
        if any(a >= b for a, b in zip(bands, bands[1:], strict=False)):
            raise ValueError("temperature bands must be strictly increasing")
        if not (
            math.isfinite(self.indoor_cool_below)
            and math.isfinite(self.indoor_warm_from)
            and self.indoor_cool_below < self.indoor_warm_from
        ):
            raise ValueError("indoor temperature bands must be finite and increasing")
        if not self.demo and not self.weather_entity.startswith("weather."):
            raise ValueError("live mode requires a weather entity")
        if not self.ha_url.startswith(("http://", "https://")):
            raise ValueError("ha_url must be HTTP(S)")


def load_config(path: str | None = None) -> Config:
    selected = path or os.environ.get("BABY_CONFIG")
    if selected is None and Path("/data/options.json").exists():
        selected = "/data/options.json"
    values = json.loads(Path(selected).read_text()) if selected else {}
    if Path("/data").is_dir():
        values.setdefault("cache_dir", "/data/cache")
    return Config(**values)
