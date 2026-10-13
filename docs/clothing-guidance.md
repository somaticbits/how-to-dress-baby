# Clothing guidance and evidence boundaries

This is general guidance for caregivers of healthy infants, not an individual
medical profile. Indoor recommendations use actual room sensors, never a target
temperature. Outdoor suggestions are a weather-only starting point: caregivers
adjust for activity, transport, existing coverings, fabric, fit and comfort.

## Verified principles

| Principle | Source |
| --- | --- |
| Multiple thin removable layers; warm hat, mittens and socks/booties in cold weather | [NHS clothing essentials](https://www.nhs.uk/baby/caring-for-a-newborn/what-you-will-need-for-your-baby/) |
| Adjustable layers; the extra-layer rule of thumb includes older babies, but is not a fixed garment count | [AAP cold-weather guidance](https://www.healthychildren.org/english/safety-prevention/at-play/pages/cold-weather-safety.aspx) |
| Light, loose clothing in heat; broad-brimmed hat; non-walking babies do not need shoes except protection | [Naître et grandir, clinically reviewed](https://naitreetgrandir.com/fr/etape/0_12_mois/soins/bebe-vetements/) |
| Avoid infant outings in grand froid; no carrier transport in those conditions; protect head, ears, hands, feet, and keep clothing dry | [Ameli cold-weather guidance](https://www.ameli.fr/assure/sante/themes/froid-pathologies-sante/savoir-proteger-froid) |
| No bulky coat/snowsuit underneath car-seat harness; removable warmth above buckled straps; no pram inserts in car seats | [AAP winter car-seat safety](https://www.healthychildren.org/English/safety-prevention/on-the-go/Pages/Winter-Car-Seat-Safety-Tips.aspx) |
| Carrier face visible and airway clear; follow TICKS; watch overheating | [Lullaby Trust sling safety](https://www.lullabytrust.org.uk/baby-safety/baby-product-information/slings-and-carriers/) |
| Sleeping room 18–20°C; correctly fitted gigoteuse; avoid excessive layers and loose bedding; check neck for sweating | [Ameli safe sleep](https://www.ameli.fr/assure/sante/bons-gestes/bebe/coucher-bebe) |
| No hat while sleeping | [Naître et grandir](https://naitreetgrandir.com/fr/etape/0_12_mois/soins/bebe-vetements/) |
| Shade and sun protection; do not cover pram/car seat with a blanket | [Alder Hey NHS sun safety](https://www.alderhey.nhs.uk/sun-safety-keeping-children-safe-in-hot-weather/) |

Sources reviewed 2026-10-12 and 2026-10-13. They support principles and garment categories,
not a clinically validated universal temperature-to-outfit algorithm.
French Ameli sleep advice is the default; do not silently merge
the UK's 16–20°C room range into a conflicting French recommendation.

## Product heuristics (explicitly not medical thresholds)

| Input | Default behaviour |
| --- | --- |
| Air temperature below 10°C, above the extreme-cold gate | Base layers, gilet, socks, outdoor coat, bonnet and mittens worn |
| 10°C to below 18°C | Body long, trousers, gilet, socks; light jacket to bring |
| 18°C to below 22°C | Body long, trousers, socks; removable gilet to bring |
| 22°C to below 25°C | Body short, trousers, socks; removable gilet to bring |
| 25°C and above | Light outfit and sun hat, shade reminder |
| Air/apparent/forecast below 0°C or at/above 32°C | Stop automatic outdoor outfit and show caution |
| Rain/snow/hail or forecast rain probability >= 50% | Keep dry, seek shelter, bring dry spare clothes when an outfit is offered |
| Wind >= 30 km/h | Shelter/exposure reminder, no invented wind-chill calculation |
| UV >= 3 | Shade and protection reminder |
| Indoor temperature below 18°C | Body long + pyjama + removable gilet |
| Indoor 18°C to below 25°C | Body long + trousers, monitor comfort |
| Indoor at/above 25°C | Lightweight body; monitor heat |

Numerical bands in `Config` can be edited in add-on options; rain/wind/UV reminder
thresholds are small product defaults in `app/rules.py`. The 0°C caution is a
conservative product gate, NOT a definition of official “grand froid.”
Air temperature is the outfit selector; apparent temperature remains visible as
context and an extreme-weather caution input, not an infant comfort model. The
separate 18°C warmth-layer and 22°C sleeve transitions avoid changing both at once.
These choices are adjustable heuristics, not research-established cutoffs. The
16°C default is long sleeves, trousers, socks and a removable lightweight gilet.
Wind/rain/UV change preparation and visible advice, never invented temperature
penalties. Indoor thresholds are separate from outdoor thresholds.
The one-more-layer-than-adult guideline is not applied mechanically.

The day page deliberately has no transport-mode selector. The outdoor coat is
for outside use, **not permission to wear bulky clothing under a car-seat harness**.
Caregivers handle carrier warmth, vehicle heating and footmuffs themselves; the
safety principles above still apply. Gigoteuse choices remain manual.

## Deferred decisions

- Actual wardrobe availability, fit and fabric/insulation differences.
- Footmuff make/model and manufacturer instructions. No assumed thermal equivalence.
- Gigoteuse make/model, rating and manufacturer's clothing guide. No automated TOG table.
- Outing duration, sheltered/exposed location, and under-/over-coat carrier use.
- Forecast-driven outfit adaptation beyond displaying the next four hours.

Caregivers must check comfort and adjust. The app does not diagnose hypothermia,
overheating, fever, or other illness. For relevant health concerns, consult a clinician.

## Data provenance

[HA Météo-France integration](https://www.home-assistant.io/integrations/meteo_france/)
supplies current/hourly weather and optional department-level vigilance.
[HA weather documentation](https://www.home-assistant.io/integrations/weather/)
describes optional units/attributes. The backend must never turn missing data into
zero precipitation, zero UV, or assumed room temperature. `last_reported` or
`last_updated` is used as HA's observation proxy, not asserted as the upstream
meteorological measurement time.
