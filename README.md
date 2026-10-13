# How to dress baby

A local weather-to-wardrobe display for a jailbroken Kindle, powered by Home
Assistant. Deterministic Python rules, original garment illustrations, and a
600 × 800 grayscale image: no runtime AI, cloud rendering, or image subscriptions.

<p>
  <img src="images/day.png" width="300" alt="Day page with fictitious weather and a layered outfit" />
  <img src="images/night.png" width="300" alt="Night page with fictitious bedroom readings and manual sleepwear guidance" />
</p>

**The screenshots are demonstrations, not live weather or clothing prescriptions.**

## What it does

- **Day:** a weather-only starting outfit, indoor awake clothing, removable layers
  to carry, and brief wind/rain/sun advice. Parents adjust for transport and comfort.
- **Night:** separately labelled baby/parents bedroom readings; gigoteuse and TOG
  selection stay manual. Outdoor weather is never substituted for room temperature.
- **Kindle:** `/display.png` switches day/night in the configured timezone;
  `/day.png` and `/night.png` are available separately. Existing downloads can report
  battery level for a prominent low-battery reminder, with no additional wake-ups.
- **Resilience:** persistent cache, explicit stale/missing-data warnings, ETags,
  bounded HA requests, and packaged fonts for offline rendering.

At **16°C air temperature**, the default outdoor baseline is **long-sleeved body,
trousers, socks and a removable lightweight cardigan**. Provider “feels like” is
context, not the outfit selector. Numeric bands are **adjustable comfort heuristics,
not clinically validated cutoffs**. See [evidence and limitations](docs/clothing-guidance.md).

## Install on Home Assistant OS

1. Open **Settings → Apps → App store** (called **Add-ons** on older versions).
2. Open **⋮ → Repositories** and add:
   `https://github.com/somaticbits/how-to-dress-baby`
3. Install **How to dress baby**, start in demo mode, and open its web UI.
4. Configure your weather entity and room temperature entities, then set
   `demo: false`. Leave `ha_url: http://supervisor/core` for the add-on.

The Supervisor supplies API authentication; **no token belongs in the configuration**.
Expose port 8000 only to trusted LAN clients. This app is not Internet-safe.

The repository builds the image on your HA host. New versions appear through
HA’s normal update flow after checking the app store for updates.

### Migrating from a local ZIP installation

A repository installation may be a **different app instance**. Save your existing
options, stop the local copy, install this one, and transfer the options. Do not
run both on port 8000. Verify `/health` and both images before re-enabling Kindle
downloads. Local caches are not migrated automatically; keep the old installation
stopped until the replacement is verified rather than deleting it immediately.

## Configure

```yaml
demo: false
weather_entity: weather.your_home
living_room_entity: sensor.your_living_room_temperature
bedroom_entity: sensor.your_baby_room_temperature
parents_bedroom_entity: sensor.your_other_bedroom_temperature
alert_entity: ""
```

`parents_bedroom_entity` and the Météo-France vigilance entity are optional.
Entity names are examples: select your actual HA entities. The night page shows
both rooms, without averaging readings or guessing where the baby is sleeping.

Defaults: day 07:00–19:00 in Europe/Paris, HA refresh every 15 minutes, readings
expire after 120 minutes. Configure those values for your sensors and routine.
Indoor thresholds and outdoor thresholds are independent.

## Kindle setup

See [Kindle setup](docs/kindle.md). Tested manually on a Basic 8th-generation
KT3 with firmware 5.12.5, native 600 × 800 portrait PNGs. Exact compatibility with
other devices is not established. Scheduling, networking and OTA protection are
device-side concerns, not features that a server image can enable by itself.

## Development

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
PYTHONPATH=how_to_dress_baby .venv/bin/python -m unittest discover -s tests -v
.venv/bin/ruff check .
.venv/bin/ruff format --check .
PYTHONPATH=how_to_dress_baby .venv/bin/python -m app --render-demo cache/day.png --page day
```

For a standalone server, supply a private JSON configuration and `HA_TOKEN` in
the process environment; do not commit either. HA OS needs no separate token.
`/health` reports build version, freshness and the outdoor decision input/band,
making it possible to explain an unexpected outfit rather than silently retune it.

```text
repository.yaml              HA store metadata
how_to_dress_baby/
  config.yaml                App options and version
  Dockerfile                 Self-contained HA build context
  app/                       Adapter, rules, renderer, HTTP service, local assets
tests/                       Decisions, freshness, HTTP/cache and measured layout checks
docs/                        Evidence boundaries and device setup
kindle/                      Optional downloader overrides
```

## Design and engineering

The constraints shape the product: a sleeping e-ink device, an always-on HA host,
uncertain sensor freshness, and caregivers who need a readable starting point.
The renderer separates **what to wear now** from **what to bring**; typography
uses Fredoka headings and Atkinson Hyperlegible body text. Garment drawings are
original Pillow geometry. Footer tests measure real font bounds and reserve
space for a low-battery banner, rather than merely asserting PNG generation.

Source builds have been checked on arm64. CI checks Python behavior and an amd64
Docker build. armv7 and other Kindle firmware need target-device verification;
do not interpret advertised architecture names as exhaustive certification.

## Safety and privacy

This is not medical advice, a physiological model, or an automated dressing
system. Caregivers must check comfort, avoid overheating and adapt to actual
conditions. No bulky coat goes under a car-seat harness, and carrier airways must
remain clear—even though transport-specific UI has deliberately been removed.
No automatic footmuff equivalents or sleep TOG tables are provided.

The unauthenticated image endpoint is for a trusted LAN. Battery values are used
per image request, not as a remote tracking feed. Keep credentials, real household
configuration and device reports outside the repository.

MIT for the application and original illustrations; see [third-party notices](THIRD_PARTY_NOTICES.md)
for fonts and dependencies.
