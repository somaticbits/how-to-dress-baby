# Configuration and updates

Start in demo mode to check the display before connecting your Home Assistant
entities. Then edit the installed app's configuration with your actual entity
IDs and set `demo: false`.

## Connect your sensors

```yaml
demo: false
weather_entity: weather.your_home
living_room_entity: sensor.your_living_room_temperature
bedroom_entity: sensor.your_baby_room_temperature
parents_bedroom_entity: sensor.your_other_bedroom_temperature
alert_entity: ""
```

These are examples, not entity IDs to copy unchanged. Keep the other options
provided by the app. Find your entity IDs in Home Assistant's
**Settings → Devices & services → Entities**.

| Option | Used for |
| --- | --- |
| `weather_entity` | Current outdoor weather and available forecast data |
| `living_room_entity` | Daytime indoor clothing suggestions |
| `bedroom_entity` | Baby's bedroom reading on the night page |
| `parents_bedroom_entity` | Optional second bedroom reading; leave blank if unused |
| `alert_entity` | Optional Météo-France vigilance input; leave blank if unused |

Bedroom readings are labelled separately, never averaged. Missing or stale
readings are shown explicitly rather than replaced with a target temperature.

Leave `ha_url: http://supervisor/core` for the Home Assistant app. The Supervisor
supplies authentication; no separate token is needed.

## Adjust the display

Defaults are day **07:00–19:00**, timezone **Europe/Paris**, weather refresh every
**15 minutes**, and reading expiry after **120 minutes**. Set the location label,
timezone, schedule and freshness limits for your home and sensors.

Outdoor temperature bands and indoor thresholds are independent and configurable.
They are comfort heuristics, not medical cutoffs; read the
[clothing guidance](clothing-guidance.md) before changing them.

## Image endpoints

Replace `YOUR_HA_LAN_IP` with your Home Assistant host's local address.

| Path | Result |
| --- | --- |
| `/display.png` | Day or night image according to the configured schedule |
| `/day.png` | Day image regardless of the time |
| `/night.png` | Night image regardless of the time |
| `/health` | Version, data freshness and outdoor decision inputs |

Example: `http://YOUR_HA_LAN_IP:8000/display.png`.
All endpoints are unauthenticated and must stay on a trusted LAN.

## Updates

The repository builds the image on your Home Assistant host. Check the app store
for updates and use Home Assistant's normal update flow. See the
[changelog](../CHANGELOG.md) for changes.

## Migrating from a local ZIP installation

A repository installation may be a **different app instance**:

1. Save your existing options and stop the local copy.
2. Install the repository-backed app and transfer your options.
3. Start the new app. Do not run both copies on port 8000.
4. Check `/health`, `/day.png` and `/night.png` before resuming Kindle downloads.

Local caches do not migrate automatically. Keep the old installation stopped
until you have verified the replacement rather than deleting it immediately.
