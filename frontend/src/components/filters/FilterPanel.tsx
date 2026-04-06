import { FILTERABLE_AMENITIES } from "../../types/park";

interface Props {
  search: string;
  onSearchChange: (value: string) => void;
  activeAmenities: Set<string>;
  onToggleAmenity: (key: string) => void;
  onClear: () => void;
  resultCount: number;
  activeFilterCount: number;
  open: boolean;
  onClose: () => void;
}

export default function FilterPanel({
  search,
  onSearchChange,
  activeAmenities,
  onToggleAmenity,
  onClear,
  resultCount,
  activeFilterCount,
  open,
  onClose,
}: Props) {
  const grouped = FILTERABLE_AMENITIES.reduce<
    Record<string, typeof FILTERABLE_AMENITIES>
  >((acc, a) => {
    (acc[a.category] ??= []).push(a);
    return acc;
  }, {});

  const panel = (
    <aside
      className={`flex shrink-0 flex-col border-r border-gray-200 bg-white
                  md:static md:w-72
                  ${open ? "fixed inset-y-0 left-0 z-40 w-72" : "hidden md:flex"}`}
    >
      {/* Mobile close button */}
      <div className="flex items-center justify-between border-b border-gray-200 p-3 md:hidden">
        <span className="text-sm font-semibold text-gray-700">Filters</span>
        <button
          onClick={onClose}
          className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          aria-label="Close filters"
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

      {/* Search */}
      <div className="border-b border-gray-200 p-3">
        <input
          type="text"
          placeholder="Search parks…"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm
                     placeholder:text-gray-400 focus:border-brand-500 focus:outline-none
                     focus:ring-1 focus:ring-brand-500"
        />
      </div>

      {/* Amenity filter groups */}
      <div className="flex-1 overflow-y-auto p-3">
        {Object.entries(grouped).map(([category, amenities]) => (
          <div key={category} className="mb-4">
            <h3 className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-gray-500">
              {category}
            </h3>
            <div className="space-y-1">
              {amenities.map((a) => (
                <label
                  key={a.key}
                  className="flex cursor-pointer items-center gap-2 rounded px-2 py-1
                             text-sm hover:bg-gray-50"
                >
                  <input
                    type="checkbox"
                    checked={activeAmenities.has(a.key)}
                    onChange={() => onToggleAmenity(a.key)}
                    className="h-4 w-4 rounded border-gray-300 text-brand-600
                               focus:ring-brand-500"
                  />
                  {a.label}
                </label>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Footer: result count + clear */}
      <div className="flex items-center justify-between border-t border-gray-200 px-3 py-2 text-xs text-gray-500">
        <span>
          <strong className="text-gray-900">
            {resultCount.toLocaleString()}
          </strong>{" "}
          parks
        </span>
        {activeFilterCount > 0 && (
          <button
            onClick={onClear}
            className="font-medium text-brand-600 hover:text-brand-800"
          >
            Clear filters
          </button>
        )}
      </div>
    </aside>
  );

  return (
    <>
      {/* Backdrop for mobile drawer */}
      {open && (
        <div
          className="fixed inset-0 z-30 bg-black/40 md:hidden"
          onClick={onClose}
        />
      )}
      {panel}
    </>
  );
}
