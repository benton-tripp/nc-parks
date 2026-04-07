import type { Park } from "../../types/park";
import StarRating from "../ratings/StarRating";

interface Props {
  park: Park;
  onClick: (park: Park) => void;
  isSelected?: boolean;
}

export default function ParkCard({ park, onClick, isSelected }: Props) {
  const googleRating = park.extras.google_rating as number | undefined;
  const googleRatingCount = park.extras.google_rating_count as
    | number
    | undefined;
  const amenityCount = Object.values(park.amenities).filter(Boolean).length;

  return (
    <button
      onClick={() => onClick(park)}
      className={`w-full rounded-lg border p-3 text-left transition-colors
                  hover:border-brand-300 hover:bg-brand-50/50
                  ${isSelected ? "border-brand-500 bg-brand-50 ring-1 ring-brand-500" : "border-gray-200"}`}
    >
      {/* Photo placeholder */}
      <div className="mb-2 flex h-24 items-center justify-center rounded-md bg-gray-100 text-gray-300">
        <svg
          className="h-8 w-8"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z"
          />
        </svg>
      </div>

      <h3 className="truncate text-sm font-semibold text-gray-900">
        {park.name}
      </h3>
      {park.county && (
        <p className="truncate text-xs text-gray-500">{park.county}</p>
      )}

      {googleRating != null && (
        <div className="mt-1">
          <StarRating
            rating={googleRating}
            count={googleRatingCount}
            size="sm"
          />
        </div>
      )}

      {amenityCount > 0 && (
        <p className="mt-1 text-xs text-gray-400">
          {amenityCount} {amenityCount === 1 ? "amenity" : "amenities"}
        </p>
      )}
    </button>
  );
}
