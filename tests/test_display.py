import io
import json
import tempfile
import threading
import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from app.artwork import LABELS, icon
from app.config import Config
from app.render import battery_notice, font, render
from app.server import Display, decode, encode, handler_for
from app.weather import demo_snapshot

NOW = datetime(2026, 10, 12, 8, tzinfo=UTC)


class DisplayTests(unittest.TestCase):
    def test_low_battery_notice_preserves_kindles_png_format(self):
        base = render(demo_snapshot(NOW), Config(), NOW)
        low = battery_notice(base, 15, False)
        self.assertNotEqual(base, low)
        with Image.open(io.BytesIO(low)) as image:
            self.assertEqual(image.size, (600, 800))
            self.assertEqual(image.mode, "L")
            self.assertEqual(image.getpixel((300, 763)), 0)
            bar = image.crop((16, 761, 585, 799))
            dark_pixels = sum(count for count, shade in bar.getcolors(256) if shade < 64)
            self.assertGreater(dark_pixels, bar.width * bar.height // 2)

    def test_no_battery_notice_for_charging_normal_or_unknown_readings(self):
        base = render(demo_snapshot(NOW), Config(), NOW)
        for level, charging in (
            (15, True),
            (16, False),
            (None, None),
            (-1, False),
            (101, False),
            (True, False),
        ):
            with self.subTest(level=level, charging=charging):
                self.assertEqual(battery_notice(base, level, charging), base)

    def test_native_grayscale_png(self):
        data = render(demo_snapshot(NOW), Config(), NOW)
        with Image.open(io.BytesIO(data)) as image:
            self.assertEqual(image.size, (600, 800))
            self.assertEqual(image.mode, "L")
            self.assertEqual(image.format, "PNG")
            self.assertNotIn("icc_profile", image.info)

    def test_render_deterministic(self):
        snapshot = demo_snapshot(NOW)
        self.assertEqual(render(snapshot, Config(), NOW), render(snapshot, Config(), NOW))

    def test_french_font_characters_are_not_missing_glyphs(self):
        regular = font(20)
        missing = bytes(regular.getmask("\u0378"))
        for character in "éèêàçÉÀ—–’":
            with self.subTest(character=character):
                self.assertNotEqual(bytes(regular.getmask(character)), missing)

    def test_every_garment_has_nonempty_artwork(self):
        for garment in LABELS:
            with self.subTest(garment=garment):
                image = icon(garment)
                self.assertEqual(image.size, (64, 64))
                self.assertLess(image.getextrema()[0], 255)

    def test_cache_roundtrip(self):
        snapshot = demo_snapshot(NOW)
        self.assertEqual(decode(encode(snapshot)), snapshot)

    def test_expiration_changes_image_without_fetch(self):
        with tempfile.TemporaryDirectory() as directory:
            display = Display(Config(cache_dir=directory))
            display.refresh(NOW)
            before, before_etag = display.image(NOW)
            after, after_etag = display.image(NOW + timedelta(hours=3))
        self.assertNotEqual(before, after)
        self.assertNotEqual(before_etag, after_etag)

    def test_cached_demo_never_becomes_live(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "snapshot.json").write_bytes(encode(demo_snapshot(NOW)))
            display = Display(
                Config(demo=False, weather_entity="weather.home", cache_dir=directory)
            )
            self.assertIsNone(display.snapshot.weather)

    def test_live_cache_survives_restart_and_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            snapshot = replace(demo_snapshot(NOW), demo=False)
            Path(directory, "snapshot.json").write_bytes(encode(snapshot))
            display = Display(
                Config(demo=False, weather_entity="weather.home", cache_dir=directory)
            )
            with patch.object(display.client, "fetch", side_effect=RuntimeError("secret")):
                display.refresh(NOW)
            self.assertEqual(display.snapshot.weather, snapshot.weather)
            self.assertTrue(display.error)
            self.assertNotIn("secret", str(display.status()))

    def test_corrupt_cache_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "snapshot.json").write_text("not json")
            display = Display(
                Config(demo=False, weather_entity="weather.home", cache_dir=directory)
            )
            self.assertIsNone(display.snapshot.weather)

    def test_dst_does_not_break_render(self):
        for date in (datetime(2026, 3, 29, 1, tzinfo=UTC), datetime(2026, 10, 25, 1, tzinfo=UTC)):
            with self.subTest(date=date):
                self.assertTrue(render(demo_snapshot(date), Config(), date))


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.display = Display(Config(cache_dir=self.directory.name))
        self.display.refresh()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(self.display))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.connection = HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)

    def tearDown(self):
        self.connection.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.directory.cleanup()

    def test_png_and_conditional_get(self):
        self.connection.request("GET", "/display.png?batteryLevel=80")
        response = self.connection.getresponse()
        self.assertEqual(response.status, 200)
        self.assertEqual(response.getheader("Content-Type"), "image/png")
        etag = response.getheader("ETag")
        self.assertTrue(response.read().startswith(b"\x89PNG"))
        self.connection.request("GET", "/display.png", headers={"If-None-Match": etag})
        response = self.connection.getresponse()
        self.assertEqual(response.status, 304)
        self.assertEqual(response.read(), b"")

    def test_head(self):
        self.connection.request("HEAD", "/display.png")
        response = self.connection.getresponse()
        self.assertEqual(response.status, 200)
        self.assertGreater(int(response.getheader("Content-Length")), 0)
        self.assertEqual(response.read(), b"")

    def test_separate_day_and_night_endpoints(self):
        images = []
        for page in ("day", "night"):
            self.connection.request("GET", f"/{page}.png")
            response = self.connection.getresponse()
            self.assertEqual(response.status, 200)
            images.append(response.read())
        self.assertNotEqual(*images)

    def test_battery_notice_etag_and_no_cross_request_leak(self):
        results = []
        for query in (
            "",
            "?batteryLevel=15&isCharging=No",
            "?batteryLevel=15&isCharging=Yes",
            "?batteryLevel=invalid",
            "?batteryLevel=999",
            "",
        ):
            self.connection.request("GET", "/night.png" + query)
            response = self.connection.getresponse()
            self.assertEqual(response.status, 200)
            results.append((response.read(), response.getheader("ETag")))
        self.assertNotEqual(results[0], results[1])
        for result in results[2:]:
            self.assertEqual(results[0], result)

    def test_low_battery_conditional_get(self):
        url = "/day.png?batteryLevel=0&isCharging=false"
        self.connection.request("GET", url)
        response = self.connection.getresponse()
        etag = response.getheader("ETag")
        response.read()
        self.connection.request("GET", url, headers={"If-None-Match": etag})
        response = self.connection.getresponse()
        self.assertEqual(response.status, 304)
        self.assertEqual(response.read(), b"")

    def test_health_exposes_no_credentials(self):
        self.connection.request("GET", "/health")
        response = self.connection.getresponse()
        self.assertEqual(response.status, 200)
        value = json.loads(response.read())
        self.assertEqual(value["status"], "demo")
        self.assertEqual(value["version"], "0.3.0")
        self.assertEqual(value["decision"]["basis"], "air_temperature")
        self.assertEqual(value["decision"]["band"], "cool")
        self.assertNotIn("token", str(value))

    def test_unknown_path(self):
        self.connection.request("GET", "/config")
        response = self.connection.getresponse()
        self.assertEqual(response.status, 404)
        response.read()

    def test_degraded_live_health_returns_503(self):
        self.display.config = replace(
            self.display.config, demo=False, weather_entity="weather.home"
        )
        self.display.error = True
        self.connection.request("GET", "/health")
        response = self.connection.getresponse()
        self.assertEqual(response.status, 503)
        self.assertEqual(json.loads(response.read())["status"], "degraded")


if __name__ == "__main__":
    unittest.main()
