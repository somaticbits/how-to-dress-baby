"""Conservative, configurable comfort heuristics, NOT medical prescriptions.

Safety constraints are sourced in docs/clothing-guidance.md. Numerical outdoor
bands are product defaults; never present them as validated clinical thresholds.
Footmuff insulation and gigoteuse selection deliberately remain manual.
"""

from datetime import datetime, timedelta

from app.config import Config
from app.models import Recommendation, Snapshot

WET = {"rainy", "pouring", "snowy", "snowy-rainy", "hail", "lightning-rainy"}
HAZARDOUS = {"lightning", "lightning-rainy", "hail", "exceptional"}
KNOWN = (
    WET
    | HAZARDOUS
    | {
        "sunny",
        "clear-night",
        "cloudy",
        "partlycloudy",
        "fog",
        "windy",
        "windy-variant",
    }
)


def fresh(observed: datetime, now: datetime, max_age_minutes: int) -> bool:
    age = now - observed
    return -timedelta(minutes=5) <= age <= timedelta(minutes=max_age_minutes)


def recommend(snapshot: Snapshot, config: Config, now: datetime) -> Recommendation:
    indoor: tuple[str, ...] = ()
    outdoor: tuple[str, ...] = ()
    bring: tuple[str, ...] = ()
    notes: list[str] = []
    adjustment = "Vérifier la nuque ; ajuster si bébé transpire."
    band = None
    room = snapshot.living_room
    if room and fresh(room.observed_at, now, config.max_age_minutes):
        if room.temperature >= config.indoor_warm_from:
            indoor = ("body_short",)
        elif room.temperature < config.indoor_cool_below:
            indoor = ("body_long", "sleepsuit", "cardigan")
        else:
            indoor = ("body_long", "trousers")
    else:
        notes.append("Température intérieure inconnue ou périmée : vérifier la pièce.")

    weather = snapshot.weather
    if weather is None or not fresh(weather.observed_at, now, config.max_age_minutes):
        notes.insert(0, "Météo indisponible ou périmée : vérifier dehors avant de sortir.")
        return Recommendation(indoor, (), (), tuple(notes), caution=True)

    conditions = {weather.condition, *weather.forecast_conditions}
    if weather.condition not in KNOWN:
        notes.insert(0, "Conditions météo inconnues : vérifier dehors avant de sortir.")
        return Recommendation(indoor, (), (), tuple(notes), caution=True)
    # Clothing uses air temperature. Provider apparent values are contextual
    # estimates, not infant-specific thermal models; retain only extreme gates.
    temperature = weather.temperature
    extremes = [temperature]
    if weather.apparent_temperature is not None:
        extremes.append(weather.apparent_temperature)
    if weather.forecast_low is not None:
        extremes.append(weather.forecast_low)
    if weather.forecast_high is not None:
        extremes.append(weather.forecast_high)
    serious_alert = weather.alert and weather.alert.casefold() not in {
        "vert",
        "green",
        "aucun",
        "none",
        "0",
    }
    caution = bool(
        conditions & HAZARDOUS
        or min(extremes) < config.extreme_cold_below
        or max(extremes) >= config.extreme_heat_from
        or serious_alert
    )
    if caution:
        notes.insert(0, "Prudence : consulter la vigilance et reconsidérer la sortie.")
        notes.append("Pas de tenue automatique pour ces conditions.")
    elif temperature < config.cold_below:
        band = "cold"
        outdoor = (
            "body_long",
            "trousers",
            "cardigan",
            "socks",
            "warm_outerwear",
            "warm_hat",
            "mittens",
        )
    elif temperature < config.cool_below:
        band = "cool"
        outdoor = ("body_long", "trousers", "cardigan", "socks")
        bring = ("light_jacket",)
    elif temperature < config.mild_below:
        band = "mild"
        outdoor = ("body_long", "trousers", "socks")
        bring = ("cardigan",)
    elif temperature < config.warm_from:
        band = "warm"
        outdoor = ("body_short", "trousers", "socks")
        bring = ("cardigan",)
    else:
        band = "hot"
        outdoor = ("light_outfit", "sun_hat")
        notes.append("Privilégier l’ombre ; éviter les couches isolantes inutiles.")
        adjustment = "Chaleur : ombre et couches légères, éviter la surchauffe."

    if conditions & WET or (
        weather.rain_probability is not None and weather.rain_probability >= 50
    ):
        if not caution:
            bring = (*bring, "spare_clothes")
        notes.append("Pluie/neige : garder les vêtements secs, prévoir un abri.")
        adjustment = "Pluie : garder les vêtements secs, prévoir un abri."
    if weather.wind_kmh is not None and weather.wind_kmh >= 30:
        notes.append("Vent soutenu : chercher un abri, surveiller les extrémités.")
        if not caution and "rain_shell" not in bring:
            bring = (*bring, "rain_shell")
        adjustment = "Vent : couche coupe-vent si besoin, chercher un abri."
    if weather.forecast_low is not None and weather.forecast_high is not None:
        if weather.forecast_high - weather.forecast_low >= 5 or (
            weather.forecast_low < config.cool_below <= temperature
        ):
            notes.append("Température changeante : ajuster les couches pendant la sortie.")
            if (
                not caution
                and temperature < config.warm_from
                and "cardigan" not in (*outdoor, *bring)
            ):
                bring = (*bring, "cardigan")
    if weather.uv is not None and weather.uv >= 3:
        notes.append("UV : ombre et protection solaire, même avec des nuages.")
        adjustment = "UV : ombre et protection solaire, même avec des nuages."
    return Recommendation(indoor, outdoor, bring, tuple(notes), caution, adjustment, band)
