# Development

Use Python 3.12. Run these commands from the public repository root:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
PYTHONPATH=how_to_dress_baby .venv/bin/python -m unittest discover -s tests -v
.venv/bin/ruff check .
.venv/bin/ruff format --check .
PYTHONPATH=how_to_dress_baby .venv/bin/python -m app --render-demo cache/day.png --page day
```

The last command renders a sample day page without connecting to Home Assistant.
Use `--page night` for a night preview.

## Architecture

```text
Home Assistant weather + room sensors
                  ↓
          Configurable Python rules
                  ↓
          Pillow → grayscale PNG
                  ↓
          LAN download → Kindle
```

Home Assistant provides the always-on host; the Kindle wakes to download an image
on its own schedule. The server does not wake the Kindle. There is no runtime AI
or external rendering service.

```text
repository.yaml              Home Assistant store metadata
how_to_dress_baby/
  config.yaml                App options and version
  Dockerfile                 Self-contained build context
  app/                       HA adapter, rules, renderer, HTTP service and assets
tests/                       Rules, freshness, HTTP/cache and layout checks
docs/                        Setup, evidence and device guidance
kindle/                      Optional downloader overrides
```

The service uses a persistent cache, explicit stale-data handling, bounded HA
requests and ETags for conditional image downloads. `/health` exposes the build
version, freshness and outdoor decision inputs to help explain unexpected outfits.

For a standalone server, provide a private JSON configuration and `HA_TOKEN` in
the process environment. Never commit either. The HA OS app needs no separate token.

## Display design

Original garment illustrations are drawn with Pillow. Typography uses bundled
Fredoka headings and Atkinson Hyperlegible body text. Layout checks measure real
font bounds and keep all content above the low-battery banner.

Battery reporting uses each existing image download; it does not require another
wake-up. A warning appears at 15% or below unless charging is reported. It reflects
the last download, not a live gauge.

## Compatibility and checks

Version 0.3.0 has been built and tested on arm64 locally and amd64 in GitHub CI.
armv7 builds still need target verification. Kindle testing covers the Basic
8th-generation KT3 with firmware 5.12.5, not every model or firmware.

Before submitting a change, run the tests, lint and formatting checks above.
For visual changes, render both pages and check cold, mild, hot, stale-data and
low-battery cases. Keep new clothing rules deterministic, test their boundaries,
and distinguish product heuristics from sourced safety guidance.

For larger changes, open an issue to discuss the approach first. Do not include
credentials, household settings or real device logs in contributions.
