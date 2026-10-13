# Changelog

## 0.3.2

- Add optional `baby_name` configuration and 50 personalised French greetings.
- Rotate daytime and bedtime greetings daily, keeping bedtime stable across midnight.
- Fit greetings to the header and keep names local to the configured display.

## 0.3.1

- Rebalance both pages: the outdoor outfit leads in one sentence (« A, B et C »),
  with the temperature and conditions in a circle beside it.
- Move the update time into the header; remove the footer tips.
- Show the apparent temperature only when it differs from the air temperature.
- Spell dates in words (« lundi 12 octobre », « Nuit du 12 au 13 octobre »).
- Centre indoor and carried-layer cards; one carried layer gets a large drawing.
- Keep every line of text above the low-battery band, checked by tests.

## 0.3.0

- First public Home Assistant app repository.
- Use air temperature for outdoor outfits, with a distinct mild-weather band.
- Show complete worn ensembles and separate removable carried layers.
- Remove transport-specific UI; retain safety guidance in documentation.
- Keep indoor and outdoor thresholds independent.
- Expose version and decision inputs through `/health`.
- Keep separate day/night pages, both bedroom readings and a prominent low-battery alert.
- Verify footer spacing with measured font bounds.
