interface Props {
  rating: number;
  count?: number;
  size?: "sm" | "md";
}

export default function StarRating({ rating, count, size = "sm" }: Props) {
  const stars = [];
  const rounded = Math.round(rating * 2) / 2; // round to nearest 0.5

  for (let i = 1; i <= 5; i++) {
    if (i <= rounded) {
      // Full star
      stars.push(
        <svg key={i} className={iconClass(size)} viewBox="0 0 20 20" fill="currentColor">
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>,
      );
    } else if (i - 0.5 === rounded) {
      // Half star (clip trick)
      stars.push(
        <svg key={i} className={iconClass(size)} viewBox="0 0 20 20">
          <defs>
            <linearGradient id={`half-${i}`}>
              <stop offset="50%" stopColor="currentColor" />
              <stop offset="50%" stopColor="#D1D5DB" />
            </linearGradient>
          </defs>
          <path
            fill={`url(#half-${i})`}
            d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"
          />
        </svg>,
      );
    } else {
      // Empty star
      stars.push(
        <svg key={i} className={iconClass(size)} viewBox="0 0 20 20" fill="#D1D5DB">
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>,
      );
    }
  }

  return (
    <div className="flex items-center gap-1 text-amber-400">
      <div className="flex">{stars}</div>
      <span className={`font-medium text-gray-700 ${size === "sm" ? "text-xs" : "text-sm"}`}>
        {rating.toFixed(1)}
      </span>
      {count != null && (
        <span className={`text-gray-400 ${size === "sm" ? "text-xs" : "text-sm"}`}>
          ({count.toLocaleString()})
        </span>
      )}
    </div>
  );
}

function iconClass(size: "sm" | "md"): string {
  return size === "sm" ? "h-3.5 w-3.5" : "h-4 w-4";
}
