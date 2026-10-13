import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from urllib.error import URLError

from app.config import Config
from app.weather import HAClient, celsius, number, timestamp, wind_kmh

NOW = datetime(2026, 10, 12, 8, tzinfo=UTC)


class WeatherTests(unittest.TestCase):
    def test_normalize_temperature(self):
        self.assertEqual(celsius(68, "°F"), 20)
        self.assertAlmostEqual(celsius(293.15, "K"), 20)
        self.assertEqual(celsius(19, "°C"), 19)
        self.assertIsNone(celsius(19, None))

    def test_bad_numbers_stay_unknown(self):
        for value in (None, "unavailable", "nan", "inf", True):
            with self.subTest(value=value):
                self.assertIsNone(number(value))

    def test_wind_units(self):
        self.assertEqual(wind_kmh(10, "m/s"), 36)
        self.assertAlmostEqual(wind_kmh(10, "mph"), 16.09344)
        self.assertIsNone(wind_kmh(10, None))

    def test_timestamp_requires_timezone(self):
        with self.assertRaises(ValueError):
            timestamp("2026-10-12T08:00:00")

    def test_actual_ha_forecast_response(self):
        config = Config(demo=False, weather_entity="weather.fontainebleau")
        client = HAClient(config)
        state = {
            "state": "cloudy",
            "last_updated": (NOW - timedelta(minutes=20)).isoformat(),
            "last_reported": NOW.isoformat(),
            "attributes": {"temperature": 12, "temperature_unit": "°C"},
        }
        response = {
            "service_response": {
                config.weather_entity: {
                    "forecast": [
                        {
                            "datetime": NOW.isoformat(),
                            "temperature": 10,
                            "condition": "rainy",
                            "precipitation_probability": 70,
                        },
                        {"datetime": (NOW + timedelta(hours=2)).isoformat(), "temperature": 15},
                        {"datetime": (NOW + timedelta(hours=8)).isoformat(), "temperature": 30},
                    ]
                }
            }
        }
        with (
            patch.object(client, "state", return_value=state),
            patch.object(client, "request", return_value=response) as request,
        ):
            snapshot = client.fetch(NOW)
        self.assertEqual(snapshot.weather.forecast_low, 10)
        self.assertEqual(snapshot.weather.forecast_high, 15)
        self.assertEqual(snapshot.weather.rain_probability, 70)
        self.assertIsNone(snapshot.weather.uv)
        self.assertIsNone(snapshot.living_room)
        self.assertFalse(snapshot.demo)
        self.assertEqual(snapshot.weather.observed_at, NOW)
        self.assertIn("return_response", request.call_args.args[0])

    def test_hourly_failure_preserves_current_weather(self):
        client = HAClient(Config(demo=False, weather_entity="weather.home"))
        state = {
            "state": "cloudy",
            "last_updated": NOW.isoformat(),
            "attributes": {"temperature": 12, "temperature_unit": "°C"},
        }
        with (
            patch.object(client, "state", return_value=state),
            patch.object(client, "request", side_effect=URLError("offline")),
        ):
            snapshot = client.fetch(NOW)
        self.assertEqual(snapshot.weather.temperature, 12)
        self.assertIsNone(snapshot.weather.rain_probability)
        self.assertTrue(snapshot.warnings)

    def test_room_observation_is_not_fetch_time(self):
        client = HAClient(Config())
        old = NOW - timedelta(hours=3)
        with patch.object(
            client,
            "state",
            return_value={
                "state": "19",
                "last_updated": old.isoformat(),
                "attributes": {"unit_of_measurement": "°C"},
            },
        ):
            self.assertEqual(client.room("sensor.room").observed_at, old)


if __name__ == "__main__":
    unittest.main()
