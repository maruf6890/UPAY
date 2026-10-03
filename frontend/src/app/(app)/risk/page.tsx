import Link from "next/link";
import { Suspense } from "react";
import { SearchX } from "lucide-react";
import { levelBarClass } from "@/components/dashboard/manager-widgets";
import { DistrictFilter } from "@/components/shared/district-filter";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { LevelBadge } from "@/components/shared/level-badge";
import { LinkTabs } from "@/components/shared/link-tabs";
import { PageHeader } from "@/components/shared/page-header";
import { TableSkeleton } from "@/components/shared/skeletons";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { safe } from "@/lib/api/safe";
import { requireRole } from "@/lib/auth";
import { formatBdt, formatPercent, formatTime, humanize } from "@/lib/format";
import { getAsOf } from "@/lib/session";
import { buildHref } from "@/lib/url";
import { getMeta } from "@/services/dashboard";
import { getRisk } from "@/services/liquidity";

type SearchParams = Promise<{ level?: string; district?: string }>;

export default async function RiskPage({ searchParams }: { searchParams: SearchParams }) {
  await requireRole(["manager"]);
  const { level, district } = await searchParams;
  const meta = await safe(() => getMeta());

  return (
    <>
      <PageHeader
        title="Liquidity risk"
        description="Every agent, ranked by how likely they are to run out of cash or e-float in the next 24 hours."
        actions={<DistrictFilter districts={meta.data?.districts ?? []} value={district} />}
      />
      <Suspense key={`${level}-${district}`} fallback={<TableSkeleton rows={8} />}>
        <RiskTable level={level} district={district} />
      </Suspense>
    </>
  );
}

async function RiskTable({ level, district }: { level?: string; district?: string }) {
  const asOf = await getAsOf();
  const { data, error, status } = await safe(() => getRisk({ asOf, level, district, limit: 100 }));

  if (!data) {
    return <ErrorState message={error ?? "Could not load the risk table."} status={status} />;
  }

  const total = data.summary.HIGH + data.summary.MEDIUM + data.summary.LOW;
  const tabs = [
    { href: buildHref("/risk", { district }), label: "All", active: !level, count: total },
    { href: buildHref("/risk", { district, level: "HIGH" }), label: "High", active: level === "HIGH", count: data.summary.HIGH },
    { href: buildHref("/risk", { district, level: "MEDIUM" }), label: "Medium", active: level === "MEDIUM", count: data.summary.MEDIUM },
    { href: buildHref("/risk", { district, level: "LOW" }), label: "Low", active: level === "LOW", count: data.summary.LOW },
  ];

  return (
    <div className="space-y-4">
      <LinkTabs tabs={tabs} />
      {data.agents.length === 0 ? (
        <EmptyState icon={SearchX} title="No agents match" description="Try another risk level or district." />
      ) : (
        <Card className="gap-0 py-0">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="pl-5">Agent</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Risk</TableHead>
                <TableHead className="min-w-36">Chance of running out</TableHead>
                <TableHead>Cash now</TableHead>
                <TableHead>E-float now</TableHead>
                <TableHead>Add</TableHead>
                <TableHead className="pr-5">Runs out</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.agents.map((agent) => {
                const topUp = agent.riskSide === "cash" ? agent.cashTopupBdt : agent.floatTopupBdt;
                return (
                  <TableRow key={agent.agentCode}>
                    <TableCell className="pl-5">
                      <Link href={`/agents/${agent.agentCode}`} prefetch={false} className="font-medium hover:underline">
                        {agent.agentCode}
                      </Link>
                      <div className="text-xs text-muted-foreground">{agent.district}</div>
                    </TableCell>
                    <TableCell className="text-ink-secondary">{humanize(agent.archetype)}</TableCell>
                    <TableCell>
                      <LevelBadge level={agent.riskLevel} />
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Progress value={agent.stockoutProbability * 100} barClassName={levelBarClass(agent.riskLevel)} className="w-20" />
                        <span className="text-xs tabular-nums text-ink-secondary">{formatPercent(agent.stockoutProbability)}</span>
                      </div>
                    </TableCell>
                    <TableCell className="tabular-nums">{formatBdt(agent.cashBalance)}</TableCell>
                    <TableCell className="tabular-nums">{formatBdt(agent.floatBalance)}</TableCell>
                    <TableCell className="tabular-nums">
                      {agent.riskLevel === "LOW" || topUp <= 0 ? (
                        <span className="text-muted-foreground">-</span>
                      ) : (
                        <>
                          {formatBdt(topUp)} <span className="text-xs text-muted-foreground">{agent.riskSide === "cash" ? "cash" : "e-float"}</span>
                        </>
                      )}
                    </TableCell>
                    <TableCell className="pr-5 text-ink-secondary">{agent.expectedStockoutTime ? formatTime(agent.expectedStockoutTime) : "-"}</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
          <div className="border-t px-5 py-3 text-xs text-muted-foreground">
            Showing the {data.agents.length} highest-risk agents. The percentage is a ranking aid, not an exact probability.
          </div>
        </Card>
      )}
    </div>
  );
}
