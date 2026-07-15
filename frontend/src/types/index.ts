export type RiskLevel = "low" | "medium" | "high" | "critical";
export type Trend = "up" | "down" | "flat";
export type ActionPriority = "low" | "medium" | "high";
export type ActionStatus = "open" | "in_progress" | "resolved";
export type InsightSeverity = "critical" | "high" | "medium" | "info";

export interface Metrics {
  cleanClaimRate: number;
  denialRate: number;
  daysInAR: number;
  firstPassResolutionRate: number;
  codingAccuracy: number;
  priorAuthApprovalRate: number;
  netCollectionRate: number;
  avgReimbursementPerClaim: number;
  claimsVolumeMonthly: number;
  documentationAccuracy: number;
  patientSatisfactionScore: number;
  clinicalQualityScore: number;
  patientVisitsMonthly: number;
  patientPortalAdoptionRate: number;
}

export interface DenialReasonBreakdown {
  reason: string;
  count: number;
}

export interface ClaimsHistoryPoint {
  month: string;
  claimsSubmitted: number;
  claimsPaid: number;
  claimsDenied: number;
  claimsPending: number;
  revenueCollected: number;
  denialReasons: DenialReasonBreakdown[];
}

export interface Action {
  id: string;
  title: string;
  description: string;
  priority: ActionPriority;
  status: ActionStatus;
  category: string;
  source: "ai" | "manual";
  createdAt: string;
  isRecurring: boolean;
  consecutiveQuarters: number;
}

export interface QuarterlySnapshot {
  quarter: string;
  performanceScore: number;
  riskLevel: RiskLevel;
  trend: Trend;
  metrics: Metrics;
  peerAverageMetrics: Metrics;
}

export type Granularity = "week" | "month" | "quarter" | "year";

export interface MetricSnapshot {
  period: string;
  label: string;
  performanceScore: number;
  riskLevel: RiskLevel;
  trend: Trend;
  metrics: Metrics;
  peerAverageMetrics: Metrics;
}

export interface ClaimsStatusSummary {
  paid: number;
  denied: number;
  pending: number;
  resubmitted: number;
  total: number;
}

export type PracticeType = "medical" | "dental";

export interface Provider {
  id: string;
  name: string;
  specialty: string;
  facility: string;
  npi: string;
  email: string;
  practiceType: PracticeType;
  performanceScore: number;
  riskLevel: RiskLevel;
  trend: Trend;
  scoreHistory: number[];
  flagged: boolean;
  flagReason: string | null;
  reviewed: boolean;
  stuckAtRiskQuarters: number;
  metrics: Metrics;
  peerAverageMetrics: Metrics;
  claimsHistory: ClaimsHistoryPoint[];
  actions: Action[];
  quarterlyHistory: QuarterlySnapshot[];
}

export interface ProviderSummary {
  id: string;
  name: string;
  specialty: string;
  facility: string;
  email: string;
  practiceType: PracticeType;
  performanceScore: number;
  riskLevel: RiskLevel;
  trend: Trend;
  scoreHistory: number[];
  flagged: boolean;
  flagReason: string | null;
  reviewed: boolean;
  stuckAtRiskQuarters: number;
  denialRate: number;
  netCollectionRate: number;
  pendingActionsCount: number;
}

export interface DashboardSummary {
  totalProviders: number;
  averageScore: number;
  criticalHighRiskCount: number;
  flaggedCount: number;
  topPerformerId: string;
  topPerformerName: string;
  topPerformerScore: number;
}

export interface Insight {
  id: string;
  providerId: string | null;
  providerName: string | null;
  severity: InsightSeverity;
  title: string;
  narrative: string;
  recommendedAction: string;
  confidenceScore: number;
  estimatedFinancialImpact: number | null;
  generatedBy: "ai" | "rule";
}

export interface RootCauseAnalysis {
  providerId: string;
  narrative: string;
  contributingFactors: string[];
  citedPolicies: string[];
  recommendedRemediation: string[];
  generatedBy: "ai" | "rule";
}

export interface ClaimStatusEvent {
  status: string;
  eventDate: string;
  note: string | null;
}

export interface ClaimSummary {
  id: string;
  providerId: string;
  claimDate: string;
  quarter: string;
  payer: string;
  amountBilled: number;
  amountPaid: number;
  status: string;
  denialReason: string | null;
}

export interface ClaimDetail extends ClaimSummary {
  statusHistory: ClaimStatusEvent[];
  isRecurringDenial: boolean;
  relatedActionIds: string[];
  procedureCode: string;
  procedureDescription: string;
  isCleanClaim: boolean;
  daysToResolution: number | null;
}

export interface ClaimsPage {
  claims: ClaimSummary[];
  total: number;
  page: number;
  pageSize: number;
}

export interface DemoAccount {
  id: string;
  email: string;
  displayName: string;
  role: string;
  description: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  toolsUsed?: string[];
}

export interface ToolCallLog {
  tool: string;
  input: Record<string, unknown>;
  summary: string;
}

export interface ChatResponse {
  reply: string;
  toolCalls: ToolCallLog[];
  model: string;
  available: boolean;
}

export interface PracticeReviewFinding {
  title: string;
  narrative: string;
  severity: InsightSeverity;
}

export interface PracticeReviewAction {
  title: string;
  description: string;
  priority: ActionPriority;
}

export type ReviewPeriod = "weekly" | "monthly" | "quarterly";

export interface PracticeReviewReport {
  period: ReviewPeriod;
  periodLabel: string;
  generatedAt: string;
  keyFindings: PracticeReviewFinding[];
  priorityActions: PracticeReviewAction[];
  generatedBy: "ai" | "rule";
}

export type DetectedFormat = "fhir" | "hl7" | "csv";

export interface ImportWarning {
  row?: number;
  field?: string;
  message: string;
}

export interface ImportPreviewRow {
  name: string | null;
  specialty: string | null;
  facility: string | null;
  npi: string | null;
  performanceScore: number | null;
}

export interface ImportPreviewResult {
  detectedFormat: DetectedFormat;
  importToken: string;
  rows: ImportPreviewRow[];
  warnings: ImportWarning[];
}

export interface EmailDraftResponse {
  subject: string;
  body: string;
  generatedBy: "ai" | "rule";
}

export interface EmailMessageRecord {
  id: string;
  providerIds: string[];
  recipients: string[];
  subject: string;
  body: string;
  relatedAppointmentId: string | null;
  sentAt: string;
}

export interface Appointment {
  id: string;
  providerIds: string[];
  providerNames: string[];
  topic: string;
  agenda: string;
  scheduledAt: string;
  status: string;
  createdAt: string;
}
