// MapLibre GL runs its heavy work in a web worker. Bundlers cannot find that worker on their own,
// so we copy the two files it needs into public/ and point MapLibre at them (see src/lib/map.ts).
import { copyFileSync, mkdirSync } from "node:fs";

mkdirSync("public/maplibre", { recursive: true });
for (const file of ["maplibre-gl-worker.mjs", "maplibre-gl-shared.mjs"]) {
  copyFileSync(`node_modules/maplibre-gl/dist/${file}`, `public/maplibre/${file}`);
}
console.log("copied the MapLibre worker files to public/maplibre");
