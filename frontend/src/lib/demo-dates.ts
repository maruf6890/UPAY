/**
 * The data is synthetic and ends on 30 June 2026, so the app has a "demo date" picker.
 * Each date shows a different situation. "default" lets the backend choose.
 */
export type DemoDate = { value: string; label: string; hint: string };

export const DEMO_DATES: DemoDate[] = [
  { value: "default", label: "Server default", hint: "20 May, Eid week" },
  { value: "2026-05-18 08:00", label: "18 May, 8am", hint: "A normal busy morning" },
  { value: "2026-05-20 08:00", label: "20 May, 8am", hint: "Eid week cash crunch" },
  { value: "2026-06-20 08:00", label: "20 Jun, 8am", hint: "Calm, few agents at risk" },
  { value: "2026-03-23 07:00", label: "23 Mar, 7am", hint: "E-float risk after Eid" },
];
