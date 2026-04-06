export default function Header() {
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
    </header>
  );
}
