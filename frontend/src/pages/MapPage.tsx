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
  const [filtersOpen, setFiltersOpen] = useState(false);

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
          open={filtersOpen}
          onClose={() => setFiltersOpen(false)}
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

          {/* Mobile filter toggle */}
          <button
            onClick={() => setFiltersOpen(true)}
            className="absolute left-3 top-3 z-10 flex items-center gap-1.5 rounded-lg
                       bg-white px-3 py-2 text-sm font-medium text-gray-700 shadow-md
                       hover:bg-gray-50 md:hidden"
          >
            <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path
                fillRule="evenodd"
                d="M3 5a1 1 0 011-1h12a1 1 0 010 2H4a1 1 0 01-1-1zm3
                   5a1 1 0 011-1h6a1 1 0 010 2H7a1 1 0 01-1-1zm2 5a1
                   1 0 011-1h2a1 1 0 010 2H9a1 1 0 01-1-1z"
                clipRule="evenodd"
              />
            </svg>
            Filters
            {activeFilterCount > 0 && (
              <span className="flex h-5 w-5 items-center justify-center rounded-full
                               bg-brand-600 text-xs text-white">
                {activeFilterCount}
              </span>
            )}
          </button>

          {/* Mobile park count */}
          <div className="absolute bottom-4 left-1/2 z-10 -translate-x-1/2 rounded-full
                          bg-white/90 px-3 py-1 text-xs font-medium text-gray-600
                          shadow-md backdrop-blur-sm md:hidden">
            {filtered.length.toLocaleString()} parks
          </div>
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
