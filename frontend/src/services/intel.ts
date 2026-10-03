import { privateApi } from "@/lib/api/client";
import type { ChurnList, PerformanceList, PerformanceSummary } from "@/types/models";

export function getPerformanceSummary(asOf?: string, district?: string) {
  return privateApi<PerformanceSummary>("/intel/performance/summary", { query: { as_of: asOf, district } });
}

export function getPerformanceAgents(params: { asOf?: string; segment?: string; district?: string; limit?: number }) {
  return privateApi<PerformanceList>("/intel/performance/agents", {
    query: { as_of: params.asOf, segment: params.segment, district: params.district, limit: params.limit ?? 15 },
  });
}

export function getChurnRisk(params: { asOf?: string; level?: string; district?: string; limit?: number }) {
  return privateApi<ChurnList>("/intel/churn/risk", {
    query: { as_of: params.asOf, level: params.level, district: params.district, limit: params.limit ?? 15 },
  });
}
