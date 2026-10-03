import { privateApi } from "@/lib/api/client";
import type { CopilotBrief } from "@/types/models";

export function getCopilotBrief(asOf?: string) {
  return privateApi<CopilotBrief>("/copilot/brief", { query: { as_of: asOf } });
}
