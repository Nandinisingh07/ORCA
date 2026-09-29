# ORCA demo backend (FastAPI)

Backend for the `sea-scribe-gallery` frontend. Multi-agent pipeline (Planner → Weather / Ocean / Geospatial /
Geofence / PFZ / Route → rule-based Risk → Explainability → Language). Demo scale: no PostGIS, no Redis, no LLM required.

## Run
```bash
pip install -r requirements.txt
cp .env.example .env
python -m scripts.check_live         # once, with internet: verifies every real source AND warms the offline cache
uvicorn app.main:app --reload        # http://localhost:8000/docs
# or: docker compose up --build
```
Tests: `pip install -r requirements-dev.txt && pytest`

## Endpoints (one per frontend page)
| Page | Endpoint |
|---|---|
| /ask | `POST /api/chat` `{message, session_id?, language?, mode?, place?, lat?, lon?}` |
| /conditions | `GET /api/conditions?place=&day=today\|tomorrow\|day_after` |
| /fishing-zones | `GET /api/fishing-zones?place=Gujarat coast` |
| /alerts | `GET /api/alerts?region=all\|west\|east&type=all\|weather\|sea` |
| /routes | `POST /api/route` `{origin, distance_km, bearing_deg?, day?}` |
| /boundaries | `GET /api/boundaries?layer=` · `POST /api/boundaries/check {lat, lon}` |
| /briefings | `GET /api/briefing?place=&lang=en\|hi\|gu\|ta&mode=` |
| satellite | `GET /api/eo?place=` (chlorophyll/SST summary + candidate zones) |
| ops | `GET /api/health?deep=true` (probes Open-Meteo), `GET /api/places` |

Add `?scenario=calm|rough|storm` (or `"scenario"` in chat/route body) to force a labelled **mock** case, e.g. to
demo an Unsafe verdict on a calm day. Disable with `DEMO_SCENARIOS=false`.

## What is real vs. not (read before the demo)
| Piece | Status |
|---|---|
| Wave, swell, SST, wind, gusts, thunderstorm code | **Real** Open-Meteo forecasts (≈8 km grid, sampled at an approximate offshore point per place) |
| Safe / Caution / Unsafe verdict | Real rule engine, but thresholds are **demo values** (`risk.py`, rule set `demo-v1`). Replace with official IMD/INCOIS criteria |
| Tide | Real Open-Meteo `sea_level_height_msl` (model, ~8 km, mean-sea-level datum). Fine for planning, **not for navigation or port entry** |
| Chlorophyll + SST | Real satellite data via NOAA CoastWatch ERDDAP (NOAA-20 VIIRS chlorophyll `nesdisVHNnoaa20chlaDaily`, MUR SST `jplMURSST41`). **Cloud gaps and processing lag are normal**: the API reports the actual observation date and age. Dataset IDs were checked against the ERDDAP pages, but live queries were not tested at build time. Run `python -m scripts.check_live` |
| Fishing zones | If satellite data is available: **heuristic candidate zones** (high chlorophyll, boosted by SST fronts; demo thresholds; `is_incois_pfz: false`). Otherwise labelled sample zones (`is_sample: true`). **Never** an INCOIS PFZ advisory. INCOIS publishes real PFZ advisories sector by sector on its own site; no endpoint for them is wired here |
| Cyclone / IMD alerts | Only a labelled **format sample**. Wave/wind/thunder alerts are derived from the forecast |
| Boundaries / protected areas | **Illustrative geometry**, not legal boundaries. Put validated GeoJSON in `data/boundaries/` and it replaces the sample automatically |
| Languages hi/gu/ta | **Template stub**, not Bhashini (no translation of free text, no ASR/TTS). Have native speakers review strings in `lang.py` |
| Voice briefing / SMS / IVR | Not implemented (`audio: null`) |
| LLM | Optional, off by default. It may only re-phrase the finished answer; verdict/numbers never come from it |

## Data provenance (`data_mode`)
`live` = fetched (or cache hit < `CACHE_TTL_MIN`) · `cached` = source failed, last real fetch served (see `fetched_at`) ·
`mock` = synthetic sample. Every response, evidence item and answer text carries it, and `confidence` drops accordingly.
Set `FORCE_MOCK=true` to run fully offline.

## Known limits
- Sessions are in memory (lost on restart, single process).
- Chat intent detection is keyword-based (en/hi/gu/ta), not an LLM. Unusual phrasing falls back to "conditions".
- If no place is given, `DEFAULT_PLACE` is assumed and `place.assumed=true` (the answer says so).
- Route check samples 3 points and picks the best of 3 headings; it is not a navigation tool.
- Open-Meteo free tier is for non-commercial use; check terms if this goes beyond the hackathon.

## Wiring the frontend
Copy `frontend-snippets/api.ts` to `src/lib/api.ts`, set `VITE_API_URL`. The current pages carry "not live" notices
(e.g. `Notice` in ask/conditions); update that copy once a page is wired, and show `data_mode` + source + time next to numbers.
