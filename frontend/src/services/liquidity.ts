import { privateApi } from "@/lib/api/client";
import type { AgentForecast, AnomalyPoint, RiskAgent, RiskLevel, RiskResponse, RoutePlan } from "@/types/models";

/** /risk calls the probability "stockout_prob" and the times "p50_stockout_time". This converter uses the same names as the forecast. */
type RawRiskAgent = Omit<RiskAgent, "stockoutProbability" | "expectedStockoutTime" | "possibleStockoutTimeP90"> & {
  stockoutProb: number;
  p50StockoutTime: string | null;
  p90StockoutTime: string | null;
};
type RawRiskResponse = { asOf: string; summary: Record<RiskLevel, number>; agents: RawRiskAgent[] };

function toRiskAgent(raw: RawRiskAgent): RiskAgent {
  const { stockoutProb, p50StockoutTime, p90StockoutTime, ...rest } = raw;
  return { ...rest, stockoutProbability: stockoutProb, expectedStockoutTime: p50StockoutTime, possibleStockoutTimeP90: p90StockoutTime };
}

type RiskParams = { asOf?: string; district?: string; level?: string; limit?: number };

export async function getRisk(params: RiskParams): Promise<RiskResponse> {
  const raw = await privateApi<RawRiskResponse>("/risk", {
    query: { as_of: params.asOf, district: params.district, level: params.level, limit: params.limit ?? 100 },
  });
  return { asOf: raw.asOf, summary: raw.summary, agents: raw.agents.map(toRiskAgent) };
}

export function getAgentForecast(code: string, asOf?: string) {
  return privateApi<AgentForecast>(`/agents/${code}/forecast`, { query: { as_of: asOf } });
}

export function getAgentAnomaly(code: string, days = 30, asOf?: string) {
  return privateApi<AnomalyPoint[]>(`/agents/${code}/anomaly`, { query: { days, as_of: asOf } });
}

type RouteParams = { asOf?: string; district?: string; vanCapacityBdt?: number; maxStops?: number };

export function getRoutePlan(params: RouteParams) {
  return privateApi<RoutePlan>("/rebalance", {
    query: { as_of: params.asOf, district: params.district, van_capacity_bdt: params.vanCapacityBdt, max_stops: params.maxStops },
  });
}
