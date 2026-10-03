"use client";
import { CartesianGrid, Line, LineChart, ReferenceLine, Tooltip, XAxis, YAxis } from "recharts";
import { ChartContainer, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import { formatDay } from "@/lib/format";
import type { AnomalyPoint } from "@/types/models";

const config: ChartConfig = { alertScore: { label: "Anomaly score", color: "var(--ai)" } };

type AnomalyChartProps = { points: AnomalyPoint[]; medium: number; high: number };

/** How unusual the agent's behaviour looked each day. Above the amber line is flagged for review. */
export function AnomalyChart({ points, medium, high }: AnomalyChartProps) {
  return (
    <ChartContainer config={config} className="h-[240px]">
      <LineChart data={points} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="date" tickFormatter={formatDay} tickLine={false} axisLine={false} minTickGap={28} />
        <YAxis domain={[0.3, 0.6]} tickCount={4} tickLine={false} axisLine={false} width={40} />
        <Tooltip content={<ChartTooltipContent config={config} labelFormatter={(label) => formatDay(String(label))} valueFormatter={(value) => value.toFixed(3)} />} />
        <ReferenceLine y={medium} stroke="var(--warning)" strokeDasharray="4 4" label={{ value: "Review", position: "insideBottomRight", fill: "var(--warning)", fontSize: 11 }} />
        <ReferenceLine y={high} stroke="var(--danger)" strokeDasharray="4 4" label={{ value: "High", position: "insideTopRight", fill: "var(--danger)", fontSize: 11 }} />
        <Line type="monotone" dataKey="alertScore" stroke="var(--ai)" strokeWidth={2.5} dot={false} />
      </LineChart>
    </ChartContainer>
  );
}
