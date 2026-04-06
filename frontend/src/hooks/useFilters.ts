import { useState, useCallback, useMemo } from "react";
import type { Park } from "../types/park";

export function useFilters(parks: Park[] | undefined) {
  const [search, setSearch] = useState("");
  const [amenities, setAmenities] = useState<Set<string>>(new Set());

  const toggleAmenity = useCallback((key: string) => {
    setAmenities((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const clearFilters = useCallback(() => {
    setSearch("");
    setAmenities(new Set());
  }, []);

  const filtered = useMemo(() => {
    if (!parks) return [];
    return parks.filter((park) => {
      // Text search on name, address, county, city
      if (search) {
        const q = search.toLowerCase();
        const haystack = [park.name, park.address, park.county, park.city]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        if (!haystack.includes(q)) return false;
      }
      // Amenity filters — park must have ALL selected amenities
      for (const key of amenities) {
        if (!park.amenities[key]) return false;
      }
      return true;
    });
  }, [parks, search, amenities]);

  return {
    search,
    setSearch,
    amenities,
    toggleAmenity,
    clearFilters,
    filtered,
    activeFilterCount: amenities.size + (search ? 1 : 0),
  };
}
