import Link from "next/link";
import { Banknote, Route as RouteIcon, Smartphone, Truck } from "lucide-react";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { LevelBadge } from "@/components/shared/level-badge";
import { PageHeader } from "@/components/shared/page-header";
import { RouteFilters } from "@/components/shared/route-filters";
import { StatCard } from "@/components/shared/stat-card";
import { WidgetCard } from "@/components/dashboard/widget-card";
import { RouteMapLoader } from "@/components/map/route-map-loader";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { safe } from "@/lib/api/safe";
import { requireRole } from "@/lib/auth";
import { addMinutes, formatBdt, formatBdtFull, formatTime } from "@/lib/format";
import { getAsOf } from "@/lib/session";
import { getMeta } from "@/services/dashboard";
import { getRoutePlan } from "@/services/liquidity";
import { Info } from "lucide-react";

type SearchParams = Promise<{ district?: string; capacity?: string; stops?: string }>;

const DEFAULT_CAPACITY = 5_000_000;
const DEFAULT_STOPS = 12;

/** Reads a number from the address bar and falls back to a default when it is missing or silly. */
function readNumber(text: string | undefined, fallback: number, min: number, max: number): number {
  const value = Number(text);
  if (!text || Number.isNaN(value) || value < min || value > max) {
    return fallback;
  }
  return value;
}

export default async function RoutePage({ searchParams }: { searchParams: SearchParams }) {
  const user = await requireRole(["manager"]);
  const params = await searchParams;
  const district = params.district ?? user.district ?? "Dhaka";
  const capacity = readNumber(params.capacity, DEFAULT_CAPACITY, 1, 1_000_000_000);
  const maxStops = Math.round(readNumber(params.stops, DEFAULT_STOPS, 1, 40));

  const asOf = await getAsOf();
  const [meta, route] = await Promise.all([
    safe(() => getMeta()),
    safe(() => getRoutePlan({ asOf, district, vanCapacityBdt: capacity, maxStops })),
  ]);

  return (
    <>
      <PageHeader title="Cash delivery route" description="Which agents one van should visit, and in what order." />
      <div className="mb-6">
        <RouteFilters districts={meta.data?.districts ?? [district]} district={district} capacity={capacity} maxStops={maxStops} />
      </div>

      {!route.data ? (
        <ErrorState message={route.error ?? "Could not plan the route."} status={route.status} />
      ) : route.data.stops.length === 0 ? (
        <EmptyState
          icon={Truck}
          title={`No cash delivery needed in ${district}`}
          description="No high or medium risk agent here needs cash, or the van is too small to carry any of the amounts."
        />
      ) : (
        <RoutePlanView plan={route.data} />
      )}
    </>
  );
}

function RoutePlanView({ plan }: { plan: NonNullable<Awaited<ReturnType<typeof getRoutePlan>>> }) {
  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Stops" value={String(plan.stops.length)} icon={Truck} tone="default" />
        <StatCard label="Driving distance" value={`${plan.totalKm} km`} hint="one way, straight lines" icon={RouteIcon} tone="info" />
        <StatCard label="Cash to carry" value={formatBdt(plan.totalCashBdt)} icon={Banknote} tone="success" />
        <StatCard label="E-float to send" value={String(plan.digitalTransfers.length)} hint="digital, no visit needed" icon={Smartphone} tone="ai" />
      </div>

      <div className="grid gap-4 lg:grid-cols-12">
        <div className="lg:col-span-7">
          <RouteMapLoader plan={plan} />
        </div>
        <div className="lg:col-span-5">
          <WidgetCard title="Visit order" description="Estimated arrival, assuming the van leaves at the demo date">
            <ol className="space-y-3.5">
              {plan.stops.map((stop) => {
                const arrival = addMinutes(plan.asOf, stop.etaMin);
                const late = stop.firstRiskTime !== null && arrival > stop.firstRiskTime;
                return (
                  <li key={stop.agentCode} className="flex items-start gap-3">
                    <span className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">{stop.stop}</span>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <Link href={`/agents/${stop.agentCode}`} prefetch={false} className="text-sm font-medium hover:underline">
                          {stop.agentCode}
                        </Link>
                        <LevelBadge level={stop.riskLevel} />
                        {late ? <Badge variant="danger">Arrives after they run out</Badge> : null}
                      </div>
                      <div className="mt-0.5 text-xs text-muted-foreground">
                        {stop.district}, {stop.legKm} km, arrive about {formatTime(arrival)}
                        {stop.firstRiskTime ? `, bad-day stockout ${formatTime(stop.firstRiskTime)}` : ""}
                      </div>
                    </div>
                    <div className="text-right text-sm font-medium tabular-nums">{formatBdtFull(stop.cashToDeliverBdt)}</div>
                  </li>
                );
              })}
            </ol>
          </WidgetCard>
        </div>
      </div>

      {plan.digitalTransfers.length > 0 || plan.unserved.length > 0 ? (
        <div className={plan.digitalTransfers.length > 0 && plan.unserved.length > 0 ? "grid gap-4 lg:grid-cols-2" : "grid gap-4"}>
          {plan.digitalTransfers.length > 0 ? (
            <WidgetCard title="E-float to send digitally" description="No visit needed">
              <ul className="divide-y text-sm">
                {plan.digitalTransfers.map((transfer) => (
                  <li key={transfer.agentCode} className="flex justify-between py-2 first:pt-0 last:pb-0">
                    <Link href={`/agents/${transfer.agentCode}`} prefetch={false} className="font-medium hover:underline">
                      {transfer.agentCode}
                    </Link>
                    <span className="tabular-nums">{formatBdtFull(transfer.floatTopupBdt)}</span>
                  </li>
                ))}
              </ul>
            </WidgetCard>
          ) : null}
          {plan.unserved.length > 0 ? (
            <WidgetCard title="Needs cash but did not fit" description="The van was full. These need a second van or another trip.">
              <ul className="divide-y text-sm">
                {plan.unserved.map((item) => (
                  <li key={item.agentCode} className="flex justify-between py-2 first:pt-0 last:pb-0">
                    <Link href={`/agents/${item.agentCode}`} prefetch={false} className="font-medium hover:underline">
                      {item.agentCode}
                    </Link>
                    <span className="tabular-nums">{formatBdtFull(item.cashTopupBdt)}</span>
                  </li>
                ))}
              </ul>
            </WidgetCard>
          ) : null}
        </div>
      ) : null}

      <Alert variant="info">
        <Info />
        <AlertTitle>How this route is built</AlertTitle>
        <AlertDescription>
          Agents are picked by risk times shortfall until the van is full, then visited nearest-first using straight-line distance at 30 km/h plus 10 minutes per stop. It is a simple heuristic: it does not yet put the most urgent agents first, and the depot is the centre of the chosen agents.
        </AlertDescription>
      </Alert>
    </div>
  );
}
