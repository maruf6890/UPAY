import { EmptyState } from "@/components/shared/empty-state";
import { Badge } from "@/components/ui/badge";
import { formatDateTime, formatPercent, humanize } from "@/lib/format";
import { WidgetCard } from "./widget-card";
import type { ModelQualityData, ReviewActivityData } from "@/types/widgets";

export function ReviewActivityWidget({ data }: { data: ReviewActivityData }) {
  return (
    <WidgetCard title="Review activity" description="Decisions made so far" href="/alerts?status=confirmed" linkLabel="History">
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-lg bg-success-soft px-3.5 py-3">
            <div className="text-xl font-semibold tabular-nums">{data.totals.confirmed}</div>
            <div className="text-xs text-ink-secondary">confirmed</div>
          </div>
          <div className="rounded-lg bg-subtle px-3.5 py-3">
            <div className="text-xl font-semibold tabular-nums">{data.totals.dismissed}</div>
            <div className="text-xs text-ink-secondary">dismissed</div>
          </div>
        </div>
        {data.recent.length === 0 ? (
          <EmptyState title="No reviews yet" description="Confirm or dismiss an alert and it will show up here." />
        ) : (
          <ul className="divide-y">
            {data.recent.map((item) => (
              <li key={`${item.alertId}-${item.reviewedAt}`} className="flex items-center justify-between gap-2 py-2.5 text-sm first:pt-0 last:pb-0">
                <div className="min-w-0">
                  <div className="truncate font-medium">{item.alertId}</div>
                  <div className="text-xs text-muted-foreground">
                    {item.reviewer}, {formatDateTime(item.reviewedAt)}
                  </div>
                </div>
                <Badge variant={item.status === "confirmed" ? "success" : "secondary"}>{humanize(item.status)}</Badge>
              </li>
            ))}
          </ul>
        )}
      </div>
    </WidgetCard>
  );
}

type QualityItem = { label: string; value: string; hint: string };

function present(value: number | null | undefined): value is number {
  return value !== null && value !== undefined;
}

export function ModelQualityWidget({ data }: { data: ModelQualityData }) {
  const items: QualityItem[] = [];
  if (present(data.forecastErrorReductionVsBaselinePct)) {
    items.push({ label: "Hourly forecast error", value: `${data.forecastErrorReductionVsBaselinePct.toFixed(0)}% lower`, hint: "than the 7-day average rule" });
  }
  if (present(data.dailyErrorReductionVsBaselinePct)) {
    items.push({ label: "Daily net-flow error", value: `${data.dailyErrorReductionVsBaselinePct.toFixed(0)}% lower`, hint: "than the 7-day average rule" });
  }
  if (present(data.p90CashCoverage) && present(data.p90FloatCoverage)) {
    items.push({ label: "Bad-day coverage", value: `${formatPercent(data.p90CashCoverage)} / ${formatPercent(data.p90FloatCoverage)}`, hint: "cash / e-float, target 90%" });
  }
  if (present(data.stockoutHoursReductionVsHabitualPct)) {
    items.push({ label: "Stockout hours", value: `${data.stockoutHoursReductionVsHabitualPct.toFixed(0)}% fewer`, hint: "vs agents' usual restocking, same cash" });
  }
  if (present(data.anomalyAuc)) {
    items.push({ label: "Anomaly detector", value: `AUC ${data.anomalyAuc.toFixed(2)}`, hint: present(data.anomalyPrecision) && present(data.anomalyRecall) ? `precision ${formatPercent(data.anomalyPrecision)}, recall ${formatPercent(data.anomalyRecall)}` : "" });
  }
  if (present(data.churnAuc)) {
    items.push({ label: "Churn model", value: `AUC ${data.churnAuc.toFixed(2)}`, hint: "agents leaving within 4 weeks" });
  }

  return (
    <WidgetCard title="Model quality" description="Measured on a held-out period the models never saw" href="/models" linkLabel="Full report">
      <div className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item) => (
            <div key={item.label} className="rounded-lg border bg-sidebar-surface px-4 py-3">
              <div className="text-xs text-muted-foreground">{item.label}</div>
              <div className="mt-1 text-lg font-semibold tabular-nums">{item.value}</div>
              <div className="text-xs text-ink-secondary">{item.hint}</div>
            </div>
          ))}
        </div>
        <p className="text-xs text-muted-foreground">{data.note} The anomaly detector flags for review; most flags still need a person to dismiss them.</p>
      </div>
    </WidgetCard>
  );
}
