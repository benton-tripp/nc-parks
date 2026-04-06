import type { Park } from "../types/park";

const DATA_URL = import.meta.env.VITE_DATA_URL ?? "/data/parks_latest.json";

export async function fetchParks(): Promise<Park[]> {
  const res = await fetch(DATA_URL);
  if (!res.ok) throw new Error(`Failed to load parks: ${res.status}`);
  return res.json();
}
