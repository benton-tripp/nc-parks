export interface Park {
  source: string;
  source_id: string;
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

/** Amenities available for filtering, grouped by category. */
export const FILTERABLE_AMENITIES: AmenityInfo[] = [
  // Playground
  { key: "playground", label: "Playground", category: "Playground" },
  { key: "swings", label: "Swings", category: "Playground" },
  { key: "slides", label: "Slides", category: "Playground" },
  { key: "splash_pad", label: "Splash Pad", category: "Playground" },
  { key: "fenced_playground", label: "Fenced", category: "Playground" },

  // Facilities
  { key: "restrooms", label: "Restrooms", category: "Facilities" },
  { key: "drinking_water", label: "Drinking Water", category: "Facilities" },
  { key: "picnic_shelter", label: "Picnic Shelter", category: "Facilities" },
  { key: "pavilion", label: "Pavilion", category: "Facilities" },
  { key: "parking", label: "Parking", category: "Facilities" },

  // Sports
  { key: "basketball_courts", label: "Basketball", category: "Sports" },
  { key: "tennis_courts", label: "Tennis", category: "Sports" },
  { key: "ball_fields", label: "Ball Fields", category: "Sports" },
  { key: "multipurpose_field", label: "Multi-Use Field", category: "Sports" },
  { key: "skate_park", label: "Skate Park", category: "Sports" },
  { key: "disc_golf", label: "Disc Golf", category: "Sports" },

  // Outdoors
  { key: "walking_trails", label: "Walking Trails", category: "Outdoors" },
  { key: "greenway_access", label: "Greenway Access", category: "Outdoors" },
  { key: "biking", label: "Biking", category: "Outdoors" },
  { key: "dog_park", label: "Dog Park", category: "Outdoors" },
  { key: "fishing", label: "Fishing", category: "Outdoors" },
  { key: "gardens", label: "Gardens", category: "Outdoors" },

  // Accessibility
  { key: "ada_accessible", label: "ADA Accessible", category: "Accessibility" },
];

/** Human-readable labels for all amenity keys. */
export const AMENITY_LABELS: Record<string, string> = {
  playground: "Playground",
  restrooms: "Restrooms",
  swings: "Swings",
  slides: "Slides",
  splash_pad: "Splash Pad",
  fenced_playground: "Fenced",
  shaded_areas: "Shaded",
  picnic_tables: "Picnic Tables",
  picnic_shelter: "Picnic Shelter",
  pavilion: "Pavilion",
  ada_accessible: "ADA Accessible",
  parking: "Parking",
  drinking_water: "Drinking Water",
  walking_trails: "Walking Trails",
  basketball_courts: "Basketball",
  tennis_courts: "Tennis",
  swimming_pool: "Pool",
  dog_park: "Dog Park",
  disc_golf: "Disc Golf",
  fishing: "Fishing",
  boat_rental: "Boat Rental",
  canoe_kayak: "Canoe / Kayak",
  skate_park: "Skate Park",
  greenway_access: "Greenway",
  gym: "Gym",
  multipurpose_field: "Multi-Use Field",
  ball_fields: "Ball Fields",
  community_center: "Community Center",
  neighborhood_center: "Neighborhood Center",
  track: "Track",
  biking: "Biking",
  gardens: "Gardens",
  camping: "Camping",
  equestrian: "Equestrian",
  sand_volleyball: "Sand Volleyball",
  bmx_track: "BMX Track",
  open_field: "Open Field",
  carousel: "Carousel",
  wheelchair_accessible: "Wheelchair Accessible",
  horseshoes: "Horseshoes",
  volleyball: "Volleyball",
  bocce: "Bocce",
  pickleball: "Pickleball",
  shuffleboard: "Shuffleboard",
  outdoor_fitness: "Outdoor Fitness",
  amphitheater: "Amphitheater",
  nature_center: "Nature Center",
  soccer: "Soccer",
  baseball: "Baseball",
  softball: "Softball",
  football: "Football",
  lacrosse: "Lacrosse",
};

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
