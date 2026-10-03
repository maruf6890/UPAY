/** The shape of `widget.data` for each dashboard widget. The backend decides which widgets each role gets. */

export type LiquidityOverviewData = {
  agentsInScope: number;
  counts: { HIGH: number; MEDIUM: number; LOW: number };
  totalCashToDeliverBdt: number;
  totalFloatToTransferBdt: number;
};

export type RiskiestAgentsData = {
  rows: {
    agentCode: string;
    district: string;
    riskLevel: string;
    riskSide: string;
    stockoutProbability: number;
    expectedStockoutTime: string | null;
    cashTopupBdt: number;
    floatTopupBdt: number;
  }[];
};

export type DeliveryRouteData = {
  stops: number;
  totalKm: number;
  cashToCarryBdt: number;
  digitalTransfers: number;
  nextStops: { stop: number; agentCode: string; cashToDeliverBdt: number; etaMin: number }[];
};

/** The alerts widget has two shapes: managers get a short list (top), analysts a table (rows). */
export type AlertsWidgetData = {
  count: number;
  top?: { alertId: string; agentCode: string; severity: string }[];
  rows?: { alertId: string; agentCode: string; district: string; severity: string; signals: string[] }[];
};

export type RetentionData = {
  high: number;
  medium: number;
  rows: { agentCode: string; district: string; churnProbability: number; riskLevel: string; topReason: string }[];
};

export type PerformanceWidgetData = {
  segments: Record<string, number>;
  clusters: Record<string, number>;
  lostVolume4wAtServiceGapAgentsBdt: number;
};

export type CoverageGapsData = {
  hexagonsByGapType: Record<string, number>;
  rows: { area: string; gapType: string; opportunityBdtPerMonth: number; recommendation: string }[];
  note: string;
};

export type MyStatusData = {
  agentCode: string;
  cashBalanceBdt: number;
  eFloatBalanceBdt: number;
  riskLevel: string;
  riskSide: string;
  stockoutProbability: number;
  expectedStockoutTime: string | null;
  cashTopupBdt: number;
  floatTopupBdt: number;
  adviceEn: string;
  adviceBn: string;
};

export type NextHoursData = {
  points: { time: string; cashTypical: number; cashBadDay: number; floatTypical: number; floatBadDay: number }[];
};

export type WhyData = { reasons: { textEn: string; textBn: string }[] };

export type RecentActivityData = { rows: { day: string; cashOutBdt: number; cashInBdt: number; stockoutHours: number }[] };

export type MyPerformanceData = { segment: string; performanceScore: number; volumePercentileAmongSimilarAgents: number };

export type ReviewActivityData = {
  totals: { confirmed: number; dismissed: number };
  recent: { alertId: string; status: string; reviewer: string; reviewedAt: string }[];
};

export type ModelQualityData = {
  forecastErrorReductionVsBaselinePct: number | null;
  dailyErrorReductionVsBaselinePct: number | null;
  p90CashCoverage: number | null;
  p90FloatCoverage: number | null;
  stockoutHoursReductionVsHabitualPct: number | null;
  anomalyAuc: number | null;
  anomalyPrecision: number | null;
  anomalyRecall: number | null;
  churnAuc?: number | null;
  note: string;
};
