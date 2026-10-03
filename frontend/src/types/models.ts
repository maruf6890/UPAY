/** Types for the data the backend sends (after the keys were converted to camelCase). */

export type Role = "manager" | "agent" | "analyst";
export type RiskLevel = "HIGH" | "MEDIUM" | "LOW";

export type CurrentUser = {
  id: number;
  username: string;
  fullName: string;
  role: Role;
  district: string | null;
  agentCode: string | null;
};

export type TokenResponse = {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  expiresIn: number;
  user: CurrentUser;
};

export type Meta = {
  defaultAsOf: string;
  dataStart: string;
  dataEnd: string;
  nAgents: number;
  districts: string[];
  calibration?: { thresholdsAnomaly?: { medium: number; high: number } };
};

/* ───────────── dashboard ───────────── */
export type WidgetType = "stats" | "table" | "list" | "route" | "chart";
export type Widget = { key: string; title: string; type: WidgetType; data: Record<string, unknown> };
export type Dashboard = {
  user: { username: string; fullName: string; role: Role; district: string | null; agentCode: string | null };
  scope: string;
  asOf: string;
  widgets: Widget[];
  warnings: string[];
};

/* ───────────── liquidity ───────────── */
export type RiskAgent = {
  agentCode: string;
  district: string;
  division: string;
  archetype: string;
  areaType: string;
  lat: number;
  lon: number;
  cashBalance: number;
  floatBalance: number;
  riskSide: "cash" | "float";
  stockoutProbability: number;
  riskLevel: RiskLevel;
  cashTopupBdt: number;
  floatTopupBdt: number;
  expectedStockoutTime: string | null;
  possibleStockoutTimeP90: string | null;
  baselineCashTopupBdt: number;
  baselineFloatTopupBdt: number;
};

export type RiskResponse = { asOf: string; summary: Record<RiskLevel, number>; agents: RiskAgent[] };

export type HourlyPoint = {
  timestamp: string;
  netQ10: number;
  netQ50: number;
  netQ90: number;
  baselineNetQ50: number;
  cashBalanceP50: number;
  cashBalanceP90Worst: number;
  floatBalanceP50: number;
  floatBalanceP90Worst: number;
  actualNet: number | null;
};

export type Driver = { theme: string; labelEn: string; labelBn: string; impactBdt: number; direction: string; textEn: string; textBn: string };

export type AgentForecast = {
  agent: { agentCode: string; district: string; division: string; archetype: string; areaType: string; lat: number; lon: number };
  asOf: string;
  horizonHours: number;
  reserveBdt: number;
  currentBalances: { cash: number; eFloat: number };
  risk: {
    level: RiskLevel;
    side: "cash" | "float";
    stockoutProbability: number;
    expectedStockoutTime: string | null;
    possibleStockoutTimeP90: string | null;
  };
  recommendation: {
    cashTopupBdt: number;
    floatTopupBdt: number;
    needCashP90: number;
    needFloatP90: number;
    advice: { en: string; bn: string };
  };
  baselineComparison: {
    method: string;
    baselineCashTopupBdt: number;
    baselineFloatTopupBdt: number;
    actualPeakCashDrain: number | null;
    actualPeakFloatDrain: number | null;
  };
  drivers: Driver[];
  hourly: HourlyPoint[];
  notes: string;
};

export type AnomalyPoint = { date: string; alertScore: number };

/* ───────────── route ───────────── */
export type RouteStop = {
  stop: number;
  agentCode: string;
  district: string;
  lat: number;
  lon: number;
  legKm: number;
  etaMin: number;
  cashToDeliverBdt: number;
  stockoutProb: number;
  riskLevel: RiskLevel;
  firstRiskTime: string | null;
};

export type RoutePlan = {
  asOf: string;
  district: string;
  stops: RouteStop[];
  totalKm: number;
  totalCashBdt: number;
  digitalTransfers: { agentCode: string; floatTopupBdt: number }[];
  depot: { lat: number; lon: number } | null;
  unserved: { agentCode: string; cashTopupBdt: number }[];
};

/* ───────────── alerts ───────────── */
export type AlertReason = { signal: string; label: string; detail: string; zPeer: number; zOwn: number };
export type AlertReview = { status: "pending" | "confirmed" | "dismissed"; reviewer?: string; note?: string | null; reviewedAt?: string };
export type Alert = {
  alertId: string;
  agentCode: string;
  district: string;
  archetype: string;
  date: string;
  anomalyScore: number;
  severity: "HIGH" | "MEDIUM";
  reasons: AlertReason[];
  review: AlertReview;
  nextStep: string;
};
export type AlertsResponse = { asOf: string; alerts: Alert[] };

/* ───────────── coverage ───────────── */
export type CoverageProps = {
  h3: string;
  gapType: string;
  nearestTown: string;
  demandBdt: number;
  supplyBdt: number;
  coverageRatio: number;
  untappedBdt: number;
  unservedBdt: number;
  agentsInCell: number;
  agentsNearby: number;
  agentsNeeded: number;
  opportunityCommissionBdt: number;
  recommendation: string;
};
export type CoverageFeature = { type: "Feature"; geometry: { type: "Polygon"; coordinates: number[][][] }; properties: CoverageProps };
export type CoverageGeoJson = { type: "FeatureCollection"; features: CoverageFeature[] };
export type CoverageSummary = {
  window: string;
  hexagons: number;
  hexagonsByGapType: Record<string, number>;
  estimatedDemandCoveredShare: number;
  untappedMonthlyVolumeBdt: number;
  monthlyVolumeLostToStockoutsBdt: number;
  ofWhichInCapacityGapHexagonsBdt: number;
  typicalAgentMonthlyVolumeBdt: number;
  note: string;
};
export type CoverageGap = CoverageProps & { lat: number; lon: number; opportunityBdtPerMonth: number };

/* ───────────── agent insights ───────────── */
export type PerformanceSummary = {
  weekStart: string;
  agents: number;
  segments: Record<string, number>;
  flags: Record<string, number>;
  clusters: Record<string, number>;
  lostVolume4wAtServiceGapAgentsBdt: number;
};
export type PerformanceAgent = {
  agentCode: string;
  district: string;
  archetype: string;
  performanceScore: number;
  segment: string;
  flags: string[];
  clusterName: string;
  volumePercentile: number;
  relativeGrowth: number;
  stockoutRate4w: number;
  lostVolume4wBdt: number;
  recommendedAction: string;
};
export type PerformanceList = { weekStart: string; total: number; agents: PerformanceAgent[] };

export type ChurnDriver = { feature: string; shapValue: number; value: number; textEn: string; textBn: string };
export type ChurnAgent = {
  agentCode: string;
  district: string;
  archetype: string;
  status: string;
  churnProbability: number;
  riskLevel: string;
  txnRatio4w: number;
  stockoutHours4w: number;
  drivers: ChurnDriver[];
  recommendedAction: string;
};
export type ChurnList = { weekStart: string; horizonWeeks: number; levelCounts: Record<string, number>; agents: ChurnAgent[] };

/* ───────────── copilot ───────────── */
export type CopilotPriority = { section: string; subject: string; action: string; why: string; drillDown?: string };
export type CopilotItem = { subject: string; detail: string; drillDown: string };
export type CopilotSection = { key: string; title: string; headline: string; items: CopilotItem[]; drillDownLists: string[] };
export type CopilotBrief = {
  asOf: string;
  scope: string;
  headline: string;
  summary: string;
  priorities: CopilotPriority[];
  banglaSummary: string;
  droppedUnverifiedPriorities: number;
  sections: CopilotSection[];
  warnings: string[];
  generatedBy: string;
};

/* ───────────── model quality ───────────── */
export type Metrics = {
  modelRunId?: number;
  trainedAt?: string;
  split: { trainEnd: string; valEnd: string; testStart: string };
  hourlyForecast: Record<string, number>;
  peakDrainP90: Record<string, number>;
  policySimulation: Record<string, Record<string, number | string>>;
  fairness: { areaType: Record<string, number | string>[]; division: Record<string, number | string>[] };
  anomaly: Record<string, number | Record<string, number>>;
};
