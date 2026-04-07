import { useState, useRef, useEffect } from "react";
import type { Park } from "../../types/park";
import ParkCard from "./ParkCard";
import ParkDetailContent from "./ParkDetailContent";

type SortKey = "name" | "rating" | "reviews" | "amenities";

interface Props {
  parks: Park[];
  mapBounds: [number, number, number, number] | null;
  selectedPark: Park | null;
  onSelectPark: (park: Park) => void;
  onDeselectPark: () => void;
  className?: string;
}

function sortParks(parks: Park[], sortKey: SortKey): Park[] {
  return [...parks].sort((a, b) => {
    switch (sortKey) {
      case "name":
        return a.name.localeCompare(b.name);
      case "rating": {
        const ra = (a.extras.google_rating as number) ?? 0;
        const rb = (b.extras.google_rating as number) ?? 0;
        return rb - ra || a.name.localeCompare(b.name);
      }
      case "reviews": {
        const ca = (a.extras.google_rating_count as number) ?? 0;
        const cb = (b.extras.google_rating_count as number) ?? 0;
        return cb - ca || a.name.localeCompare(b.name);
      }
      case "amenities": {
        const aa = Object.values(a.amenities).filter(Boolean).length;
        const ab = Object.values(b.amenities).filter(Boolean).length;
        return ab - aa || a.name.localeCompare(b.name);
      }
      default:
        return 0;
    }
  });
}

function filterByBounds(
  parks: Park[],
  bounds: [number, number, number, number] | null,
): Park[] {
  if (!bounds) return parks;
  const [west, south, east, north] = bounds;
  return parks.filter(
    (p) =>
      p.longitude >= west &&
      p.longitude <= east &&
      p.latitude >= south &&
      p.latitude <= north,
  );
}

export default function ParkListPanel({
  parks,
  mapBounds,
  selectedPark,
  onSelectPark,
  onDeselectPark,
  className = "",
}: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("name");
  const [showAll, setShowAll] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // All filtering + sorting computed directly each render — no stale memoization
  const areaParks = showAll ? parks : filterByBounds(parks, mapBounds);
  const sorted = sortParks(areaParks, sortKey);

  // Filter out selected park from the card list so it doesn't appear twice
  const remaining = selectedPark
    ? sorted.filter(
        (p) =>
          !(
            p.source === selectedPark.source &&
            p.source_id === selectedPark.source_id
          ),
      )
    : sorted;

  // Scroll to top when a park is selected
  useEffect(() => {
    if (selectedPark && scrollRef.current) {
      scrollRef.current.scrollTo({ top: 0, behavior: "smooth" });
    }
  }, [selectedPark]);

  return (
    <aside
      className={`flex flex-col border-l border-gray-200 bg-white md:w-96 ${className}`}
    >
      {/* Area toggle + count */}
      <div className="flex items-center justify-between border-b border-gray-200 px-3 py-2">
        <div className="inline-flex rounded-full bg-gray-100 p-0.5">
          <button
            onClick={() => setShowAll(false)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              !showAll
                ? "bg-white text-gray-800 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            Current area
          </button>
          <button
            onClick={() => setShowAll(true)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              showAll
                ? "bg-white text-gray-800 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            All NC
          </button>
        </div>
        <span className="text-xs text-gray-400">
          {areaParks.length.toLocaleString()} parks{!showAll && ` of ${parks.length.toLocaleString()}`}
        </span>
      </div>

      {/* Controls bar */}
      <div className="flex items-center justify-end border-b border-gray-200 px-3 py-2">
        <select
          value={sortKey}
          onChange={(e) => setSortKey(e.target.value as SortKey)}
          className="rounded border border-gray-300 px-2 py-1 text-xs text-gray-700
                     focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        >
          <option value="name">Name A–Z</option>
          <option value="rating">Highest Rated</option>
          <option value="reviews">Most Reviewed</option>
          <option value="amenities">Most Amenities</option>
        </select>
      </div>

      {/* Scrollable content */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        {/* Selected park detail (inline) */}
        {selectedPark && (
          <div className="border-b border-gray-200 p-4">
            <ParkDetailContent
              park={selectedPark}
              onClose={onDeselectPark}
            />
          </div>
        )}

        {/* Card grid */}
        <div
          className={`p-3 ${
            selectedPark ? "space-y-2" : "grid grid-cols-2 gap-2"
          }`}
        >
          {remaining.map((park) => (
            <ParkCard
              key={`${park.source}-${park.source_id}-${park.latitude}-${park.longitude}`}
              park={park}
              onClick={onSelectPark}
              isSelected={
                selectedPark?.source === park.source &&
                selectedPark?.source_id === park.source_id
              }
            />
          ))}
        </div>

        {areaParks.length === 0 && (
          <div className="flex h-40 items-center justify-center text-sm text-gray-400">
            {showAll ? "No parks found" : "No parks in this area"}
          </div>
        )}
      </div>
    </aside>
  );
}
