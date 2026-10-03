import { setWorkerUrl, type StyleSpecification } from "maplibre-gl";

// MapLibre 6 needs to be told where its worker file lives. The file is copied to public/ by scripts/copy-map-worker.mjs.
setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");

/** A plain pale-blue background. Used when the online basemap cannot be loaded, so the data still shows. */
export const BLANK_STYLE: StyleSpecification = {
  version: 8,
  sources: {},
  layers: [{ id: "background", type: "background", paint: { "background-color": "#EAF2FB" } }],
};

const configured = process.env.NEXT_PUBLIC_MAP_STYLE;

/** The default is the light CARTO basemap (free, no key). Set NEXT_PUBLIC_MAP_STYLE to another style URL, or "blank". */
export const MAP_STYLE: string | StyleSpecification =
  configured === "blank" ? BLANK_STYLE : configured ? configured : "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json";

/** Bangladesh */
export const BANGLADESH_VIEW = { longitude: 90.35, latitude: 23.8, zoom: 6.3 };
