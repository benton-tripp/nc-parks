import { useState, useCallback } from "react";
import Header from "../components/layout/Header";
import FilterPanel from "../components/filters/FilterPanel";
import ParkMap from "../components/map/ParkMap";
import ParkDetail from "../components/parks/ParkDetail";
import { useParks } from "../hooks/useParks";
import { useFilters } from "../hooks/useFilters";
import type { Park } from "../types/park";

export default function MapPage() {
  const { data: parks, isLoading, error } = useParks();
  const {
    search,
    setSearch,
    amenities,
    toggleAmenity,
    clearFilters,
    filtered,
    activeFilterCount,
  } = useFilters(parks);

  const [selectedPark, setSelectedPark] = useState<Park | null>(null);

  const handleSelectPark = useCallback((park: Park) => {
    setSelectedPark(park);
  }, []);

  if (error) {
    return (
      <div className="flex h-screen flex-col">
        <Header />
        <div className="flex flex-1 items-center justify-center">
          <p className="text-red-600">
            Failed to load parks data. Make sure{" "}
            <code>public/data/parks_latest.json</code> exists.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col">
      <Header />
      <div className="flex flex-1 overflow-hidden">
        <FilterPanel
          search={search}
          onSearchChange={setSearch}
          activeAmenities={amenities}
          onToggleAmenity={toggleAmenity}
          onClear={clearFilters}
          resultCount={filtered.length}
          activeFilterCount={activeFilterCount}
        />
        <main className="relative flex-1">
          {isLoading ? (
            <div className="flex h-full items-center justify-center">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-200 border-t-brand-600" />
            </div>
          ) : (
            <ParkMap
              parks={filtered}
              onSelectPark={handleSelectPark}
              selectedPark={selectedPark}
            />
          )}
        </main>
        {selectedPark && (
          <ParkDetail
            park={selectedPark}
            onClose={() => setSelectedPark(null)}
          />
        )}
      </div>
    </div>
  );
}
