# NC Parks/Playgrounds Source Scrapability Analysis

**Date:** 2026-04-02

---

## 1. nctriadoutdoors.com/playgrounds/

| Field | Details |
|-------|---------|
| **Data Available** | Park names, brief descriptions, thumbnail photos. No addresses or coordinates on the listing page (individual park pages may have more). |
| **Data Structure** | Static HTML. Park cards rendered server-side with `<h3>` headings and descriptions inside standard WordPress markup. |
| **CMS** | **WordPress** (wp-content paths visible in image URLs) |
| **Scraping Method** | `requests` + `BeautifulSoup` sufficient. Static HTML, no JS rendering needed. |
| **Approx Count** | ~10 parks on the playgrounds page (Volunteer Park, Shaffner Park, Hester Park, Happy Hill Park, Asheboro Memorial Park, Freedom Park Liberty, Fourth of July Park, North Asheboro Park, Red Slide Park, Allen Jay Park). Focused on NC Triad region. |
| **API Endpoints** | None discovered. Standard WordPress site — could try `/wp-json/wp/v2/posts` or `/wp-json/wp/v2/pages` if REST API is enabled. Check for custom post types at `/wp-json/wp/v2/places`. |
| **Anti-scraping** | None observed. |
| **Value Assessment** | **Low-Medium**. Small dataset, Triad region only. Individual park pages likely have addresses. Worth scraping individual park URLs (e.g., `/places/volunteer-park/`) for full details. |

---

## 2. southernpines.net/591/Parks-Playgrounds

| Field | Details |
|-------|---------|
| **Data Available** | Park names, locations/addresses, detailed amenity lists (Playground, Basketball Court, Shelter, Restrooms, Tennis Courts, etc.), rental info, photos, hours. |
| **Data Structure** | Static HTML rendered in table layout. Each park is a table row with image, name, description, address, and amenity list. Well-structured and parseable. |
| **CMS** | **CivicPlus** (footer: "Government Websites by CivicPlus®") |
| **Scraping Method** | `requests` + `BeautifulSoup` sufficient. All content server-rendered. |
| **Approx Count** | ~13 parks/facilities (Blanchie Carter Discovery Park, Campbell House Park, Downtown Park, E.S. Douglass Community Center, Elizabeth High Rounds Park, Sports Park, Martin Park, Memorial Park, J. Pleasant Hines Park, Sandhurst Park, Reservoir Park, Whitehall, plus others) |
| **API Endpoints** | CivicPlus sites sometimes expose `/api/` endpoints but nothing discovered in page source. |
| **Anti-scraping** | None observed. Standard CivicPlus template. |
| **Value Assessment** | **Medium**. Good structured data for Southern Pines specifically. Addresses and amenities are extractable from the table layout. Single municipality. |

---

## 3. accessibleplayground.net/united-states/north-carolina/

| Field | Details |
|-------|---------|
| **Data Available** | Park names, addresses, detailed accessibility descriptions (ADA features, surface types, swing types, ramp access, sensory equipment). Some location data. Photos for some entries. Organized by city. |
| **Data Structure** | Static HTML. Parks grouped under `<h4>` city headings with description paragraphs and links to external park sites. Also references a separate **Playground Directory** at `/playground-directory/pg/1/?cn-cat=49`. |
| **CMS** | **WordPress** (Icelander theme, wp-login.php, Akismet) |
| **Scraping Method** | `requests` + `BeautifulSoup` sufficient. Static content. |
| **Approx Count** | ~20-25 playgrounds listed on the NC page (Cary, Concord, East Flat Rock, Hickory, Huntersville, multiple Mecklenburg County parks, Raleigh, Shelby, Winston-Salem). The separate directory may have more. |
| **API Endpoints** | WordPress REST API may be available (`/wp-json/wp/v2/`). The Playground Directory likely uses a WordPress plugin with pagination (`/pg/1/`). |
| **Anti-scraping** | None observed. |
| **Value Assessment** | **Medium**. Niche but valuable — accessibility-focused data not available elsewhere. Good supplement for ADA/inclusive features. Should also scrape the Playground Directory for additional entries. |

---

## 4. houseofhensen.com/blog/my-favorite-charlotte-area-playgrounds

| Field | Details |
|-------|---------|
| **Data Available** | Park names, general locations (neighborhood/area), addresses (some), detailed qualitative reviews (fencing, shade, crowds, toddler-friendliness), photo mentions (Instagram Reels). No coordinates or structured amenity data. |
| **Data Structure** | Blog post format. Parks in `<h3>` headings, freeform text descriptions. Unstructured prose, not tabular. |
| **CMS** | **Squarespace** (squarespace-based blog URL patterns, author link format) |
| **Scraping Method** | `requests` + `BeautifulSoup` sufficient for HTML. Content is server-rendered. |
| **Approx Count** | ~12 playgrounds (Airport Overlook, William Davie Park, Park Road Park, Freedom Park, Stream Park, Crooked Creek Park, Squirrel Lake Park, Pineville Lake Park, Nevin Community Park, Rosedale Park, Eastway Rec Center, plus others) |
| **API Endpoints** | None. Squarespace doesn't expose public APIs easily. |
| **Anti-scraping** | None observed. |
| **Value Assessment** | **Low**. Blog content — unstructured, opinion-based, Charlotte area only. Would require NLP to extract structured data. Better as a reference/validation source than a primary data source. Some addresses are embedded in text with 📍 emoji markers. |

---

## 5. playgroundexplorers.com/playgrounds/north-carolina

| Field | Details |
|-------|---------|
| **Data Available** | Park names, cities, type (Indoor/Outdoor, Public/Commercial), pricing (Free/Paid), amenities (Restrooms, Accessible, Water features), photos, links to individual detail pages with Google Reviews. |
| **Data Structure** | **Likely JavaScript-rendered**. Card-based grid layout with filters (amenities, city, type). Lists 141 playgrounds across 34 cities. Pagination present ("Previous 1 2 Next"). Individual playground pages at structured URLs like `/playgrounds/north-carolina/fayetteville/north-carolina-veterans-park`. |
| **CMS** | **Custom/React-based** (Gate City Labs, LLC). Modern SPA-style site. |
| **Scraping Method** | **Likely needs Selenium/headless browser** OR look for underlying API. The filtering and pagination suggest a backend API serving JSON data. Check Network tab for XHR requests to an API — highly likely there's a REST or GraphQL API behind the card listings. |
| **Approx Count** | **141 playgrounds** (117 outdoor, 24 indoor) across 34 NC cities. Top cities: Fayetteville (24), Charlotte (16), Greensboro (16), Durham (14), Asheville (6). |
| **API Endpoints** | **HIGH PRIORITY to investigate**. The filtering/sorting/pagination strongly suggest a backend API. Try: `/api/playgrounds`, `/api/v1/playgrounds?state=north-carolina`, or examine network requests. The structured URL pattern suggests a well-organized data model. |
| **Anti-scraping** | Unknown — needs browser investigation. May have rate limiting. |
| **Value Assessment** | **HIGH**. Best single source found — 141 playgrounds with structured data, amenities, accessibility info, photos, and city organization. If an API exists, this is gold. Even without API, individual detail pages have rich data. Priority source. |

---

## 6. nashcountync.gov/745/Parks-Facilities

| Field | Details |
|-------|---------|
| **Data Available** | Park names, full addresses, detailed amenity descriptions (baseball fields, basketball courts, playgrounds, walking trails, soccer fields, shelters, restrooms), hours of operation, photo galleries with multiple images per park. |
| **Data Structure** | Static HTML. Each park in its own `<h2>` section with address, description, and image carousel (numbered images). Well-structured and consistent across entries. |
| **CMS** | **CivicPlus** (footer: "Government Websites by CivicPlus®", standard CivicPlus URL pattern `/745/Parks-Facilities`) |
| **Scraping Method** | `requests` + `BeautifulSoup` sufficient. All content server-rendered. Images served from `/ImageRepository/Document?documentID=`. |
| **Approx Count** | ~7 parks (Nash County Miracle Park at Coopers, Bailey/Middlesex Community Park, J.W. Glover Memorial Park, Spring Hope Community Park, W.B. Ennis Memorial Park, Castalia Community Park, plus at least one more from image carousel) |
| **API Endpoints** | CivicPlus ImageRepository API visible: `/ImageRepository/Document?documentID=XXXX`. Standard CivicPlus structure. |
| **Anti-scraping** | None observed. Standard government site. |
| **Value Assessment** | **Medium**. Good structured data for Nash County. Addresses and amenities cleanly extractable. Small dataset but high quality. |

---

## 7. manteonc.gov/community/visitors/parks-and-playgrounds

| Field | Details |
|-------|---------|
| **Data Available** | Park/playground names, descriptions, addresses (some), photos. No coordinates or structured amenity lists — descriptions are narrative. |
| **Data Structure** | Static HTML. Parks described with `<h3>` headings and narrative paragraphs. Somewhat inconsistent formatting across entries. Photos from `/Home/ShowPublishedImage/`. |
| **CMS** | **Granicus** (footer: "Created By Granicus - Connecting People & Government") |
| **Scraping Method** | `requests` + `BeautifulSoup` sufficient. Server-rendered content. |
| **Approx Count** | ~7 parks/locations (Downtown Waterfront Playground, Jule's Park, Magnolia Pavilion, Edwards Landing, Manteo Skate Park, Cartwright Park, Collis Playground) |
| **API Endpoints** | Granicus standard image endpoint: `/Home/ShowPublishedImage/`. Calendar component API: `/Home/Components/Calendar/Event/`. |
| **Anti-scraping** | None observed. |
| **Value Assessment** | **Low-Medium**. Small dataset (Manteo only). Some addresses mentioned inline. Useful for Dare County coverage but limited data volume. |

---

## 8. lexingtonnc.gov/city-services/parks-and-recreation/parks-and-facilities

| Field | Details |
|-------|---------|
| **Data Available** | States "over 20 parks and facilities" but the park listing is **hidden behind JavaScript tabs** (+ PARK LISTING, + SHELTER RESERVATIONS, etc.). The main page content only shows the intro and tab headers. |
| **Data Structure** | **JavaScript tabs** hide the actual park data. The tab content may be loaded dynamically or hidden via CSS. Need to investigate whether the content is in the initial HTML but hidden, or loaded via AJAX. |
| **CMS** | **Granicus** (footer: "Design By GRANICUS - Connecting People & Government") |
| **Scraping Method** | **May need Selenium** if tab content is AJAX-loaded. Try `requests` first — Granicus sites often include tab content in the initial HTML with `display:none`. If content is present in page source, BS4 can extract it. |
| **Approx Count** | 20+ parks (stated on page but list not visible in fetched content) |
| **API Endpoints** | None discovered in page source. Granicus standard endpoints for images/calendar. |
| **Anti-scraping** | Tab-based content hiding. Not anti-scraping per se, but requires investigation. |
| **Value Assessment** | **Medium**. 20+ parks is a decent dataset for Lexington. Need to get past the tabs. Likely has addresses and amenity info once content is accessible. Worth a Selenium pass to evaluate the hidden content. |

---

## 9. kdhnc.com/1002/Parks-and-Playgrounds

| Field | Details |
|-------|---------|
| **Data Available** | Park names, addresses, detailed amenity lists (Fitness Trail, Pond, Dog Park, Pavilion, Roller Hockey Rink, Skateboard Ramps, Playground, Picnic Tables, Restrooms, Splash Pad, Pickleball/Tennis Courts), photos with multiple images per park. |
| **Data Structure** | Static HTML. Each park section has name, address, amenity description, and image gallery. Clean, parseable structure. |
| **CMS** | **CivicPlus** (footer: "Government Websites by CivicPlus®") |
| **Scraping Method** | `requests` + `BeautifulSoup` sufficient. Standard CivicPlus static render. |
| **Approx Count** | ~4 parks (Aviation Park & Frog/Turtle Pond, Copley Drive, Meekins Field, West Hayman Blvd). Small town = small dataset. |
| **API Endpoints** | CivicPlus ImageRepository: `/ImageRepository/Document?documentId=XXXXX`. |
| **Anti-scraping** | None observed. |
| **Value Assessment** | **Low-Medium**. Very small dataset (Kill Devil Hills only, 4 parks). But good structured data with addresses and amenities. Useful for Dare County / OBX coverage. |

---

## 10. highpointnc.gov/572/Parks

| Field | Details |
|-------|---------|
| **Data Available** | Park names with links to individual park pages (some via `/Facilities/Facility/Details/` pattern, others via `/XXXX/Park-Name`). No addresses, amenities, or details on the listing page itself. General info about shelter reservations. |
| **Data Structure** | Static HTML listing page with park name links. Individual park detail pages use a **CivicPlus Facility Directory** system (`/Facilities/Facility/Details/ParkName-ID`). Links to park maps at `/1970/Park-Maps`. |
| **CMS** | **CivicPlus** (footer: "Government Websites by CivicPlus®") |
| **Scraping Method** | `requests` + `BeautifulSoup` for the listing page, then follow links to individual park detail pages. The `/Facilities/Facility/Details/` pattern suggests a CivicPlus Facility Directory module which may have an API. |
| **Approx Count** | ~25-30+ parks listed (Allen Jay, Harvell, Oakview, Armstrong, Hedgecock, Parkside, Barker Bradshaw, plus many more visible in link list). |
| **API Endpoints** | **CivicPlus Facility Directory** — look for `/Facilities/FacilityDirectory/` or `/Home/Components/FacilityDirectory/` API endpoints. High Point also uses the Piedmont Discovery App which may have its own API. |
| **Anti-scraping** | None observed. |
| **Value Assessment** | **Medium-High**. Good number of parks (~25-30). Need two-phase scrape: listing page for URLs, then individual pages for details. The Facility Directory pattern is reusable across other CivicPlus sites. |

---

## 11. hendersoncountync.gov/recreation/page/parks-facilities

| Field | Details |
|-------|---------|
| **Data Available** | Park names, addresses, Google Maps links. OpenLayers map with markers. Links to individual park detail pages (e.g., `/recreation/page/jackson-park`). No amenities on the listing page — details on individual pages. |
| **Data Structure** | Table-based layout with park name, address, "See map: Google Maps" links. **OpenLayers map** with tile markers (OpenStreetMap tiles). Park data likely embedded in JavaScript for the map. |
| **CMS** | **Drupal** (paths like `/sites/all/modules/openlayers/`, Drupal-style URL patterns `/recreation/page/parks-facilities`) |
| **Scraping Method** | `requests` + `BeautifulSoup` for the table data. For coordinates, need to inspect the page's JavaScript for the OpenLayers map initialization data — coordinates are likely embedded in a `<script>` tag or Drupal settings object. |
| **Approx Count** | ~15 parks/facilities (Athletics & Activity Center, Bell Park, Jackson Park, Edneyville Community Center, Dana Park, East Flat Rock Park, Edneyville Community Park, Etowah Park, Westfeldt Park, Blantyre Park, Tuxedo Park, Upper Hickory Nut Gorge Trailhead, Donnie Jones Playground, Henderson County Sports Complex, Horse Shoe Boat Access) |
| **API Endpoints** | OpenLayers map data likely in page source JS. Drupal may expose JSON at `/recreation/page/parks-facilities?format=json` or via Views module. |
| **Anti-scraping** | None observed. |
| **Value Assessment** | **Medium-High**. Good structured data with addresses. OpenLayers map likely contains coordinates. Need to scrape individual park pages for amenities. Drupal sites are generally scrape-friendly. |

---

## 12. greensboro-nc.gov/.../neighborhood-parks

| Field | Details |
|-------|---------|
| **Data Available** | Park names, full addresses, amenity lists (Playgrounds, Shelter, Multipurpose Court, Walking Trail, Stream/Pond, Natural Area, Accessible/Inclusive features), phone numbers (some), links to individual park detail pages. **Esri-powered map** with markers. |
| **Data Structure** | **CivicPlus Facility Directory** with structured data — park name, address, amenity bullet points. Paginated listing (5 pages, "86 facilities found"). Each park links to `/Home/Components/FacilityDirectory/FacilityDirectory/ID/1204`. |
| **CMS** | **Granicus/CivicPlus hybrid** (Granicus footer but CivicPlus-style Facility Directory URLs) |
| **Scraping Method** | `requests` + `BeautifulSoup` for paginated listings. **But check for the Esri/ArcGIS API** — the "Powered by Esri" map almost certainly has a **Feature Service REST API** that would return all 86 facilities as GeoJSON with coordinates. This is the best approach. |
| **Approx Count** | **86 neighborhood parks** (confirmed "Total 86 facilities found"). This is just neighborhood parks — Greensboro has additional larger parks (Barber Park, Bryan Park, Country Park, etc.) on separate pages. |
| **API Endpoints** | **HIGH PRIORITY**: The Esri map has a backing ArcGIS Feature Service. Look for URLs like `https://services.arcgis.com/.../FeatureServer/0/query?where=1%3D1&outFields=*&f=json`. The Facility Directory also has component API: `/Home/Components/FacilityDirectory/FacilityDirectory/`. Pagination URLs: `/-npage-2` through `/-npage-5`. |
| **Anti-scraping** | None observed. |
| **Value Assessment** | **HIGH**. 86+ parks with structured addresses and amenities. The Esri/ArcGIS API is likely the most efficient path — would return all data with coordinates in a single API call. Pagination scraping is viable as fallback. |

---

## 13. cityofgraham.com/grpd-parks-playgrounds/

| Field | Details |
|-------|---------|
| **Data Available** | Park names, full addresses, detailed descriptions, age ranges (2-5, 5-12), amenity lists (swings, shelters, zipline, slides, climbing boulders, Gaga Ball, volleyball, exercise equipment, walking tracks), playground categories (Community, Neighborhood, Center). Photos. |
| **Data Structure** | Static HTML. Well-organized with `<h4>` headings, address blocks, and description paragraphs. Clean three-section structure: Community Park Playgrounds, Neighborhood Park Playgrounds, Center Playgrounds. |
| **CMS** | **WordPress** (standard WordPress page structure, not a CivicPlus/Granicus government template) |
| **Scraping Method** | `requests` + `BeautifulSoup` sufficient. Standard server-rendered WordPress page. |
| **Approx Count** | ~10 playgrounds (Graham Regional Park — 3 areas: playUNITED, Natural Playground, Youth Challenge Course; Bill Cooke Park; South Graham Park; Harman Park; Marshall Street Park; Greenway Park; Oakley Street Park; Graham Rec Center; Graham Civic Center) |
| **API Endpoints** | WordPress REST API may be available at `/wp-json/wp/v2/pages`. |
| **Anti-scraping** | None observed. |
| **Value Assessment** | **Medium**. Well-structured data for Graham/Alamance County area. Addresses, age ranges, and amenities are cleanly extractable. Good quality for a single municipality. |

---

## 14. nhcgov.com/DocumentCenter/View/844/Parks-Guide-PDF

| Field | Details |
|-------|---------|
| **Data Available** | Unknown — **this is a PDF document**, not HTML. Likely contains New Hanover County parks guide with maps, park descriptions, amenities. |
| **Data Structure** | **PDF file**. Cannot be scraped with standard HTML tools. |
| **CMS** | Host site is **CivicPlus** (standard DocumentCenter URL pattern) |
| **Scraping Method** | Need to **download the PDF** and parse with `PyPDF2`, `pdfplumber`, or `tabula-py`. For maps/images, may need `camelot` for table extraction. Consider OCR if the PDF is image-based. |
| **Approx Count** | Unknown until PDF is downloaded and analyzed. |
| **API Endpoints** | Direct download URL: `https://www.nhcgov.com/DocumentCenter/View/844/Parks-Guide-PDF`. CivicPlus DocumentCenter may list other documents at `/DocumentCenter/Index/`. |
| **Anti-scraping** | None (direct PDF download). |
| **Value Assessment** | **Low-Medium**. PDF parsing is brittle and labor-intensive. Worth downloading to assess content quality, but should be a lower priority than structured HTML/API sources. May be outdated (unknown publication date). |

---

## Summary Priority Ranking

| Priority | Source | Count | Method | Key Advantage |
|----------|--------|-------|--------|---------------|
| **1 — HIGH** | playgroundexplorers.com | 141 | Selenium or API discovery | Largest dataset, structured, multi-city |
| **2 — HIGH** | greensboro-nc.gov (neighborhood parks) | 86 | Esri API or pagination scrape | Esri/ArcGIS API likely has GeoJSON with coords |
| **3 — MED-HIGH** | highpointnc.gov | 25-30 | BS4 + follow links | CivicPlus Facility Directory, reusable pattern |
| **4 — MED-HIGH** | hendersoncountync.gov | 15 | BS4 + OpenLayers map JS | Drupal, coordinates in map data |
| **5 — MEDIUM** | southernpines.net | 13 | BS4 (static HTML) | Clean table layout, addresses + amenities |
| **6 — MEDIUM** | cityofgraham.com | 10 | BS4 (static HTML) | Well-structured WordPress, age ranges included |
| **7 — MEDIUM** | accessibleplayground.net | 20-25 | BS4 (static HTML) | Unique accessibility data, WordPress |
| **8 — MEDIUM** | nctriadoutdoors.com | 10 | BS4 (static HTML) | WordPress, individual park pages have details |
| **9 — MEDIUM** | nashcountync.gov | 7 | BS4 (static HTML) | CivicPlus, addresses + amenities |
| **10 — MED-LOW** | lexingtonnc.gov | 20+ | Selenium (JS tabs) | Granicus, content behind tabs |
| **11 — LOW-MED** | manteonc.gov | 7 | BS4 (static HTML) | Granicus, narrative format |
| **12 — LOW-MED** | kdhnc.com | 4 | BS4 (static HTML) | CivicPlus, very small dataset |
| **13 — LOW** | houseofhensen.com | 12 | BS4 (static HTML) | Blog/unstructured, Charlotte only |
| **14 — LOW-MED** | nhcgov.com (PDF) | ? | PDF parser | PDF, unknown content/freshness |

## CMS Distribution

| CMS | Sites | Notes |
|-----|-------|-------|
| **CivicPlus** | southernpines.net, nashcountync.gov, kdhnc.com, highpointnc.gov, nhcgov.com | Most common. Consistent URL patterns (`/XXX/Page-Name`), ImageRepository API, Facility Directory module. **Build one CivicPlus scraper, reuse across many NC gov sites.** |
| **Granicus** | manteonc.gov, lexingtonnc.gov, greensboro-nc.gov | Second most common for NC gov sites. Similar patterns to CivicPlus. Some overlap (Greensboro uses both). |
| **WordPress** | nctriadoutdoors.com, accessibleplayground.net, cityofgraham.com | Standard WP structure. REST API may be available. |
| **Drupal** | hendersoncountync.gov | OpenLayers integration, Views module may expose JSON. |
| **Squarespace** | houseofhensen.com | Blog platform, limited scraping value. |
| **Custom** | playgroundexplorers.com | Modern SPA, likely has backend API. |

## Recommended Next Steps

1. **Investigate playgroundexplorers.com API**: Open in browser DevTools, check Network tab for XHR/fetch requests during filtering/pagination. This is likely the highest-value single source.
2. **Find the Greensboro Esri Feature Service**: Inspect the ArcGIS map source to find the Feature Service URL. Query it for all 86 parks with coordinates.
3. **Build a generic CivicPlus scraper**: Pattern works for 5+ sites. Parse `/XXX/Page-Name` pattern, extract from Facility Directory components.
4. **Test Lexington tab content**: Fetch raw HTML with requests to check if tab content is present but hidden (vs. AJAX-loaded).
5. **Download and assess the NHC PDF**: Determine if it's worth the parsing effort.
