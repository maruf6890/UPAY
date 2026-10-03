import { privateApi } from "@/lib/api/client";
import type { CoverageGap, CoverageGeoJson, CoverageSummary } from "@/types/models";

export function getCoverageMap(asOf?: string) {
  return privateApi<CoverageGeoJson>("/coverage/map", { query: { as_of: asOf } });
}

export function getCoverageSummary(asOf?: string) {
  return privateApi<CoverageSummary>("/coverage/summary", { query: { as_of: asOf } });
}

export function getCoverageGaps(asOf?: string, limit = 8) {
  return privateApi<{ gaps: CoverageGap[] }>("/coverage/gaps", { query: { as_of: asOf, limit } });
}
