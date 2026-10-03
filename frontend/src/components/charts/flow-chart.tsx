"use client";
import { Area, CartesianGrid, ComposedChart, Line, Tooltip, XAxis, YAxis } from "recharts";
import { ChartContainer, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import { formatBdt, formatBdtFull, formatDateTime, formatTime } from "@/lib/format";
import type { HourlyPoint } from "@/types/models";

const config: ChartConfig = {
  band: { label: "Likely range", color: "var(--info)" },
  typical: { label: "Typical (model)", color: "var(--info)" },
  baseline: { label: "7-day average rule", color: "var(--text-color-subtle)" },
  actual: { label: "What happened", color: "var(--success)" },
};

/** Net cash going out each hour: the model's typical value and likely range, compared with the simple rule and with reality. */
export function FlowChart({ hourly }: { hourly: HourlyPoint[] }) {
  const data = hourly.map((hour) => ({
    time: hour.timestamp,
    band: [hour.netQ10, hour.netQ90],
    typical: hour.netQ50,
    baseline: hour.baselineNetQ50,
    actual: hour.actualNet,
  }));
  const hasActual = hourly.some((hour) => hour.actualNet !== null);

  return (
    <ChartContainer config={config}>
      <ComposedChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="time" tickFormatter={formatTime} tickLine={false} axisLine={false} minTickGap={28} />
        <YAxis tickFormatter={formatBdt} tickLine={false} axisLine={false} width={64} />
        <Tooltip content={<ChartTooltipContent config={config} labelFormatter={(label) => formatDateTime(String(label))} valueFormatter={formatBdtFull} />} />
        <Area type="monotone" dataKey="band" stroke="none" fill="var(--info)" fillOpacity={0.14} />
        <Line type="monotone" dataKey="baseline" stroke="var(--text-color-subtle)" strokeWidth={1.5} strokeDasharray="4 4" dot={false} />
        <Line type="monotone" dataKey="typical" stroke="var(--info)" strokeWidth={2.5} dot={false} />
        {hasActual ? <Line type="monotone" dataKey="actual" stroke="var(--success)" strokeWidth={0} dot={{ r: 3.5, fill: "var(--success)", strokeWidth: 0 }} activeDot={{ r: 5 }} /> : null}
      </ComposedChart>
    </ChartContainer>
  );
}
