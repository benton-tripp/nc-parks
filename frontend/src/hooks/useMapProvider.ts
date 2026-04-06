import { useCallback, useSyncExternalStore } from "react";

export type MapProvider = "google" | "apple";

const STORAGE_KEY = "nc-parks-map-provider";

function getSnapshot(): MapProvider {
  return (localStorage.getItem(STORAGE_KEY) as MapProvider) ?? "google";
}

function getServerSnapshot(): MapProvider {
  return "google";
}

let listeners: Array<() => void> = [];
function subscribe(cb: () => void) {
  listeners = [...listeners, cb];
  return () => {
    listeners = listeners.filter((l) => l !== cb);
  };
}

function emitChange() {
  for (const l of listeners) l();
}

export function useMapProvider() {
  const provider = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const setProvider = useCallback((p: MapProvider) => {
    localStorage.setItem(STORAGE_KEY, p);
    emitChange();
  }, []);

  return { provider, setProvider } as const;
}

export function directionsUrl(
  park: { latitude: number; longitude: number; name: string },
  provider: MapProvider,
): string {
  if (provider === "apple") {
    return `https://maps.apple.com/?daddr=${park.latitude},${park.longitude}&q=${encodeURIComponent(park.name)}`;
  }
  return `https://www.google.com/maps/dir/?api=1&destination=${park.latitude},${park.longitude}`;
}
