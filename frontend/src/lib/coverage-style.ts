import type { Tone } from "@/lib/format";

/** One colour and one label for each kind of coverage gap. Used by the map and by every list. */
export const GAP_STYLES: Record<string, { label: string; color: string; tone: Tone }> = {
  NO_COVERAGE: { label: "No coverage", color: "#D94A4A", tone: "danger" },
  UNDER_SERVED: { label: "Under-served", color: "#E0922B", tone: "warning" },
  CAPACITY_GAP: { label: "Capacity gap", color: "#8066D6", tone: "ai" },
  BALANCED: { label: "Balanced", color: "#16A36A", tone: "success" },
  OVER_SUPPLIED: { label: "Over-supplied", color: "#4387D8", tone: "info" },
  LOW_DEMAND: { label: "Low demand", color: "#CCD5E0", tone: "secondary" },
};

export const GAP_ORDER = ["NO_COVERAGE", "UNDER_SERVED", "CAPACITY_GAP", "BALANCED", "OVER_SUPPLIED", "LOW_DEMAND"];
