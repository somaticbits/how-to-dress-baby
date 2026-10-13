"""Original vector-like garment drawings, composed locally using Pillow.

Every catalogue entry has an illustration; none uses a downloaded photograph,
remote URL, generative model, or third-party icon pack.
"""

import math

from PIL import Image, ImageDraw

GREY = 232


class RoundedDraw:
    """Supersampled, rounded strokes in a 100-unit drawing space."""

    def __init__(self, image: Image.Image, stroke: float):
        self.draw = ImageDraw.Draw(image)
        self.stroke = max(1, round(stroke * 4))

    def __getattr__(self, name):
        method = getattr(self.draw, name)

        def scaled(xy, *args, **kwargs):
            points = (
                [(x * 4, y * 4) for x, y in xy]
                if isinstance(xy[0], tuple)
                else tuple(value * 4 for value in xy)
            )
            if "width" in kwargs:
                kwargs["width"] = self.stroke
            if "radius" in kwargs:
                kwargs["radius"] *= 4
            return method(points, *args, **kwargs)

        return scaled

    def line(self, points, fill=0, width=3):
        scaled = [(x * 4, y * 4) for x, y in points]
        self.draw.line(scaled, fill=fill, width=self.stroke, joint="curve")
        radius = self.stroke / 2
        for x, y in scaled:
            self.draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=fill)

    def polygon(self, points, fill=GREY, outline=0, width=3):
        self.draw.polygon([(x * 4, y * 4) for x, y in points], fill=fill)
        self.line([*points, points[0]], fill=outline)


def star_points(cx: float, cy: float, radius: float) -> list[tuple[float, float]]:
    return [
        (
            cx
            + math.cos(-math.pi / 2 + index * math.pi / 5)
            * radius
            * (1 if index % 2 == 0 else 0.45),
            cy
            + math.sin(-math.pi / 2 + index * math.pi / 5)
            * radius
            * (1 if index % 2 == 0 else 0.45),
        )
        for index in range(10)
    ]


LABELS = {
    "body_short": "Body court",
    "body_long": "Body long",
    "sleepsuit": "Pyjama",
    "top": "Haut léger",
    "trousers": "Pantalon",
    "shorts": "Short",
    "cardigan": "Gilet",
    "sweater": "Pull",
    "fleece": "Polaire fine",
    "light_jacket": "Veste légère",
    "warm_outerwear": "Manteau",
    "snowsuit": "Combinaison",
    "rain_shell": "Coupe-pluie",
    "socks": "Chaussettes",
    "booties": "Chaussons",
    "mittens": "Moufles",
    "warm_hat": "Bonnet",
    "sun_hat": "Chapeau",
    "light_outfit": "Tenue légère",
    "spare_clothes": "Change sec",
    "sleep_bag": "Gigoteuse",
    "footmuff": "Chancelière",
}


def icon(item: str, size: int = 64) -> Image.Image:
    if item not in LABELS:
        raise ValueError(f"Unknown garment: {item}")
    image = Image.new("L", (400, 400), 255)
    draw = RoundedDraw(image, 280 / size)

    def polygon(points: list[tuple[int, int]]) -> None:
        draw.polygon(points, fill=GREY, outline=0, width=3)

    def line(points: list[tuple[int, int]]) -> None:
        draw.line(points, fill=0, width=3)

    if item in {"body_short", "body_long"}:
        sleeve = 38 if item == "body_short" else 60
        polygon(
            [
                (34, 15),
                (20, 24),
                (9, sleeve),
                (25, sleeve + 4),
                (32, 38),
                (32, 68),
                (40, 87),
                (60, 87),
                (68, 68),
                (68, 38),
                (75, sleeve + 4),
                (91, sleeve),
                (80, 24),
                (66, 15),
            ]
        )
        draw.arc((35, 5, 65, 28), 0, 180, fill=0, width=3)
        line([(32, 68), (44, 76), (56, 76), (68, 68)])
        for x in (44, 50, 56):
            draw.ellipse((x - 1, 80, x + 1, 82), fill=0)
        draw.polygon([(44, 44), (47, 41), (50, 44), (53, 41), (56, 44), (50, 51)], fill=0)
    elif item in {"trousers", "shorts"}:
        bottom = 90 if item == "trousers" else 65
        polygon(
            [(24, 18), (76, 18), (82, bottom), (56, bottom), (50, 46), (44, bottom), (18, bottom)]
        )
        line([(25, 28), (75, 28)])
    elif item in {"sleepsuit", "snowsuit"}:
        polygon(
            [
                (34, 12),
                (18, 22),
                (6, 54),
                (21, 60),
                (29, 39),
                (28, 89),
                (44, 89),
                (50, 60),
                (56, 89),
                (72, 89),
                (71, 39),
                (79, 60),
                (94, 54),
                (82, 22),
                (66, 12),
            ]
        )
        line([(50, 18), (50, 60), (33, 88)])
        if item == "snowsuit":
            draw.ellipse((26, 3, 40, 17), fill=GREY, outline=0, width=3)
            draw.ellipse((60, 3, 74, 17), fill=GREY, outline=0, width=3)
            for y in (32, 44, 56):
                line([(31, y), (69, y)])
        else:
            for y in (31, 42, 53):
                draw.ellipse((46, y - 1, 49, y + 2), fill=0)
    elif item in {
        "cardigan",
        "sweater",
        "fleece",
        "light_jacket",
        "warm_outerwear",
        "rain_shell",
        "top",
        "light_outfit",
        "spare_clothes",
    }:
        short = item in {"top", "light_outfit"}
        sleeve = 42 if short else 64
        polygon(
            [
                (35, 15),
                (20, 24),
                (7, sleeve),
                (23, sleeve + 5),
                (31, 41),
                (31, 83),
                (69, 83),
                (69, 41),
                (77, sleeve + 5),
                (93, sleeve),
                (80, 24),
                (65, 15),
            ]
        )
        draw.arc((35, 6, 65, 30), 0, 180, fill=0, width=3)
        if item not in {"top", "sweater", "light_outfit", "spare_clothes"}:
            line([(50, 28), (50, 82)])
        if item == "warm_outerwear":
            for y in (43, 58, 73):
                line([(32, y), (68, y)])
        if item == "rain_shell":
            draw.arc((32, 2, 68, 37), 180, 360, fill=0, width=3)
        if item == "spare_clothes":
            draw.rounded_rectangle((61, 60, 95, 94), radius=4, fill=255, outline=0, width=3)
            line([(68, 76), (88, 76)])
            line([(78, 66), (78, 86)])
    elif item == "socks":
        for shift in (0, 39):
            polygon(
                [
                    (12 + shift, 18),
                    (37 + shift, 18),
                    (37 + shift, 57),
                    (48 + shift, 69),
                    (46 + shift, 82),
                    (18 + shift, 82),
                    (12 + shift, 72),
                ]
            )
            line([(13 + shift, 29), (36 + shift, 29)])
    elif item == "booties":
        for shift in (0, 42):
            draw.rounded_rectangle(
                (8 + shift, 44, 46 + shift, 78), radius=12, fill=GREY, outline=0, width=3
            )
            draw.rectangle((12 + shift, 27, 34 + shift, 53), fill=GREY, outline=0, width=3)
    elif item == "mittens":
        for shift in (0, 43):
            draw.rounded_rectangle(
                (9 + shift, 18, 38 + shift, 74), radius=14, fill=GREY, outline=0, width=3
            )
            draw.ellipse((30 + shift, 42, 46 + shift, 65), fill=GREY, outline=0, width=3)
            draw.rectangle((12 + shift, 71, 35 + shift, 83), fill=GREY, outline=0, width=3)
            draw.polygon(
                [
                    (17 + shift, 43),
                    (20 + shift, 40),
                    (23 + shift, 43),
                    (26 + shift, 40),
                    (29 + shift, 43),
                    (23 + shift, 51),
                ],
                fill=0,
            )
    elif item == "warm_hat":
        draw.pieslice((16, 23, 84, 96), start=180, end=360, fill=GREY, outline=0, width=3)
        draw.rounded_rectangle((13, 58, 87, 76), radius=4, fill=GREY, outline=0, width=3)
        draw.ellipse((43, 12, 57, 26), fill=GREY, outline=0, width=3)
    elif item == "sun_hat":
        polygon([(31, 26), (69, 26), (78, 63), (22, 63)])
        draw.ellipse((7, 56, 93, 78), fill=GREY, outline=0, width=3)
        line([(24, 56), (76, 56)])
    elif item in {"sleep_bag", "footmuff"}:
        draw.rounded_rectangle((23, 13, 77, 91), radius=15, fill=GREY, outline=0, width=3)
        if item == "sleep_bag":
            draw.rectangle((39, 10, 61, 25), fill=255)
            draw.arc((39, 15, 61, 35), 0, 180, fill=0, width=3)
            line([(50, 35), (50, 80)])
            draw.polygon(star_points(61, 48, 7), fill=0)
        else:
            draw.arc((27, 25, 73, 50), 0, 180, fill=0, width=3)
            for y in (57, 70, 83):
                line([(26, y), (74, y)])
    return image.resize((size, size), Image.Resampling.LANCZOS)


def marker(kind: str, size: int = 30) -> Image.Image:
    image = Image.new("L", (400, 400), 255)
    draw = RoundedDraw(image, 280 / size)
    if kind == "tree":
        draw.rounded_rectangle((43, 55, 57, 93), radius=4, fill=GREY, outline=0, width=3)
        for bounds in ((15, 26, 65, 74), (36, 26, 86, 74), (26, 5, 76, 55)):
            draw.ellipse(bounds, fill=GREY, outline=0, width=3)
    elif kind == "house":
        draw.rounded_rectangle((22, 38, 78, 90), radius=8, fill=GREY, outline=0, width=3)
        draw.polygon([(12, 42), (50, 10), (88, 42)], fill=GREY, outline=0, width=3)
        draw.rounded_rectangle((42, 60, 59, 90), radius=4, fill=255, outline=0, width=3)
    elif kind == "moon":
        draw.ellipse((12, 10, 83, 88), fill=GREY, outline=0, width=3)
        draw.ellipse((37, 1, 94, 66), fill=255)
        draw.polygon(star_points(77, 22, 14), fill=0)
    elif kind == "star":
        draw.polygon(star_points(50, 50, 40), fill=0)
    elif kind == "bag":
        draw.rounded_rectangle((21, 32, 79, 89), radius=12, fill=GREY, outline=0, width=3)
        draw.arc((35, 12, 65, 52), start=180, end=360, fill=0, width=3)
    else:
        raise ValueError(f"Unknown marker: {kind}")
    return image.resize((size, size), Image.Resampling.LANCZOS)
