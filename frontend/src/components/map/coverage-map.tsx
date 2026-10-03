"use client";
import "maplibre-gl/dist/maplibre-gl.css";
import { useState } from "react";
import type { FeatureCollection } from "geojson";
import MapView, { Layer, NavigationControl, Source, type LayerProps, type MapLayerMouseEvent } from "react-map-gl/maplibre";
import { X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { GAP_ORDER, GAP_STYLES } from "@/lib/coverage-style";
import { formatBdt, formatBdtFull } from "@/lib/format";
import { BANGLADESH_VIEW, BLANK_STYLE, MAP_STYLE } from "@/lib/map";
import type { CoverageGeoJson, CoverageProps } from "@/types/models";

/** Builds the "colour each hexagon by its gap type" rule that MapLibre understands. */
function buildFillColor() {
  const rule: unknown[] = ["match", ["get", "gapType"]];
  for (const gap of GAP_ORDER) {
    rule.push(gap, GAP_STYLES[gap].color);
  }
  rule.push("#CCD5E0");
  return rule;
}

const fillLayer: LayerProps = {
  id: "hex-fill",
  type: "fill",
  paint: {
    "fill-color": buildFillColor() as never,
    "fill-opacity": ["case", ["==", ["get", "gapType"], "LOW_DEMAND"], 0.3, 0.62] as never,
  },
};

const outlineLayer: LayerProps = {
  id: "hex-outline",
  type: "line",
  paint: { "line-color": "#FFFFFF", "line-width": 1, "line-opacity": 0.9 },
};

export function CoverageMap({ data }: { data: CoverageGeoJson }) {
  const [selected, setSelected] = useState<CoverageProps | null>(null);
  const [hovering, setHovering] = useState(false);
  const [style, setStyle] = useState(MAP_STYLE);
  const [loaded, setLoaded] = useState(false);

  function handleClick(event: MapLayerMouseEvent) {
    const feature = event.features && event.features[0];
    setSelected(feature ? (feature.properties as unknown as CoverageProps) : null);
  }

  function handleMove(event: MapLayerMouseEvent) {
    setHovering(Boolean(event.features && event.features.length > 0));
  }

  const highlight: LayerProps = {
    id: "hex-selected",
    type: "line",
    paint: { "line-color": "#182230", "line-width": 3 },
    filter: ["==", ["get", "h3"], selected ? selected.h3 : ""],
  };

  return (
    <div className="relative h-full min-h-[520px] w-full overflow-hidden rounded-xl border">
      <MapView
        initialViewState={BANGLADESH_VIEW}
        mapStyle={style}
        style={{ width: "100%", height: "100%" }}
        interactiveLayerIds={["hex-fill"]}
        cursor={hovering ? "pointer" : "grab"}
        onClick={handleClick}
        onMouseMove={handleMove}
        onLoad={() => setLoaded(true)}
        // If the online basemap cannot be reached, fall back to a plain background so the hexagons still show.
        onError={() => {
          if (!loaded && style !== BLANK_STYLE) {
            setStyle(BLANK_STYLE);
          }
        }}
      >
        <NavigationControl position="top-right" showCompass={false} />
        <Source id="hexagons" type="geojson" data={data as unknown as FeatureCollection}>
          <Layer {...fillLayer} />
          <Layer {...outlineLayer} />
          <Layer {...highlight} />
        </Source>
      </MapView>

      <div className="pointer-events-none absolute bottom-3 left-3 rounded-xl border bg-card/95 p-3 shadow-sm backdrop-blur">
        <div className="mb-1.5 text-[11px] font-medium text-muted-foreground">Coverage gap</div>
        <ul className="space-y-1">
          {GAP_ORDER.map((gap) => (
            <li key={gap} className="flex items-center gap-2 text-xs">
              <span className="size-3 rounded-sm" style={{ background: GAP_STYLES[gap].color }} />
              {GAP_STYLES[gap].label}
            </li>
          ))}
        </ul>
      </div>

      {selected ? (
        <div className="absolute top-3 left-3 w-72 rounded-xl border bg-card p-4 shadow-lg">
          <div className="flex items-start justify-between gap-2">
            <div>
              <div className="text-sm font-semibold">{selected.nearestTown}</div>
              <Badge variant={GAP_STYLES[selected.gapType]?.tone ?? "secondary"} className="mt-1">
                {GAP_STYLES[selected.gapType]?.label ?? selected.gapType}
              </Badge>
            </div>
            <button type="button" onClick={() => setSelected(null)} className="cursor-pointer rounded-md p-1 text-muted-foreground hover:bg-subtle" aria-label="Close">
              <X className="size-4" />
            </button>
          </div>
          <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-2 text-xs">
            <dt className="text-muted-foreground">Demand / month</dt>
            <dd className="text-right font-medium tabular-nums">{formatBdt(selected.demandBdt)}</dd>
            <dt className="text-muted-foreground">Handled by agents</dt>
            <dd className="text-right font-medium tabular-nums">{formatBdt(selected.supplyBdt)}</dd>
            <dt className="text-muted-foreground">Agents here / nearby</dt>
            <dd className="text-right font-medium tabular-nums">
              {selected.agentsInCell} / {selected.agentsNearby}
            </dd>
            <dt className="text-muted-foreground">Lost to stockouts</dt>
            <dd className="text-right font-medium tabular-nums">{formatBdtFull(selected.unservedBdt)}</dd>
          </dl>
          <p className="mt-3 border-t pt-3 text-xs leading-relaxed text-ink-secondary">{selected.recommendation}</p>
        </div>
      ) : null}
    </div>
  );
}
