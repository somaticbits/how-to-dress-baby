import unittest
from dataclasses import replace
from datetime import UTC, datetime
from unittest.mock import patch

from PIL import ImageDraw

from app.config import Config
from app.models import Room
from app.render import BATTERY_TOP, battery_notice, render
from app.weather import demo_snapshot

NOW = datetime(2026, 10, 13, 8, tzinfo=UTC)


class FooterLayoutTests(unittest.TestCase):
    def test_footer_text_has_separate_rows_and_clear_battery_area(self):
        sample = replace(demo_snapshot(NOW), parents_bedroom=Room(19.3, NOW))
        boxes = []
        original = ImageDraw.ImageDraw.text

        def capture(draw, xy, text, *args, **kwargs):
            if 694 <= xy[1] < BATTERY_TOP:
                boxes.append(draw.textbbox(xy, text, font=kwargs["font"]))
            return original(draw, xy, text, *args, **kwargs)

        for page in ("day", "night"):
            for snapshot in (
                sample,
                replace(sample, demo=False),
                replace(sample, weather=None, living_room=None, bedroom=None),
            ):
                for level, charging in ((None, None), (0, False), (15, False), (15, True)):
                    with self.subTest(
                        page=page, demo=snapshot.demo, level=level, charging=charging
                    ):
                        boxes.clear()
                        with patch.object(ImageDraw.ImageDraw, "text", new=capture):
                            content = render(snapshot, Config(), NOW, page)
                            battery_notice(content, level, charging)
                        self.assertEqual(len(boxes), 3 if page == "day" else 2)
                        for left, top, right, bottom in boxes:
                            self.assertGreater(top, 694)
                            self.assertGreaterEqual(left, 16)
                            self.assertLessEqual(right, 584)
                            self.assertLessEqual(bottom + 3, BATTERY_TOP)
                        for first, second in zip(boxes, boxes[1:], strict=False):
                            self.assertLessEqual(first[3] + 3, second[1])


if __name__ == "__main__":
    unittest.main()
