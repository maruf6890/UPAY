import { privateApi } from "@/lib/api/client";
import type { Dashboard, Meta, Metrics } from "@/types/models";

export function getDashboard(asOf?: string) {
  return privateApi<Dashboard>("/dashboard", { query: { as_of: asOf } });
}

export function getMeta() {
  return privateApi<Meta>("/meta");
}

export function getMetrics() {
  return privateApi<Metrics>("/metrics");
}
