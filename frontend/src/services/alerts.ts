import { privateApi } from "@/lib/api/client";
import type { AlertsResponse } from "@/types/models";

type AlertParams = { asOf?: string; status?: string; lookbackDays?: number };

export function getAlerts(params: AlertParams) {
  return privateApi<AlertsResponse>("/alerts", {
    query: { as_of: params.asOf, status: params.status, lookback_days: params.lookbackDays },
  });
}
