import tempfile
import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from PIL import ImageDraw

from app.config import Config
from app.models import Room
from app.render import page_for, render
from app.server import Display
from app.weather import HAClient, demo_snapshot

NOW = datetime(2026, 10, 12, 18, tzinfo=UTC)


def rendered_text(snapshot, now=NOW, page="night"):
    messages = []
    original = ImageDraw.ImageDraw.text

    def capture(self, xy, text, *args, **kwargs):
        messages.append(text)
        return original(self, xy, text, *args, **kwargs)

    with patch.object(ImageDraw.ImageDraw, "text", new=capture):
        render(snapshot, Config(), now, page=page)
    return " ".join(messages)


class PageTests(unittest.TestCase):
    def test_day_night_boundaries_in_paris(self):
        for hour, minute, expected in [
            (4, 59, "night"),
            (5, 0, "day"),
            (16, 59, "day"),
            (17, 0, "night"),
        ]:
            with self.subTest(hour=hour, minute=minute):
                now = NOW.replace(hour=hour, minute=minute)
                self.assertEqual(page_for(Config(), now), expected)

    def test_schedule_uses_dst_not_fixed_utc_offset(self):
        summer = datetime(2026, 7, 1, 17, tzinfo=UTC)
        winter = datetime(2026, 12, 1, 17, tzinfo=UTC)
        self.assertEqual(page_for(Config(), summer), "night")
        self.assertEqual(page_for(Config(), winter), "day")

    def test_custom_switch_times(self):
        self.assertEqual(page_for(Config(night_start="21:00"), NOW), "day")

    def test_invalid_schedule(self):
        for options in (
            {"day_start": "25:00"},
            {"night_start": "7:00"},
            {"day_start": "19:00", "night_start": "07:00"},
        ):
            with self.subTest(options=options), self.assertRaises(ValueError):
                Config(**options)

    def test_day_has_no_sleep_recommendations(self):
        text = rendered_text(demo_snapshot(NOW), page="day")
        self.assertIn("DÉMONSTRATION — DONNÉES FICTIVES", text)
        self.assertIn("Journée", text)
        self.assertNotIn("gigoteuse", text.lower())
        self.assertNotIn("chambre", text.lower())
        self.assertNotIn("Voiture", text)
        self.assertNotIn("Portage", text)
        self.assertNotIn("poussette", text)
        self.assertIn("Body manches longues, pantalon, gilet et chaussettes", text)
        self.assertIn("Les 4 prochaines heures : 10 à 15°", text)

    def test_night_has_no_weather_or_transport(self):
        text = rendered_text(demo_snapshot(NOW))
        self.assertIn("DÉMONSTRATION — CHAMBRE FICTIVE", text)
        self.assertIn("Nuit", text)
        self.assertIn("19° chambre", text)
        self.assertNotIn("Pluie", text)
        self.assertNotIn("Voiture", text)
        self.assertIn("choix manuel", text)
        self.assertIn("Pas de bonnet ni de couverture libre au lit.", text)

    def test_full_cold_worn_ensemble_is_not_truncated(self):
        snapshot = demo_snapshot(NOW)
        snapshot = replace(
            snapshot,
            weather=replace(snapshot.weather, temperature=5, apparent_temperature=7),
        )
        text = rendered_text(snapshot, page="day")
        for garment in ("gilet", "chaussettes", "manteau", "bonnet", "moufles"):
            self.assertIn(garment, text)
        self.assertNotIn("…", text)

    def test_carried_rain_and_wind_layers_are_not_truncated(self):
        snapshot = demo_snapshot(NOW)
        snapshot = replace(snapshot, weather=replace(snapshot.weather, wind_kmh=40))
        text = rendered_text(snapshot, page="day")
        self.assertIn("Veste légère, change sec et coupe-pluie", text)
        self.assertNotIn("…", text)

    def test_night_depends_only_on_bedroom(self):
        snapshot = demo_snapshot(NOW)
        other = replace(snapshot, weather=None, living_room=Room(32, NOW))
        self.assertEqual(
            render(snapshot, Config(), NOW, "night"), render(other, Config(), NOW, "night")
        )

    def test_stale_bedroom_is_not_shown_as_current(self):
        snapshot = replace(demo_snapshot(NOW), bedroom=Room(19, NOW - timedelta(hours=3)))
        text = rendered_text(snapshot)
        self.assertIn("TEMPÉRATURE ABSENTE OU PÉRIMÉE", text)
        self.assertIn("À mesurer", text)
        self.assertNotIn("19°", text)

    def test_night_date_spans_months(self):
        now = datetime(2026, 10, 31, 22, tzinfo=UTC)
        text = rendered_text(demo_snapshot(now), now)
        self.assertIn("Nuit du 31 octobre au 1er novembre", text)

    def test_apparent_temperature_shown_only_when_different(self):
        snapshot = demo_snapshot(NOW)
        self.assertIn("ressenti 10°", rendered_text(snapshot, page="day"))
        same = replace(snapshot, weather=replace(snapshot.weather, apparent_temperature=12.2))
        self.assertNotIn("ressenti", rendered_text(same, page="day"))

    def test_update_time_moves_to_header_without_footer_tips(self):
        text = rendered_text(demo_snapshot(NOW), page="day")
        self.assertIn("Mis à jour à 20 h 00", text)
        self.assertNotIn("heure de Paris", text)
        self.assertNotIn("Vérifier la nuque", text)
        self.assertNotIn("+", text)

    def test_night_date_spans_midnight(self):
        now = datetime(2026, 10, 12, 23, tzinfo=UTC)
        text = rendered_text(demo_snapshot(now), now)
        self.assertIn("Nuit du 12 au 13 octobre", text)

    def test_auto_switch_changes_etag_without_new_weather(self):
        before = NOW.replace(hour=16, minute=59)
        after = NOW.replace(hour=17, minute=0)
        with tempfile.TemporaryDirectory() as directory:
            display = Display(Config(cache_dir=directory))
            display.refresh(before)
            _, first = display.image(before)
            _, second = display.image(after)
        self.assertNotEqual(first, second)

    def test_forced_night_cache_date_changes_at_morning_boundary(self):
        before = NOW.replace(hour=4, minute=59)
        after = NOW.replace(hour=5, minute=0)
        with tempfile.TemporaryDirectory() as directory:
            display = Display(Config(cache_dir=directory))
            display.refresh(before)
            _, first = display.image(before, "night")
            _, second = display.image(after, "night")
        self.assertNotEqual(first, second)

    def test_bedroom_fetched_even_if_weather_unavailable(self):
        client = HAClient(
            Config(demo=False, weather_entity="weather.home", bedroom_entity="sensor.bedroom")
        )

        def state(entity):
            if entity == "weather.home":
                raise ValueError("Weather provider unavailable")
            return {
                "state": "19",
                "last_updated": NOW.isoformat(),
                "attributes": {"unit_of_measurement": "°C"},
            }

        with patch.object(client, "state", side_effect=state):
            snapshot = client.fetch(NOW)
        self.assertIsNone(snapshot.weather)
        self.assertEqual(snapshot.bedroom.temperature, 19)


if __name__ == "__main__":
    unittest.main()
