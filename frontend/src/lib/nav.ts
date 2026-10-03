import { Activity, BellRing, Gauge, LayoutDashboard, Map, Route, Sparkles, TrendingUp, type LucideIcon } from "lucide-react";
import type { Role } from "@/types/models";

export type NavItem = { href: string; label: string; icon: LucideIcon; roles: Role[] };

/** The menu. Each role only sees the items listed for it. */
export const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, roles: ["manager", "agent", "analyst"] },
  { href: "/risk", label: "Liquidity risk", icon: Activity, roles: ["manager"] },
  { href: "/route", label: "Cash route", icon: Route, roles: ["manager"] },
  { href: "/alerts", label: "Alerts", icon: BellRing, roles: ["manager", "analyst"] },
  { href: "/insights", label: "Agent insights", icon: TrendingUp, roles: ["manager", "analyst"] },
  { href: "/coverage", label: "Coverage map", icon: Map, roles: ["manager", "analyst"] },
  { href: "/copilot", label: "Copilot", icon: Sparkles, roles: ["manager", "analyst"] },
  { href: "/models", label: "Model quality", icon: Gauge, roles: ["analyst"] },
];

export const ROLE_LABELS: Record<Role, string> = {
  manager: "Area manager",
  agent: "Agent",
  analyst: "Risk analyst",
};
