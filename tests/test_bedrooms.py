import json
import tempfile
import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from PIL import ImageDraw

from app.config import Config
from app.models import Room
from app.render import render
from app.server import Display, decode, encode
from app.weather import HAClient, demo_snapshot

NOW = datetime(2026, 10, 12, 18, tzinfo=UTC)


class BedroomTests(unittest.TestCase):
    def capture(self, snapshot, config=None):
        config = config or Config()
        messages = []
        original = ImageDraw.ImageDraw.text

        def record(draw, xy, text, *args, **kwargs):
            messages.append(text)
            return original(draw, xy, text, *args, **kwargs)

        with patch.object(ImageDraw.ImageDraw, "text", new=record):
            render(snapshot, config, NOW, "night")
        return " ".join(messages)

    def test_both_rooms_are_labelled_without_averaging(self):
        snapshot = replace(demo_snapshot(NOW), parents_bedroom=Room(22, NOW))
        text = self.capture(snapshot)
        self.assertIn("Bébé : 19.0°C", text)
        self.assertIn("Parents : 22.0°C", text)
        self.assertNotIn("20.5°C", text)

    def test_missing_configured_parent_sensor_is_explicit(self):
        text = self.capture(demo_snapshot(NOW), Config(parents_bedroom_entity="sensor.parents"))
        self.assertIn("Parents : À mesurer", text)

    def test_stale_parent_sensor_does_not_hide_fresh_baby_sensor(self):
        snapshot = replace(demo_snapshot(NOW), parents_bedroom=Room(22, NOW - timedelta(hours=3)))
        text = self.capture(snapshot)
        self.assertIn("Bébé : 19.0°C", text)
        self.assertIn("Parents : À mesurer", text)
        self.assertNotIn("22.0°C", text)

    def test_cache_round_trip_and_backward_compatibility(self):
        snapshot = replace(demo_snapshot(NOW), parents_bedroom=Room(22, NOW))
        self.assertEqual(decode(encode(snapshot)), snapshot)
        old = json.loads(encode(snapshot))
        del old["parents_bedroom"]
        self.assertIsNone(decode(json.dumps(old).encode()).parents_bedroom)

    def test_parent_freshness_invalidates_cached_image(self):
        with tempfile.TemporaryDirectory() as directory:
            display = Display(Config(cache_dir=directory))
            display.snapshot = replace(
                demo_snapshot(NOW), parents_bedroom=Room(22, NOW - timedelta(minutes=119))
            )
            _, first = display.image(NOW, "night")
            _, second = display.image(NOW + timedelta(minutes=2), "night")
            self.assertNotEqual(first, second)

    def test_ha_fetches_both_bedrooms_independently(self):
        config = Config(bedroom_entity="sensor.baby", parents_bedroom_entity="sensor.parents")
        client = HAClient(config)
        with (
            patch.object(client, "room", side_effect=[None, Room(19, NOW), Room(22, NOW)]),
            patch.object(client, "fetch_weather", return_value=None),
        ):
            snapshot = client.fetch(NOW)
        self.assertEqual(snapshot.bedroom.temperature, 19)
        self.assertEqual(snapshot.parents_bedroom.temperature, 22)


if __name__ == "__main__":
    unittest.main()
