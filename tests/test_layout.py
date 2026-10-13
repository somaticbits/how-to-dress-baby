import unittest
from dataclasses import replace
from datetime import UTC, datetime
from unittest.mock import patch

from PIL import ImageDraw

from app.config import Config
from app.models import Room
from app.render import BATTERY_TOP, CONTENT_BOTTOM, battery_notice, render
from app.weather import demo_snapshot

NOW = datetime(2026, 10, 13, 8, tzinfo=UTC)


class LayoutTests(unittest.TestCase):
    def test_text_stays_inside_the_page_and_clear_of_the_battery_band(self):
        sample = replace(demo_snapshot(NOW), parents_bedroom=Room(19.3, NOW))
        cold = replace(sample, weather=replace(sample.weather, temperature=5))
        windy = replace(sample, weather=replace(sample.weather, wind_kmh=40))
        boxes = []
        original = ImageDraw.ImageDraw.text

        def capture(draw, xy, text, *args, **kwargs):
            if not text.startswith("Kindle"):
                anchor = kwargs.get("anchor")
                boxes.append(draw.textbbox(xy, text, font=kwargs["font"], anchor=anchor))
            return original(draw, xy, text, *args, **kwargs)

        for page in ("day", "night"):
            for snapshot in (
                sample,
                cold,
                windy,
                replace(sample, demo=False),
                replace(sample, weather=None, living_room=None, bedroom=None),
            ):
                for level, charging in ((None, None), (0, False), (15, True)):
                    with self.subTest(page=page, demo=snapshot.demo, level=level):
                        boxes.clear()
                        with patch.object(ImageDraw.ImageDraw, "text", new=capture):
                            content = render(snapshot, Config(), NOW, page)
                            battery_notice(content, level, charging)
                        self.assertTrue(boxes)
                        for left, top, right, bottom in boxes:
                            self.assertGreaterEqual(left, 16)
                            self.assertLessEqual(right, 584)
                            self.assertGreaterEqual(top, 0)
                            self.assertLessEqual(bottom, CONTENT_BOTTOM)
        self.assertLess(CONTENT_BOTTOM, BATTERY_TOP)


if __name__ == "__main__":
    unittest.main()
