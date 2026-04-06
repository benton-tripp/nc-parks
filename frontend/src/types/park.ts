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
};
