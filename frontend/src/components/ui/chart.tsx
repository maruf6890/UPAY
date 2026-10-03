"use client";
import * as React from "react";
import * as Recharts from "recharts";
import { cn } from "@/lib/utils";

/** One entry per data series: the label shown in tooltips and the colour used in the chart. */
export type ChartConfig = Record<string, { label: string; color: string }>;

type ChartContainerProps = { config: ChartConfig; className?: string; children: React.ReactElement };

/** Gives a chart a fixed height, responsive width and the theme colours as CSS variables (--color-<series>). */
export function ChartContainer({ config, className, children }: ChartContainerProps) {
  const colourVariables: Record<string, string> = {};
  for (const key of Object.keys(config)) {
    colourVariables[`--color-${key}`] = config[key].color;
  }
  return (
    <div
      data-slot="chart"
      style={colourVariables as React.CSSProperties}
      className={cn(
        "h-[300px] w-full text-xs [&_.recharts-cartesian-axis-tick_text]:fill-muted-foreground [&_.recharts-cartesian-grid_line]:stroke-border/70",
        className,
      )}
    >
      <Recharts.ResponsiveContainer width="100%" height="100%">
        {children}
      </Recharts.ResponsiveContainer>
    </div>
  );
}

type TooltipItem = { dataKey?: string | number; name?: string | number; value?: number | string | (number | string)[]; color?: string };

type ChartTooltipContentProps = {
  active?: boolean;
  payload?: TooltipItem[];
  label?: string | number;
  config: ChartConfig;
  labelFormatter?: (label: string | number) => string;
  valueFormatter?: (value: number) => string;
};

/** The small white box that appears when you hover a chart. */
export function ChartTooltipContent({ active, payload, label, config, labelFormatter, valueFormatter }: ChartTooltipContentProps) {
  if (!active || !payload || payload.length === 0) {
    return null;
  }
  const title = label !== undefined && labelFormatter ? labelFormatter(label) : label;
  return (
    <div className="min-w-40 rounded-lg border bg-popover px-3 py-2 text-xs shadow-lg">
      {title !== undefined ? <div className="mb-1.5 font-medium text-foreground">{title}</div> : null}
      <div className="grid gap-1">
        {payload.map((item) => {
          const key = String(item.dataKey);
          const setting = config[key];
          const format = (raw: number | string) => (valueFormatter ? valueFormatter(Number(raw)) : String(raw));
          // a range (low to high) arrives as a list of two numbers
          const shown = Array.isArray(item.value) ? `${format(item.value[0])} to ${format(item.value[1])}` : format(item.value ?? 0);
          return (
            <div key={key} className="flex items-center justify-between gap-4">
              <span className="flex items-center gap-1.5 text-ink-secondary">
                <span className="size-2 rounded-full" style={{ background: setting ? setting.color : item.color }} />
                {setting ? setting.label : item.name}
              </span>
              <span className="font-medium tabular-nums text-foreground">{shown}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
