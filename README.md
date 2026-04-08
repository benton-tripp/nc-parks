# NC Parks — North Carolina Playground Finder

A community-driven web application helping parents find the perfect playground in North Carolina. Search, filter, rate, and verify parks based on the amenities that matter most to your family.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Data Sources & Pipeline](#data-sources--pipeline)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Infrastructure & Deployment](#infrastructure--deployment)
- [Mobile Strategy](#mobile-strategy)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

NC Parks is a purpose-built tool for parents in North Carolina who want to quickly find playgrounds that match their family's needs — public restrooms, fenced play areas, shade, swings, splash pads, and more. The app combines data from 22 public sources (4,798 parks) with a local admin review tool to build the most comprehensive playground directory in the state.

### Problem

Parents waste time driving to parks only to find they lack basic amenities (no restrooms, no shade, broken equipment). Existing map apps show park locations but tell you almost nothing about what's actually there.

### Solution

A filterable, map-first experience with verified data. Every park has structured amenity tags, Google Places ratings when available, and admin-verified fields — so parents know exactly what to expect before they go.

---

## Key Features

### Map & Discovery

- **Interactive map** powered by MapLibre GL JS with vector tiles
- **Search by name** with real-time filtering
- **Filter by amenities** — restrooms, fenced playground, swings, slides, splash pad, shade structures, picnic tables, ADA accessible, parking, trails, etc.
- **Cluster view** at low zoom, individual pins at higher zoom
- **List/map toggle** on mobile — switch between map view and scrollable park list
- **Selected park highlighting** — distinct marker color for the active park

### Park Profiles

- Amenity checklist with structured boolean flags (35 amenities)
- Google Places ratings (stars + review count + data date) when available
- Links to Google Maps, Apple Maps, source website
- All data sources listed per park
- Address, city, county

### Community (Planned)

- Rate & review parks (requires backend auth — not yet implemented)
- "I was here" check-in verification
- Submit amenity updates and new parks
- Photo uploads with moderation

---

## Tech Stack

### Frontend

| Technology | Purpose |
|---|---|
| **React 18+** | UI framework — component model, ecosystem, and path to mobile via React Native |
| **TypeScript** | Type safety across the codebase |
| **Vite** | Fast dev server and optimized production builds |
| **MapLibre GL JS** | Open-source map rendering with vector tiles (no vendor lock-in) |
| **TanStack Query** | Server state management, caching, background refetching |
| **React Router** | Client-side routing |
| **Tailwind CSS** | Utility-first styling for rapid UI development |

### Backend (Planned — AWS)

| Service | Purpose |
|---|---|
| **API Gateway (HTTP API)** | REST endpoints; pay-per-request pricing |
| **Lambda (Python)** | Business logic — park CRUD, ratings, moderation |
| **DynamoDB** | Primary datastore — on-demand capacity, zero idle cost |
| **S3** | Photo storage, static site hosting |
| **CloudFront** | CDN for static assets and map tiles |
| **Cognito** | User authentication |

> **Note:** The backend is not yet implemented. The `backend/` directory contains skeleton structure only (`template.yaml` is empty). The app currently runs entirely from static JSON data produced by the pipeline.

### Map Tiles

| Option | Notes |
|---|---|
| **MapTiler Free Tier** | High-quality vector basemap; generous free tier for low-traffic apps |
| **OpenFreeMap** | Fully free, self-hostable OSM vector tiles (no API key) |
| **PMTiles on S3/CloudFront** | Self-hosted NC-only tile extract; zero per-request cost after initial generation |

> **Recommended starting approach:** Use MapTiler's free tier for development and early launch. Evaluate PMTiles (NC extract from OpenStreetMap) for cost-free production tiles as traffic grows.

### Data Pipeline

| Tool | Purpose |
|---|---|
| **Python scripts** | ETL — fetch, parse, normalize, geocode, enrich, validate, deduplicate, apply overrides |
| **Overpass API** | Query OpenStreetMap for `leisure=playground`, `leisure=park` in NC |
| **Google Places API** | 2,751 parks with ratings, reviews, types (pre-fetched data, no live API calls in pipeline) |
| **Open data portals** | City/county ArcGIS REST APIs (Wake County, Charlotte, etc.) |
| **Beautiful Soup** | Web scraping for municipal parks & rec sites |
| **Shapely** | Point-in-polygon county assignment, spatial deduplication |
| **Nominatim** | Forward + reverse geocoding with persistent backoff |

### Admin Review Tool

| Tool | Purpose |
|---|---|
| **Streamlit** | Local admin UI for park verification, editing, dedup review |
| **Folium** | Interactive maps with satellite imagery in admin pages |
| **streamlit-folium** | Streamlit integration for Folium maps |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        CloudFront CDN                       │
│              (static site + photos + tile cache)            │
└──────────┬──────────────────────────────┬───────────────────┘
           │                              │
     ┌─────▼──────┐              ┌────────▼────────┐
     │  S3 Bucket  │              │  API Gateway    │
     │ (React SPA) │              │  (HTTP API)     │
     └─────────────┘              └────────┬────────┘
                                           │
                                  ┌────────▼────────┐
                                  │  Lambda Functions│
                                  │  (Python)        │
                                  └──┬─────┬─────┬──┘
                                     │     │     │
                              ┌──────▼┐ ┌──▼──┐ ┌▼───────┐
                              │Dynamo │ │ S3  │ │Cognito │
                              │  DB   │ │Photos│ │ Auth   │
                              └───────┘ └─────┘ └────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Data Pipeline (offline)                   │
│                                                             │
│  OSM Overpass ──┐                                           │
│  Open Data ─────┼──► Python ETL ──► DynamoDB / S3           │
│  Web Scraping ──┘    (GitHub Actions)                       │
└─────────────────────────────────────────────────────────────┘
```

### Cost Profile

The architecture is designed around **pay-per-use** services with generous free tiers:

| Service | Free Tier | Expected Early Cost |
|---|---|---|
| Lambda | 1M requests/mo | $0 |
| API Gateway (HTTP) | 1M requests/mo | $0 |
| DynamoDB (on-demand) | 25 GB storage, 25 RCU/WCU | $0 |
| S3 | 5 GB storage | < $1/mo |
| CloudFront | 1 TB transfer/mo | $0 |
| Cognito | 50,000 MAU | $0 |
| **Total (early stage)** | | **~$0–$5/mo** |

---

## Data Sources & Pipeline

### Current Data (4,798 parks from 22 sources)

| Source | Parks | Method |
|---|---|---|
| OSM (Statewide) | 2,673 | Overpass API + child POI amenity enrichment |
| Google Places | 1,467 | Pre-fetched API data (ratings, reviews, types) |
| Wake County | 279 | ArcGIS REST API (42 amenity flags) |
| Charlotte | 68 | ArcGIS / open data portal |
| Playground Explorers | 57 | RSC flight data parsing |
| Mecklenburg County | 51 | ArcGIS REST API |
| Greensboro | 36 | Web scraper (undetected-chromedriver) |
| Wilmington | 34 | PDF parsing (pyMuPDF) |
| Johnston County | 30 | Web scraper |
| Southern Pines | 22 | CivicPlus scraper |
| Lexington | 20 | Web scraper |
| New Bern | 18 | Web scraper |
| Elizabeth City | 10 | Web scraper |
| High Point | 9 | Web scraper (CivicPlus) |
| Nash County | 8 | CivicPlus scraper |
| Alamance County | 6 | Web scraper |
| Graham | 2 | Web scraper |
| Manteo | 2 | Web scraper |
| Goldsboro | 2 | Web scraper |
| NC Triad Outdoors | 2 | Web scraper |
| Kill Devil Hills | 1 | Static page scraper |
| New Hanover County | 1 | PDF parsing |

### Pipeline Steps

1. **Fetch** — pull data from all registered sources (or load from cached raw files with `--skip-fetch`)
2. **Normalize** — standardize to canonical schema (name, address, city, county, coords, amenities, source, source_id)
3. **Geocode** — forward + reverse geocoding via Nominatim with persistent backoff
4. **Enrich** — county assignment via point-in-polygon + nearest-county fallback for coastal parks
5. **Validate URLs** — check source URLs for liveness
6. **Deduplicate** — spatial proximity (haversine) + fuzzy name matching with facility-type guards
7. **Apply Overrides** — apply manual deletions, merges, field edits, and verification stamps from `data/overrides/`
8. **Save** — timestamped JSON + `parks_latest.json` + auto-copy to `frontend/public/data/`

4. **Web Scraping (supplemental)**
   - Municipal parks & recreation department websites via Beautiful Soup
   - Reusable CivicPlus scraper base class for CivicPlus-powered sites
   - Rate-limited, respectful crawling with robots.txt compliance

### Override System

The admin tool writes manual corrections to `data/overrides/`:

- **`deletions.json`** — park keys to exclude (non-parks, businesses, duplicates)
- **`manual_merges.json`** — explicit merge instructions (keep park A, drop park B, with optional field overrides)
- **`field_edits.json`** — per-park field corrections (name, address, coords, amenities, etc.)
- **`verifications.json`** — per-park per-field verification status and timestamps

Overrides are applied both in the pipeline (`apply_overrides.py`) and in the admin UI (`data_io.py load_parks()`) so changes are visible immediately.

---

## Project Structure

```
nc-parks/
├── README.md
├── TODO.md
│
├── admin/                       # Streamlit admin review tool
│   ├── app.py                   # Entry point — sidebar nav, page routing
│   ├── data_io.py               # Shared data loading (applies all overrides in-memory)
│   └── views/
│       ├── dashboard.py         # Verification progress, data quality stats
│       ├── park_review.py       # Browse, verify, edit individual parks
│       ├── dedup_review.py      # Duplicate detection + field-by-field merge builder
│       └── deletions.py         # Manage parks marked for deletion
│
├── frontend/                    # React SPA
│   ├── public/
│   │   └── data/
│   │       └── parks_latest.json  # Auto-copied from pipeline output
│   ├── src/
│   │   ├── components/
│   │   │   ├── map/             # ParkMap (MapLibre GL, clusters, markers)
│   │   │   ├── parks/           # ParkCard, ParkDetail, ParkDetailContent, ParkListPanel
│   │   │   ├── filters/         # FilterPanel (search + amenity toggles)
│   │   │   ├── ratings/         # StarRating (Google Places ratings display)
│   │   │   └── layout/          # Header (settings dropdown, Buy Me a Coffee)
│   │   ├── hooks/               # useParks, useFilters, useMapProvider
│   │   ├── api/                 # parks.ts (fetch + parse parks_latest.json)
│   │   ├── types/               # park.ts (TypeScript interfaces)
│   │   ├── pages/               # MapPage.tsx
│   │   ├── App.tsx              # Router (single route → MapPage)
│   │   └── main.tsx
│   ├── index.html
│   ├── tailwind.config.ts
│   ├── vite.config.ts
│   └── package.json
│
├── backend/                     # AWS Lambda functions (planned — not yet implemented)
│   ├── functions/               # Skeleton dirs: auth, moderation, parks, photos, ratings, etc.
│   ├── shared/
│   ├── requirements.txt
│   └── template.yaml            # AWS SAM template (empty)
│
├── data/                        # Pipeline data (gitignored)
│   ├── raw/                     # Timestamped snapshots per source
│   ├── processed/               # Post-normalize, post-enrich
│   ├── final/                   # Deduplicated output (parks_latest.json)
│   ├── overrides/               # Manual corrections from admin tool
│   │   ├── deletions.json
│   │   ├── manual_merges.json
│   │   ├── field_edits.json
│   │   └── verifications.json
│   └── reference/               # County boundaries GeoJSON
│
├── data-pipeline/               # ETL pipeline
│   ├── pipeline.py              # Orchestrator (27 registered sources)
│   ├── load.py                  # DynamoDB loader (future use)
│   ├── requirements.txt
│   ├── sources/                 # 27+ source modules (wake_county.py, osm.py, google_places.py, ...)
│   ├── processing/              # normalize, deduplicate, geocode, enrich, validate_urls, apply_overrides
│   ├── utils/                   # cleanup, export_excel, warm_cache
│   └── tests/
│
└── docs/
    ├── data-sources.md
    ├── api.md
    ├── counties.md
    ├── source-analysis.md
    └── moderation.md
```

---

## Getting Started

### Prerequisites

- Node.js 20+
- Python 3.12+
- Git

### Frontend

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

### Admin Review Tool

```bash
pip install streamlit streamlit-folium folium
streamlit run admin/app.py
# Opens at http://localhost:8501
```

The admin tool reads `data/final/parks_latest.json` and writes corrections to `data/overrides/`. All four pages (Dashboard, Park Review, Dedup Review, Deletions) apply pending overrides in-memory so changes are visible immediately without re-running the pipeline.

### Data Pipeline

```bash
cd data-pipeline
pip install -r requirements.txt

# Run from project root:
python data-pipeline/pipeline.py                          # all registered sources
python data-pipeline/pipeline.py -s wake_county            # single source
python data-pipeline/pipeline.py -s wake_county -s osm     # multiple sources
python data-pipeline/pipeline.py --skip-fetch              # re-normalize from cached raw files
python data-pipeline/pipeline.py --skip-geocode            # skip reverse geocoding step
python data-pipeline/pipeline.py --skip-fetch --skip-geocode  # fast reprocess from raw cache
python data-pipeline/pipeline.py --reprocess               # re-run geocode/enrich/dedup on parks_latest.json
python data-pipeline/pipeline.py --geocode-batch 200       # limit geocode API calls (≈1 req/sec)
python data-pipeline/pipeline.py --refresh-boundaries      # re-download county boundary polygons
python data-pipeline/pipeline.py --dry-run                 # process without writing final output
python data-pipeline/pipeline.py -v                        # verbose/debug logging
```

| Flag | Short | Description |
|---|---|---|
| `--source NAME` | `-s` | Run only the named source(s). Repeatable. Default: all registered sources. |
| `--skip-fetch` | | Load from latest raw files on disk instead of re-fetching from APIs/scrapers. |
| `--skip-geocode` | | Skip the Nominatim reverse-geocode step entirely. |
| `--reprocess` | | Load `parks_latest.json` and re-run geocode → enrich → validate → dedup → save (skips fetch + normalize). |
| `--geocode-batch N` | | Cap the number of geocode API calls per run (0 = unlimited). Nominatim rate: ≈1 req/sec. |
| `--refresh-boundaries` | | Re-download NC county boundary polygons from the Census Bureau. |
| `--dry-run` | `-n` | Run the full pipeline but don't write final output files. |
| `--verbose` | `-v` | Enable debug-level logging. |

Output lands in `data/` (gitignored):

- `data/raw/` — timestamped snapshots of each source
- `data/processed/` — post-normalize, post-enrich
- `data/final/parks_latest.json` — deduplicated, ready for frontend or DynamoDB load
- `data/reference/nc_counties.geojson` — 100 county boundary polygons

### Test Map

After running the pipeline, verify the data visually:

```bash
python -m http.server 8080
# Open http://localhost:8080/test-map.html
```

This loads `parks_latest.json` as clustered markers and `nc_counties.geojson` as boundary outlines on a MapLibre GL JS map — the same rendering approach the production frontend will use.

---

## Infrastructure & Deployment

Not yet deployed. The app currently runs locally:

- **Frontend:** `npm run dev` → localhost:5173
- **Admin tool:** `streamlit run admin/app.py` → localhost:8501
- **Pipeline:** `python data-pipeline/pipeline.py` → writes to `data/final/`

Future deployment plan: React SPA on S3/CloudFront, API Gateway + Lambda backend, DynamoDB datastore. See `backend/` for planned structure.

---

## Mobile Strategy

The frontend is built as a responsive React web app that works well on mobile browsers. A future React Native app could share TypeScript types and API layer with the web app.

---

## Roadmap

### Done

- [x] Data pipeline: 22 active sources producing 4,798 parks
- [x] Google Places integration (ratings, reviews, types)
- [x] Map view with park markers, clustering, and list view
- [x] Amenity filters + search
- [x] Park detail panel with Google ratings
- [x] Admin review tool: park verification, field editing, dedup merge builder, deletion management
- [x] Override system integrated into pipeline
- [x] SEO foundations + PWA manifest
- [x] Buy Me a Coffee integration

### Next

- [ ] AWS backend (API Gateway + Lambda + DynamoDB + Cognito)
- [ ] User auth and community ratings/reviews
- [ ] Photo uploads with moderation
- [ ] Submit new park / amenity corrections
- [ ] PWA offline support (service worker via vite-plugin-pwa)
- [ ] Admin bulk actions + audit log
- [ ] Remaining 5 source scrapers (Henderson County, Durham, Fayetteville, Asheville, Wilson)

### Future

- [ ] React Native mobile app
- [ ] Favorites and visited lists
- [ ] Server-side rendering for SEO
- [ ] Geolocation-based "near me" search

---

## License

TBD — will be determined before public release.
