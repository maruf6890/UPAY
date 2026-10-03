import { WidgetCard } from "./widget-card";
import { MyPerformanceWidget, MyStatusWidget, NextHoursWidget, RecentActivityWidget, WhyWidget } from "./agent-widgets";
import { ModelQualityWidget, ReviewActivityWidget } from "./analyst-widgets";
import { DeliveryRouteWidget, LiquidityOverviewWidget, RetentionWidget, RiskiestAgentsWidget } from "./manager-widgets";
import { AlertsWidget, CoverageGapsWidget, PerformanceWidget } from "./shared-widgets";
import type { Role, Widget } from "@/types/models";
import type * as W from "@/types/widgets";

/** How wide each widget is on a large screen (out of 12 columns). The same widget can be sized differently per role. */
const SPANS: Record<Role, Record<string, string>> = {
  manager: {
    liquidity_overview: "lg:col-span-12",
    riskiest_agents: "lg:col-span-8",
    delivery_route: "lg:col-span-4",
    pending_alerts: "lg:col-span-4",
    retention: "lg:col-span-8",
    performance: "lg:col-span-6",
    coverage_gaps: "lg:col-span-6",
  },
  agent: {
    my_status: "lg:col-span-12",
    next_24_hours: "lg:col-span-8",
    why: "lg:col-span-4",
    recent_activity: "lg:col-span-7",
    my_performance: "lg:col-span-5",
  },
  analyst: {
    pending_alerts: "lg:col-span-8",
    review_activity: "lg:col-span-4",
    model_quality: "lg:col-span-12",
    performance: "lg:col-span-6",
    coverage_gaps: "lg:col-span-6",
  },
};

/** A widget this app does not know yet still shows up, so a new backend widget is never silently lost. */
function GenericWidget({ widget }: { widget: Widget }) {
  return (
    <WidgetCard title={widget.title}>
      <pre className="overflow-x-auto rounded-lg bg-subtle p-3 text-xs">{JSON.stringify(widget.data, null, 2)}</pre>
    </WidgetCard>
  );
}

function renderWidget(widget: Widget) {
  const data = widget.data;
  switch (widget.key) {
    case "liquidity_overview":
      return <LiquidityOverviewWidget data={data as unknown as W.LiquidityOverviewData} />;
    case "riskiest_agents":
      return <RiskiestAgentsWidget data={data as unknown as W.RiskiestAgentsData} />;
    case "delivery_route":
      return <DeliveryRouteWidget data={data as unknown as W.DeliveryRouteData} />;
    case "pending_alerts":
      return <AlertsWidget data={data as unknown as W.AlertsWidgetData} />;
    case "retention":
      return <RetentionWidget data={data as unknown as W.RetentionData} />;
    case "performance":
      return <PerformanceWidget data={data as unknown as W.PerformanceWidgetData} />;
    case "coverage_gaps":
      return <CoverageGapsWidget data={data as unknown as W.CoverageGapsData} />;
    case "my_status":
      return <MyStatusWidget data={data as unknown as W.MyStatusData} />;
    case "next_24_hours":
      return <NextHoursWidget data={data as unknown as W.NextHoursData} />;
    case "why":
      return <WhyWidget data={data as unknown as W.WhyData} />;
    case "recent_activity":
      return <RecentActivityWidget data={data as unknown as W.RecentActivityData} />;
    case "my_performance":
      return <MyPerformanceWidget data={data as unknown as W.MyPerformanceData} />;
    case "review_activity":
      return <ReviewActivityWidget data={data as unknown as W.ReviewActivityData} />;
    case "model_quality":
      return <ModelQualityWidget data={data as unknown as W.ModelQualityData} />;
    default:
      return <GenericWidget widget={widget} />;
  }
}

export function WidgetGrid({ widgets, role }: { widgets: Widget[]; role: Role }) {
  return (
    <div className="grid gap-4 lg:grid-cols-12">
      {widgets.map((widget) => (
        <div key={widget.key} className={SPANS[role][widget.key] ?? "lg:col-span-6"}>
          {renderWidget(widget)}
        </div>
      ))}
    </div>
  );
}
