export interface Park {
  source: string;
  source_id: string;
  source_url?: string;
  name: string;
  latitude: number;
  longitude: number;
  address: string | null;
  city: string | null;
  county: string | null;
  state: string;
  phone: string | null;
  url: string | null;
  amenities: Record<string, boolean>;
  extras: Record<string, unknown>;
  geohash?: string;
  all_sources?: { source: string; source_id: string }[];
}

/** Amenity metadata for display and filtering. */
export interface AmenityInfo {
  key: string;
  label: string;
  category: string;
}

/** Raw registry entry shape from amenities.json. */
interface AmenityRegistryEntry {
  key: string;
  label: string;
  category: string;
  filterable: boolean;
}

import amenityRegistry from "../../../amenities.json";
const _registry: AmenityRegistryEntry[] = amenityRegistry as AmenityRegistryEntry[];

/** Amenities available for filtering, grouped by category. */
export const FILTERABLE_AMENITIES: AmenityInfo[] = _registry
  .filter((a) => a.filterable)
  .map(({ key, label, category }) => ({ key, label, category }));

/** Human-readable labels for all amenity keys. */
export const AMENITY_LABELS: Record<string, string> = Object.fromEntries(
  _registry.map((a) => [a.key, a.label]),
);

/** Format an amenity key into a display label with consistent title case. */
export function formatAmenityLabel(key: string): string {
  return (
    AMENITY_LABELS[key] ??
    key
      .replace(/_/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase())
  );
}

/** Human-readable source display names. */
export const SOURCE_LABELS: Record<string, string> = {
  wake_county: "Wake County",
  johnston_county: "Johnston County",
  osm: "OpenStreetMap",
  alamance_county: "Alamance County",
  greensboro: "Greensboro",
  high_point: "High Point",
  playground_explorers: "Playground Explorers",
  southern_pines: "Southern Pines",
  nash_county: "Nash County",
  kill_devil_hills: "Kill Devil Hills",
  google_places: "Google",
  triad: "NC Triad Outdoors",
  wilson: "Wilson",
  graham: "Graham",
  manteo: "Manteo",
  elizabeth_city: "Elizabeth City",
  new_bern: "New Bern",
  fayetteville: "Fayetteville",
  goldsboro: "Goldsboro",
  henderson_county: "Henderson County",
  durham: "Durham",
  lexington: "Lexington",
  asheville: "Asheville",
  charlotte: "Charlotte",
  mecklenburg_county: "Mecklenburg County",
  wilmington: "Wilmington",
  new_hanover_county: "New Hanover County",
};

/** URLs for each data source (links to their portal / website). */
export const SOURCE_URLS: Record<string, string> = {
  wake_county: "https://data-wake.opendata.arcgis.com/",
  johnston_county: "https://www.johnstoncountync.org/parks-and-recreation/",
  osm: "https://www.openstreetmap.org/",
  alamance_county: "https://www.alamance-nc.com/recreation/",
  greensboro: "https://www.greensboro-nc.gov/departments/parks-recreation",
  high_point: "https://www.highpointnc.gov/656/Parks-Facilities",
  playground_explorers: "https://playgroundexplorers.com/",
  southern_pines: "https://www.southernpines.net/",
  nash_county: "https://www.nash-nc.com/",
  kill_devil_hills: "https://www.kdhnc.com/",
  google_places: "https://maps.google.com/",
  triad: "https://nctriadoutdoors.com/",
  wilson: "https://www.wilsonnc.org/",
};
