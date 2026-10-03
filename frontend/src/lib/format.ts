/** Small helpers that turn numbers and timestamps into text. No time zones involved: backend times are used as written. */

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function formatNumber(value: number): string {
  return Math.round(value).toLocaleString("en-US");
}

/** ৳1.2M, ৳45k, ৳820 */
export function formatBdt(value: number): string {
  const absolute = Math.abs(value);
  const sign = value < 0 ? "-" : "";
  if (absolute >= 1_000_000_000) {
    return `${sign}৳${(absolute / 1_000_000_000).toFixed(1)}B`;
  }
  if (absolute >= 1_000_000) {
    return `${sign}৳${(absolute / 1_000_000).toFixed(absolute >= 10_000_000 ? 0 : 1)}M`;
  }
  if (absolute >= 10_000) {
    return `${sign}৳${Math.round(absolute / 1000)}k`;
  }
  return `${sign}৳${formatNumber(absolute)}`;
}

/** ৳313,600 */
export function formatBdtFull(value: number): string {
  return `${value < 0 ? "-" : ""}৳${formatNumber(Math.abs(value))}`;
}

export function formatPercent(value: number, digits = 0): string {
  return `${(value * 100).toFixed(digits)}%`;
}

/** "2026-05-20T08:00:00" -> "08:00". Text such as "Wed 08:00 AM" is returned unchanged. */
export function formatTime(value: string | null | undefined): string {
  if (!value) return "-";
  if (value.includes("T")) return value.slice(11, 16);
  return value;
}

/** "2026-05-20T08:00:00" -> "20 May" */
export function formatDay(value: string | null | undefined): string {
  if (!value) return "-";
  const month = Number(value.slice(5, 7));
  const day = Number(value.slice(8, 10));
  if (!month || !day) return value;
  return `${day} ${MONTHS[month - 1]}`;
}

/** "2026-05-20T08:00:00" -> "20 May, 08:00" */
export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "-";
  return `${formatDay(value)}, ${formatTime(value)}`;
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  const first = parts[0] ? parts[0][0] : "";
  const second = parts.length > 1 ? parts[parts.length - 1][0] : "";
  return (first + second).toUpperCase();
}

/** "EMERGING_HIGH_PERFORMER" -> "Emerging high performer" */
export function humanize(code: string): string {
  const text = code.toLowerCase().split("_").join(" ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export type Tone = "danger" | "warning" | "success" | "info" | "ai" | "secondary";

export function levelTone(level: string): Tone {
  if (level === "HIGH") return "danger";
  if (level === "MEDIUM") return "warning";
  if (level === "LOW") return "success";
  return "secondary";
}

export function segmentTone(segment: string): Tone {
  if (segment === "DECLINING") return "danger";
  if (segment === "SERVICE_GAP") return "warning";
  if (segment === "EMERGING_HIGH_PERFORMER") return "success";
  if (segment === "TOP_PERFORMER") return "info";
  return "secondary";
}

/** Adds minutes to a backend timestamp ("2026-05-20T08:00:00"). Used to estimate when a van arrives. */
export function addMinutes(value: string, minutes: number): string {
  const moved = new Date(`${value.slice(0, 19)}Z`);
  moved.setUTCMinutes(moved.getUTCMinutes() + minutes);
  return moved.toISOString().slice(0, 19);
}

/** Upper-cases only the first letter and leaves the rest alone: "AI (LightGBM P90)" stays as it is. */
export function capitalizeFirst(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}
