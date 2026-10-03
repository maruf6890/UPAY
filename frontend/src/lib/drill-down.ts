/**
 * The copilot sends links that point at BACKEND urls (for example /agents/AG0142/forecast?as_of=...).
 * This converter turns them into the matching SCREEN in this app.
 */
export function drillDownToRoute(backendPath: string): string {
  const agent = backendPath.match(/AG\d{4}/);
  if (backendPath.startsWith("/agents/") || backendPath.startsWith("/intel/") || backendPath.startsWith("/alerts/")) {
    if (backendPath.startsWith("/alerts/")) return "/alerts";
    if (agent) return `/agents/${agent[0]}`;
  }
  if (backendPath.startsWith("/alerts")) return "/alerts";
  if (backendPath.startsWith("/coverage")) return "/coverage";
  if (backendPath.startsWith("/rebalance")) return "/route";
  if (backendPath.startsWith("/risk")) return "/risk";
  if (backendPath.startsWith("/intel")) return "/insights";
  return "/dashboard";
}
