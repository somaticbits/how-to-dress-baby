import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from PIL import ImageDraw

from app.config import Config
from app.messages import DAY_MESSAGES, NIGHT_MESSAGES, greeting
from app.render import Page, render
from app.weather import demo_snapshot

NOW = datetime(2026, 10, 13, 8, tzinfo=UTC)


class MessageTests(unittest.TestCase):
    def test_fifty_unique_personalised_messages(self):
        messages = DAY_MESSAGES + NIGHT_MESSAGES
        self.assertEqual(len(messages), 50)
        self.assertEqual(len(set(messages)), 50)
        self.assertTrue(all(message.count("{name}") == 1 for message in messages))

    def test_name_and_blank_fallback(self):
        self.assertIn("Éloïse", greeting(Config(baby_name=" Éloïse "), NOW, "day"))
        self.assertIn("bébé", greeting(Config(baby_name="  "), NOW, "day"))

    def test_daily_rotation_covers_each_set(self):
        for page in ("day", "night"):
            messages = {greeting(Config(), NOW + timedelta(days=i), page) for i in range(25)}
            self.assertEqual(len(messages), 25)
            self.assertEqual(
                greeting(Config(), NOW, page), greeting(Config(), NOW.replace(hour=9), page)
            )

    def test_night_stable_across_midnight(self):
        evening = NOW.replace(hour=21)
        morning = (NOW + timedelta(days=1)).replace(hour=3)
        self.assertEqual(greeting(Config(), evening, "night"), greeting(Config(), morning, "night"))

    def test_invalid_names(self):
        for name in (None, 123, "x" * 41, "a\nb", "a\tb", "a\x00b"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                Config(baby_name=name)

    def test_every_greeting_fits_header_with_long_name(self):
        page = Page()
        boxes = []
        original = ImageDraw.ImageDraw.text

        def capture(draw, xy, text, *args, **kwargs):
            boxes.append(draw.textbbox(xy, text, font=kwargs["font"], anchor=kwargs.get("anchor")))
            return original(draw, xy, text, *args, **kwargs)

        for template in DAY_MESSAGES + NIGHT_MESSAGES:
            with patch.object(ImageDraw.ImageDraw, "text", new=capture):
                boxes.clear()
                page.header(
                    36,
                    "Journée",
                    "Chez nous",
                    "Mis à jour à 10 h 00",
                    template.format(name="W" * 40),
                )
            left, top, right, bottom = boxes[0]
            self.assertGreaterEqual(left, 64)
            self.assertLessEqual(right, 454)
            self.assertLessEqual(bottom, 90)

    def test_render_uses_personalised_greeting(self):
        config = Config(baby_name="Camille")
        texts = []
        original = ImageDraw.ImageDraw.text

        def capture(draw, xy, text, *args, **kwargs):
            texts.append(text)
            return original(draw, xy, text, *args, **kwargs)

        with patch.object(ImageDraw.ImageDraw, "text", new=capture):
            render(replace(demo_snapshot(NOW), demo=False), config, NOW, "day")
        self.assertIn(greeting(config, NOW, "day"), texts)
        self.assertNotIn("Habiller bébé", texts)
