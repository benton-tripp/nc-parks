# TODO

## Data Pipeline — Sources (22 active, 4,771 parks)

**Implemented:** Wake County, Johnston County, Alamance County, OSM (statewide), Greensboro, High Point,
Playground Explorers, Southern Pines, Nash County, Kill Devil Hills, Google Places, Charlotte,
Mecklenburg County, Wilmington, New Bern, Elizabeth City, Goldsboro, Graham, Manteo, Lexington,
NC Triad Outdoors, New Hanover County

**Not yet producing parks** (scrapers exist but 0 in final output): Henderson County, Durham County,
Fayetteville, Asheville, Wilson

### Potential New Sources

- **Accessible Playground** (accessibleplayground.net) — accessibility-focused enrichment data
- **House of Hensen blog** — manual discovery only, not scrapable
- **TripAdvisor / Yelp** — deferred indefinitely (ToS risk, low value vs. effort)

---

## Data Pipeline — Remaining Improvements

- [ ] Reverse geocode remaining parks missing addresses
- [ ] Review remaining sources for unmapped fields that could feed into new amenity keys

---

## Admin Review Tool (`streamlit run admin/app.py`)

Streamlit-based local admin UI for park verification, field editing, dedup review, and deletions.
Override files in `data/overrides/` (field_edits, manual_merges, deletions, verifications) persist
across pipeline re-runs. All overrides include audit timestamps.

### Remaining

- [ ] **Bulk actions**: verify all parks in a county, mark source as reviewed, etc.
- [ ] **FUTURE: User-verified park handling/protection**: Any parks that have been verified, had adjusted ammenedies, and/or submitted by users need to be handled in the pipeline

---

## Frontend

React + TypeScript + Vite + Tailwind + MapLibre GL. Responsive (mobile bottom sheet, drawer filters).
Google ratings displayed. PWA manifest in place.

### Remaining

- [ ] Complete PWA: add icon files (`icon-192.png`, `icon-512.png`), add `vite-plugin-pwa` for offline
- [ ] Consider `react-helmet-async` for per-park SEO if individual park pages are added
- [ ] In-app ratings/reviews (requires backend auth)

---

## Amenity System

**Single source of truth:** `amenities.json` — 66 amenities across 7 categories (Playground, Facilities,
Sports, Outdoors, Water, Accessibility, Surface). All consumers derive from this file:

- Pipeline (`normalize.py`) → `CANONICAL_AMENITIES`
- Admin (`data_io.py`) → `AMENITY_COLS`, `AMENITY_CATEGORIES`, `AMENITY_LABELS`
- Frontend (`park.ts`) → `FILTERABLE_AMENITIES`, `AMENITY_LABELS`
- Excel export (`export_excel.py`) → `AMENITY_COLS`

**Adding a new amenity** = one entry in `amenities.json` + source `AMENITY_MAP` entries if applicable.

### Post-pipeline amenity counts (April 2026)

| Amenity | Parks | Notes |
|---|---|---|
| pickleball | 82 | asheville, civicplus, goldsboro, OSM |
| slides | 59 | OSM, playground_explorers, goldsboro |
| swings | 52 | OSM, playground_explorers, goldsboro, durham |
| swimming_pool | 116 | wake, civicplus, osm, google, asheville |
| sandbox | 9 | OSM (playground:sandpit), playground_explorers (fixed) |
| lake_swimming | 0 | manual tagging via admin |
| shaded_playground | 0 | manual tagging via admin |
| surface_* | 0 | manual tagging via admin |

### Remaining

- [ ] Add `lake_swimming` detection in OSM (`natural=water` + `sport=swimming` / `leisure=swimming_area`)
- [ ] `shaded_playground` — primarily manual-verification; keyword scan risky
- [ ] `sandbox` — OSM captures via `playground:sandpit`. Other sources don't distinguish from general playground
- [ ] Verify admin tool shows new amenity checkboxes grouped by category
- [ ] Verify frontend filters work for new amenities

---

## Backend (AWS)

- [ ] DynamoDB table design + SAM template
- [ ] API Gateway + Lambda for park queries
- [ ] User auth (Cognito)
- [ ] Ratings / reviews API
- [ ] Photo upload (S3 + moderation)
- [ ] Park submission + verification workflow
