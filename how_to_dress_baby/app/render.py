"""French baby-book layouts, rendered as native-size grayscale Kindle images."""

import io
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

from app.artwork import GREY, LABELS, icon, marker
from app.config import Config
from app.models import Room, Snapshot
from app.rules import fresh, recommend

FONT_DIR = Path(__file__).parent / "assets" / "fonts"
FOOTER_ROWS = (700, 720, 740)
BATTERY_TOP = 761
CONDITIONS = {
    "sunny": "Soleil",
    "clear-night": "Nuit claire",
    "cloudy": "Nuageux",
    "partlycloudy": "Éclaircies",
    "rainy": "Pluie",
    "pouring": "Forte pluie",
    "snowy": "Neige",
    "snowy-rainy": "Pluie et neige",
    "windy": "Vent",
    "windy-variant": "Vent et nuages",
    "fog": "Brouillard",
    "hail": "Grêle",
    "lightning": "Orage",
    "lightning-rainy": "Orage et pluie",
    "exceptional": "Conditions exceptionnelles",
}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    weight = "Bold" if bold else "Regular"
    return ImageFont.truetype(str(FONT_DIR / f"AtkinsonHyperlegible-{weight}.ttf"), size)


def rounded_font(size: int, weight: int = 600) -> ImageFont.FreeTypeFont:
    result = ImageFont.truetype(str(FONT_DIR / "Fredoka.ttf"), size)
    # Fredoka's axes are weight then width; retain normal width.
    result.set_variation_by_axes([weight, 100])
    return result


def page_for(config: Config, now: datetime) -> str:
    local_time = now.astimezone(ZoneInfo(config.timezone)).strftime("%H:%M")
    return "day" if config.day_start <= local_time < config.night_start else "night"


class Page:
    def __init__(self):
        self.image = Image.new("L", (600, 800), 255)
        self.draw = ImageDraw.Draw(self.image)

    def text(self, x, y, value, size=18, rounded=False, bold=False, fill=0):
        face = rounded_font(size, 700 if bold else 600) if rounded else font(size, bold)
        self.draw.text((x, y), value, font=face, fill=fill)

    def lines(self, x, y, value, width, size=20, rounded=False, max_lines=2):
        face = rounded_font(size) if rounded else font(size)
        lines = []
        current = ""
        for word in value.split():
            candidate = f"{current} {word}".strip()
            if self.draw.textlength(candidate, font=face) > width and current:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        for index, line in enumerate(lines[:max_lines]):
            if len(lines) > max_lines and index == max_lines - 1:
                while self.draw.textlength(line + "…", font=face) > width:
                    line = line[:-1]
                line += "…"
            self.text(x, y + index * (size + 6), line, size, rounded=rounded)

    def panel(self, bounds):
        self.draw.rounded_rectangle(bounds, radius=30, fill=255, outline=0, width=3)

    def heading(self, x, y, title, symbol):
        self.image.paste(marker(symbol, 30), (x, y))
        self.text(x + 40, y - 1, title, 23, rounded=True)

    def garments(self, items, x, y, width, size=76):
        if not items:
            return
        spacing = width / len(items)
        for index, item in enumerate(items):
            center = x + spacing * (index + 0.5)
            self.image.paste(icon(item, size), (round(center - size / 2), y))
            caption = LABELS[item]
            face = font(14)
            caption_width = self.draw.textlength(caption, font=face)
            self.text(round(center - caption_width / 2), y + size + 8, caption, 14)

    def temperature(self, value, label, apparent=None):
        self.draw.ellipse((425, 130, 563, 268), fill=GREY)
        for y, text, size, rounded in (
            (155, f"{value:.0f}°C" if value is not None else "?°C", 34, True),
            (204, label, 16, False),
            (230, f"ressenti {apparent:.0f}°C" if apparent is not None else "", 16, False),
        ):
            face = rounded_font(size, 700) if rounded else font(size)
            length = self.draw.textlength(text, font=face)
            self.text(round(494 - length / 2), y, text, size, rounded=rounded, bold=rounded)

    def banner(self, message):
        if message:
            self.draw.rectangle((0, 0, 599, 31), fill=0)
            self.text(18, 4, message, 18, bold=True, fill=255)

    def footer_lines(self, *lines: str) -> None:
        """Separate footer rows from panels and the reserved battery banner."""
        if len(lines) > len(FOOTER_ROWS):
            raise ValueError("Footer supports at most three lines")
        for y, line in zip(FOOTER_ROWS, lines, strict=False):
            self.text(24, y, line, 15)

    def png(self):
        buffer = io.BytesIO()
        self.image.save(buffer, format="PNG", optimize=True)
        return buffer.getvalue()


def usable(room: Room | None, config: Config, now: datetime) -> bool:
    return bool(room and fresh(room.observed_at, now, config.max_age_minutes))


def header(page: Page, snapshot: Snapshot, config: Config, now: datetime, night=False):
    page.image.paste(marker("star", 26), (22, 48))
    page.text(59, 39, "Habiller bébé", 36, rounded=True, bold=True)
    page.text(477, 54, "La nuit" if night else "Le jour", 20)
    local = now.astimezone(ZoneInfo(config.timezone))
    if night:
        evening = local.date()
        if local.strftime("%H:%M") < config.day_start:
            evening -= timedelta(days=1)
        morning = evening + timedelta(days=1)
        date = f"Nuit du {evening:%d/%m} au {morning:%d/%m/%Y}"
    else:
        date = f"{config.location[:28]} · {local:%d/%m/%Y}"
    page.text(24, 84, date, 15)


def footer(page: Page, snapshot: Snapshot, config: Config, room=None):
    zone = ZoneInfo(config.timezone)
    observed = room.observed_at if room else snapshot.fetched_at
    at = observed.astimezone(zone)
    expiry = (observed + timedelta(minutes=config.max_age_minutes)).astimezone(zone)
    page.footer_lines(
        f"Mis à jour le {at:%d/%m à %H:%M} · heure de Paris",
        f"À vérifier de nouveau après {expiry:%H:%M}.",
    )


def recommendation(items, full_sleeves=True):
    labels = (
        {"body_short": "Body manches courtes", "body_long": "Body manches longues"}
        if full_sleeves
        else {"body_short": "Body court", "body_long": "Body long"}
    )
    return " + ".join(labels.get(item, LABELS[item].lower()) for item in items)


def render(snapshot: Snapshot, config: Config, now: datetime, page: str = "auto") -> bytes:
    selected = page_for(config, now) if page == "auto" else page
    if selected == "day":
        return render_day(snapshot, config, now)
    if selected == "night":
        return render_night(snapshot, config, now)
    raise ValueError("page must be auto, day, or night")


def battery_notice(content: bytes, level: int | None, charging: bool | None = None) -> bytes:
    """Annotate only a current, valid Kindle reading; never infer a battery level."""
    if type(level) is not int or not 0 <= level <= 15 or charging is True:
        return content
    with Image.open(io.BytesIO(content)) as original:
        image = original.convert("L")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((16, BATTERY_TOP, 584, 798), radius=7, fill=0)
    draw.rounded_rectangle((29, 771, 52, 787), radius=2, outline=255, width=2)
    draw.rectangle((53, 776, 56, 782), fill=255)
    draw.rectangle((33, 775, 36, 783), fill=255)
    draw.text((69, 768), f"Kindle : {level}% — À RECHARGER", fill=255, font=font(20, True))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def render_day(snapshot: Snapshot, config: Config, now: datetime) -> bytes:
    page = Page()
    advice = recommend(snapshot, config, now)
    weather = snapshot.weather
    valid_weather = weather and fresh(weather.observed_at, now, config.max_age_minutes)
    room_ok = usable(snapshot.living_room, config, now)
    if snapshot.demo:
        banner = "DÉMONSTRATION — DONNÉES FICTIVES"
        if not valid_weather or not room_ok:
            banner = "DÉMO — DONNÉES ABSENTES OU PÉRIMÉES"
    elif not valid_weather or not room_ok:
        banner = "DONNÉES ABSENTES OU PÉRIMÉES — À VÉRIFIER"
    elif advice.caution:
        banner = "VIGILANCE — TENUE À VÉRIFIER"
    elif snapshot.warnings:
        banner = "DONNÉES PARTIELLES — À VÉRIFIER"
    else:
        banner = ""
    page.banner(banner)
    header(page, snapshot, config, now)
    page.panel((16, 111, 584, 425))
    page.heading(35, 130, "Dehors", "tree")
    page.temperature(
        weather.temperature if valid_weather else None,
        "dehors",
        weather.apparent_temperature if valid_weather else None,
    )
    page.text(37, 165, "À porter maintenant · selon l’air mesuré", 14)
    base = (
        recommendation(advice.outdoor, full_sleeves=False) if advice.outdoor else "Tenue à vérifier"
    )
    page.lines(37, 190, base, 365, size=21, rounded=True, max_lines=3)
    page.garments(advice.outdoor, 34, 281, 532, size=64 if len(advice.outdoor) > 5 else 76)
    if advice.caution and advice.notes:
        page.lines(37, 378, advice.notes[0], 523, size=17, max_lines=2)
    elif snapshot.warnings:
        page.lines(37, 378, snapshot.warnings[0], 523, size=17, max_lines=2)
    elif valid_weather:
        summary = CONDITIONS.get(weather.condition, "Conditions inconnues")
        if weather.forecast_low is not None and weather.forecast_high is not None:
            summary += (
                f" · prochaines {config.forecast_hours} h : "
                f"{weather.forecast_low:.0f}–{weather.forecast_high:.0f}°C"
            )
        page.text(37, 393, summary, 17)
    else:
        page.text(37, 393, "Vérifier la météo avant de choisir la tenue.", 17)
    page.panel((16, 447, 292, 694))
    page.heading(34, 465, "Intérieur", "house")
    room = snapshot.living_room
    page.text(36, 508, f"{room.temperature:.0f}°C" if room_ok else "À mesurer", 27, rounded=True)
    page.lines(36, 548, recommendation(advice.indoor), 235, size=19, rounded=True)
    page.garments(advice.indoor, 30, 601, 247, size=56)
    page.panel((308, 447, 584, 694))
    page.heading(326, 465, "À emporter", "bag")
    if advice.bring:
        page.lines(328, 515, recommendation(advice.bring), 235, size=18, rounded=True, max_lines=3)
        page.text(328, 587, "À ajouter si besoin", 13)
        page.garments(advice.bring, 320, 605, 247, size=53 if len(advice.bring) > 2 else 57)
    else:
        page.lines(328, 515, "À choisir selon la sortie", 225, size=22, rounded=True)
    observed = snapshot.fetched_at.astimezone(ZoneInfo(config.timezone))
    page.footer_lines(
        "Adapter les couches ; éviter la surchauffe.",
        advice.adjustment,
        f"Mis à jour le {observed:%d/%m à %H:%M} · heure de Paris",
    )
    return page.png()


def render_night(snapshot: Snapshot, config: Config, now: datetime) -> bytes:
    page = Page()
    room = snapshot.bedroom
    room_ok = usable(room, config, now)
    parents = snapshot.parents_bedroom
    show_parents = bool(config.parents_bedroom_entity or parents)
    parents_ok = usable(parents, config, now)
    if snapshot.demo:
        banner = "DÉMONSTRATION — CHAMBRE FICTIVE"
        if not room_ok or (show_parents and not parents_ok):
            banner = "DÉMO — TEMPÉRATURE ABSENTE OU PÉRIMÉE"
    else:
        banner = (
            ""
            if room_ok and (not show_parents or parents_ok)
            else "TEMPÉRATURE ABSENTE OU PÉRIMÉE — À VÉRIFIER"
        )
    page.banner(banner)
    header(page, snapshot, config, now, night=True)
    page.panel((16, 111, 584, 425))
    page.heading(35, 130, "Cette nuit", "moon")
    page.temperature(room.temperature if room_ok else None, "bébé" if show_parents else "chambre")
    page.lines(37, 179, "Gigoteuse à choisir selon sa notice", 350, 27, rounded=True)
    page.garments(("sleep_bag",), 30, 269, 540, size=89)
    page.text(37, 395, "Modèle et TOG à renseigner · choix manuel", 17)
    page.panel((16, 447, 292, 694))
    page.heading(34, 465, "Vêtements", "moon")
    page.lines(36, 515, "À choisir selon la gigoteuse", 233, 23, rounded=True)
    page.lines(36, 598, "Pas de bonnet ni de couverture libre au lit.", 233, 17, max_lines=3)
    page.lines(36, 663, "Éviter la surchauffe.", 233, 16)
    page.panel((308, 447, 584, 694))
    page.heading(326, 465, "Les chambres" if show_parents else "La chambre", "house")
    if show_parents:
        for y, label, reading, valid in (
            (510, "Bébé", room, room_ok),
            (565, "Parents", parents, parents_ok),
        ):
            value = f"{reading.temperature:.1f}°C" if valid else "À mesurer"
            page.text(328, y, f"{label} : {value}", 21, rounded=True)
            if valid:
                at = reading.observed_at.astimezone(ZoneInfo(config.timezone))
                page.text(328, y + 29, f"Mesuré le {at:%d/%m à %H:%M}", 13)
        page.lines(328, 630, "Choisir la pièce où bébé dort, sans moyenner.", 226, 17, max_lines=3)
    else:
        page.text(
            328, 514, f"{room.temperature:.0f}°C" if room_ok else "À mesurer", 30, rounded=True
        )
        page.lines(
            328, 564, "Mesure actuelle, pas une prévision pour la nuit.", 226, 19, max_lines=3
        )
    footer(page, snapshot, config, room=room if room_ok else None)
    return page.png()
