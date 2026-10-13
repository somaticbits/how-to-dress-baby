"""Local French greetings, stable for a whole day or sleep period."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import Config

DAY_MESSAGES = (
    "Bonjour, {name} !",
    "Coucou, {name} !",
    "Belle journée, {name} !",
    "Un sourire, {name} ?",
    "Tout doux, {name} !",
    "Prêt pour un câlin, {name} ?",
    "Petit bonjour à {name} !",
    "Au fil du jour, {name}",
    "À ton rythme, {name}",
    "Place aux sourires, {name} !",
    "Un jour à découvrir, {name}",
    "Les petits bonheurs de {name}",
    "Bienvenue au jour, {name} !",
    "Des câlins pour {name}",
    "On prend le temps, {name}",
    "Une douce journée, {name}",
    "À petits pas, {name}",
    "Le monde t’attend, {name}",
    "Du bonheur pour {name}",
    "C’est ton moment, {name}",
    "Un peu de douceur, {name}",
    "On découvre ensemble, {name}",
    "Bonjour les sourires de {name} !",
    "Une pause câlin, {name} ?",
    "Jour après jour, {name}",
)

NIGHT_MESSAGES = (
    "Bonne nuit, {name}",
    "Doux rêves, {name}",
    "Bonsoir, {name}",
    "Tout doucement, {name}",
    "Une nuit paisible, {name}",
    "Un câlin du soir, {name}",
    "La lune te salue, {name}",
    "Le jour se repose, {name}",
    "Un soir tout doux, {name}",
    "À demain, {name}",
    "Les étoiles pour {name}",
    "Une pause tendresse, {name}",
    "Le calme du soir, {name}",
    "Au pays des rêves, {name}",
    "La nuit arrive, {name}",
    "Des rêves pour {name}",
    "Un petit bisou, {name}",
    "Le soir à ton rythme, {name}",
    "Douce soirée, {name}",
    "Un moment calme, {name}",
    "Sous les étoiles, {name}",
    "La journée s’achève, {name}",
    "On ralentit, {name}",
    "Tendre nuit, {name}",
    "Une berceuse pour {name}",
)


def greeting(config: Config, now: datetime, page: str) -> str:
    local = now.astimezone(ZoneInfo(config.timezone))
    date = local.date()
    if page == "night":
        if local.strftime("%H:%M") < config.day_start:
            date -= timedelta(days=1)
        messages = NIGHT_MESSAGES
    elif page == "day":
        messages = DAY_MESSAGES
    else:
        raise ValueError("page must be day or night")
    return messages[date.toordinal() % len(messages)].format(
        name=config.baby_name.strip() or "bébé"
    )
