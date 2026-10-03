import { Coins, Hexagon, Info, Percent, ShieldAlert } from "lucide-react";
import { WidgetCard } from "@/components/dashboard/widget-card";
import { CoverageMapLoader } from "@/components/map/coverage-map-loader";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { safe } from "@/lib/api/safe";
import { requireRole } from "@/lib/auth";
import { GAP_STYLES } from "@/lib/coverage-style";
import { formatBdt, formatPercent } from "@/lib/format";
import { getAsOf } from "@/lib/session";
import { getCoverageGaps, getCoverageMap, getCoverageSummary } from "@/services/coverage";

export default async function CoveragePage() {
  await requireRole(["manager", "analyst"]);
  const asOf = await getAsOf();
  const [map, summary, gaps] = await Promise.all([
    safe(() => getCoverageMap(asOf)),
    safe(() => getCoverageSummary(asOf)),
    safe(() => getCoverageGaps(asOf, 8)),
  ]);

  if (!map.data || !summary.data) {
    return (
      <>
        <PageHeader title="Coverage map" />
        <ErrorState message={map.error ?? summary.error ?? "Could not load the coverage map."} status={map.status ?? summary.status} />
      </>
    );
  }

  const stats = summary.data;
  return (
    <>
      <PageHeader title="Coverage map" description="Where agents are missing, stretched, or running out of money. Each hexagon is about 250 km²." />

      <Alert variant="info" className="mb-4">
        <Info />
        <AlertTitle>Read this map as a ranking, not a measurement</AlertTitle>
        <AlertDescription>{stats.note}</AlertDescription>
      </Alert>

      <div className="mb-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Areas mapped" value={String(stats.hexagons)} hint={stats.window} icon={Hexagon} tone="info" />
        <StatCard label="Demand covered" value={formatPercent(stats.estimatedDemandCoveredShare)} hint="estimated" icon={Percent} tone="success" />
        <StatCard label="Untapped volume" value={`${formatBdt(stats.untappedMonthlyVolumeBdt)}/mo`} hint="where no agent reaches (assumed)" icon={Coins} tone="warning" />
        <StatCard label="Lost to stockouts" value={`${formatBdt(stats.monthlyVolumeLostToStockoutsBdt)}/mo`} hint="demand agents could not serve" icon={ShieldAlert} tone="danger" />
      </div>

      <div className="grid gap-4 lg:grid-cols-12">
        <div className="lg:col-span-8">
          <CoverageMapLoader data={map.data} />
        </div>
        <div className="lg:col-span-4">
          <WidgetCard title="Biggest gaps" description="Click a hexagon on the map for details">
            {!gaps.data || gaps.data.gaps.length === 0 ? (
              <EmptyState title="No gaps found" description={gaps.error ?? "Coverage looks balanced."} />
            ) : (
              <ul className="divide-y">
                {gaps.data.gaps.map((gap) => (
                  <li key={gap.h3} className="py-3 first:pt-0 last:pb-0">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-medium">{gap.nearestTown}</span>
                      <Badge variant={GAP_STYLES[gap.gapType]?.tone ?? "secondary"}>{GAP_STYLES[gap.gapType]?.label ?? gap.gapType}</Badge>
                    </div>
                    <p className="mt-1 text-xs leading-relaxed text-ink-secondary">{gap.recommendation}</p>
                    <p className="mt-1 text-xs font-medium tabular-nums text-foreground">{formatBdt(gap.opportunityBdtPerMonth)} / month</p>
                  </li>
                ))}
              </ul>
            )}
          </WidgetCard>
        </div>
      </div>
    </>
  );
}
