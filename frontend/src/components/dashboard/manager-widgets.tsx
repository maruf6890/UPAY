import Link from "next/link";
import { Banknote, CircleCheck, Flame, TriangleAlert } from "lucide-react";
import { EmptyState } from "@/components/shared/empty-state";
import { LevelBadge } from "@/components/shared/level-badge";
import { StatCard } from "@/components/shared/stat-card";
import { Progress } from "@/components/ui/progress";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatBdt, formatPercent, formatTime, humanize } from "@/lib/format";
import { cn } from "@/lib/utils";
import { WidgetCard } from "./widget-card";
import type { DeliveryRouteData, LiquidityOverviewData, RetentionData, RiskiestAgentsData } from "@/types/widgets";

/** The bar colour that matches a risk level. */
export function levelBarClass(level: string): string {
  if (level === "HIGH") return "bg-danger";
  if (level === "MEDIUM") return "bg-warning";
  return "bg-success";
}

export function LiquidityOverviewWidget({ data }: { data: LiquidityOverviewData }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard label="High risk agents" value={String(data.counts.HIGH)} hint={`of ${data.agentsInScope} agents`} icon={Flame} tone="danger" />
      <StatCard label="Medium risk agents" value={String(data.counts.MEDIUM)} hint="may run short today" icon={TriangleAlert} tone="warning" />
      <StatCard label="Low risk agents" value={String(data.counts.LOW)} hint="balances look fine" icon={CircleCheck} tone="success" />
      <StatCard label="Cash to deliver" value={formatBdt(data.totalCashToDeliverBdt)} hint="to cover high and medium agents" icon={Banknote} tone="info" />
    </div>
  );
}

export function RiskiestAgentsWidget({ data }: { data: RiskiestAgentsData }) {
  return (
    <WidgetCard title="Riskiest agents" description="Most likely to run out in the next 24 hours" href="/risk" contentClassName="px-0">
      {data.rows.length === 0 ? (
        <div className="px-5">
          <EmptyState title="No agents at risk" description="Every agent in scope has enough cash and e-float for the next 24 hours." />
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="pl-5">Agent</TableHead>
              <TableHead>Risk</TableHead>
              <TableHead className="min-w-36">Chance of running out</TableHead>
              <TableHead>Add</TableHead>
              <TableHead className="pr-5">Runs out</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.rows.map((row) => (
              <TableRow key={row.agentCode}>
                <TableCell className="pl-5">
                  <Link href={`/agents/${row.agentCode}`} prefetch={false} className="font-medium hover:underline">
                    {row.agentCode}
                  </Link>
                  <div className="text-xs text-muted-foreground">{row.district}</div>
                </TableCell>
                <TableCell>
                  <LevelBadge level={row.riskLevel} />
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Progress value={row.stockoutProbability * 100} barClassName={levelBarClass(row.riskLevel)} className="w-20" />
                    <span className="text-xs tabular-nums text-ink-secondary">{formatPercent(row.stockoutProbability)}</span>
                  </div>
                </TableCell>
                <TableCell className="tabular-nums">
                  {formatBdt(row.riskSide === "cash" ? row.cashTopupBdt : row.floatTopupBdt)}
                  <span className="ml-1 text-xs text-muted-foreground">{row.riskSide === "cash" ? "cash" : "e-float"}</span>
                </TableCell>
                <TableCell className="pr-5 text-ink-secondary">{row.expectedStockoutTime ? formatTime(row.expectedStockoutTime) : "Not expected"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </WidgetCard>
  );
}

export function DeliveryRouteWidget({ data }: { data: DeliveryRouteData }) {
  return (
    <WidgetCard title="Cash delivery route" description="One van, ordered stops" href="/route" linkLabel="Open route">
      {data.stops === 0 ? (
        <EmptyState title="No delivery needed" description="No agent in scope needs a cash delivery right now." />
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <div className="text-xl font-semibold tabular-nums">{data.stops}</div>
              <div className="text-xs text-muted-foreground">stops</div>
            </div>
            <div>
              <div className="text-xl font-semibold tabular-nums">{data.totalKm}</div>
              <div className="text-xs text-muted-foreground">km</div>
            </div>
            <div>
              <div className="text-xl font-semibold tabular-nums">{formatBdt(data.cashToCarryBdt)}</div>
              <div className="text-xs text-muted-foreground">cash to carry</div>
            </div>
          </div>
          <ol className="space-y-2.5">
            {data.nextStops.map((stop) => (
              <li key={stop.agentCode} className="flex items-center gap-3 text-sm">
                <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">{stop.stop}</span>
                <Link href={`/agents/${stop.agentCode}`} prefetch={false} className="font-medium hover:underline">
                  {stop.agentCode}
                </Link>
                <span className="ml-auto tabular-nums text-ink-secondary">{formatBdt(stop.cashToDeliverBdt)}</span>
                <span className="w-14 text-right text-xs text-muted-foreground">{stop.etaMin} min</span>
              </li>
            ))}
          </ol>
          {data.digitalTransfers > 0 ? (
            <p className="text-xs text-muted-foreground">Plus {data.digitalTransfers} e-float top-up(s) to send digitally, no visit needed.</p>
          ) : null}
        </div>
      )}
    </WidgetCard>
  );
}

export function RetentionWidget({ data }: { data: RetentionData }) {
  return (
    <WidgetCard title="Agents at risk of leaving" description={`${data.high} high and ${data.medium} medium risk in the next 4 weeks`} href="/insights?tab=churn" contentClassName="px-0">
      {data.rows.length === 0 ? (
        <div className="px-5">
          <EmptyState title="Nobody is likely to leave" description="No active agent shows a clear drop in activity right now." />
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="pl-5">Agent</TableHead>
              <TableHead className="min-w-32">Chance of leaving</TableHead>
              <TableHead className="pr-5">Main reason</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.rows.map((row) => (
              <TableRow key={row.agentCode}>
                <TableCell className="pl-5">
                  <Link href={`/agents/${row.agentCode}`} prefetch={false} className="font-medium hover:underline">
                    {row.agentCode}
                  </Link>
                  <div className="text-xs text-muted-foreground">{row.district}</div>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Progress value={row.churnProbability * 100} barClassName={levelBarClass(row.riskLevel)} className="w-16" />
                    <span className="text-xs tabular-nums text-ink-secondary">{formatPercent(row.churnProbability)}</span>
                  </div>
                </TableCell>
                <TableCell className={cn("max-w-sm pr-5 text-sm text-ink-secondary")}>{row.topReason || humanize(row.riskLevel)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </WidgetCard>
  );
}
