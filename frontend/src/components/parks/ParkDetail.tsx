import type { Park } from "../../types/park";
import { AMENITY_LABELS } from "../../types/park";
import { useMapProvider, directionsUrl } from "../../hooks/useMapProvider";

interface Props {
  park: Park;
  onClose: () => void;
}

export default function ParkDetail({ park, onClose }: Props) {
  const { provider } = useMapProvider();
  const positiveAmenities = Object.entries(park.amenities)
    .filter(([, v]) => v)
    .map(([k]) => AMENITY_LABELS[k] ?? k.replace(/_/g, " "))
    .sort();

  return (
    <>
      {/* Mobile backdrop */}
      <div
        className="fixed inset-0 z-30 bg-black/40 md:hidden"
        onClick={onClose}
      />

      {/* Desktop: right sidebar. Mobile: bottom sheet */}
      <div
        className="fixed inset-x-0 bottom-0 z-40 flex max-h-[70vh] flex-col rounded-t-2xl
                   bg-white shadow-2xl md:static md:inset-auto md:z-auto md:max-h-none
                   md:w-80 md:shrink-0 md:rounded-none md:border-l md:border-gray-200
                   md:shadow-lg"
      >
      {/* Header */}
      <div className="flex items-start justify-between gap-2 border-b border-gray-200 p-4">
        {/* Mobile drag handle */}
        <div className="absolute left-1/2 top-2 h-1 w-8 -translate-x-1/2 rounded-full bg-gray-300 md:hidden" />
        <div>
          <h2 className="text-lg font-bold leading-tight">{park.name}</h2>
          {park.county && (
            <p className="mt-0.5 text-xs text-gray-500">{park.county}</p>
          )}
        </div>
        <button
          onClick={onClose}
          className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          aria-label="Close"
        >
          <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path
              fillRule="evenodd"
              d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0
                 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414
                 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586
                 10 4.293 5.707a1 1 0 010-1.414z"
              clipRule="evenodd"
            />
          </svg>
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-4">
        {/* Address */}
        {park.address && (
          <p className="mb-3 text-sm text-gray-700">{park.address}</p>
        )}

        {/* Action buttons */}
        <div className="mb-4 flex flex-wrap gap-2">
          <a
            href={directionsUrl(park, provider)}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 rounded-lg bg-brand-600 px-3
                       py-1.5 text-sm font-medium text-white hover:bg-brand-700"
          >
            <svg
              className="h-4 w-4"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7
                   0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z"
                clipRule="evenodd"
              />
            </svg>
            Directions
          </a>
          {park.url && (
            <a
              href={park.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 rounded-lg border border-gray-300
                         px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Website
            </a>
          )}
        </div>

        {/* Phone */}
        {park.phone && (
          <div className="mb-4">
            <a
              href={`tel:${park.phone}`}
              className="inline-flex items-center gap-1 text-sm text-gray-700 hover:underline"
            >
              {park.phone}
            </a>
          </div>
        )}

        {/* Amenity badges */}
        {positiveAmenities.length > 0 && (
          <div>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500">
              Amenities
            </h3>
            <div className="flex flex-wrap gap-1.5">
              {positiveAmenities.map((label) => (
                <span
                  key={label}
                  className="rounded-full bg-brand-50 px-2.5 py-0.5 text-xs font-medium
                             text-brand-700"
                >
                  {label}
                </span>
              ))}
            </div>
          </div>
        )}

        {positiveAmenities.length === 0 && (
          <p className="text-sm italic text-gray-400">
            No amenity data available
          </p>
        )}

        {/* Source info */}
        <div className="mt-6 text-xs text-gray-400">
          Source: {park.source}
          {park.all_sources && park.all_sources.length > 1 && (
            <> (+{park.all_sources.length - 1} more)</>
          )}
        </div>
      </div>
      </div>
    </>
  );
}
