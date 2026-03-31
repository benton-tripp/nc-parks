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

NC Parks is a purpose-built tool for parents in North Carolina who want to quickly find playgrounds that match their family's needs — public restrooms, fenced play areas, shade, swings, splash pads, and more. The app combines data from free public sources with community contributions to build the most comprehensive and up-to-date playground directory in the state.

### Problem

Parents waste time driving to parks only to find they lack basic amenities (no restrooms, no shade, broken equipment). Existing map apps show park locations but tell you almost nothing about what's actually there.

### Solution

A filterable, map-first experience with verified community data. Every park has structured amenity tags, ratings, verified visitor counts, and user-submitted photos — so parents know exactly what to expect before they go.

---

## Key Features

### Map & Discovery

- **Interactive map** powered by MapLibre GL JS with high-quality vector tiles
- **Search by location** — address, city, county, or "near me" (geolocation)
- **Filter by amenities** — restrooms, fenced playground, swings, slides, splash pad, shade structures, picnic tables, ADA accessible, parking, trails, etc.
- **Filter by age range** — toddler-friendly, ages 2–5, ages 5–12
- **Cluster view** at low zoom, individual pins with preview cards at higher zoom

### Park Profiles

- Amenity checklist with community-verified statuses
- Overall rating (1–5 stars) plus sub-ratings:
  - Cleanliness
  - Equipment condition
  - Shade / comfort
  - Safety / visibility
  - Toddler-friendliness
- **Verified visitor count** — "X visitors have verified this park"
- User-submitted photos (moderated; no photos containing identifiable people/children)
- Operating hours, address, and directions link
- Last verified / last updated timestamp

### Community Interaction

- **Rate & review** — authenticated users can leave a rating + optional written review
- **Verify a park** — "I was here" check-in (GPS-validated when possible) to confirm the park still exists and is open
- **Submit amenity updates** — crowdsourced corrections ("restrooms are closed," "new swing set added")
- **Submit a new park** — users suggest parks not yet in the database; submissions enter a moderation queue
- **Photo uploads** — community photos with automated moderation (no identifiable people)
- **Flag issues** — report vandalism, closures, safety hazards

### Personalization (future)

- Favorite / bookmark parks
- "Visited" list
- Notifications when a favorited park gets updated

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

### Backend (AWS — minimal cost)

| Service | Purpose |
|---|---|
| **API Gateway (HTTP API)** | REST endpoints; pay-per-request pricing |
| **Lambda (Python)** | Business logic — park CRUD, ratings, moderation, user actions |
| **DynamoDB** | Primary datastore — on-demand capacity, zero idle cost |
| **S3** | Photo storage, static site hosting, data pipeline artifacts |
| **CloudFront** | CDN for static assets and map tiles |
| **Cognito** | User authentication (email/social sign-in) |
| **SES** | Transactional email (verification, notifications) |
| **EventBridge** | Async events (new submission → moderation workflow) |

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
| **Python scripts** | ETL — fetch, parse, normalize, deduplicate park data |
| **Overpass API** | Query OpenStreetMap for `leisure=playground`, `leisure=park` in NC |
| **Open data portals** | City/county/state GIS datasets (Raleigh, Charlotte, NC OneMap, etc.) |
| **Beautiful Soup / Scrapy** | Web scraping for supplemental sources (parks & rec department sites) |
| **Shapely** | Spatial operations — point-in-polygon county assignment, deduplication by proximity |
| **GitHub Actions** | Scheduled pipeline runs (weekly/monthly refresh) |

### Infrastructure as Code

| Tool | Purpose |
|---|---|
| **AWS SAM or CDK** | Define all AWS resources as code; reproducible deployments |

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

### Initial Data Sources (Free)

1. **OpenStreetMap via Overpass API**
   - Query: `leisure=playground`, `leisure=park` within NC bounding box
   - Extracts: name, coordinates, surface type, access, lit, fee tags
   - Refresh: weekly

2. **NC OneMap / State GIS**
   - Parks and recreation facility layers
   - Municipal boundaries for county/city tagging

3. **City/County Open Data Portals**
   - **Wake County ArcGIS** — 291 parks with 42 amenity flags ✅ *implemented*
   - Charlotte Open Data — park facilities *(stub)*
   - Durham, Greensboro, Winston-Salem, Fayetteville, etc. *(planned)*
   - Mecklenburg County GIS *(planned)*

4. **Web Scraping (supplemental)**
   - Municipal parks & recreation department websites
   - Amenity details not available in structured data
   - Respectful crawling with rate limits and robots.txt compliance

### Data Model (DynamoDB)

**Parks Table**

```
PK: PARK#<uuid>
SK: METADATA

Attributes:
  name: string
  slug: string
  location: { lat, lng }
  geohash: string              # for geo queries
  county: string
  city: string
  address: string
  source: string               # "osm", "raleigh_opendata", "user_submitted"
  sourceId: string             # original ID from source
  amenities: Map {
    restrooms: boolean | null
    fencedPlayground: boolean | null
    swings: boolean | null
    slides: boolean | null
    splashPad: boolean | null
    shadedAreas: boolean | null
    picnicTables: boolean | null
    pavilion: boolean | null
    adaAccessible: boolean | null
    parking: boolean | null
    drinkingWater: boolean | null
    trails: boolean | null
    basketballCourt: boolean | null
    tennisCourt: boolean | null
    openField: boolean | null
  }
  ageRange: list<string>       # ["toddler", "2-5", "5-12"]
  avgRating: number
  ratingCount: number
  verifiedVisitors: number
  photoCount: number
  status: string               # "active", "pending_review", "closed"
  lastVerified: string         # ISO timestamp
  createdAt: string
  updatedAt: string
```

**Ratings Table**

```
PK: PARK#<uuid>
SK: RATING#<userId>#<timestamp>

Attributes:
  overall: number (1-5)
  cleanliness: number (1-5)
  equipmentCondition: number (1-5)
  shade: number (1-5)
  safety: number (1-5)
  toddlerFriendly: number (1-5)
  review: string (optional, max 1000 chars)
  visitDate: string
```

**Verifications Table**

```
PK: PARK#<uuid>
SK: VERIFY#<userId>#<timestamp>

Attributes:
  lat: number                  # user's location at check-in
  lng: number
  amenityUpdates: Map          # optional corrections
  status: string               # "confirmed", "reported_issue"
  note: string
```

**User Submissions Table**

```
PK: SUBMISSION#<uuid>
SK: METADATA

Attributes:
  type: string                 # "new_park", "amenity_update", "photo", "issue_report"
  submittedBy: string          # userId
  parkId: string               # null for new park submissions
  data: Map                    # submission payload
  status: string               # "pending", "approved", "rejected"
  moderatedBy: string
  createdAt: string
```

### Deduplication Strategy

Parks appear in multiple sources. The pipeline deduplicates by:

1. **Spatial proximity** — parks within ~50m of each other are candidates for merging
2. **Name similarity** — fuzzy string matching (Levenshtein / Jaro-Winkler)
3. **Manual review queue** — ambiguous matches flagged for manual resolution
4. Merged records retain all source IDs for future refresh reconciliation

---

## Project Structure

```
nc-parks/
├── README.md
│
├── frontend/                    # React SPA
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── map/             # MapLibre map, markers, clusters, popups
│   │   │   ├── parks/           # Park cards, detail view, amenity badges
│   │   │   ├── filters/         # Amenity filter panel, search bar
│   │   │   ├── ratings/         # Star ratings, review form, sub-ratings
│   │   │   ├── photos/          # Photo gallery, upload flow
│   │   │   ├── submissions/     # New park form, amenity correction form
│   │   │   ├── auth/            # Login, signup, profile
│   │   │   └── layout/          # Header, footer, sidebar, nav
│   │   ├── hooks/               # Custom hooks (useParks, useFilters, useGeolocation)
│   │   ├── api/                 # API client functions
│   │   ├── types/               # TypeScript interfaces
│   │   ├── utils/               # Helpers (geo, formatting)
│   │   ├── pages/               # Route-level components
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── index.html
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── package.json
│
├── backend/                     # AWS Lambda functions
│   ├── functions/
│   │   ├── parks/               # GET /parks, GET /parks/:id
│   │   ├── ratings/             # POST /parks/:id/ratings
│   │   ├── verifications/       # POST /parks/:id/verify
│   │   ├── submissions/         # POST /submissions
│   │   ├── photos/              # POST /parks/:id/photos (presigned URL)
│   │   ├── moderation/          # Admin review endpoints
│   │   └── auth/                # Cognito triggers (post-confirmation, etc.)
│   ├── shared/                  # Shared utilities, DB helpers
│   ├── requirements.txt
│   └── template.yaml            # AWS SAM template
│
├── data/                        # Pipeline output (gitignored)
│   ├── raw/                     # Cached API responses per source
│   ├── processed/               # After normalize + enrich
│   ├── final/                   # Deduplicated output (parks_latest.json)
│   └── reference/               # County boundaries GeoJSON
│
├── data-pipeline/               # ETL scripts
│   ├── sources/
│   │   ├── wake_county.py       # Wake County ArcGIS open data
│   │   ├── county_boundaries.py # NC county boundary polygons
│   │   ├── osm.py               # Overpass API queries (stub)
│   │   ├── charlotte.py         # Charlotte open data (stub)
│   │   ├── nc_onemap.py         # State GIS layers (stub)
│   │   └── scraper.py           # Generic parks & rec scraper (stub)
│   ├── processing/
│   │   ├── normalize.py         # Standardize schemas
│   │   ├── deduplicate.py       # Spatial + fuzzy dedup
│   │   ├── geocode.py           # Reverse geocode for missing addresses
│   │   └── enrich.py            # Point-in-polygon county assignment + geohash
│   ├── load.py                  # Write to DynamoDB
│   ├── pipeline.py              # Orchestrator
│   ├── requirements.txt
│   └── tests/
│
├── .github/
│   └── workflows/
│       ├── deploy-frontend.yml  # Build + deploy React to S3/CloudFront
│       ├── deploy-backend.yml   # SAM build + deploy
│       └── data-refresh.yml     # Scheduled pipeline run
│
└── docs/
    ├── data-sources.md          # Detailed source documentation
    ├── api.md                   # API endpoint reference
    └── moderation.md            # Content moderation guidelines
```

---

## Getting Started

### Prerequisites

- Node.js 20+
- Python 3.12+
- AWS CLI v2 (configured with credentials)
- AWS SAM CLI
- Git

### Frontend

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

Environment variables (`.env.local`):
```
VITE_API_URL=http://localhost:3000
VITE_MAPTILER_KEY=your_key_here
VITE_COGNITO_USER_POOL_ID=us-east-1_xxxxx
VITE_COGNITO_CLIENT_ID=xxxxx
```

### Backend (local)

```bash
cd backend
pip install -r requirements.txt
sam local start-api
# API available at http://localhost:3000
```

### Data Pipeline

```bash
cd data-pipeline
pip install -r requirements.txt

# Run from project root:
python data-pipeline/pipeline.py                          # all registered sources
python data-pipeline/pipeline.py -s wake_county            # single source
python data-pipeline/pipeline.py --refresh-boundaries      # re-fetch county polygons
python data-pipeline/pipeline.py --dry-run                 # process without saving
python data-pipeline/pipeline.py -v                        # verbose/debug logging
```

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

### Initial Setup

1. **Domain** — Register or point a domain (e.g., `nc-parks.com`) to CloudFront
2. **AWS account** — Create a dedicated AWS account or use an isolated profile
3. **SAM deploy** — `cd backend && sam build && sam deploy --guided`
4. **Frontend deploy** — Build and sync to S3: `npm run build && aws s3 sync dist/ s3://your-bucket`
5. **CloudFront** — Invalidate cache on deploy

### CI/CD

GitHub Actions workflows handle:

- **Frontend:** lint → test → build → deploy to S3 → CloudFront invalidation
- **Backend:** lint → test → SAM build → SAM deploy
- **Data pipeline:** scheduled weekly run (cron) + manual trigger

### Cost Optimization Notes

- DynamoDB on-demand mode — no cost when idle, scales automatically
- Lambda — only runs when called; no idle servers
- S3 + CloudFront — static hosting is pennies; CDN absorbs traffic spikes
- Cognito — free up to 50K monthly active users
- No RDS, no ECS, no EC2 — zero always-on compute
- Consider S3 Intelligent-Tiering for photos if storage grows

---

## Mobile Strategy

The frontend is built with React specifically to enable a future mobile path:

1. **Phase 1 (now):** Responsive React web app — works well on mobile browsers
2. **Phase 2:** PWA enhancements — offline support, "Add to Home Screen," push notifications
3. **Phase 3:** React Native app — share business logic, API layer, and TypeScript types; rebuild UI components with React Native equivalents

The API-first backend design means the mobile app consumes the exact same endpoints as the web app — no backend changes needed.

---

## Roadmap

### Phase 1 — MVP

- [ ] Data pipeline: OSM + 2–3 city open data sources
- [ ] Map view with park markers and clustering
- [ ] Amenity filters (restrooms, fenced, swings, shade, etc.)
- [ ] Basic park detail page with amenity checklist
- [ ] User auth (Cognito)
- [ ] Star ratings and sub-ratings
- [ ] "I was here" verification

### Phase 2 — Community

- [ ] User reviews (text)
- [ ] Photo uploads with moderation
- [ ] Submit new park flow
- [ ] Amenity correction submissions
- [ ] Moderation admin dashboard
- [ ] Additional data sources (more cities/counties)

### Phase 3 — Polish

- [ ] PWA (offline, installable)
- [ ] Favorites and visited lists
- [ ] "Parks near me" push notifications
- [ ] Directions integration (Google Maps / Apple Maps deep links)
- [ ] Social sharing (park cards)
- [ ] SEO — server-side rendered park pages for search indexing

### Phase 4 — Mobile App

- [ ] React Native app (iOS + Android)
- [ ] Native camera integration for photo uploads
- [ ] Background location for check-in verification

---

## License

TBD — will be determined before public release.
