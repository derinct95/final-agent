from typing import Literal, Optional

from pydantic import BaseModel

RiskLevel = Literal["low", "medium", "high", "critical"]
Trend = Literal["up", "down", "flat"]
ActionPriority = Literal["low", "medium", "high"]
ActionStatus = Literal["open", "in_progress", "resolved"]
ActionCategory = Literal["coding", "denials", "documentation", "compliance", "collections"]
InsightSeverity = Literal["critical", "high", "medium", "info"]
InsightSource = Literal["ai", "rule"]
Granularity = Literal["week", "month", "quarter", "year"]
PracticeType = Literal["medical", "dental"]


class Metrics(BaseModel):
    cleanClaimRate: float
    denialRate: float
    daysInAR: float
    firstPassResolutionRate: float
    codingAccuracy: float
    priorAuthApprovalRate: float
    netCollectionRate: float
    avgReimbursementPerClaim: float
    claimsVolumeMonthly: float
    documentationAccuracy: float
    patientSatisfactionScore: float
    clinicalQualityScore: float
    patientVisitsMonthly: float
    patientPortalAdoptionRate: float


class DenialReasonBreakdown(BaseModel):
    reason: str
    count: int


class ClaimsHistoryPoint(BaseModel):
    month: str
    claimsSubmitted: int
    claimsPaid: int
    claimsDenied: int
    claimsPending: int
    revenueCollected: float
    denialReasons: list[DenialReasonBreakdown]


class Action(BaseModel):
    id: str
    title: str
    description: str
    priority: ActionPriority
    status: ActionStatus
    category: ActionCategory
    source: Literal["ai", "manual"]
    createdAt: str
    isRecurring: bool = False
    consecutiveQuarters: int = 0


class QuarterlySnapshot(BaseModel):
    quarter: str
    performanceScore: float
    riskLevel: RiskLevel
    trend: Trend
    metrics: Metrics
    peerAverageMetrics: Metrics


class MetricSnapshot(BaseModel):
    period: str
    label: str
    performanceScore: float
    riskLevel: RiskLevel
    trend: Trend
    metrics: Metrics
    peerAverageMetrics: Metrics


class ClaimsStatusSummary(BaseModel):
    paid: int = 0
    denied: int = 0
    pending: int = 0
    resubmitted: int = 0
    total: int = 0


class Provider(BaseModel):
    id: str
    name: str
    specialty: str
    facility: str
    npi: str
    email: str = ""
    practiceType: PracticeType = "medical"
    performanceScore: float
    riskLevel: RiskLevel
    trend: Trend
    scoreHistory: list[float]
    flagged: bool
    flagReason: Optional[str] = None
    reviewed: bool
    stuckAtRiskQuarters: int = 0
    metrics: Metrics
    peerAverageMetrics: Metrics
    claimsHistory: list[ClaimsHistoryPoint]
    actions: list[Action]
    quarterlyHistory: list[QuarterlySnapshot] = []


class ProviderSummary(BaseModel):
    id: str
    name: str
    specialty: str
    facility: str
    email: str = ""
    practiceType: PracticeType = "medical"
    performanceScore: float
    riskLevel: RiskLevel
    trend: Trend
    scoreHistory: list[float]
    flagged: bool
    flagReason: Optional[str] = None
    reviewed: bool
    stuckAtRiskQuarters: int = 0
    denialRate: float
    netCollectionRate: float
    pendingActionsCount: int = 0


class ClaimStatusEvent(BaseModel):
    status: str
    eventDate: str
    note: Optional[str] = None


class ClaimSummary(BaseModel):
    id: str
    providerId: str
    claimDate: str
    quarter: str
    payer: str
    amountBilled: float
    amountPaid: float
    status: str
    denialReason: Optional[str] = None


class ClaimDetail(ClaimSummary):
    statusHistory: list[ClaimStatusEvent]
    isRecurringDenial: bool = False
    relatedActionIds: list[str] = []
    procedureCode: str = ""
    procedureDescription: str = ""
    isCleanClaim: bool = False
    daysToResolution: Optional[int] = None


class ClaimsPage(BaseModel):
    claims: list[ClaimSummary]
    total: int
    page: int
    pageSize: int


class DemoAccount(BaseModel):
    id: str
    email: str
    displayName: str
    role: str
    description: str


class ChatMessageIn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessageIn]


class ToolCallLog(BaseModel):
    tool: str
    input: dict
    summary: str


class ChatResponse(BaseModel):
    reply: str
    toolCalls: list[ToolCallLog] = []
    model: str
    available: bool = True


class PracticeReviewFinding(BaseModel):
    title: str
    narrative: str
    severity: InsightSeverity = "info"


class PracticeReviewAction(BaseModel):
    title: str
    description: str
    priority: ActionPriority = "medium"


class PracticeReviewReport(BaseModel):
    period: Literal["weekly", "monthly", "quarterly"]
    periodLabel: str
    generatedAt: str
    keyFindings: list[PracticeReviewFinding]
    priorityActions: list[PracticeReviewAction]
    generatedBy: InsightSource


DetectedFormat = Literal["fhir", "hl7", "csv"]


class ImportWarning(BaseModel):
    row: Optional[int] = None
    field: Optional[str] = None
    message: str


class ImportPreviewRow(BaseModel):
    name: Optional[str] = None
    specialty: Optional[str] = None
    facility: Optional[str] = None
    npi: Optional[str] = None
    performanceScore: Optional[float] = None


class ImportPreviewResult(BaseModel):
    detectedFormat: DetectedFormat
    importToken: str
    rows: list[ImportPreviewRow]
    warnings: list[ImportWarning]


class ImportCommitRequest(BaseModel):
    importToken: str


class DashboardSummary(BaseModel):
    totalProviders: int
    averageScore: float
    criticalHighRiskCount: int
    flaggedCount: int
    topPerformerId: str
    topPerformerName: str
    topPerformerScore: float


class Insight(BaseModel):
    id: str
    providerId: Optional[str] = None
    providerName: Optional[str] = None
    severity: InsightSeverity
    title: str
    narrative: str
    recommendedAction: str
    confidenceScore: float
    estimatedFinancialImpact: Optional[float] = None
    generatedBy: InsightSource


class RootCauseAnalysis(BaseModel):
    providerId: str
    narrative: str
    contributingFactors: list[str]
    citedPolicies: list[str]
    recommendedRemediation: list[str]
    generatedBy: InsightSource


class LoginRequest(BaseModel):
    email: str
    password: str
    name: str | None = None


class LoginResponse(BaseModel):
    token: str
    name: str
    email: str


class FlagUpdateRequest(BaseModel):
    flagged: Optional[bool] = None
    reviewed: Optional[bool] = None


class ActionUpdateRequest(BaseModel):
    status: ActionStatus


class EmailDraftRequest(BaseModel):
    providerIds: list[str]
    topic: str


class EmailDraftResponse(BaseModel):
    subject: str
    body: str
    generatedBy: InsightSource


class EmailSendRequest(BaseModel):
    providerIds: list[str]
    subject: str
    body: str
    relatedAppointmentId: Optional[str] = None


class EmailMessage(BaseModel):
    id: str
    providerIds: list[str]
    recipients: list[str]
    subject: str
    body: str
    relatedAppointmentId: Optional[str] = None
    sentAt: str


class AppointmentCreateRequest(BaseModel):
    providerIds: list[str]
    topic: str
    agenda: str = ""
    scheduledAt: str
    sendConfirmationEmail: bool = True


class Appointment(BaseModel):
    id: str
    providerIds: list[str]
    providerNames: list[str] = []
    topic: str
    agenda: str
    scheduledAt: str
    status: str
    createdAt: str


class AgendaSuggestRequest(BaseModel):
    providerIds: list[str]
    topic: str
