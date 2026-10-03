"use client";
import { useState } from "react";
import { Area, CartesianGrid, ComposedChart, Line, ReferenceLine, Tooltip, XAxis, YAxis } from "recharts";
import { ChartContainer, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { formatBdt, formatBdtFull, formatDateTime, formatTime } from "@/lib/format";

export type BalancePoint = { time: string; cashTypical: number; cashBadDay: number; floatTypical: number; floatBadDay: number };

type Side = "cash" | "float";

/** How much cash (or e-float) the agent will have left, hour by hour. Below the red line means running out. */
export function BalanceChart({ points, initialSide = "cash" }: { points: BalancePoint[]; initialSide?: Side }) {
  const [side, setSide] = useState<Side>(initialSide);
  const typicalKey = side === "cash" ? "cashTypical" : "floatTypical";
  const badKey = side === "cash" ? "cashBadDay" : "floatBadDay";

  const config: ChartConfig = {
    [typicalKey]: { label: "Typical day", color: "var(--info)" },
    [badKey]: { label: "Bad day (1 in 10)", color: "var(--danger)" },
  };

  return (
    <div className="space-y-3">
      <Tabs value={side} onValueChange={(value) => setSide(value as Side)}>
        <TabsList>
          <TabsTrigger value="cash">Cash</TabsTrigger>
          <TabsTrigger value="float">E-float</TabsTrigger>
        </TabsList>
      </Tabs>

      <ChartContainer config={config}>
        <ComposedChart data={points} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="fillTypical" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="var(--info)" stopOpacity={0.25} />
              <stop offset="95%" stopColor="var(--info)" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="time" tickFormatter={formatTime} tickLine={false} axisLine={false} minTickGap={28} />
          <YAxis
            tickFormatter={formatBdt}
            tickLine={false}
            axisLine={false}
            width={64}
            domain={[(lowest: number) => Math.min(lowest, 0) * 1.08, (highest: number) => Math.max(highest, 0) * 1.1 + 25000]}
          />
          <Tooltip
            content={<ChartTooltipContent config={config} labelFormatter={(label) => formatDateTime(String(label))} valueFormatter={formatBdtFull} />}
          />
          <ReferenceLine y={0} stroke="var(--danger)" strokeDasharray="4 4" label={{ value: "Out of money", position: "insideTopRight", fill: "var(--danger)", fontSize: 11 }} />
          <Area type="monotone" dataKey={typicalKey} stroke="var(--info)" strokeWidth={2} fill="url(#fillTypical)" dot={false} />
          <Line type="monotone" dataKey={badKey} stroke="var(--danger)" strokeWidth={2} strokeDasharray="5 4" dot={false} />
        </ComposedChart>
      </ChartContainer>
    </div>
  );
}
