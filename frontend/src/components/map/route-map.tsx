"use client";
import "maplibre-gl/dist/maplibre-gl.css";
import { useState } from "react";
import type { Feature } from "geojson";
import MapView, { Layer, Marker, NavigationControl, Source } from "react-map-gl/maplibre";
import { Landmark } from "lucide-react";
import { BLANK_STYLE, MAP_STYLE } from "@/lib/map";
import { cn } from "@/lib/utils";
import type { RoutePlan } from "@/types/models";

/** The delivery route: a dashed line through numbered stops, starting at the depot. */
export function RouteMap({ plan }: { plan: RoutePlan }) {
  const [style, setStyle] = useState(MAP_STYLE);
  const [loaded, setLoaded] = useState(false);

  const coordinates: number[][] = [];
  if (plan.depot) {
    coordinates.push([plan.depot.lon, plan.depot.lat]);
  }
  for (const stop of plan.stops) {
    coordinates.push([stop.lon, stop.lat]);
  }

  let minLon = 180;
  let maxLon = -180;
  let minLat = 90;
  let maxLat = -90;
  for (const point of coordinates) {
    minLon = Math.min(minLon, point[0]);
    maxLon = Math.max(maxLon, point[0]);
    minLat = Math.min(minLat, point[1]);
    maxLat = Math.max(maxLat, point[1]);
  }

  const line = { type: "Feature" as const, properties: {}, geometry: { type: "LineString" as const, coordinates } };

  return (
    <div className="h-full min-h-[420px] w-full overflow-hidden rounded-xl border">
      <MapView
        initialViewState={{ bounds: [minLon, minLat, maxLon, maxLat], fitBoundsOptions: { padding: 70, maxZoom: 12 } }}
        mapStyle={style}
        style={{ width: "100%", height: "100%" }}
        onLoad={() => setLoaded(true)}
        onError={() => {
          if (!loaded && style !== BLANK_STYLE) {
            setStyle(BLANK_STYLE);
          }
        }}
      >
        <NavigationControl position="top-right" showCompass={false} />
        <Source id="route" type="geojson" data={line as unknown as Feature}>
          <Layer id="route-line" type="line" paint={{ "line-color": "#182230", "line-width": 3, "line-dasharray": [2, 1.5] }} />
        </Source>

        {plan.depot ? (
          <Marker longitude={plan.depot.lon} latitude={plan.depot.lat} anchor="center">
            <div className="flex size-8 items-center justify-center rounded-lg bg-foreground text-white shadow-md" title="Depot (start)">
              <Landmark className="size-4" />
            </div>
          </Marker>
        ) : null}

        {plan.stops.map((stop) => (
          <Marker key={stop.agentCode} longitude={stop.lon} latitude={stop.lat} anchor="center">
            <div
              title={`${stop.agentCode}, ${stop.riskLevel}`}
              className={cn(
                "flex size-7 items-center justify-center rounded-full border-2 border-white text-xs font-semibold text-white shadow-md",
                stop.riskLevel === "HIGH" ? "bg-danger" : "bg-warning",
              )}
            >
              {stop.stop}
            </div>
          </Marker>
        ))}
      </MapView>
    </div>
  );
}
