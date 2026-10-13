import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from app.config import Config
from app.models import Room
from app.rules import fresh, recommend
from app.weather import demo_snapshot

NOW = datetime(2026, 10, 12, 8, tzinfo=UTC)


class RulesTests(unittest.TestCase):
    def setUp(self):
        self.config = Config()
        self.snapshot = demo_snapshot(NOW)

    def advice(self, **changes):
        weather = replace(self.snapshot.weather, **changes)
        return recommend(replace(self.snapshot, weather=weather), self.config, NOW)

    def test_demo_uses_room_temperature(self):
        result = recommend(self.snapshot, self.config, NOW)
        self.assertEqual(result.indoor, ("body_long", "trousers"))

    def test_room_never_falls_back_to_target_19(self):
        result = recommend(replace(self.snapshot, living_room=None), self.config, NOW)
        self.assertEqual(result.indoor, ())

    def test_stale_room_removed_independently(self):
        room = Room(19, NOW - timedelta(hours=3))
        result = recommend(replace(self.snapshot, living_room=room), self.config, NOW)
        self.assertFalse(result.indoor)
        self.assertTrue(result.outdoor)

    def test_stale_weather_disables_outdoor_but_not_indoor(self):
        result = self.advice(observed_at=NOW - timedelta(hours=3))
        self.assertFalse(result.outdoor)
        self.assertTrue(result.indoor)
        self.assertTrue(result.caution)

    def test_future_weather_disables_outdoor(self):
        result = self.advice(observed_at=NOW + timedelta(hours=1))
        self.assertFalse(result.outdoor)

    def test_freshness_boundary(self):
        self.assertTrue(fresh(NOW - timedelta(minutes=120), NOW, 120))
        self.assertFalse(fresh(NOW - timedelta(minutes=120, seconds=1), NOW, 120))

    def test_missing_weather(self):
        result = recommend(replace(self.snapshot, weather=None), self.config, NOW)
        self.assertFalse(result.outdoor)
        self.assertTrue(result.caution)

    def test_unknown_condition(self):
        self.assertFalse(self.advice(condition="unknown").outdoor)

    def test_temperature_boundaries(self):
        for temperature, first in [
            (9.9, "body_long"),
            (10, "body_long"),
            (18, "body_long"),
            (22, "body_short"),
            (25, "light_outfit"),
        ]:
            with self.subTest(temperature=temperature):
                result = self.advice(temperature=temperature, apparent_temperature=None)
                self.assertEqual(result.outdoor[0], first)

    def test_air_temperature_used_without_double_wind_penalty(self):
        result = self.advice(temperature=20, apparent_temperature=19, wind_kmh=40)
        self.assertEqual(result.outdoor[0], "body_long")
        self.assertNotIn("cardigan", result.outdoor)
        self.assertIn("rain_shell", result.bring)

    def test_16_degree_baseline_ignores_warmer_apparent_temperature(self):
        for apparent in (None, 16, 18, 22):
            with self.subTest(apparent=apparent):
                result = self.advice(temperature=16, apparent_temperature=apparent)
                self.assertEqual(result.outdoor, ("body_long", "trousers", "cardigan", "socks"))
                self.assertEqual(result.band, "cool")

    def test_sleeves_and_warmth_layer_change_at_separate_boundaries(self):
        for temperature, first, cardigan, band in (
            (17.99, "body_long", True, "cool"),
            (18, "body_long", False, "mild"),
            (21.99, "body_long", False, "mild"),
            (22, "body_short", False, "warm"),
            (24.99, "body_short", False, "warm"),
            (25, "light_outfit", False, "hot"),
        ):
            with self.subTest(temperature=temperature):
                result = self.advice(temperature=temperature, apparent_temperature=None)
                self.assertEqual(result.outdoor[0], first)
                self.assertEqual("cardigan" in result.outdoor, cardigan)
                self.assertEqual(result.band, band)

    def test_outdoor_band_changes_do_not_change_indoor_recommendations(self):
        snapshot = replace(self.snapshot, living_room=Room(17, NOW))
        default = recommend(snapshot, Config(), NOW)
        custom = recommend(snapshot, Config(cool_below=15), NOW)
        self.assertEqual(custom.indoor, default.indoor)

    def test_rain_and_snow_bring_dry_spare_not_extra_insulation(self):
        for condition in ("rainy", "snowy", "snowy-rainy"):
            with self.subTest(condition=condition):
                result = self.advice(condition=condition)
                self.assertIn("spare_clothes", result.bring)
                self.assertNotIn("warm_outerwear", result.outdoor)

    def test_no_rain_probability_is_not_zero(self):
        result = self.advice(
            condition="cloudy", rain_probability=None, forecast_conditions=("cloudy",)
        )
        self.assertNotIn("spare_clothes", result.bring)

    def test_forecast_rain_adds_spare(self):
        result = self.advice(condition="cloudy", rain_probability=70)
        self.assertIn("spare_clothes", result.bring)

    def test_extremes_remove_confident_outfit(self):
        for changes in (
            {"temperature": -1},
            {"temperature": 33},
            {"apparent_temperature": -5},
            {"apparent_temperature": 35},
            {"forecast_low": -2},
            {"forecast_high": 35},
        ):
            with self.subTest(changes=changes):
                self.assertFalse(self.advice(**changes).outdoor)

    def test_forecast_thunderstorm_overrides_clear_current_weather(self):
        result = self.advice(condition="sunny", forecast_conditions=("lightning",))
        self.assertFalse(result.outdoor)

    def test_vigilance_non_green_conservative_override(self):
        for alert in ("Jaune", "Orange", "Rouge"):
            with self.subTest(alert=alert):
                self.assertFalse(self.advice(alert=alert).outdoor)
        self.assertTrue(self.advice(alert="Vert").outdoor)

    def test_sleep_and_manual_products_never_in_day_outfit(self):
        for temperature in (2, 12, 20, 27):
            result = self.advice(temperature=temperature, apparent_temperature=None)
            for item in ("snowsuit", "footmuff", "sleep_bag"):
                self.assertNotIn(item, result.outdoor)
                self.assertNotIn(item, result.indoor)

    def test_cold_baseline_wears_outdoor_coat_not_merely_carries_it(self):
        result = self.advice(temperature=5, apparent_temperature=None)
        self.assertIn("warm_outerwear", result.outdoor)
        self.assertNotIn("warm_outerwear", result.bring)

    def test_indoor_warm_room_is_not_assumed_19(self):
        result = recommend(replace(self.snapshot, living_room=Room(27, NOW)), self.config, NOW)
        self.assertEqual(result.indoor, ("body_short",))

    def test_hot_weather_omits_insulation(self):
        result = self.advice(temperature=27, apparent_temperature=None)
        self.assertNotIn("cardigan", result.outdoor)
        self.assertNotIn("warm_outerwear", result.bring)
        self.assertIn("sun_hat", result.outdoor)


class ConfigTests(unittest.TestCase):
    def test_invalid_bands(self):
        with self.assertRaises(ValueError):
            Config(cold_below=20, cool_below=18)

    def test_nan_band(self):
        with self.assertRaises(ValueError):
            Config(cold_below=float("nan"))

    def test_live_requires_entity(self):
        with self.assertRaises(ValueError):
            Config(demo=False)

    def test_refresh_cannot_spin(self):
        with self.assertRaises(ValueError):
            Config(refresh_seconds=0)


if __name__ == "__main__":
    unittest.main()
