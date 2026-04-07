import { useState, useCallback } from "react";
import Header from "../components/layout/Header";
import FilterPanel from "../components/filters/FilterPanel";
import ParkMap from "../components/map/ParkMap";
import ParkDetail from "../components/parks/ParkDetail";
import ParkListPanel from "../components/parks/ParkListPanel";
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
  const [mobileView, setMobileView] = useState<"map" | "list">("map");
  const [mapBounds, setMapBounds] = useState<
    [number, number, number, number] | null
  >(null);

  const handleSelectPark = useCallback((park: Park) => {
    setSelectedPark(park);
  }, []);

  const handleDeselectPark = useCallback(() => {
    setSelectedPark(null);
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

        {/* Map — always visible on desktop, hidden on mobile when list active */}
        <main
          className={`relative flex-1 ${mobileView === "list" ? "hidden md:block" : ""}`}
        >
          {isLoading ? (
            <div className="flex h-full items-center justify-center">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-200 border-t-brand-600" />
            </div>
          ) : (
            <ParkMap
              parks={filtered}
              onSelectPark={handleSelectPark}
              selectedPark={selectedPark}
              onBoundsChange={setMapBounds}
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
        </main>

        {/* List panel — always visible on desktop, toggleable on mobile */}
        <ParkListPanel
          parks={filtered}
          mapBounds={mapBounds}
          selectedPark={selectedPark}
          onSelectPark={handleSelectPark}
          onDeselectPark={handleDeselectPark}
          className={
            mobileView === "map"
              ? "hidden md:flex"
              : "flex flex-1 md:flex-none"
          }
        />

        {/* Mobile bottom sheet for selected park (map view only) */}
        {selectedPark && mobileView === "map" && (
          <ParkDetail park={selectedPark} onClose={handleDeselectPark} />
        )}
      </div>

      {/* Mobile map/list toggle */}
      <div className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2 md:hidden">
        <div className="flex overflow-hidden rounded-full bg-white shadow-lg ring-1 ring-black/5">
          <button
            onClick={() => setMobileView("map")}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium transition-colors ${
              mobileView === "map"
                ? "bg-brand-600 text-white"
                : "text-gray-600 hover:bg-gray-50"
            }`}
          >
            <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path
                fillRule="evenodd"
                d="M12 1.586l-4 4v12.828l4-4V1.586zM3.707 3.293A1 1 0
                   002 4.586v10a1 1 0 00.293.707l4 4a1 1 0 001.414
                   0l4-4a1 1 0 00.293-.707v-10a1 1 0 00-.293-.707l-4-4a1
                   1 0 00-1.414 0l-4 4z"
                clipRule="evenodd"
              />
            </svg>
            Map
          </button>
          <button
            onClick={() => setMobileView("list")}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium transition-colors ${
              mobileView === "list"
                ? "bg-brand-600 text-white"
                : "text-gray-600 hover:bg-gray-50"
            }`}
          >
            <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path
                fillRule="evenodd"
                d="M3 4a1 1 0 011-1h12a1 1 0 010 2H4a1 1 0 01-1-1zm0
                   4a1 1 0 011-1h12a1 1 0 010 2H4a1 1 0 01-1-1zm0 4a1
                   1 0 011-1h12a1 1 0 010 2H4a1 1 0 01-1-1zm0 4a1 1 0
                   011-1h12a1 1 0 010 2H4a1 1 0 01-1-1z"
                clipRule="evenodd"
              />
            </svg>
            List
          </button>
        </div>
      </div>
    </div>
  );
}
