import { useState, useRef, useEffect } from "react";
import { useMapProvider, type MapProvider } from "../../hooks/useMapProvider";

export default function Header() {
  const { provider, setProvider } = useMapProvider();
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  const options: { value: MapProvider; label: string }[] = [
    { value: "google", label: "Google Maps" },
    { value: "apple", label: "Apple Maps" },
  ];

  return (
    <header className="flex items-center gap-3 bg-brand-700 px-4 py-3 text-white shadow-md">
      <svg
        className="h-7 w-7"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
      >
        <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z" />
        <circle cx="12" cy="9" r="2.5" />
      </svg>
      <h1 className="text-lg font-bold tracking-tight">NC Parks</h1>
      <span className="text-sm font-normal text-brand-200">
        Playground Finder
      </span>

      {/* Settings */}
      <div className="relative ml-auto" ref={menuRef}>
        <button
          onClick={() => setOpen((v) => !v)}
          className="rounded p-1.5 text-brand-200 hover:bg-brand-600 hover:text-white"
          aria-label="Settings"
        >
          <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path
              fillRule="evenodd"
              d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0
                 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061
                 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0
                 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0
                 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0
                 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0
                 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0
                 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0
                 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z"
              clipRule="evenodd"
            />
          </svg>
        </button>

        {open && (
          <div className="absolute right-0 top-full z-50 mt-1 w-48 rounded-lg bg-white py-1 shadow-lg ring-1 ring-black/5">
            <p className="px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-gray-400">
              Directions open in
            </p>
            {options.map((opt) => (
              <button
                key={opt.value}
                onClick={() => {
                  setProvider(opt.value);
                  setOpen(false);
                }}
                className={`flex w-full items-center gap-2 px-3 py-2 text-sm ${
                  provider === opt.value
                    ? "bg-brand-50 font-medium text-brand-700"
                    : "text-gray-700 hover:bg-gray-50"
                }`}
              >
                {provider === opt.value && (
                  <svg className="h-4 w-4 text-brand-600" viewBox="0 0 20 20" fill="currentColor">
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414
                         0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1
                         0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                )}
                {provider !== opt.value && <span className="inline-block w-4" />}
                {opt.label}
              </button>
            ))}
          </div>
        )}
      </div>
    </header>
  );
}
