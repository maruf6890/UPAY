import { CalendarClock, MapPin } from "lucide-react";
import { WidgetGrid } from "@/components/dashboard/widget-grid";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { PageHeader } from "@/components/shared/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { safe } from "@/lib/api/safe";
import { formatDateTime } from "@/lib/format";
import { getAsOf } from "@/lib/session";
import { getDashboard } from "@/services/dashboard";
import { TriangleAlert } from "lucide-react";

export default async function DashboardPage() {
  const asOf = await getAsOf();
  const { data, error, status } = await safe(() => getDashboard(asOf));

  if (!data) {
    return (
      <>
        <PageHeader title="Dashboard" />
        <ErrorState message={error ?? "Could not load the dashboard."} status={status} />
      </>
    );
  }

  // "Area Manager (all districts)" -> "Area Manager". A real name such as "Maria Akter" stays as it is.
  const shownName = data.user.fullName.replace(/\s*\(.*\)/, "").trim();
  const title = data.user.role === "agent" ? "My agent dashboard" : `Welcome back, ${shownName}`;

  return (
    <>
      <PageHeader
        title={title}
        description={data.user.role === "agent" ? "Your cash and e-float for the next 24 hours." : "Here is the liquidity picture for your area."}
        actions={
          <>
            <Badge variant="outline" className="gap-1.5 py-1">
              <MapPin /> {data.scope}
            </Badge>
            <Badge variant="outline" className="gap-1.5 py-1">
              <CalendarClock /> As of {formatDateTime(data.asOf)}
            </Badge>
          </>
        }
      />

      {data.warnings.length > 0 ? (
        <Alert variant="warning" className="mb-4">
          <TriangleAlert />
          <AlertTitle>Some panels are unavailable</AlertTitle>
          <AlertDescription>{data.warnings.join(" ")}</AlertDescription>
        </Alert>
      ) : null}

      {data.widgets.length === 0 ? (
        <EmptyState title="Nothing to show yet" description="No dashboard panels are available for your account." />
      ) : (
        <WidgetGrid widgets={data.widgets} role={data.user.role} />
      )}
    </>
  );
}
