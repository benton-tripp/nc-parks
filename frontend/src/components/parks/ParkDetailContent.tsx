import { useState } from "react";
import type { Park } from "../../types/park";
import {
  formatAmenityLabel,
  SOURCE_LABELS,
  SOURCE_URLS,
} from "../../types/park";
import { useMapProvider, directionsUrl } from "../../hooks/useMapProvider";
import StarRating from "../ratings/StarRating";

interface Props {
  park: Park;
  onClose?: () => void;
}

function SourceLink({ source, sourceUrl }: { source: string; sourceUrl?: string }) {
  const label = SOURCE_LABELS[source] ?? source.replace(/_/g, " ");
  const url = sourceUrl ?? SOURCE_URLS[source];
  if (url) {
    return (
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className="text-brand-600 hover:text-brand-800 hover:underline"
      >
        {label}
      </a>
    );
  }
  return <span>{label}</span>;
}

export default function ParkDetailContent({ park, onClose }: Props) {
  const { provider } = useMapProvider();
  const [sourcesExpanded, setSourcesExpanded] = useState(false);

  const positiveAmenities = Object.entries(park.amenities)
    .filter(([, v]) => v)
    .map(([k]) => formatAmenityLabel(k))
    .sort();

  const googleRating = park.extras.google_rating as number | undefined;
  const googleRatingCount = park.extras.google_rating_count as
    | number
    | undefined;
  const googleMapsUri = park.extras.google_maps_uri as string | undefined;
  const googleDataDate = park.extras.google_data_date as string | undefined;

  const uniqueSources = [
    ...new Set(
      (park.all_sources ?? [{ source: park.source, source_id: park.source_id }])
        .map((s) => s.source),
    ),
  ];
  const sourceCount = uniqueSources.length;

  return (
    <div>
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <h2 className="text-lg font-bold leading-tight">{park.name}</h2>
          {park.county && (
            <p className="mt-0.5 text-xs text-gray-500">{park.county}</p>
          )}
        </div>
        {onClose && (
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
        )}
      </div>

      {/* Body */}
      <div className="mt-3">
        {/* Address */}
        {park.address && (
          <p className="mb-3 text-sm text-gray-700">{park.address}</p>
        )}

        {/* Google Rating */}
        {googleRating != null && (
          <div className="mb-3">
            <div className="flex items-center gap-2">
              <StarRating
                rating={googleRating}
                count={googleRatingCount}
                size="md"
              />
              {googleMapsUri && (
                <a
                  href={googleMapsUri}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-gray-400 hover:text-gray-600 hover:underline"
                >
                  Google
                </a>
              )}
            </div>
            {googleDataDate && (
              <p className="mt-0.5 text-[10px] text-gray-400">
                as of {googleDataDate}
              </p>
            )}
          </div>
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
            <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
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

        {/* Photo placeholder */}
        <div className="mb-4">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500">
            Photos
          </h3>
          <div className="flex gap-2">
            <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-lg border-2 border-dashed border-gray-200 bg-gray-50 text-gray-300">
              <svg
                className="h-6 w-6"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M6.827 6.175A2.31 2.31 0 015.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 00-1.134-.175 2.31 2.31 0 01-1.64-1.055l-.822-1.316a2.192 2.192 0 00-1.736-1.039 48.774 48.774 0 00-5.232 0 2.192 2.192 0 00-1.736 1.039l-.821 1.316z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M16.5 12.75a4.5 4.5 0 11-9 0 4.5 4.5 0 019 0z"
                />
              </svg>
            </div>
            <div className="flex h-20 flex-1 items-center justify-center rounded-lg border-2 border-dashed border-gray-200 bg-gray-50">
              <span className="text-xs text-gray-400">Photos coming soon</span>
            </div>
          </div>
        </div>

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

        {/* Sources */}
        <div className="mt-6 text-xs text-gray-400">
          {sourceCount === 1 ? "Source" : "Sources"}:{" "}
          <SourceLink source={uniqueSources[0]} sourceUrl={park.source_url} />
          {sourceCount > 1 && !sourcesExpanded && (
            <button
              onClick={() => setSourcesExpanded(true)}
              className="ml-1 text-brand-600 hover:text-brand-800 hover:underline"
            >
              (+{sourceCount - 1} more)
            </button>
          )}
          {sourceCount > 1 &&
            sourcesExpanded &&
            uniqueSources.slice(1).map((src, i) => (
              <span key={i}>
                {" · "}
                <SourceLink source={src} />
              </span>
            ))}
        </div>
      </div>
    </div>
  );
}
