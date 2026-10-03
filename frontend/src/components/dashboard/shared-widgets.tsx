import Link from "next/link";
import { EmptyState } from "@/components/shared/empty-state";
import { Badge } from "@/components/ui/badge";
import { GAP_ORDER, GAP_STYLES } from "@/lib/coverage-style";
import { formatBdt, humanize, segmentTone } from "@/lib/format";
import { WidgetCard } from "./widget-card";
import type { AlertsWidgetData, CoverageGapsData, PerformanceWidgetData } from "@/types/widgets";

function SeverityBadge({ severity }: { severity: string }) {
  return <Badge variant={severity === "HIGH" ? "danger" : "warning"}>{humanize(severity)}</Badge>;
}

/** Managers get a short list, analysts get the signals behind each alert. The backend sends a different shape for each. */
export function AlertsWidget({ data }: { data: AlertsWidgetData }) {
  const analystRows = data.rows;
  const managerRows = data.top;
  const empty = (analystRows ?? managerRows ?? []).length === 0;

  return (
    <WidgetCard title="Alerts waiting for review" description={`${data.count} unusual agent(s) flagged for a person to check`} href="/alerts">
      {empty ? (
        <EmptyState title="Nothing to review" description="No agent is behaving unusually right now." />
      ) : analystRows ? (
        <ul className="divide-y">
          {analystRows.slice(0, 5).map((row) => (
            <li key={row.alertId} className="flex items-start gap-3 py-3 first:pt-0 last:pb-0">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <Link href={`/agents/${row.agentCode}`} prefetch={false} className="text-sm font-medium hover:underline">
                    {row.agentCode}
                  </Link>
                  <span className="text-xs text-muted-foreground">{row.district}</span>
                </div>
                <p className="mt-0.5 truncate text-xs text-ink-secondary">{row.signals[0]}</p>
              </div>
              <SeverityBadge severity={row.severity} />
            </li>
          ))}
        </ul>
      ) : (
        <ul className="divide-y">
          {(managerRows ?? []).map((row) => (
            <li key={row.alertId} className="flex items-center justify-between py-2.5 first:pt-0 last:pb-0">
              <Link href={`/agents/${row.agentCode}`} prefetch={false} className="text-sm font-medium hover:underline">
                {row.agentCode}
              </Link>
              <SeverityBadge severity={row.severity} />
            </li>
          ))}
        </ul>
      )}
    </WidgetCard>
  );
}

const SEGMENT_ORDER = ["DECLINING", "SERVICE_GAP", "EMERGING_HIGH_PERFORMER", "TOP_PERFORMER", "STEADY"];

export function PerformanceWidget({ data }: { data: PerformanceWidgetData }) {
  return (
    <WidgetCard title="Agent performance" description="Compared with similar agents" href="/insights" linkLabel="Details">
      <div className="space-y-4">
        <div className="flex flex-wrap gap-2">
          {SEGMENT_ORDER.filter((segment) => data.segments[segment] !== undefined).map((segment) => (
            <Badge key={segment} variant={segmentTone(segment)} className="gap-1.5 py-1">
              {humanize(segment)}
              <span className="font-semibold tabular-nums">{data.segments[segment]}</span>
            </Badge>
          ))}
        </div>
        <div className="rounded-lg bg-warning-soft px-3.5 py-3">
          <div className="text-lg font-semibold tabular-nums">{formatBdt(data.lostVolume4wAtServiceGapAgentsBdt)}</div>
          <div className="text-xs text-ink-secondary">demand lost over 4 weeks at agents that often run out of money</div>
        </div>
      </div>
    </WidgetCard>
  );
}

export function CoverageGapsWidget({ data }: { data: CoverageGapsData }) {
  return (
    <WidgetCard title="Where to expand" description="Biggest coverage gaps on the map" href="/coverage" linkLabel="Open map">
      <div className="space-y-4">
        <div className="flex flex-wrap gap-2">
          {GAP_ORDER.slice(0, 3).map((gap) => (
            <Badge key={gap} variant={GAP_STYLES[gap].tone} className="gap-1.5 py-1">
              {GAP_STYLES[gap].label}
              <span className="font-semibold tabular-nums">{data.hexagonsByGapType[gap] ?? 0}</span>
            </Badge>
          ))}
        </div>
        {data.rows.length === 0 ? (
          <EmptyState title="No gaps found" description="Coverage looks balanced everywhere." />
        ) : (
          <ul className="divide-y">
            {data.rows.slice(0, 3).map((row) => (
              <li key={`${row.area}-${row.gapType}-${row.opportunityBdtPerMonth}`} className="py-2.5 first:pt-0 last:pb-0">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium">{row.area}</span>
                  <Badge variant={GAP_STYLES[row.gapType]?.tone ?? "secondary"}>{GAP_STYLES[row.gapType]?.label ?? humanize(row.gapType)}</Badge>
                </div>
                <p className="mt-0.5 line-clamp-2 text-xs text-ink-secondary">{row.recommendation}</p>
              </li>
            ))}
          </ul>
        )}
        <p className="text-[11px] text-muted-foreground">{data.note}</p>
      </div>
    </WidgetCard>
  );
}
