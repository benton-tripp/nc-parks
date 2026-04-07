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
- [x] Remaining Locations:
    - [x] Triad
- [ ] Make sure all of the locations work/are built into the pipeline (normalization, geocoding, deduping, etc.)
- [ ] OSM amenity enrichment for remaining unmapped child POI tags
- [ ] Reverse geocode remaining ~2,000 OSM parks missing addresses
- [ ] Update Sources to be the URLs
- [ ] Update duplicates (e.g., Wilson's Mills Athletic Complex has three entries)
- [ ] Google Places API - add the max-date of complete google-places from the "raw" data folder into
      the finalized datset (ammeneties, google reviews, locations, addresses, etc.); note there will need
      to be a pre-processing step since it includes things like state/national parks, trampoline parks, etc.;
      Also, it's good for google ratings, but make sure metadata reflects the date of the ratings + rating count.
      There is a lot of rich information here that I had to pay to use, so make good use of it.

---

## Frontend

- [x] React + TypeScript + Vite project setup
- [x] MapLibre GL JS integration with clustered park markers
- [x] Amenity filter sidebar
- [x] Park detail panel / modal
- [x] Search by name / location
- [x] Is it mobile-friendly?
- [ ] Reviews / ratings (from Google initially, we will incorporate in-app ratings/reviews and things like checking in or validating ammenedies or park locations later)
- [ ] Is everything SEO-friendly?
- [ ] Is everything Desktop + mobile friendly, and easily implemented into a mobile app (the end goal is a web + mobile app)?

---

## Backend (AWS)

- [ ] DynamoDB table design + SAM template
- [ ] API Gateway + Lambda for park queries
- [ ] User auth (Cognito)
- [ ] Ratings / reviews API
- [ ] Photo upload (S3 + moderation)
- [ ] Park submission + verification workflow
