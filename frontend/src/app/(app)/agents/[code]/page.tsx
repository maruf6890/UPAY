import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { ArrowLeft, Lightbulb } from "lucide-react";
import { AnomalyChart } from "@/components/charts/anomaly-chart";
import { BalanceChart, type BalancePoint } from "@/components/charts/balance-chart";
import { FlowChart } from "@/components/charts/flow-chart";
import { WidgetCard } from "@/components/dashboard/widget-card";
import { Bilingual } from "@/components/shared/bilingual";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { LevelBadge } from "@/components/shared/level-badge";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { safe } from "@/lib/api/safe";
import { getCurrentUser } from "@/lib/auth";
import { formatBdt, formatBdtFull, formatDateTime, formatPercent, formatTime, humanize } from "@/lib/format";
import { getAsOf } from "@/lib/session";
import { getMeta } from "@/services/dashboard";
import { getAgentAnomaly, getAgentForecast } from "@/services/liquidity";
import { Banknote, Percent, Wallet, Zap } from "lucide-react";

const ADVICE_TONES = {
  HIGH: "border-danger-border bg-danger-soft",
  MEDIUM: "border-warning-border bg-warning-soft",
  LOW: "border-success-border bg-success-soft",
};

export default async function AgentPage({ params }: { params: Promise<{ code: string }> }) {
  const { code: rawCode } = await params;
  const code = rawCode.toUpperCase();

  const user = await getCurrentUser();
  if (user.role === "agent" && user.agentCode !== code) {
    redirect(`/agents/${user.agentCode}`);
  }

  const asOf = await getAsOf();
  const [forecast, anomaly, meta] = await Promise.all([
    safe(() => getAgentForecast(code, asOf)),
    safe(() => getAgentAnomaly(code, 30, asOf)),
    safe(() => getMeta()),
  ]);

  if (forecast.status === 404) {
    notFound();
  }
  if (!forecast.data) {
    return (
      <>
        <PageHeader title={code} />
        <ErrorState message={forecast.error ?? "Could not load this agent."} status={forecast.status} />
      </>
    );
  }

  const data = forecast.data;
  const risk = data.risk;
  const topUp = risk.side === "cash" ? data.recommendation.cashTopupBdt : data.recommendation.floatTopupBdt;
  const showTopUp = risk.level !== "LOW" && topUp > 0;

  const balancePoints: BalancePoint[] = data.hourly.map((hour) => ({
    time: hour.timestamp,
    cashTypical: hour.cashBalanceP50,
    cashBadDay: hour.cashBalanceP90Worst,
    floatTypical: hour.floatBalanceP50,
    floatBadDay: hour.floatBalanceP90Worst,
  }));

  const comparison = data.baselineComparison;
  const aiPlan = risk.side === "cash" ? data.recommendation.cashTopupBdt : data.recommendation.floatTopupBdt;
  const basePlan = risk.side === "cash" ? comparison.baselineCashTopupBdt : comparison.baselineFloatTopupBdt;
  const actualPeak = risk.side === "cash" ? comparison.actualPeakCashDrain : comparison.actualPeakFloatDrain;
  const balanceNow = risk.side === "cash" ? data.currentBalances.cash : data.currentBalances.eFloat;
  const comparisonRows = [
    { label: "This forecast's plan", covers: balanceNow + aiPlan, tone: "bg-info" },
    { label: "7-day average rule", covers: balanceNow + basePlan, tone: "bg-text-color-subtle" },
  ];
  const scale = Math.max(...comparisonRows.map((row) => row.covers), actualPeak ?? 0, 1);

  const thresholds = meta.data?.calibration?.thresholdsAnomaly;

  return (
    <>
      {user.role !== "agent" ? (
        <Button asChild variant="ghost" size="sm" className="mb-3 -ml-2">
          <Link href="/risk" prefetch={false}>
            <ArrowLeft /> Back to risk list
          </Link>
        </Button>
      ) : null}

      <PageHeader
        title={data.agent.agentCode}
        description={`${data.agent.district}, ${data.agent.division}. Forecast for the 24 hours from ${formatDateTime(data.asOf)}.`}
        actions={
          <>
            <Badge variant="outline">{humanize(data.agent.archetype)}</Badge>
            <Badge variant="outline">{humanize(data.agent.areaType)}</Badge>
            <LevelBadge level={risk.level} />
          </>
        }
      />

      <div className={`mb-4 rounded-xl border px-5 py-4 ${ADVICE_TONES[risk.level]}`}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="max-w-3xl text-base font-medium">
            <Bilingual en={data.recommendation.advice.en} bn={data.recommendation.advice.bn} className="bn" />
          </p>
          {showTopUp ? (
            <div className="text-right">
              <div className="text-xs text-ink-secondary">Suggested top-up ({risk.side === "cash" ? "cash" : "e-float"})</div>
              <div className="text-2xl font-semibold tabular-nums">{formatBdtFull(topUp)}</div>
            </div>
          ) : null}
        </div>
      </div>

      <div className="mb-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Cash in the drawer" value={formatBdtFull(data.currentBalances.cash)} icon={Banknote} tone="default" />
        <StatCard label="E-float balance" value={formatBdtFull(data.currentBalances.eFloat)} icon={Wallet} tone="info" />
        <StatCard label="Chance of running out" value={formatPercent(risk.stockoutProbability)} hint="a ranking aid, tends to read low" icon={Percent} tone={risk.level === "HIGH" ? "danger" : risk.level === "MEDIUM" ? "warning" : "success"} />
        <StatCard label="Expected to run out" value={risk.expectedStockoutTime ? formatTime(risk.expectedStockoutTime) : "Not expected"} hint={risk.possibleStockoutTimeP90 ? `bad day: ${formatTime(risk.possibleStockoutTimeP90)}` : "bad day: not expected"} icon={Zap} tone="warning" />
      </div>

      <div className="grid gap-4 lg:grid-cols-12">
        <div className="lg:col-span-8">
          <WidgetCard title="Projected balance" description="Typical day and a bad day (1 in 10). Below the red line you run out.">
            <BalanceChart points={balancePoints} initialSide={risk.side} />
          </WidgetCard>
        </div>
        <div className="lg:col-span-4">
          <WidgetCard title="Why this forecast" description="Biggest reasons for the expected cash drain">
            {data.drivers.length === 0 ? (
              <EmptyState title="No reasons to show" />
            ) : (
              <ul className="space-y-3.5">
                {data.drivers.map((driver) => (
                  <li key={driver.theme} className="flex gap-3 text-sm">
                    <span className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full bg-brand-soft">
                      <Lightbulb className="size-3.5 text-[#8a6a00]" />
                    </span>
                    <Bilingual en={driver.textEn} bn={driver.textBn} className="text-ink-secondary" />
                  </li>
                ))}
              </ul>
            )}
          </WidgetCard>
        </div>

        <div className="lg:col-span-8">
          <WidgetCard title="Hourly net cash out" description="Cash paid out minus cash received, each hour">
            <FlowChart hourly={data.hourly} />
          </WidgetCard>
        </div>
        <div className="lg:col-span-4">
          <WidgetCard title="Does the model beat a simple rule?" description={`Cash plan vs what really happened (${risk.side})`}>
            <div className="space-y-4">
              {comparisonRows.map((row) => (
                <div key={row.label}>
                  <div className="mb-1 flex justify-between text-xs">
                    <span className="text-ink-secondary">{row.label}</span>
                    <span className="font-medium tabular-nums">{formatBdt(row.covers)}</span>
                  </div>
                  <Progress value={(row.covers / scale) * 100} barClassName={row.tone} />
                </div>
              ))}
              {actualPeak !== null ? (
                <div>
                  <div className="mb-1 flex justify-between text-xs">
                    <span className="text-ink-secondary">What the day really needed</span>
                    <span className="font-medium tabular-nums">{formatBdt(actualPeak + data.reserveBdt)}</span>
                  </div>
                  <Progress value={((actualPeak + data.reserveBdt) / scale) * 100} barClassName="bg-success" />
                </div>
              ) : null}
              <p className="text-xs text-muted-foreground">Bars show the {risk.side} the agent would hold after following each plan. The best plan is the one closest to, and not below, the green bar.</p>
            </div>
          </WidgetCard>
        </div>

        <div className="lg:col-span-12">
          <WidgetCard title="Unusual behaviour score" description="How different the agent looked from their own history and from similar agents, last 30 days">
            {anomaly.data && anomaly.data.length > 0 ? (
              <AnomalyChart points={anomaly.data} medium={thresholds?.medium ?? 0.47} high={thresholds?.high ?? 0.494} />
            ) : (
              <EmptyState title="No score history" description={anomaly.error ?? "There are no scores for this period."} />
            )}
          </WidgetCard>
        </div>
      </div>
    </>
  );
}
