import { useState, useMemo, useRef, useEffect } from "react";
import type { Park } from "../../types/park";
import ParkCard from "./ParkCard";
import ParkDetailContent from "./ParkDetailContent";

type SortKey = "name" | "rating" | "reviews" | "amenities";

interface Props {
  parks: Park[];
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

export default function ParkListPanel({
  parks,
  selectedPark,
  onSelectPark,
  onDeselectPark,
  className = "",
}: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("name");
  const scrollRef = useRef<HTMLDivElement>(null);

  const sorted = useMemo(() => sortParks(parks, sortKey), [parks, sortKey]);

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
      {/* Controls bar */}
      <div className="flex items-center justify-between border-b border-gray-200 px-3 py-2">
        <span className="text-sm font-medium text-gray-700">
          <strong>{parks.length.toLocaleString()}</strong> parks
        </span>
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
              key={`${park.source}-${park.source_id}`}
              park={park}
              onClick={onSelectPark}
              isSelected={
                selectedPark?.source === park.source &&
                selectedPark?.source_id === park.source_id
              }
            />
          ))}
        </div>

        {parks.length === 0 && (
          <div className="flex h-40 items-center justify-center text-sm text-gray-400">
            No parks in this area
          </div>
        )}
      </div>
    </aside>
  );
}
