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

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open]);

  const mapOptions: { value: MapProvider; label: string }[] = [
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

      {/* Hamburger menu */}
      <div className="relative ml-auto" ref={menuRef}>
        <button
          onClick={() => setOpen((v) => !v)}
          className="rounded p-1.5 text-brand-200 hover:bg-brand-600 hover:text-white"
          aria-label="Menu"
          aria-expanded={open}
        >
          {open ? (
            <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <path d="M6 18L18 6M6 6l12 12" />
            </svg>
          ) : (
            <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <path d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          )}
        </button>

        {open && (
          <div className="absolute right-0 top-full z-50 mt-1 w-56 rounded-lg bg-white py-1 shadow-lg ring-1 ring-black/5">
            {/* Account (placeholder) */}
            <button
              disabled
              className="flex w-full items-center gap-3 px-4 py-2.5 text-sm text-gray-400 cursor-not-allowed"
            >
              <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
              </svg>
              Account
              <span className="ml-auto text-[10px] font-medium uppercase tracking-wide text-gray-300">Soon</span>
            </button>

            {/* Submit a Park (placeholder) */}
            <button
              disabled
              className="flex w-full items-center gap-3 px-4 py-2.5 text-sm text-gray-400 cursor-not-allowed"
            >
              <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" />
              </svg>
              Submit a Park
              <span className="ml-auto text-[10px] font-medium uppercase tracking-wide text-gray-300">Soon</span>
            </button>

            <div className="my-1 border-t border-gray-100" />

            {/* Settings — Directions provider */}
            <p className="px-4 py-1.5 text-xs font-semibold uppercase tracking-wider text-gray-400">
              Settings
            </p>
            <p className="px-4 pb-1 text-[11px] text-gray-400">Directions open in</p>
            {mapOptions.map((opt) => (
              <button
                key={opt.value}
                onClick={() => {
                  setProvider(opt.value);
                }}
                className={`flex w-full items-center gap-2 px-4 py-2 text-sm ${
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

            <div className="my-1 border-t border-gray-100" />

            {/* Buy me a coffee */}
            <a
              href="https://buymeacoffee.com/bentontripp"
              target="_blank"
              rel="noopener noreferrer"
              className="flex w-full items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50"
            >
              <svg className="h-4 w-4 text-amber-500" viewBox="0 0 24 24" fill="currentColor">
                <path d="M2 21h18v-2H2v2zM20 8h-2V5h2V3H4v2h2v3H4a2 2 0 00-2 2v5a6 6 0 006 6h4a6 6 0 006-6h2a2 2 0 002-2v-3a2 2 0 00-2-2zm-2 7a4 4 0 01-4 4H8a4 4 0 01-4-4v-5h14v5zm4-5h-2v-2h2v2z" />
              </svg>
              Buy me a coffee
            </a>
          </div>
        )}
      </div>
    </header>
  );
}
