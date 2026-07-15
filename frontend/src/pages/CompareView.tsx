import { AlertCircle, CalendarPlus, Download, Mail } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import MetricsRadar from "../components/charts/MetricsRadar";
import ScoreGauge from "../components/charts/ScoreGauge";
import { CATEGORICAL } from "../components/charts/theme";
import { RiskBadge, TrendBadge } from "../components/common/Badge";
import SlidePanel from "../components/common/SlidePanel";
import StuckRiskBadge from "../components/common/StuckRiskBadge";
import Value from "../components/common/Value";
import AppointmentBookingModal from "../components/communications/AppointmentBookingModal";
import EmailComposeModal from "../components/communications/EmailComposeModal";
import { ADMIN_ROLE, useAuth } from "../context/AuthContext";
import type { Provider } from "../types";

const METRIC_ROWS: { key: keyof Provider["metrics"]; label: string; type: "percent" | "number" | "currency" }[] = [
  { key: "cleanClaimRate", label: "Clean Claim Rate", type: "percent" },
  { key: "denialRate", label: "Denial Rate", type: "percent" },
  { key: "daysInAR", label: "Days in AR", type: "number" },
  { key: "firstPassResolutionRate", label: "First-Pass Resolution", type: "percent" },
  { key: "codingAccuracy", label: "Coding Accuracy", type: "percent" },
  { key: "priorAuthApprovalRate", label: "Prior-Auth Approval", type: "percent" },
  { key: "netCollectionRate", label: "Net Collection Rate", type: "percent" },
  { key: "avgReimbursementPerClaim", label: "Avg Reimbursement / Claim", type: "currency" },
  { key: "documentationAccuracy", label: "Documentation Accuracy", type: "percent" },
  { key: "patientSatisfactionScore", label: "Patient Satisfaction", type: "percent" },
  { key: "clinicalQualityScore", label: "Clinical Quality Score", type: "percent" },
  { key: "patientVisitsMonthly", label: "Patient Visits / Month", type: "number" },
  { key: "patientPortalAdoptionRate", label: "Patient Portal Adoption", type: "percent" },
];

export default function CompareView() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const ids = (searchParams.get("ids") || "").split(",").filter(Boolean);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [emailOpen, setEmailOpen] = useState(false);
  const [bookingOpen, setBookingOpen] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const { session } = useAuth();
  const isAdmin = session?.role === ADMIN_ROLE;

  useEffect(() => {
    setLoading(true);
    Promise.all(ids.map((id) => api.getProvider(id).catch(() => null)))
      .then((results) => setProviders(results.filter((p): p is Provider => p !== null)))
      .finally(() => setLoading(false));
  }, [ids.join(",")]);

  function close() {
    navigate("/dashboard");
  }

  async function handleDownload() {
    setDownloading(true);
    setDownloadError(null);
    try {
      await api.downloadCompareReport(providers.map((p) => p.id));
    } catch (err) {
      setDownloadError(err instanceof Error ? err.message : "Download failed. Please try again.");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <SlidePanel
      onClose={close}
      resizable={false}
      startMaximized
      title={<h2 className="text-sm font-semibold text-ink-primary">Compare Providers</h2>}
      headerActions={
        providers.length > 0 && (
          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={() => setEmailOpen(true)}
              disabled={!isAdmin}
              title={isAdmin ? undefined : "Requires Practice Administrator access"}
              className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg border border-line-axis text-ink-secondary hover:bg-plane transition disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-transparent"
            >
              <Mail className="w-3.5 h-3.5" /> Email Group
            </button>
            <button
              type="button"
              onClick={() => setBookingOpen(true)}
              disabled={!isAdmin}
              title={isAdmin ? undefined : "Requires Practice Administrator access"}
              className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg border border-line-axis text-ink-secondary hover:bg-plane transition disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-transparent"
            >
              <CalendarPlus className="w-3.5 h-3.5" /> Schedule Group Meeting
            </button>
            <button
              type="button"
              onClick={handleDownload}
              disabled={downloading}
              className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg border border-line-axis text-ink-secondary hover:bg-plane transition disabled:opacity-50"
            >
              <Download className="w-3.5 h-3.5" /> {downloading ? "Preparing..." : "Download Comparison"}
            </button>
          </div>
        )
      }
    >
      <div className="p-6">
        {downloadError && (
          <div className="flex items-center gap-2 text-sm text-risk-critical bg-risk-critical/10 rounded-lg px-3 py-2 mb-4">
            <AlertCircle className="w-4 h-4 shrink-0" /> {downloadError}
          </div>
        )}
        {loading && <p className="text-sm text-ink-muted">Loading comparison...</p>}
        {!loading && providers.length === 0 && <p className="text-sm text-ink-muted">No providers to compare.</p>}

        {!loading && providers.length > 0 && (
          <div className="space-y-6">
            <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${providers.length}, minmax(0, 1fr))` }}>
              {providers.map((p, i) => (
                <div key={p.id} className="bg-surface border border-ink-primary/10 rounded-2xl p-4 flex flex-col items-center text-center gap-2">
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: CATEGORICAL[i] }} />
                  <p className="text-sm font-medium text-ink-primary">{p.name}</p>
                  <p className="text-xs text-ink-muted">{p.specialty} · {p.facility}</p>
                  <ScoreGauge score={p.performanceScore} riskLevel={p.riskLevel} size={100} />
                  <div className="flex flex-wrap items-center justify-center gap-1.5">
                    <RiskBadge level={p.riskLevel} />
                    <TrendBadge trend={p.trend} />
                  </div>
                  <StuckRiskBadge quarters={p.stuckAtRiskQuarters} />
                </div>
              ))}
            </div>

            <div className="bg-surface border border-ink-primary/10 rounded-2xl p-5">
              <h3 className="text-sm font-semibold text-ink-primary mb-3">Metrics Comparison</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-line-grid text-left">
                      <th className="py-2 pr-4 text-xs font-medium text-ink-muted uppercase">Metric</th>
                      {providers.map((p) => (
                        <th key={p.id} className="py-2 pr-4 text-xs font-medium text-ink-muted uppercase">{p.name.replace("Dr. ", "")}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {METRIC_ROWS.map((row) => (
                      <tr key={row.key} className="border-b border-line-grid last:border-0">
                        <td className="py-2 pr-4 text-ink-secondary">{row.label}</td>
                        {providers.map((p) => (
                          <td key={p.id} className="py-2 pr-4 font-medium">
                            <Value value={p.metrics[row.key]} type={row.type} decimals={row.type === "currency" ? 0 : 1} />
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="bg-surface border border-ink-primary/10 rounded-2xl p-5">
              <h3 className="text-sm font-semibold text-ink-primary mb-3">Radar Overlay</h3>
              <MetricsRadar
                series={providers.map((p, i) => ({ name: p.name.replace("Dr. ", ""), metrics: p.metrics, color: CATEGORICAL[i] }))}
              />
            </div>
          </div>
        )}

        <EmailComposeModal
          open={emailOpen}
          onClose={() => setEmailOpen(false)}
          providerIds={providers.map((p) => p.id)}
          providerNames={providers.map((p) => p.name)}
          defaultTopic="Group performance discussion"
        />
        <AppointmentBookingModal
          open={bookingOpen}
          onClose={() => setBookingOpen(false)}
          providerIds={providers.map((p) => p.id)}
          providerNames={providers.map((p) => p.name)}
          defaultTopic="Group performance review"
        />
      </div>
    </SlidePanel>
  );
}
