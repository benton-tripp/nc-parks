import { useRef, useEffect } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Park } from "../../types/park";

interface Props {
  parks: Park[];
  onSelectPark: (park: Park) => void;
  selectedPark: Park | null;
  onBoundsChange?: (bounds: [number, number, number, number]) => void;
}

const MAPTILER_KEY = import.meta.env.VITE_MAPTILER_KEY ?? "";
const STYLE_URL = `https://api.maptiler.com/maps/streets-v2/style.json?key=${MAPTILER_KEY}`;

// Center of North Carolina
const NC_CENTER: [number, number] = [-79.5, 35.55];
const NC_ZOOM = 7;

function toGeoJSON(
  parks: Park[],
): GeoJSON.FeatureCollection<GeoJSON.Point> {
  return {
    type: "FeatureCollection",
    features: parks.map((p, i) => ({
      type: "Feature" as const,
      id: i,
      geometry: {
        type: "Point" as const,
        coordinates: [p.longitude, p.latitude] as [number, number],
      },
      properties: {
        index: i,
        name: p.name,
        county: p.county ?? "",
        google_rating: (p.extras.google_rating as number) ?? 0,
      },
    })),
  };
}

export default function ParkMap({ parks, onSelectPark, selectedPark, onBoundsChange }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const parksRef = useRef(parks);
  parksRef.current = parks;
  const onSelectRef = useRef(onSelectPark);
  onSelectRef.current = onSelectPark;
  const onBoundsChangeRef = useRef(onBoundsChange);
  onBoundsChangeRef.current = onBoundsChange;

  // Initialize map (runs once)
  useEffect(() => {
    if (!containerRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: STYLE_URL,
      center: NC_CENTER,
      zoom: NC_ZOOM,
    });

    map.addControl(new maplibregl.NavigationControl(), "top-right");
    map.addControl(
      new maplibregl.GeolocateControl({
        positionOptions: { enableHighAccuracy: true },
        trackUserLocation: false,
      }),
      "top-right",
    );

    map.on("load", () => {
      map.addSource("parks", {
        type: "geojson",
        data: toGeoJSON(parksRef.current),
        cluster: true,
        clusterMaxZoom: 14,
        clusterRadius: 50,
      });

      // Cluster circles — sized and shaded by count
      map.addLayer({
        id: "clusters",
        type: "circle",
        source: "parks",
        filter: ["has", "point_count"],
        paint: {
          "circle-color": [
            "step",
            ["get", "point_count"],
            "#22c55e",
            10,
            "#16a34a",
            50,
            "#15803d",
            200,
            "#166534",
          ],
          "circle-radius": [
            "step",
            ["get", "point_count"],
            18,
            10,
            24,
            50,
            30,
            200,
            36,
          ],
          "circle-stroke-width": 2,
          "circle-stroke-color": "#fff",
        },
      });

      // Cluster count labels
      map.addLayer({
        id: "cluster-count",
        type: "symbol",
        source: "parks",
        filter: ["has", "point_count"],
        layout: {
          "text-field": "{point_count_abbreviated}",
          "text-size": 13,
          "text-font": ["Open Sans Bold"],
        },
        paint: {
          "text-color": "#ffffff",
        },
      });

      // Individual park markers
      map.addLayer({
        id: "park-points",
        type: "circle",
        source: "parks",
        filter: ["!", ["has", "point_count"]],
        paint: {
          "circle-color": "#22c55e",
          "circle-radius": 7,
          "circle-stroke-width": 2,
          "circle-stroke-color": "#ffffff",
        },
      });

      // Selected park highlight (rendered on top)
      map.addLayer({
        id: "park-selected",
        type: "circle",
        source: "parks",
        filter: ["==", ["get", "index"], -1],
        paint: {
          "circle-color": "#2563eb",
          "circle-radius": 10,
          "circle-stroke-width": 3,
          "circle-stroke-color": "#ffffff",
        },
      });

      // Click cluster → zoom in
      map.on("click", "clusters", async (e) => {
        const features = map.queryRenderedFeatures(e.point, {
          layers: ["clusters"],
        });
        if (!features.length) return;
        const clusterId = features[0].properties.cluster_id;
        const source = map.getSource("parks") as maplibregl.GeoJSONSource;
        const zoom = await source.getClusterExpansionZoom(clusterId);
        map.easeTo({
          center: (features[0].geometry as GeoJSON.Point).coordinates as [
            number,
            number,
          ],
          zoom,
        });
      });

      // Click park → show detail
      map.on("click", "park-points", (e) => {
        const features = map.queryRenderedFeatures(e.point, {
          layers: ["park-points"],
        });
        if (!features.length) return;
        const idx = features[0].properties.index;
        const park = parksRef.current[idx];
        if (park) onSelectRef.current(park);
      });

      // Pointer cursors
      map.on("mouseenter", "clusters", () => {
        map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", "clusters", () => {
        map.getCanvas().style.cursor = "";
      });

      // Hover popup for park points
      const popup = new maplibregl.Popup({
        closeButton: false,
        closeOnClick: false,
        offset: 12,
        className: "park-hover-popup",
      });

      map.on("mouseenter", "park-points", (e) => {
        map.getCanvas().style.cursor = "pointer";
        const features = map.queryRenderedFeatures(e.point, {
          layers: ["park-points"],
        });
        if (!features.length) return;
        const f = features[0];
        const coords = (f.geometry as GeoJSON.Point).coordinates.slice() as [
          number,
          number,
        ];
        const name = f.properties.name as string;
        const county = f.properties.county as string;
        const rating = f.properties.google_rating as number;

        let html = `<strong>${name}</strong>`;
        if (county) html += `<br/><span class="popup-county">${county}</span>`;
        if (rating)
          html += `<br/><span class="popup-rating">★ ${rating.toFixed(1)}</span>`;

        popup.setLngLat(coords).setHTML(html).addTo(map);
      });
      map.on("mouseleave", "park-points", () => {
        map.getCanvas().style.cursor = "";
        popup.remove();
      });

    });

    // Report bounds — registered outside "load" so dragging works immediately
    const reportBounds = () => {
      if (!onBoundsChangeRef.current) return;
      const b = map.getBounds();
      onBoundsChangeRef.current([
        b.getWest(),
        b.getSouth(),
        b.getEast(),
        b.getNorth(),
      ]);
    };
    let rafId: number | null = null;
    map.on("move", () => {
      if (rafId === null) {
        rafId = requestAnimationFrame(() => {
          rafId = null;
          reportBounds();
        });
      }
    });
    map.on("moveend", () => {
      if (rafId !== null) { cancelAnimationFrame(rafId); rafId = null; }
      reportBounds();
    });
    // Initial bounds
    reportBounds();

    mapRef.current = map;
    return () => map.remove();
  }, []);

  // Update GeoJSON when parks list changes (filtering)
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const source = map.getSource("parks") as
      | maplibregl.GeoJSONSource
      | undefined;
    if (source) {
      source.setData(toGeoJSON(parks));
    }
  }, [parks]);

  // Fly to selected park + highlight marker
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    // Find the index of the selected park in the current parks array
    const idx = selectedPark
      ? parksRef.current.findIndex(
          (p) =>
            p.source === selectedPark.source &&
            p.source_id === selectedPark.source_id,
        )
      : -1;

    // Update highlight layer filter
    if (map.getLayer("park-selected")) {
      map.setFilter("park-selected", ["==", ["get", "index"], idx]);
    }

    if (selectedPark) {
      map.flyTo({
        center: [selectedPark.longitude, selectedPark.latitude],
        zoom: Math.max(map.getZoom(), 14),
        duration: 800,
      });
    }
  }, [selectedPark]);

  return <div ref={containerRef} className="h-full w-full" />;
}
