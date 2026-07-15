import type {
  Appointment,
  ChatMessage,
  ChatResponse,
  ClaimDetail,
  ClaimsPage,
  ClaimsStatusSummary,
  DashboardSummary,
  DemoAccount,
  EmailDraftResponse,
  EmailMessageRecord,
  Granularity,
  ImportPreviewResult,
  Insight,
  MetricSnapshot,
  PracticeReviewReport,
  PracticeType,
  Provider,
  ProviderSummary,
  QuarterlySnapshot,
  ReviewPeriod,
  RootCauseAnalysis,
} from "../types";
import { downloadResponse } from "../utils/download";

const SESSION_STORAGE_KEY = "ppd_session";

function getIdentityHeaders(): Record<string, string> {
  try {
    const raw = localStorage.getItem(SESSION_STORAGE_KEY);
    if (!raw) return {};
    const session = JSON.parse(raw) as { role?: string; email?: string };
    return {
      ...(session.role ? { "X-User-Role": session.role } : {}),
      ...(session.email ? { "X-User-Email": session.email } : {}),
    };
  } catch {
    return {};
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...getIdentityHeaders(), ...(init?.headers || {}) },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  login: (email: string, password: string, name?: string) =>
    request<{ token: string; name: string; email: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password, name }),
    }),

  getDemoAccounts: () => request<DemoAccount[]>("/auth/demo-accounts"),

  listProviders: (practiceType?: PracticeType) =>
    request<ProviderSummary[]>(`/providers${practiceType ? `?practiceType=${practiceType}` : ""}`),

  getSummary: (practiceType?: PracticeType) =>
    request<DashboardSummary>(`/providers/summary${practiceType ? `?practiceType=${practiceType}` : ""}`),

  getProvider: (id: string) => request<Provider>(`/providers/${id}`),

  getProviderQuarterlyHistory: (id: string) => request<QuarterlySnapshot[]>(`/providers/${id}/quarterly-history`),

  getProviderMetricHistory: (id: string, granularity: Granularity) =>
    request<MetricSnapshot[]>(`/providers/${id}/metric-history?granularity=${granularity}`),

  getProviderClaims: (id: string, page = 1, pageSize = 20, status?: string, quarter?: string) => {
    const params = new URLSearchParams({ page: String(page), pageSize: String(pageSize) });
    if (status) params.set("status", status);
    if (quarter) params.set("quarter", quarter);
    return request<ClaimsPage>(`/providers/${id}/claims?${params.toString()}`);
  },

  getClaimsStatusSummary: (id: string) => request<ClaimsStatusSummary>(`/providers/${id}/claims/summary`),

  getClaimDetail: (providerId: string, claimId: string) =>
    request<ClaimDetail>(`/providers/${providerId}/claims/${claimId}`),

  getRootCause: (providerId: string) =>
    request<RootCauseAnalysis>(`/providers/${providerId}/root-cause`, { method: "POST" }),

  setFlag: (id: string, payload: { flagged?: boolean; reviewed?: boolean }) =>
    request<Provider>(`/providers/${id}/flag`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  setActionStatus: (providerId: string, actionId: string, status: string) =>
    request<Provider>(`/providers/${providerId}/actions/${actionId}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),

  getInsights: (refresh = false, practiceType?: PracticeType) => {
    const params = new URLSearchParams();
    if (refresh) params.set("refresh", "true");
    if (practiceType) params.set("practiceType", practiceType);
    const qs = params.toString();
    return request<Insight[]>(`/insights${qs ? `?${qs}` : ""}`);
  },

  exportUrl: (scope: "all" | "flagged" = "all") => `/api/providers/export?scope=${scope}`,

  chat: (messages: ChatMessage[]) =>
    request<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({ messages: messages.map((m) => ({ role: m.role, content: m.content })) }),
    }),

  generatePracticeReview: (period: ReviewPeriod) =>
    request<PracticeReviewReport>(`/reports/practice-review?period=${period}`),

  downloadPracticeReviewReport: async (period: ReviewPeriod, format: "pdf" | "csv" = "pdf") => {
    const res = await fetch(`/api/reports/practice-review/download?period=${period}&format=${format}`);
    await downloadResponse(res, `clearview-practice-review-${period}.${format}`);
  },

  downloadProviderReport: async (
    providerId: string, granularity: Granularity = "quarter",
    periodStart?: string, periodEnd?: string, format: "pdf" | "csv" = "pdf",
  ) => {
    const params = new URLSearchParams({ format, granularity });
    if (periodStart) params.set("periodStart", periodStart);
    if (periodEnd) params.set("periodEnd", periodEnd);
    const res = await fetch(`/api/reports/providers/${providerId}/report?${params.toString()}`);
    await downloadResponse(res, `clearview-${providerId}-report.${format}`);
  },

  downloadCompareReport: async (providerIds: string[], format: "pdf" | "csv" = "pdf") => {
    const params = new URLSearchParams({ format, providerIds: providerIds.join(",") });
    const res = await fetch(`/api/reports/compare?${params.toString()}`);
    await downloadResponse(res, `clearview-comparison.${format}`);
  },

  previewImport: async (file: File): Promise<ImportPreviewResult> => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch("/api/import/preview", { method: "POST", body: form });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Import preview failed: ${res.status}`);
    }
    return res.json();
  },

  commitImport: (importToken: string) =>
    request<Provider[]>("/import/commit", {
      method: "POST",
      body: JSON.stringify({ importToken }),
    }),

  draftEmail: (providerIds: string[], topic: string) =>
    request<EmailDraftResponse>("/communications/email/draft", {
      method: "POST",
      body: JSON.stringify({ providerIds, topic }),
    }),

  sendEmail: (providerIds: string[], subject: string, body: string, relatedAppointmentId?: string) =>
    request<EmailMessageRecord>("/communications/email/send", {
      method: "POST",
      body: JSON.stringify({ providerIds, subject, body, relatedAppointmentId }),
    }),

  listEmails: (providerId?: string) =>
    request<EmailMessageRecord[]>(`/communications/emails${providerId ? `?providerId=${providerId}` : ""}`),

  createAppointment: (providerIds: string[], topic: string, agenda: string, scheduledAt: string) =>
    request<Appointment>("/appointments", {
      method: "POST",
      body: JSON.stringify({ providerIds, topic, agenda, scheduledAt, sendConfirmationEmail: true }),
    }),

  listAppointments: (providerId?: string) =>
    request<Appointment[]>(`/appointments${providerId ? `?providerId=${providerId}` : ""}`),

  suggestAgenda: (providerIds: string[], topic: string) =>
    request<EmailDraftResponse>("/communications/agenda/suggest", {
      method: "POST",
      body: JSON.stringify({ providerIds, topic }),
    }),
};
