import Link from "next/link";
import { Suspense } from "react";
import { Flame, Gauge, Medal, Rocket, TrendingDown, TriangleAlert, UserRound } from "lucide-react";
import { levelBarClass } from "@/components/dashboard/manager-widgets";
import { Bilingual } from "@/components/shared/bilingual";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { LinkTabs } from "@/components/shared/link-tabs";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { TableSkeleton } from "@/components/shared/skeletons";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { safe } from "@/lib/api/safe";
import { requireRole } from "@/lib/auth";
import { formatBdt, formatPercent, humanize, levelTone, segmentTone } from "@/lib/format";
import { getAsOf } from "@/lib/session";
import { buildHref } from "@/lib/url";
import { getChurnRisk, getPerformanceAgents, getPerformanceSummary } from "@/services/intel";

type SearchParams = Promise<{ tab?: string; segment?: string; level?: string }>;

const SEGMENTS = ["DECLINING", "SERVICE_GAP", "EMERGING_HIGH_PERFORMER", "TOP_PERFORMER"];
const LEVELS = ["HIGH", "MEDIUM", "LOW"];

export default async function InsightsPage({ searchParams }: { searchParams: SearchParams }) {
  const user = await requireRole(["manager", "analyst"]);
  const params = await searchParams;
  const tab = params.tab === "churn" ? "churn" : "performance";

  const tabs = [
    { href: "/insights", label: "Performance", active: tab === "performance" },
    { href: "/insights?tab=churn", label: "Risk of leaving", active: tab === "churn" },
  ];

  return (
    <>
      <PageHeader title="Agent insights" description="Who is growing, who is declining, who loses money to stockouts, and who may leave." />
      <div className="mb-5">
        <LinkTabs tabs={tabs} />
      </div>
      {tab === "performance" ? (
        <Suspense key={params.segment ?? "all"} fallback={<TableSkeleton rows={8} />}>
          <PerformanceTab segment={params.segment} district={user.district ?? undefined} />
        </Suspense>
      ) : (
        <Suspense key={params.level ?? "high"} fallback={<TableSkeleton rows={8} />}>
          <ChurnTab level={params.level} district={user.district ?? undefined} />
        </Suspense>
      )}
    </>
  );
}

async function PerformanceTab({ segment, district }: { segment?: string; district?: string }) {
  const asOf = await getAsOf();
  const chosen = segment && SEGMENTS.includes(segment) ? segment : undefined;
  const [summary, list] = await Promise.all([
    safe(() => getPerformanceSummary(asOf, district)),
    safe(() => getPerformanceAgents({ asOf, segment: chosen, district, limit: 15 })),
  ]);

  if (!summary.data) {
    return <ErrorState message={summary.error ?? "Performance insights are not available."} status={summary.status} />;
  }
  const counts = summary.data.segments;
  const segmentTabs = [
    { href: "/insights", label: "All", active: !chosen },
    ...SEGMENTS.map((item) => ({
      href: buildHref("/insights", { segment: item }),
      label: humanize(item),
      active: chosen === item,
      count: counts[item] ?? 0,
    })),
  ];

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Declining" value={String(counts.DECLINING ?? 0)} hint="falling behind similar agents" icon={TrendingDown} tone="danger" />
        <StatCard label="Service gap" value={String(counts.SERVICE_GAP ?? 0)} hint="strong demand, often out of money" icon={TriangleAlert} tone="warning" />
        <StatCard label="Emerging" value={String(counts.EMERGING_HIGH_PERFORMER ?? 0)} hint="growing faster than peers" icon={Rocket} tone="success" />
        <StatCard label="Lost at service-gap agents" value={formatBdt(summary.data.lostVolume4wAtServiceGapAgentsBdt)} hint="demand over the last 4 weeks" icon={Gauge} tone="info" />
      </div>

      <LinkTabs tabs={segmentTabs} />

      {!list.data || list.data.agents.length === 0 ? (
        <EmptyState icon={Medal} title="No agents in this group" description={list.error ?? "Try another group."} />
      ) : (
        <Card className="gap-0 py-0">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="pl-5">Agent</TableHead>
                <TableHead>Group</TableHead>
                <TableHead>Score</TableHead>
                <TableHead>Busier than</TableHead>
                <TableHead>Growth vs peers</TableHead>
                <TableHead>Lost to stockouts</TableHead>
                <TableHead className="pr-5">Suggested action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {list.data.agents.map((agent) => (
                <TableRow key={agent.agentCode}>
                  <TableCell className="pl-5">
                    <Link href={`/agents/${agent.agentCode}`} prefetch={false} className="font-medium hover:underline">
                      {agent.agentCode}
                    </Link>
                    <div className="text-xs text-muted-foreground">{agent.district}</div>
                  </TableCell>
                  <TableCell>
                    <Badge variant={segmentTone(agent.segment)}>{humanize(agent.segment)}</Badge>
                  </TableCell>
                  <TableCell className="tabular-nums">{agent.performanceScore.toFixed(0)}</TableCell>
                  <TableCell className="tabular-nums">{agent.volumePercentile.toFixed(0)}% of peers</TableCell>
                  <TableCell className={agent.relativeGrowth < 0 ? "tabular-nums text-danger" : "tabular-nums text-success"}>
                    {agent.relativeGrowth > 0 ? "+" : ""}
                    {formatPercent(agent.relativeGrowth)}
                  </TableCell>
                  <TableCell className="tabular-nums">{formatBdt(agent.lostVolume4wBdt)}</TableCell>
                  <TableCell className="max-w-xs pr-5 text-xs text-ink-secondary">{agent.recommendedAction}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <div className="border-t px-5 py-3 text-xs text-muted-foreground">
            Showing {list.data.agents.length} of {list.data.total}. Groups compare each agent with similar agents (same type), so network-wide swings such as Eid do not count as growth or decline.
          </div>
        </Card>
      )}
    </div>
  );
}

async function ChurnTab({ level, district }: { level?: string; district?: string }) {
  const asOf = await getAsOf();
  const chosen = level && LEVELS.includes(level) ? level : "HIGH";
  const { data, error, status } = await safe(() => getChurnRisk({ asOf, level: chosen, district, limit: 15 }));

  if (!data) {
    return <ErrorState title="Churn predictions are not available" message={error ?? "The churn model is not ready."} status={status} />;
  }

  const counts = data.levelCounts;
  const levelTabs = LEVELS.map((item) => ({
    href: buildHref("/insights", { tab: "churn", level: item }),
    label: humanize(item),
    active: chosen === item,
    count: counts[item] ?? 0,
  }));

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label="High risk of leaving" value={String(counts.HIGH ?? 0)} hint={`within ${data.horizonWeeks} weeks`} icon={Flame} tone="danger" />
        <StatCard label="Medium risk" value={String(counts.MEDIUM ?? 0)} icon={TriangleAlert} tone="warning" />
        <StatCard label="Already inactive" value={String(counts.INACTIVE ?? 0)} hint="activity has stopped" icon={UserRound} tone="info" />
      </div>

      <LinkTabs tabs={levelTabs} />

      {data.agents.length === 0 ? (
        <EmptyState icon={Medal} title="Nobody at this level" description="No active agent shows this level of risk right now." />
      ) : (
        <Card className="gap-0 py-0">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="pl-5">Agent</TableHead>
                <TableHead className="min-w-36">Chance of leaving</TableHead>
                <TableHead>Why</TableHead>
                <TableHead className="pr-5">Suggested action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.agents.map((agent) => (
                <TableRow key={agent.agentCode}>
                  <TableCell className="pl-5 align-top">
                    <Link href={`/agents/${agent.agentCode}`} prefetch={false} className="font-medium hover:underline">
                      {agent.agentCode}
                    </Link>
                    <div className="text-xs text-muted-foreground">{agent.district}</div>
                    <Badge variant={levelTone(agent.riskLevel)} className="mt-1.5">
                      {humanize(agent.riskLevel)}
                    </Badge>
                  </TableCell>
                  <TableCell className="align-top">
                    <div className="flex items-center gap-2">
                      <Progress value={agent.churnProbability * 100} barClassName={levelBarClass(agent.riskLevel)} className="w-16" />
                      <span className="text-xs tabular-nums text-ink-secondary">{formatPercent(agent.churnProbability)}</span>
                    </div>
                  </TableCell>
                  <TableCell className="max-w-sm align-top">
                    <ul className="space-y-1.5 text-xs text-ink-secondary">
                      {agent.drivers.slice(0, 3).map((driver) => (
                        <li key={driver.feature} className="flex gap-2">
                          <span className="mt-1.5 size-1 shrink-0 rounded-full bg-ai" />
                          <Bilingual en={driver.textEn} bn={driver.textBn} />
                        </li>
                      ))}
                    </ul>
                  </TableCell>
                  <TableCell className="max-w-xs pr-5 align-top text-xs text-ink-secondary">{agent.recommendedAction}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
    </div>
  );
}
