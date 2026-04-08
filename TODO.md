# TODO

## Data Pipeline — Current Sources (Implemented)

- [x] **Wake County** — ArcGIS REST API, 291 parks, rich amenity flags
- [x] **Johnston County** — Web scraper, 31 parks, amenities from detail pages
- [x] **Alamance County** — Web scraper, 6 parks, amenities from sidebar nav
- [x] **OSM (Statewide)** — Overpass API, ~3,100 parks, child POI spatial enrichment for amenities
- [x] **Greensboro** — 86 parks scraped via undetected-chromedriver (Akamai WAF); Coordinates from `data-lat`/`data-long` attributes, amenities from listing
- [x] **High Point** — 20 parks scraped via undetected-chromedriver (CivicPlus JS pagination); Amenities, addresses, acreage from detail pages; geocoder fills coordinates
- [x] **Playground Explorers** — 117 outdoor parks → 105 after dedup; RSC flight data parsing (plain `requests`); rich amenities (slides, swings, splash pads, ADA, restrooms, etc.) + coordinates across 10+ NC counties
- [x] **Southern Pines** — CivicPlus Facility Directory via reusable `CivicPlusScraper` base class
- [x] **Nash County** — CivicPlus Facility Directory with multi-city address parsing
- [x] **Kill Devil Hills** — Static content page scraper (no /Facilities endpoint); 4 parks in Dare County

---

## Data Pipeline — New Sources

### Priority 1: Large Cities (High Value)

#### Charlotte / Mecklenburg County (`charlotte.py`, `meckleburg_county.py`)

- **URLs:**
  - https://parkandrec.mecknc.gov/Places-to-Visit/Parks (redirects to Google Maps embed)
  - https://charlottemomsnetwork.com/resources/playgrounds/
  - https://www.charlottesgotalot.com/articles/things-to-do/parks-and-playground-guide
  - https://fun4charlottekids.com/Fun-Around-Town/Playgrounds-and-Parks/Page-1.html
- **Insight:** Mecklenburg County Parks & Rec redirects to an embedded Google Map — no scrapable listing page. Best bet is an ArcGIS open data portal or REST API (check `opendata.mecknc.gov`). Community sites (charlottemomsnetwork, fun4charlottekids) could supplement but have ToS concerns. Charlotte is the largest NC city — high value.
- **Method:** ArcGIS REST API (if available) or community site scraping
- **Amenities:** Varies by source
- **Coordinates:** Likely from ArcGIS or Google Maps embed data
- **Difficulty:** Medium — need to find the right API endpoint

#### Durham (`durham_county.py`)

- **URL:** https://www.dprplaymore.org/253/Playgrounds
- **~57 playgrounds at 55 parks**
- **Insight:** CivicPlus site with a rich playground features table (age range, swings yes/no, ADA yes/no, special features). Table has structured columns — easy to parse. Detail pages linked per park. Also has ArcGIS interactive map.
- **Method:** BS4 table parsing from the main page + detail page links
- **Amenities:** Yes — structured table with swings, ADA, special features per park
- **Coordinates:** Geocode from addresses or extract from ArcGIS map
- **Difficulty:** Easy

#### Fayetteville (`fayetteville.py`)

- **URL:** https://www.fayettevillenc.gov/Parks-and-Recreation/Parks-Trails
- **~13+ parks** (paginated, 2 pages)
- **Insight:** Granicus CMS with card-style listings. Each card has name, address, and description. Detail pages likely have more info. Also has ArcGIS interactive map (`faync.maps.arcgis.com`).
- **Method:** BS4 with pagination (2 pages), or ArcGIS REST API
- **Amenities:** Basic from descriptions, more from detail pages
- **Coordinates:** ArcGIS map or geocode from addresses
- **Difficulty:** Easy-Medium

#### Asheville (`asheville.py`)

- **URL:** https://www.ashevillenc.gov/locations/?avl_department=parks-recreation
- **~69 locations** (parks + community centers)
- **Insight:** Custom WordPress/CMS with excellent structured data. Listing page shows each park with name, description, and amenity tags (Playground, Basketball, Pickleball, Tennis, Restrooms, Wheelchair Accessible, etc.). Uses Leaflet map with markers — **coordinates are in the page JS**. Very clean, well-structured source.
- **Method:** BS4 — listing page has names, descriptions, amenity tags, and detail page URLs. Leaflet map JS has coordinates.
- **Amenities:** Yes — rich amenity tags per park on listing page
- **Coordinates:** Yes — from Leaflet map initialization JS
- **Difficulty:** Easy-Medium

### Priority 2: Medium Cities

#### Wilson (`wilson.py`)

- **URL:** https://www.wilsonnc.org/residents/all-departments/parks-recreation/parks-shelters
- **~38 parks/shelters** (paginated, 2 pages)
- **Insight:** Granicus CMS with a table of parks (name, address, phone). Paginated across 2 pages. Also has ArcGIS interactive map. Limited amenity info on listing page — may need detail pages.
- **Method:** BS4 table parsing with pagination
- **Amenities:** Minimal on listing page, may need detail pages
- **Coordinates:** ArcGIS map or geocode from addresses
- **Difficulty:** Easy

#### Goldsboro (`goldsboro.py`)

- **URL:** https://www.goldsboroparksandrec.com/parks/
- **~13 parks + 2 greenways**
- **Insight:** Custom WordPress site with park cards linking to detail pages. Detail pages likely have amenities and descriptions. Simple structure.
- **Method:** BS4 — follow links to detail pages for amenities
- **Amenities:** Likely on detail pages
- **Coordinates:** Geocode from addresses
- **Difficulty:** Easy

#### New Bern (`new_bern.py`)

- **URL:** https://www.newbernnc.gov/departments/parks.php
- **~30+ parks** (mini/pocket, neighborhood, community categories)
- **Insight:** Revize CMS with parks listed inline as text blocks grouped by category (Mini/Pocket Parks, Neighborhood Parks, Community Parks). Addresses are inline. No structured amenities — just names and addresses.
- **Method:** BS4 text parsing
- **Amenities:** None — names and addresses only
- **Coordinates:** Geocode from addresses
- **Difficulty:** Easy

#### Wilmington (`wilmington.py`)

- **URL:** https://www.wilmingtonnc.gov/files/assets/city/v/1/parks-amp-rec/documents/amenities/parksamenitiessheet_2025-3.pdf
- **Insight:** Primary source is a **PDF amenities spreadsheet**. Would need `pyMuPDF`, `pdfplumber`, or `tabula-py` to extract the table. Rich amenity data in tabular form. Check if Wilmington also has a web-based parks listing or ArcGIS portal.
- **Method:** PDF parsing (`pyMuPDF`) or find web alternative
- **Amenities:** Yes — detailed amenities table in PDF
- **Coordinates:** Geocode from addresses
- **Difficulty:** Medium (PDF parsing)

### Priority 3: Small / Niche

#### Henderson County (`henderson_county.py`)

- **URL:** https://www.hendersoncountync.gov/recreation/page/parks-facilities
- **~15 parks**
- **Insight:** Drupal site with an OpenLayers map — coordinates likely embedded in map initialization JavaScript. Parse the `<script>` blocks for lat/lon arrays.
- **Method:** BS4 + JS parsing for coordinates
- **Amenities:** Yes, listed per park
- **Coordinates:** Likely in OpenLayers JS init
- **Difficulty:** Medium

#### NC Triad Outdoors (`triad.py`)

- **URL:** https://nctriadoutdoors.com/playgrounds/
- **Parks across the Triad region** (Greensboro, Winston-Salem, High Point area)
- **Insight:** Community/blog-style site. May have structured park listings with amenities and photos. Good for cross-referencing and filling amenity gaps, but likely overlaps heavily with Greensboro + High Point official sources. Assess after those are done.
- **Method:** BS4
- **Amenities:** Likely (reviews/descriptions)
- **Coordinates:** Unlikely — geocode from addresses
- **Difficulty:** Easy-Medium

#### Accessible Playground (`scraper.py` — accessibleplayground.net)

- **URL:** https://www.accessibleplayground.net/united-states/north-carolina/
- **Insight:** Valuable accessibility-focused data (wheelchair access, sensory features, inclusive equipment). Best used to enrich existing parks rather than as a primary source. May overlap with Playground Explorers.
- **Method:** BS4
- **Amenities:** Yes, accessibility-focused
- **Coordinates:** Likely
- **Difficulty:** Easy

#### Graham (`graham.py`)

- **URL:** https://www.cityofgraham.com/grpd-parks-playgrounds/
- **Insight:** WordPress site. Small number of parks. Low priority but easy to scrape.
- **Method:** BS4
- **Difficulty:** Easy

#### Manteo (`manteo.py`)

- **URL:** https://www.manteonc.gov/community/visitors/parks-and-playgrounds
- **Insight:** Granicus CMS. Small coastal town, maybe 3-5 parks.
- **Method:** BS4
- **Difficulty:** Easy

#### Lexington (`lexington.py`)

- **URL:** https://www.lexingtonnc.gov/city-services/parks-and-recreation/parks-and-facilities
- **Insight:** Granicus CMS with tabbed content. Tabs may be CSS-hidden (check if content is in initial HTML before reaching for Selenium). Small number of parks.
- **Method:** BS4 (check if tabs are in initial HTML) or Selenium
- **Difficulty:** Easy-Medium

#### Elizabeth City (`elizabeth_city.py`)

- Stub exists — needs research
- **Difficulty:** Unknown

### Priority 4: Low / Deferred

#### New Hanover County (`new_hanover_county.py`)

- **URL:** https://www.nhcgov.com/DocumentCenter/View/844/Parks-Guide-PDF?bidId=
- **Insight:** This is a **PDF**, not a web page. Needs `pyMuPDF`, `pdfplumber`, or `tabula-py` to extract tables. Lowest priority — OSM likely covers most NHC parks already.
- **Method:** PDF parsing (e.g., `pyMuPDF`)
- **Difficulty:** Medium (PDF extraction is brittle)

#### House of Hensen blog (`scraper.py`)

- **URL:** https://www.houseofhensen.com/blog/my-favorite-charlotte-area-playgrounds
- **Insight:** Informal blog post — unstructured prose, not a data source. Best used for manual validation or discovery of parks to cross-reference, not automated scraping.
- **Method:** Skip automated scraping. Use for manual park discovery.
- **Difficulty:** N/A

#### TripAdvisor / Yelp / Google (`scraper.py`)

- **Insight:** All require Selenium + aggressive anti-bot bypass. High legal risk (ToS violations). Reviews could feed into LLM-based amenity extraction, but the effort-to-value ratio is poor when official sources exist. **Defer indefinitely** — user submissions + official data are a better path.

---

## Data Pipeline — Improvements

- [x] Build reusable CivicPlus scraper (`civicplus_base.py` + Southern Pines, Nash County, Kill Devil Hills subclasses)
- [x] Nominatim rate limit recovery — persistent backoff state in `nominatim_backoff.json`, escalating delays across runs
- [x] Geocode cache warming — `warm_cache.py` script runs `--skip-fetch --geocode-batch N` in rounds with pauses
- [x] County name normalization — enrich.py appends " County" suffix to bare names ("Wake" → "Wake County")
- [x] Remaining Locations
- [x] Google Places API — Integrated into pipeline: `fetch()` loads latest raw file from `data/raw/`,
      filters to NC-only (2,931 of 3,336), excludes commercial entertainment (trampoline parks, indoor
      playgrounds, vineyards, etc. — 93 excluded), stamps `google_data_date` in extras. Registered in
      `pipeline.py` SOURCES + `normalize.py` _SOURCE_HANDLERS with city parsing from Google address format.
      Extras preserved: `google_rating`, `google_rating_count`, `google_maps_uri`, `google_place_id`,
      `google_types`, `google_data_date`. Frontend shows star ratings + review count in park detail panel.
      **Note:** Run full pipeline with all sources to merge google_places into the combined dataset.
- [x] CHECK: Make sure if I re-run the full pipeline it never triggers the Google Places API; I want that to just be a standalone function, where any usage of that module in the pipeline is just using the already populated data.
      **VERIFIED:** Pipeline only calls `fetch()` which reads from `data/raw/google_places_*.json` on disk.
      `discover()` (API call) and `enrich()` (API call) are only reachable from the `__main__` CLI block
      when running `google_places.py` directly. No code path in `pipeline.py` can trigger the API.
- [x] CHECK: Make sure all of the existing pipeline.source location modules work/are built into the pipeline (normalization, geocoding, deduping, etc.)
      **VERIFIED:** All 27 SOURCES entries have matching `_SOURCE_HANDLERS` entries. 1:1 match.
      One file exists but is intentionally unregistered: `nc_onemap.py` (not a data source yet).
    - [x] Have any not been run?
          **UPDATE:** 22 of 27 sources now produce parks in the final output (4,798 total parks).
          Remaining 5 sources (henderson_county, durham_county, fayetteville, asheville, wilson)
          have scrapers but produce 0 parks after dedup or haven't been run successfully.
- [x] CHECK: Are there any missing coordinates/addresses?
      **4,542 total parks.** 1 park had 0,0 coords (Mitchell Street Park, greensboro — fixed: scraper
      now treats 0,0 as missing, normalize.py safety net added). 144 parks missing addresses (all OSM).
      79 parks missing county (43 google_places, 36 OSM — mostly coastal/barrier island parks where
      point-in-polygon fails because coords fall outside county boundary polygons).
    - [ ] If needed, Geocode or Reverse geocode remaining parks missing coordinates and or addresses
- [x] Get county field in the data using coordinates + county boundaries data (currently just getting from address, sometimes wrong or missing)
      **DONE:** `enrich.py` now always overwrites county using point-in-polygon from boundary data
      (ignores whatever the source set). Added nearest-county fallback (~2km) for coastal/waterfront
      parks whose coords land just offshore. All 79 previously missing-county parks now resolved.
- [x] OSM amenity enrichment for remaining unmapped child POI tags
      **DONE:** `dog=leashed/unleashed/designated` now maps to `dog_park`. `wheelchair=limited/designated`
      now maps to `ada_accessible`. Previously only `=yes` was recognized.
- [x] Update duplicates (e.g., Wilson's Mills Athletic Complex has three entries)
      **DONE:** Tightened dedup: lowest tier raised from 60%/150m to 70%/100m. Added facility-type guard —
      co-located but distinct facilities (dog park vs playground vs trail vs skatepark vs dam) are no
      longer merged. Fixes false positives like "Beech Mountain Dog Park" ↔ "Beech Mountain Playground",
      "Kitty Hawk Reserve" ↔ "Kitty Hawk Skatepark", "Salem Lake Trail" ↔ "Salem Lake Playground".
- [x] Update Sources to be the URLs
      **DONE:** Added `source_url` field to every park record (stamped during normalize from `_SOURCE_URLS`
      dict — canonical homepage URL per source). Frontend `SourceLink` now uses `source_url` from data
      with fallback to hardcoded `SOURCE_URLS`. Added all 27 sources to frontend `SOURCE_LABELS`.

---

## Admin Review Tool (Pipeline-Integrated Manual Override)

Goal: A local-only admin UI for verifying parks, correcting fields, resolving duplicates, and deleting
non-parks — with results that feed back into the pipeline as a post-processing step.

### Architecture

**Override files** (`data/overrides/`) — JSON files the pipeline reads after normalize + dedup:

- `field_edits.json` — per-park field corrections keyed by `source + source_id`

    ```json
    {
    "osm::osm-n123456": {
        "name": "Corrected Park Name",
        "address": "123 Real St, Raleigh, NC 27601",
        "latitude": 35.7796,
        "longitude": -78.6382
    }
    }
    ```

- `manual_merges.json` — explicit dedup instructions (merge B into A, keep A's fields unless specified)

    ```json
    [
    {
        "keep": "wake_county::wake_286_property",
        "drop": "osm::osm-w987654",
        "field_overrides": { "name": "286 Property Park" }
    }
    ]
    ```

- `deletions.json` — parks to exclude (not real parks, businesses, etc.)

    ```json
    ["google_places::gp_abc123", "osm::osm-n999999"]
    ```

- `verifications.json` — per-park per-field verification status + notes

    ```json
    {
    "wake_county::wake_marsh_creek": {
        "verified_at": "2026-04-07T12:00:00",
        "fields": {
        "name": { "status": "verified" },
        "address": { "status": "verified" },
        "coordinates": { "status": "corrected", "note": "Moved pin to entrance" },
        "amenities": { "status": "needs_review" }
        }
    }
    }
    ```

**Pipeline integration** — new step in `pipeline.py` after dedup, before final output:

- Apply `deletions.json` (remove parks)
- Apply `manual_merges.json` (merge pairs)
- Apply `field_edits.json` (overwrite fields)
- Stamp `verifications.json` status into each park's `extras`
- Log a summary of overrides applied per run

**Local admin UI - Streamlit app:**

- Python-native, runs locally (`streamlit run admin/app.py`)
- Built-in: data tables, forms, maps (via streamlit-folium), text input, buttons
- Park review page: shows all fields, Google/Apple Maps links, satellite link, amenity checkboxes.
    Click "Verified" / "Corrected" / "Flagged" per field. Edits write to override JSONs.
- Dedup review page: shows candidate pairs (name similarity + distance), side-by-side comparison,
    map showing both pins, "Merge", "Keep Both", or "Delete One" buttons.
- Deletion page: flag non-parks, businesses, or duplicates. Shows park detail + map for context.
- Dashboard: verification progress (% verified by county, by source), data quality stats.
- Reads directly from `data/final/parks_latest.json` + `data/overrides/` files.

### Admin UI Features

- [x] **Park review table**: sortable/filterable by county, source, verification status, data quality
- [x] **Field-level verification**: click through each park, mark fields as verified/corrected/flagged
- [x] **Inline editing**: edit name, address, city, phone, URL, coordinates, amenities — writes to `field_edits.json`
- [x] **Map context**: Folium map with satellite layer + nearby parks shown as circle markers
- [x] **Quick links**: Google Maps, Apple Maps, Google satellite, source URL — one click each
- [x] **Dedup review queue**: pairs ranked by similarity score, side-by-side detail + map, field-by-field
      merge builder (pick A or B per field with smart defaults), merge/keep both/delete A/B/both
- [x] **Deletion queue**: flagged non-parks with one-click confirm + restore (undelete)
- [x] **Progress dashboard**: % verified by county/source, unreviewed count, data quality flags,
      Google Places coverage stats
- [x] **Coordinate correction**: click-on-map to set lat/lon (red pin placed, fields auto-populated)
- [x] **Google Places highlighting**: park review and dedup pages prominently display Google rating,
      review count, data date, and all Google extras for every park with Google data
- [x] **Dedup threshold suggestions**: after 5+ merges, suggests threshold adjustments for `deduplicate.py`
- [x] **Overrides survive re-scrapes**: keyed by `source::source_id`, persist across pipeline runs.
      `load_parks()` in data_io.py applies all pending overrides (field edits, merges, deletions)
      in-memory so every admin page sees the effective state immediately.
- [ ] **Bulk actions**: verify all parks in a county, mark source as reviewed, etc.
- [x] **Audit log**: all override files now store timestamps — `deleted_at` in deletions,
      `merged_at` in merges, `_edited_at` in field edits, `verified_at` in verifications.
      Deletions also store the park `name` for readability. Pipeline's `apply_overrides.py`
      and `data_io.py load_parks()` skip `_`-prefixed metadata keys when applying edits.
- [ ] **User-Verified park dedup protection**: user-verified parks should be protected from future dedup merges
      (flag instead of auto-merging)

### Pipeline Integration Steps

- [x] Create `data/overrides/` directory structure with starter files
- [x] Add `apply_overrides()` step to `pipeline.py` (after dedup, before final write)
- [x] Override application order: deletions → merges → field edits → verification stamps
- [x] Log override summary each run (e.g., "Applied 12 field edits, 3 merges, 5 deletions")
- [x] Overrides are idempotent — re-running pipeline with same overrides produces same output

---

## Frontend

- [x] React + TypeScript + Vite project setup
- [x] MapLibre GL JS integration with clustered park markers
- [x] Amenity filter sidebar
- [x] Park detail panel / modal
- [x] Search by name / location
- [x] Is it mobile-friendly?
- [x] Reviews / ratings — Google ratings (stars + review count + data date) displayed in ParkDetail panel
      via `StarRating` component. Reads from `extras.google_rating`, `extras.google_rating_count`,
      `extras.google_data_date`. Links to Google Maps page when available. In-app ratings/reviews
      will come later with backend auth.
- [x] SEO foundations — Added: meta description, theme-color, canonical URL, Open Graph tags (og:title,
      og:description, og:type, og:url), Twitter Card tags, apple-mobile-web-app meta tags, web app manifest.
      **Limitation:** SPA with client-side rendering only — search engines with JS rendering (Google) will
      index fine, but pre-rendering/SSG (e.g. `vite-plugin-ssr` or Next.js migration) would improve
      crawlability for Bing/social link previews. Consider adding `react-helmet-async` for per-park
      meta tags if individual park pages are added.
- [x] Mobile + app-agnostic — Already responsive (mobile bottom sheet, drawer filters, touch-friendly).
      Added PWA manifest (`manifest.json` with standalone display mode, theme color, icon slots).
      **To complete PWA:** Add actual icon files (`public/icons/icon-192.png`, `icon-512.png`), add
      service worker via `vite-plugin-pwa` for offline caching. Framework (React + Vite) is compatible
      with Capacitor/Expo wrapping for native iOS/Android apps.
- [x] List View (like Zillow, e.g., search in area, sort by distance, etc.)
- [x] Sources as actual links, if you click +X more it shows all
- [x] Use Consistent Capitalization for ammenedies
- [X] Highlight selected park (different color maybe?)
- [x] Buy me a coffee integration: buymeacoffee.com/bentontripp
      **DONE:** Added to Header settings dropdown — coffee cup icon + "Buy me a coffee" link
      opens buymeacoffee.com/bentontripp in new tab. Separated from settings options by a divider.

## Amenity Expansion — Game Plan

### Goal

Add 6 new amenities: **Swimming (Lake)**, **Pickleball**, **Swings**, **Playground Ground Surface**,
**Shaded Playground**, **Sandbox**. Design the system so adding future amenities is a one-file change
instead of updating 5+ scattered lists.

### Current State (audit)

Amenity definitions are scattered across **5 independent lists** that have drifted out of sync:

| List | Location | Count | Notes |
|---|---|---|---|
| `CANONICAL_AMENITIES` | `normalize.py` | ~50 keys | Pipeline superset — includes `swings`, `slides`, `sandbox` etc. |
| `AMENITY_COLS` | `admin/data_io.py` | 35 keys | Admin checkbox list — missing `swings`, `slides`, `pavilion`, etc. |
| `AMENITY_COLS` | `export_excel.py` | 26 keys | Excel export subset |
| `FILTERABLE_AMENITIES` | `frontend/park.ts` | 27 entries | User-facing filter checkboxes |
| `AMENITY_LABELS` | `frontend/park.ts` | 42 entries | Display labels (includes `pickleball` label but not filterable) |

**Per-amenity status:**

| Amenity | `CANONICAL` | Admin | Frontend filter | Source data exists? |
|---|---|---|---|---|
| `swimming_pool` | ✅ | ✅ | ❌ (label only) | ✅ wake, civicplus, osm, google, asheville |
| `lake_swimming` | ❌ | ❌ | ❌ | ❌ new — needs manual tagging |
| `pickleball` | ❌ | ❌ | ❌ (label only) | ✅ asheville, civicplus, goldsboro already mapped! |
| `swings` | ✅ | ❌ | ✅ | ✅ osm, playground_explorers, goldsboro, durham |
| `sandbox` | ❌ | ❌ | ❌ | ⚠️ osm → "sandbox", but playground_explorers → "playground" (data loss!) |
| `shaded_playground` | ❌ | ❌ | ❌ | ❌ new — `shaded_areas` exists but is different |
| `playground_surface` | ❌ | ❌ | ❌ | ❌ new — design decision needed (see Phase 3) |

**Quick wins**: `swings` data already exists in parks_latest.json from OSM/goldsboro/durham — just
making it visible in admin + frontend is free. Same for `pickleball` (3+ sources already map it).

**Data loss bug**: `playground_explorers.py` maps `sandbox_available → "playground"` instead of
`"sandbox"` — loses specificity. Fix in Phase 2.

### Phase 0: Single Source of Truth — `amenities.json`

- [x] **Create `amenities.json`** at project root — canonical registry of ALL amenities (66 entries,
      7 categories: Playground, Facilities, Sports, Outdoors, Water, Accessibility, Surface)

```json
[
  { "key": "playground",        "label": "Playground",        "category": "Playground",  "filterable": true },
  { "key": "swings",            "label": "Swings",            "category": "Playground",  "filterable": true },
  { "key": "slides",            "label": "Slides",            "category": "Playground",  "filterable": true },
  { "key": "sandbox",           "label": "Sandbox",           "category": "Playground",  "filterable": true },
  { "key": "shaded_playground", "label": "Shaded Playground", "category": "Playground",  "filterable": true },
  { "key": "splash_pad",        "label": "Splash Pad",        "category": "Playground",  "filterable": true },
  { "key": "fenced_playground", "label": "Fenced Playground", "category": "Playground",  "filterable": true },
  { "key": "swimming_pool",     "label": "Swimming Pool",     "category": "Water",       "filterable": true },
  { "key": "lake_swimming",     "label": "Lake Swimming",     "category": "Water",       "filterable": true },
  { "key": "pickleball",        "label": "Pickleball",        "category": "Sports",      "filterable": true },
  ...
]
```

**Who reads it:**
- **Pipeline** (`normalize.py`): `CANONICAL_AMENITIES = {a["key"] for a in registry}`
- **Admin** (`data_io.py`): `AMENITY_COLS = [a["key"] for a in registry]`
- **Frontend** (`park.ts`): `import registry from '../../../amenities.json'` → derive
  `FILTERABLE_AMENITIES` and `AMENITY_LABELS` automatically
- **Excel export** (`export_excel.py`): same JSON file

**Benefits:**
- Adding a new amenity = add one entry to `amenities.json` + add source `AMENITY_MAP` entries
- No more 5 lists silently drifting out of sync
- Categories, labels, and filterable flags all in one place
- Frontend always matches pipeline — no invisible data

### Phase 1: Create Registry + Update All Readers

- [x] Create `amenities.json` with ALL current amenities (union of all 5 lists + the 6 new ones)
- [x] Update `normalize.py`: derive `CANONICAL_AMENITIES` from registry JSON
- [x] Update `admin/data_io.py`: derive `AMENITY_COLS` + `AMENITY_CATEGORIES` + `AMENITY_LABELS` from registry JSON
- [x] Update `data-pipeline/utils/export_excel.py`: derive its `AMENITY_COLS` from registry JSON
- [x] Update `frontend/src/types/park.ts`: derive `FILTERABLE_AMENITIES` + `AMENITY_LABELS` from registry
- [x] Verify: TypeScript compiles clean, Python imports work, all 66 amenities present

### Phase 2: Pipeline — Fix/Add Source Mappings

- [x] **Fix `playground_explorers.py`**: `sandbox_available → "sandbox"` (was mapping to `"playground"`)
- [x] **Add `pickleball` to OSM**: `_SPORT_MAP["pickleball"] = "pickleball"`
- [ ] **Add `lake_swimming` detection**:
  - OSM: `natural=water` + `sport=swimming` or `leisure=swimming_area` → `lake_swimming`
  - Most sources won't have this; primarily a manual-verification amenity via admin tool
- [ ] **`shaded_playground`**: Primarily manual-verification. Could keyword-scan source descriptions for
  "shaded" near "playground" but false-positive risk is high — better to leave for admin review.
- [ ] **`sandbox`**: Already captured by OSM (`playground:sandpit → sandbox`). Fix playground_explorers
  (above). Other sources don't distinguish sandbox from general playground.
- [ ] Review remaining sources (wake_county, greensboro, civicplus_base, durham_county) for any
  unmapped fields that could feed into the new amenity keys

### Phase 3: Design Decision — Playground Ground Surface

**Options:**

**A) Boolean sub-amenities** (recommended): `surface_rubber`, `surface_wood_chips`, `surface_sand`,
`surface_pea_gravel`, `surface_poured_rubber`
- Pro: Consistent with existing boolean model, directly filterable ("show me parks with rubber surface")
- Pro: Multiple surfaces per park (e.g., rubber under swings + sand in sandbox area)
- Con: Proliferates amenity keys (5+ new entries)

**B) Text field in extras**: `extras.playground_surface = "poured rubber"`
- Pro: Flexible, no amenity schema change
- Con: Not filterable, free-text inconsistency, invisible in amenity checkboxes

**C) Enum amenity**: `playground_surface` with values "rubber|wood_chips|sand|pea_gravel|poured"
- Pro: Structured, single key
- Con: Breaks the `Record<string, boolean>` amenity model, needs FilterPanel dropdown instead of checkbox

**Recommendation**: **Option A** — boolean sub-amenities grouped under a "Surface" category in the
filter panel. Consistent with existing patterns. Most source data won't have this info (primarily a
manual-verification field via admin checkboxes), so the proliferation concern is low.

### Phase 4: Admin Tool

- [x] `AMENITY_COLS` now reads from `amenities.json` → new amenities appear in checkboxes automatically
- [x] Group amenity checkboxes by `category` (from registry) instead of current flat 4-column grid
- [x] No logic changes needed — park_review.py already handles arbitrary amenity keys

### Phase 5: Frontend

- [x] `FILTERABLE_AMENITIES` + `AMENITY_LABELS` derived from registry → new filters auto-appear
- [x] FilterPanel.tsx already groups by category — new categories (Water, Surface) auto-render
- [x] ParkDetailContent.tsx uses `formatAmenityLabel()` fallback — works for unknown keys already
- [x] Reorganized amenities into better categories via registry:
  - `splash_pad` + `swimming_pool` + `lake_swimming` in "Water" category
  - `sandbox`, `shaded_playground`, `fenced_playground` in "Playground" category
  - `pickleball` in "Sports" category
  - Surface types (`surface_rubber`, etc.) in "Surface" category

### Phase 6: Re-run Pipeline + Verify

- [ ] Full pipeline re-run (`python -m data-pipeline.pipeline`)
- [ ] Check amenity counts for newly visible keys (swings/sandbox should have data from OSM/others)
- [ ] Verify admin tool shows new amenity checkboxes grouped by category
- [ ] Verify frontend filters work for new amenities
- [ ] Spot-check parks known to have swings/sandbox (OSM playground sub-tags) to confirm data flows

### Risk Assessment

- **Zero risk to existing data**: All changes are additive. Existing boolean amenity keys are untouched.
  New keys simply won't appear in old records (= not shown, correctly handled everywhere).
- **Data gain from "invisible" amenities**: `swings`, `slides`, and `pickleball` already exist in many
  parks' amenity dicts — they're just not displayed. Making them visible is a free data quality win.
- **Playground Explorers sandbox fix**: Changes 1 mapping. Old records with `playground: true` still
  correct (they ARE playgrounds). New `sandbox: true` adds specificity, doesn't remove anything.
- **Pipeline re-run safe**: `amenities.json` is read-only by the pipeline. Adding keys to
  `CANONICAL_AMENITIES` only affects normalization validation (warns on unknown keys) — existing
  records that already have `swings: true` from OSM will pass through unchanged.

### Files Changed (complete list)

| File | Change |
|---|---|
| `amenities.json` (new) | Canonical amenity registry |
| `data-pipeline/processing/normalize.py` | Read from registry instead of hardcoded set |
| `data-pipeline/sources/playground_explorers.py` | Fix `sandbox_available → "sandbox"` |
| `data-pipeline/sources/osm.py` | Add `pickleball` to `_SPORT_MAP` |
| `admin/data_io.py` | Read from registry instead of hardcoded list |
| `data-pipeline/utils/export_excel.py` | Read from registry instead of hardcoded list |
| `frontend/src/types/park.ts` | Read from registry, derive constants |
| `frontend/src/components/filters/FilterPanel.tsx` | No changes (already reads from `FILTERABLE_AMENITIES`) |
| `frontend/src/components/parks/ParkDetailContent.tsx` | No changes (uses `formatAmenityLabel` fallback) |
| `admin/views/park_review.py` | Minor: group checkboxes by category |

---

## Backend (AWS)

- [ ] DynamoDB table design + SAM template
- [ ] API Gateway + Lambda for park queries
- [ ] User auth (Cognito)
- [ ] Ratings / reviews API
- [ ] Photo upload (S3 + moderation)
- [ ] Park submission + verification workflow
