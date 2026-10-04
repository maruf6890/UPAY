import Link from "next/link";
import { ArrowRight, CircleCheck, Flame, Lightbulb, TriangleAlert } from "lucide-react";
import { Bilingual } from "@/components/shared/bilingual";
import { EmptyState } from "@/components/shared/empty-state";
import { LevelBadge } from "@/components/shared/level-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { BalanceChart } from "@/components/charts/balance-chart";
import { formatBdt, formatBdtFull, formatDay, formatPercent, formatTime, humanize, segmentTone } from "@/lib/format";
import { cn } from "@/lib/utils";
import { WidgetCard } from "./widget-card";
import type { MyPerformanceData, MyStatusData, NextHoursData, RecentActivityData, WhyData } from "@/types/widgets";

const BANNERS: Record<string, { box: string; icon: typeof Flame; iconBox: string }> = {
  HIGH: { box: "bg-danger-soft", icon: Flame, iconBox: "bg-card text-danger" },
  MEDIUM: { box: "bg-warning-soft", icon: TriangleAlert, iconBox: "bg-card text-warning" },
  LOW: { box: "bg-success-soft", icon: CircleCheck, iconBox: "bg-card text-success" },
};

export function MyStatusWidget({ data }: { data: MyStatusData }) {
  const banner = BANNERS[data.riskLevel] ?? BANNERS.LOW;
  const Icon = banner.icon;
  const topUp = data.riskSide === "cash" ? data.cashTopupBdt : data.floatTopupBdt;
  const showTopUp = data.riskLevel !== "LOW" && topUp > 0;

  return (
    <Card className="gap-0 overflow-hidden py-0">
      <div className={cn("flex flex-wrap items-start gap-4 border-b px-6 py-5", banner.box)}>
        <span className={cn("flex size-11 shrink-0 items-center justify-center rounded-xl shadow-xs", banner.iconBox)}>
          <Icon className="size-5" />
        </span>
        <div className="min-w-60 flex-1">
          <div className="flex items-center gap-2">
            <LevelBadge level={data.riskLevel} />
            <span className="text-xs text-ink-secondary">{formatPercent(data.stockoutProbability)} chance of running out of {data.riskSide === "cash" ? "cash" : "e-float"}</span>
          </div>
          <p className="mt-2 text-lg leading-snug font-semibold">
            <Bilingual en={data.adviceEn} bn={data.adviceBn} className="bn" />
          </p>
        </div>
        {showTopUp ? (
          <div className="text-right">
            <div className="text-xs text-ink-secondary">Add before opening</div>
            <div className="text-3xl font-semibold tracking-tight tabular-nums">{formatBdtFull(topUp)}</div>
          </div>
        ) : null}
      </div>
      <div className="grid gap-px bg-border sm:grid-cols-3">
        <div className="bg-card px-6 py-4">
          <div className="text-xs text-muted-foreground">Cash in the drawer</div>
          <div className="mt-1 text-xl font-semibold tabular-nums">{formatBdtFull(data.cashBalanceBdt)}</div>
        </div>
        <div className="bg-card px-6 py-4">
          <div className="text-xs text-muted-foreground">E-float balance</div>
          <div className="mt-1 text-xl font-semibold tabular-nums">{formatBdtFull(data.eFloatBalanceBdt)}</div>
        </div>
        <div className="flex items-end justify-between bg-card px-6 py-4">
          <div>
            <div className="text-xs text-muted-foreground">Expected to run out</div>
            <div className="mt-1 text-xl font-semibold">{data.expectedStockoutTime ? formatTime(data.expectedStockoutTime) : "Not expected today"}</div>
          </div>
          <Button asChild variant="outline" size="sm">
            <Link href={`/agents/${data.agentCode}`} prefetch={false}>
              Full forecast <ArrowRight className="size-3.5" />
            </Link>
          </Button>
        </div>
      </div>
    </Card>
  );
}

export function NextHoursWidget({ data }: { data: NextHoursData }) {
  return (
    <WidgetCard title="The next 24 hours" description="Projected balance. Below the red line means you run out.">
      <BalanceChart points={data.points} />
    </WidgetCard>
  );
}

export function WhyWidget({ data }: { data: WhyData }) {
  return (
    <WidgetCard title="Why this forecast" description="The biggest reasons, in plain words">
      {data.reasons.length === 0 ? (
        <EmptyState title="No reasons to show" />
      ) : (
        <ul className="space-y-3">
          {data.reasons.map((reason) => (
            <li key={reason.textEn} className="flex gap-3 text-sm">
              <span className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full bg-brand-soft">
                <Lightbulb className="size-3.5 text-[#8a6a00]" />
              </span>
              <Bilingual en={reason.textEn} bn={reason.textBn} className="text-ink-secondary" />
            </li>
          ))}
        </ul>
      )}
    </WidgetCard>
  );
}

export function RecentActivityWidget({ data }: { data: RecentActivityData }) {
  return (
    <WidgetCard title="Recent activity" description="Cash paid out and received, per day" contentClassName="px-0">
      {data.rows.length === 0 ? (
        <div className="px-5">
          <EmptyState title="No recent activity" />
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="pl-5">Day</TableHead>
              <TableHead>Paid out</TableHead>
              <TableHead>Received</TableHead>
              <TableHead className="pr-5">Hours out of money</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.rows.map((row) => (
              <TableRow key={row.day}>
                <TableCell className="pl-5 font-medium">{formatDay(row.day)}</TableCell>
                <TableCell className="tabular-nums">{formatBdt(row.cashOutBdt)}</TableCell>
                <TableCell className="tabular-nums">{formatBdt(row.cashInBdt)}</TableCell>
                <TableCell className="pr-5">{row.stockoutHours > 0 ? <Badge variant="danger">{row.stockoutHours} h</Badge> : <span className="text-muted-foreground">None</span>}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </WidgetCard>
  );
}

export function MyPerformanceWidget({ data }: { data: MyPerformanceData }) {
  return (
    <WidgetCard title="How I compare" description="Against similar agents">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <div className="text-xs text-muted-foreground">Group</div>
          <div className="mt-1.5">
            <Badge variant={segmentTone(data.segment)}>{humanize(data.segment)}</Badge>
          </div>
        </div>
        <div>
          <div className="text-xs text-muted-foreground">Score</div>
          <div className="mt-1 text-2xl font-semibold tabular-nums">
            {data.performanceScore.toFixed(0)}
            <span className="text-sm font-normal text-muted-foreground"> / 100</span>
          </div>
        </div>
        <div className="col-span-2 text-sm text-ink-secondary">
          Busier than <span className="font-semibold text-foreground">{data.volumePercentileAmongSimilarAgents.toFixed(0)}%</span> of similar agents.
        </div>
      </div>
    </WidgetCard>
  );
}
