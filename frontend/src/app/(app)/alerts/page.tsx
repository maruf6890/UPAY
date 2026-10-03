import { Suspense } from "react";
import { ShieldCheck } from "lucide-react";
import { AlertCard } from "@/components/alerts/alert-card";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { LinkTabs } from "@/components/shared/link-tabs";
import { PageHeader } from "@/components/shared/page-header";
import { TableSkeleton } from "@/components/shared/skeletons";
import { safe } from "@/lib/api/safe";
import { requireRole } from "@/lib/auth";
import { getAsOf } from "@/lib/session";
import { buildHref } from "@/lib/url";
import { getAlerts } from "@/services/alerts";

type SearchParams = Promise<{ status?: string; days?: string }>;

const STATUSES = ["pending", "confirmed", "dismissed"];
const DAY_OPTIONS = ["1", "3", "7"];

export default async function AlertsPage({ searchParams }: { searchParams: SearchParams }) {
  await requireRole(["manager", "analyst"]);
  const params = await searchParams;
  const status = params.status && STATUSES.includes(params.status) ? params.status : "pending";
  const days = params.days && DAY_OPTIONS.includes(params.days) ? params.days : "3";

  const statusTabs = [
    { href: buildHref("/alerts", { status: "pending", days }), label: "Waiting for review", active: status === "pending" },
    { href: buildHref("/alerts", { status: "confirmed", days }), label: "Confirmed", active: status === "confirmed" },
    { href: buildHref("/alerts", { status: "dismissed", days }), label: "Dismissed", active: status === "dismissed" },
  ];
  const dayTabs = DAY_OPTIONS.map((option) => ({
    href: buildHref("/alerts", { status, days: option }),
    label: option === "1" ? "Last day" : `Last ${option} days`,
    active: days === option,
  }));

  return (
    <>
      <PageHeader
        title="Alerts"
        description="Agents behaving unusually compared with their own history and with similar agents. These are flags for a person to check, not accusations."
      />
      <div className="mb-5 flex flex-wrap items-center gap-3">
        <LinkTabs tabs={statusTabs} />
        <LinkTabs tabs={dayTabs} />
      </div>
      <Suspense key={`${status}-${days}`} fallback={<TableSkeleton rows={4} />}>
        <AlertList status={status} days={Number(days)} />
      </Suspense>
    </>
  );
}

async function AlertList({ status, days }: { status: string; days: number }) {
  const asOf = await getAsOf();
  const { data, error, status: httpStatus } = await safe(() => getAlerts({ asOf, status, lookbackDays: days }));

  if (!data) {
    return <ErrorState message={error ?? "Could not load the alerts."} status={httpStatus} />;
  }
  if (data.alerts.length === 0) {
    return (
      <EmptyState
        icon={ShieldCheck}
        title={status === "pending" ? "Nothing waiting for review" : `No ${status} alerts in this period`}
        description="Try a longer time window, or check another tab."
      />
    );
  }
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">{data.alerts.length} alert(s). Showing each agent's latest flagged day.</p>
      {data.alerts.map((alert) => (
        <AlertCard key={alert.alertId} alert={alert} />
      ))}
    </div>
  );
}
