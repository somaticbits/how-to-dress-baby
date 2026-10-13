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
WIDTH, HEIGHT = 600, 800
MARGIN = 24
GAP = 18
PAD = 22
BANNER_HEIGHT = 32
BATTERY_TOP = 761
# Every panel ends here, so the low-battery band never covers content.
CONTENT_BOTTOM = 752
CIRCLE = 150
CONDITIONS = {
    "sunny": "soleil",
    "clear-night": "nuit claire",
    "cloudy": "nuageux",
    "partlycloudy": "éclaircies",
    "rainy": "pluie",
    "pouring": "forte pluie",
    "snowy": "neige",
    "snowy-rainy": "pluie et neige",
    "windy": "vent",
    "windy-variant": "vent et nuages",
    "fog": "brouillard",
    "hail": "grêle",
    "lightning": "orage",
    "lightning-rainy": "orage et pluie",
    "exceptional": "exceptionnel",
}
DAYS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
MONTHS = (
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
)
# Sentences name sleeves in full; captions under drawings stay one short word.
PHRASES = {"body_short": "body manches courtes", "body_long": "body manches longues"}
CAPTIONS = {**LABELS, "body_short": "Body", "body_long": "Body"}


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


def day_number(value) -> str:
    return "1er" if value.day == 1 else str(value.day)


def long_date(value) -> str:
    return f"{DAYS[value.weekday()]} {day_number(value)} {MONTHS[value.month - 1]}"


def night_dates(evening, morning) -> str:
    if evening.month == morning.month:
        return f"Nuit du {day_number(evening)} au {day_number(morning)} {MONTHS[morning.month - 1]}"
    return (
        f"Nuit du {day_number(evening)} {MONTHS[evening.month - 1]} "
        f"au {day_number(morning)} {MONTHS[morning.month - 1]}"
    )


def updated_at(observed: datetime, now: datetime, zone: ZoneInfo) -> str:
    at = observed.astimezone(zone)
    clock = f"{at.hour} h {at.minute:02d}"
    if at.date() == now.astimezone(zone).date():
        return f"Mis à jour à {clock}"
    return f"Mis à jour le {day_number(at)} {MONTHS[at.month - 1]} à {clock}"


def degrees(value: float) -> str:
    return f"{value:.0f}°"


def sentence(items) -> str:
    """French list with a single conjunction: « A, B et C »."""
    words = [PHRASES.get(item, LABELS[item].lower()) for item in items]
    if not words:
        return ""
    joined = words[0] if len(words) == 1 else f"{', '.join(words[:-1])} et {words[-1]}"
    return joined[0].upper() + joined[1:]


class Page:
    def __init__(self):
        self.image = Image.new("L", (WIDTH, HEIGHT), 255)
        self.draw = ImageDraw.Draw(self.image)

    @staticmethod
    def face(size, rounded=False, bold=False):
        return rounded_font(size, 700 if bold else 600) if rounded else font(size, bold)

    def length(self, value, size, rounded=False, bold=False):
        return self.draw.textlength(value, font=self.face(size, rounded, bold))

    def text(self, x, y, value, size=18, rounded=False, bold=False, fill=0, anchor="ls"):
        """Draw at a baseline (``ls``), or right/centre with ``rs``/``ms``."""
        face = self.face(size, rounded, bold)
        self.draw.text((round(x), round(y)), value, font=face, fill=fill, anchor=anchor)

    def wrap(self, value, width, size, rounded=False):
        face = self.face(size, rounded)
        lines, current = [], ""
        for word in value.split():
            candidate = f"{current} {word}".strip()
            if self.draw.textlength(candidate, font=face) > width and current:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        return lines

    def fit(self, value, width, sizes, max_lines, rounded=False):
        """Largest size whose wrapped text fits; ellipsis only as a last resort."""
        for size in sizes:
            lines = self.wrap(value, width, size, rounded)
            fits = all(self.length(line, size, rounded) <= width for line in lines)
            if len(lines) <= max_lines and fits:
                return size, lines
        size = sizes[-1]
        lines = self.wrap(value, width, size, rounded)
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            last = lines[-1]
            while last and self.length(last + "…", size, rounded) > width:
                last = last[:-1]
            lines[-1] = last.rstrip() + "…"
        return size, lines

    def paragraph(self, x, top, lines, size, rounded=False, leading=1.25, fill=0) -> int:
        """Lines whose first cap height starts near ``top``; returns block height."""
        step = round(size * leading)
        for index, line in enumerate(lines):
            self.text(x, top + round(size * 0.78) + index * step, line, size, rounded, fill=fill)
        return step * (len(lines) - 1) + round(size * 0.95)

    def panel(self, bounds):
        self.draw.rounded_rectangle(bounds, radius=28, outline=0, width=3)

    def heading(self, x, y, title, symbol):
        self.image.paste(marker(symbol, 28), (x, y))
        self.text(x + 38, y + 22, title, 24, rounded=True)

    def dotted(self, left, right, y):
        for x in range(left, right + 1, 6):
            self.draw.ellipse((x - 1, y - 1, x + 1, y + 1), fill=0)

    def garments(self, items, left, y, width, size) -> int:
        """Evenly spaced drawings with one-word captions; returns row height."""
        spacing = width / len(items)
        caption = 15 if spacing >= 96 else 13
        for index, item in enumerate(items):
            center = left + spacing * (index + 0.5)
            self.image.paste(icon(item, size), (round(center - size / 2), y))
            self.text(center, y + size + 20, CAPTIONS[item], caption, anchor="ms")
        return size + 26

    def icon_row(self, items, right, y, size, gap=6):
        """Uncaptioned drawings packed against ``right``; the text names them."""
        x = right - len(items) * size - (len(items) - 1) * gap
        for item in items:
            self.image.paste(icon(item, size), (round(x), round(y)))
            x += size + gap

    def circle(self, cx, cy, value, label, apparent=None):
        self.draw.ellipse(
            (cx - CIRCLE // 2, cy - CIRCLE // 2, cx + CIRCLE // 2, cy + CIRCLE // 2), fill=GREY
        )
        big = degrees(value) if value is not None else "?"
        if apparent is not None:
            self.text(cx, cy + 6, big, 64, rounded=True, bold=True, anchor="ms")
            self.text(cx, cy + 31, label, 16, anchor="ms")
            self.text(cx, cy + 51, f"ressenti {degrees(apparent)}", 15, anchor="ms")
        else:
            self.text(cx, cy + 12, big, 64, rounded=True, bold=True, anchor="ms")
            self.text(cx, cy + 40, label, 16, anchor="ms")

    def banner(self, message) -> int:
        if not message:
            return 0
        self.draw.rectangle((0, 0, WIDTH - 1, BANNER_HEIGHT - 1), fill=0)
        self.text(MARGIN, 23, message, 18, bold=True, fill=255)
        return BANNER_HEIGHT + 4

    def header(self, top, period, subtitle, updated) -> int:
        """Title and context on the left, period and freshness on the right."""
        self.image.paste(marker("star", 26), (MARGIN + 4, top + 22))
        self.text(MARGIN + 40, top + 46, "Habiller bébé", 32, rounded=True, bold=True)
        self.text(MARGIN + 4, top + 72, subtitle, 16, fill=51)
        self.text(WIDTH - MARGIN - 4, top + 44, period, 20, rounded=True, anchor="rs")
        self.text(WIDTH - MARGIN - 4, top + 72, updated, 14, fill=74, anchor="rs")
        return top + 86

    def footnote(self, left, top, width, message) -> int:
        """Dotted rule and one short line (or two) closing a panel."""
        self.dotted(left, left + width, top)
        lines = self.wrap(message, width, 17)[:2]
        return 12 + self.paragraph(left, top + 12, lines, 17, leading=1.3)

    def png(self):
        buffer = io.BytesIO()
        self.image.save(buffer, format="PNG", optimize=True)
        return buffer.getvalue()


def usable(room: Room | None, config: Config, now: datetime) -> bool:
    return bool(room and fresh(room.observed_at, now, config.max_age_minutes))


def columns():
    half = (WIDTH - 2 * MARGIN - GAP) // 2
    return (MARGIN, MARGIN + half), (WIDTH - MARGIN - half, WIDTH - MARGIN)


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


def garment_size(count: int) -> int:
    return {1: 76, 2: 76, 3: 76, 4: 76, 5: 68, 6: 60}.get(count, 54)


def render_day(snapshot: Snapshot, config: Config, now: datetime) -> bytes:
    page = Page()
    zone = ZoneInfo(config.timezone)
    advice = recommend(snapshot, config, now)
    weather = snapshot.weather
    valid_weather = bool(weather and fresh(weather.observed_at, now, config.max_age_minutes))
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
    top = page.header(
        page.banner(banner),
        "Journée",
        f"{config.location[:28]} · {long_date(now.astimezone(zone))}",
        updated_at(snapshot.fetched_at, now, zone),
    )

    # Outdoors: the recommendation leads; its temperature sits right beside it.
    left, right = MARGIN, WIDTH - MARGIN
    inner = left + PAD
    panel_top = top + 14
    page.heading(inner, panel_top + 20, "Dehors", "tree")
    cx, cy = right - 20 - CIRCLE // 2, panel_top + 20 + CIRCLE // 2
    if valid_weather:
        apparent = weather.apparent_temperature
        if apparent is not None and round(apparent) == round(weather.temperature):
            apparent = None
        label = CONDITIONS.get(weather.condition, "à vérifier")
        page.circle(cx, cy, weather.temperature, label, apparent)
    else:
        page.circle(cx, cy, None, "à vérifier")
    advice_text = sentence(advice.outdoor) if advice.outdoor else "Tenue à vérifier"
    text_width = cx - CIRCLE // 2 - 16 - inner
    size, lines = page.fit(advice_text, text_width, (31, 28, 25, 22), 3, rounded=True)
    if len(lines) == 3 and lines[-1].endswith("…"):
        size, lines = page.fit(advice_text, text_width, (20,), 4, rounded=True)
    text_bottom = panel_top + 66 + page.paragraph(inner, panel_top + 66, lines, size, True, 1.14)
    y = max(text_bottom, cy + CIRCLE // 2) + 18
    if advice.outdoor:
        y += page.garments(
            advice.outdoor, left + 16, y, right - left - 32, garment_size(len(advice.outdoor))
        )
        y += 14
    if advice.caution and advice.notes:
        message = advice.notes[0]
    elif snapshot.warnings:
        message = snapshot.warnings[0]
    elif not valid_weather:
        message = "Vérifier la météo avant de choisir la tenue."
    elif weather.forecast_low is not None and weather.forecast_high is not None:
        low, high = round(weather.forecast_low), round(weather.forecast_high)
        span = f"{low}°" if low == high else f"{low} à {high}°"
        message = f"Les {config.forecast_hours} prochaines heures : {span}"
    else:
        message = ""
    if message:
        y += page.footnote(inner, y, right - left - 2 * PAD, message)
    panel_bottom = y + 18
    page.panel((left, panel_top, right, panel_bottom))

    (lx0, lx1), (rx0, rx1) = columns()
    card_top = panel_bottom + GAP
    for x0, x1 in ((lx0, lx1), (rx0, rx1)):
        page.panel((x0, card_top, x1, CONTENT_BOTTOM))
    area_top, area_bottom = card_top + 62, CONTENT_BOTTOM - 18

    # Indoors: temperature with its drawings, then the outfit in plain words.
    page.heading(lx0 + PAD, card_top + 20, "Intérieur", "house")
    width = lx1 - lx0 - 2 * PAD
    room = snapshot.living_room
    words = sentence(advice.indoor) if room_ok and advice.indoor else "Vérifier la pièce."
    lines = page.wrap(words, width, 19)[:3]
    block = 64 + 14 + round(19 * 1.3) * len(lines)
    row = max(area_top, area_top + (area_bottom - area_top - block) // 2)
    if room_ok:
        reading = degrees(room.temperature)
        page.text(lx0 + PAD, row + 56, reading, 64, rounded=True, bold=True)
        taken = page.length(reading, 64, True, True) + 12
        items = advice.indoor
        size = 60 if len(items) <= 2 else 46
        while items and len(items) * (size + 6) - 6 > width - taken and size > 32:
            size -= 4
        page.icon_row(items, lx1 - PAD, row + (64 - size) / 2, size)
    else:
        page.text(lx0 + PAD, row + 46, "À mesurer", 34, rounded=True)
    page.paragraph(lx0 + PAD, row + 78, lines, 19, leading=1.3)

    # To bring: one item gets a large drawing beside its name; several share a row.
    page.heading(rx0 + PAD, card_top + 20, "À emporter", "bag")
    width = rx1 - rx0 - 2 * PAD
    bring = advice.bring
    if len(bring) == 1:
        drawing = 92
        size, lines = page.fit(sentence(bring), width - drawing - 10, (32, 28, 24), 3, True)
        height = round(size * 1.12) * (len(lines) - 1) + round(size * 0.95)
        middle = (area_top + area_bottom) // 2
        page.paragraph(rx0 + PAD, middle - height // 2, lines, size, True, 1.12)
        page.image.paste(icon(bring[0], drawing), (rx1 - PAD - drawing, middle - drawing // 2))
    elif bring:
        size, lines = page.fit(sentence(bring), width, (26, 23, 20), 3, True)
        drawing = 56 if len(bring) <= 3 else 44
        text_height = round(size * 1.12) * (len(lines) - 1) + round(size * 0.95)
        height = text_height + 16 + drawing
        start = max(area_top, (area_top + area_bottom - height) // 2)
        page.paragraph(rx0 + PAD, start, lines, size, True, 1.12)
        span = len(bring) * drawing + (len(bring) - 1) * 10
        page.icon_row(bring, rx0 + PAD + span, start + text_height + 16, drawing, gap=10)
    else:
        size, lines = page.fit("À choisir selon la sortie", width, (24, 21), 3, True)
        height = round(size * 1.12) * (len(lines) - 1) + round(size * 0.95)
        page.paragraph(rx0 + PAD, (area_top + area_bottom - height) // 2, lines, size, True, 1.12)
    return page.png()


def render_night(snapshot: Snapshot, config: Config, now: datetime) -> bytes:
    page = Page()
    zone = ZoneInfo(config.timezone)
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
    local = now.astimezone(zone)
    evening = local.date()
    if local.strftime("%H:%M") < config.day_start:
        evening -= timedelta(days=1)
    observed = room.observed_at if room_ok else snapshot.fetched_at
    top = page.header(
        page.banner(banner),
        "Nuit",
        night_dates(evening, evening + timedelta(days=1)),
        updated_at(observed, now, zone),
    )

    left, right = MARGIN, WIDTH - MARGIN
    inner = left + PAD
    panel_top = top + 14
    page.heading(inner, panel_top + 20, "Cette nuit", "moon")
    cx, cy = right - 20 - CIRCLE // 2, panel_top + 20 + CIRCLE // 2
    page.circle(
        cx, cy, room.temperature if room_ok else None, "bébé" if show_parents else "chambre"
    )
    text_width = cx - CIRCLE // 2 - 16 - inner
    size, lines = page.fit("Gigoteuse à choisir selon sa notice", text_width, (31, 28), 3, True)
    text_bottom = panel_top + 66 + page.paragraph(inner, panel_top + 66, lines, size, True, 1.14)
    page.image.paste(icon("sleep_bag", 89), (inner - 6, text_bottom + 14))
    y = max(text_bottom + 14 + 89, cy + CIRCLE // 2) + 18
    note = "Modèle et TOG à renseigner · choix manuel"
    y += page.footnote(inner, y, right - left - 2 * PAD, note)
    panel_bottom = y + 18
    page.panel((left, panel_top, right, panel_bottom))

    (lx0, lx1), (rx0, rx1) = columns()
    card_top = panel_bottom + GAP
    for x0, x1 in ((lx0, lx1), (rx0, rx1)):
        page.panel((x0, card_top, x1, CONTENT_BOTTOM))
    area_top, area_bottom = card_top + 62, CONTENT_BOTTOM - 18

    def centred(height: int) -> int:
        return max(area_top, (area_top + area_bottom - height) // 2)

    page.heading(lx0 + PAD, card_top + 20, "Vêtements", "moon")
    width = lx1 - lx0 - 2 * PAD
    size, title = page.fit("À choisir selon la gigoteuse", width, (24, 21), 3, True)
    rule = page.wrap("Pas de bonnet ni de couverture libre au lit.", width, 17)[:3]
    tip = page.wrap("Éviter la surchauffe.", width, 17)[:2]
    heights = (
        round(size * 1.14) * (len(title) - 1) + round(size * 0.95),
        round(17 * 1.3) * (len(rule) - 1) + round(17 * 0.95),
        round(17 * 1.3) * (len(tip) - 1) + round(17 * 0.95),
    )
    y = centred(heights[0] + 16 + heights[1] + 10 + heights[2])
    y += page.paragraph(lx0 + PAD, y, title, size, True, 1.14) + 16
    y += page.paragraph(lx0 + PAD, y, rule, 17, leading=1.3) + 10
    page.paragraph(lx0 + PAD, y, tip, 17, leading=1.3)

    rooms = "Les chambres" if show_parents else "La chambre"
    page.heading(rx0 + PAD, card_top + 20, rooms, "house")
    width = rx1 - rx0 - 2 * PAD
    if show_parents:
        y = centred(56 * 2 + 4 + round(17 * 1.3) * 2)
        for label, reading, valid in (("Bébé", room, room_ok), ("Parents", parents, parents_ok)):
            value = f"{reading.temperature:.1f}°C" if valid else "À mesurer"
            page.text(rx0 + PAD, y + 18, f"{label} : {value}", 21, rounded=True)
            if valid:
                at = reading.observed_at.astimezone(zone)
                page.text(rx0 + PAD, y + 40, f"Mesuré à {at.hour} h {at.minute:02d}", 13, fill=51)
            y += 56
        lines = page.wrap("Choisir la pièce où bébé dort, sans moyenner.", width, 17)[:3]
        page.paragraph(rx0 + PAD, y + 4, lines, 17, leading=1.3)
    else:
        reading = degrees(room.temperature) if room_ok else "À mesurer"
        lines = page.wrap("Mesure actuelle, pas une prévision pour la nuit.", width, 19)[:3]
        y = centred(48 + 14 + round(19 * 1.3) * (len(lines) - 1) + 18)
        page.text(rx0 + PAD, y + 46, reading, 52 if room_ok else 34, rounded=True, bold=room_ok)
        page.paragraph(rx0 + PAD, y + 62, lines, 19, leading=1.3)
    return page.png()
