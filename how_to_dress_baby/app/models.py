"""Immutable inputs and recommendations shared by adapters and renderer."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Weather:
    temperature: float
    condition: str
    observed_at: datetime
    apparent_temperature: float | None = None
    wind_kmh: float | None = None
    uv: float | None = None
    rain_probability: float | None = None
    forecast_low: float | None = None
    forecast_high: float | None = None
    forecast_conditions: tuple[str, ...] = ()
    alert: str | None = None


@dataclass(frozen=True)
class Room:
    temperature: float
    observed_at: datetime


@dataclass(frozen=True)
class Snapshot:
    weather: Weather | None
    living_room: Room | None
    bedroom: Room | None
    fetched_at: datetime
    demo: bool = False
    warnings: tuple[str, ...] = ()
    parents_bedroom: Room | None = None


@dataclass(frozen=True)
class Recommendation:
    indoor: tuple[str, ...]
    outdoor: tuple[str, ...]
    bring: tuple[str, ...]
    notes: tuple[str, ...]
    caution: bool = False
    adjustment: str = "Vérifier la nuque ; ajuster les couches au confort."
    band: str | None = None
