import { AlertCircle, CalendarPlus, Download, Mail, RefreshCw, Search } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { RiskBadge, TrendBadge } from "../components/common/Badge";
import { ADMIN_ROLE, useAuth } from "../context/AuthContext";
import SlidePanel from "../components/common/SlidePanel";
import StuckRiskBadge from "../components/common/StuckRiskBadge";
import AppointmentBookingModal from "../components/communications/AppointmentBookingModal";
import EmailComposeModal from "../components/communications/EmailComposeModal";
import ActionsTab from "../components/provider-detail/tabs/ActionsTab";
import ClaimsHistoryTab from "../components/provider-detail/tabs/ClaimsHistoryTab";
import MetricsTab from "../components/provider-detail/tabs/MetricsTab";
import OverviewTab from "../components/provider-detail/tabs/OverviewTab";
import RootCauseModal from "../components/provider-detail/RootCauseModal";
import { selectPeriods, type PeriodSelection } from "../components/provider-detail/PeriodPicker";
import { notifyProviderDataChanged } from "../utils/events";
import { addRecentlyViewed } from "../utils/recentlyViewed";
import type { ActionStatus, Granularity, Insight, MetricSnapshot, Provider, QuarterlySnapshot } from "../types";

type TabKey = "overview" | "metrics" | "claims" | "actions";

const TABS: { key: TabKey; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "metrics", label: "Metrics" },
  { key: "claims", label: "Claims History" },
  { key: "actions", label: "Actions" },
];

export default function ProviderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const { session } = useAuth();
  const isAdmin = session?.role === ADMIN_ROLE;

  const [provider, setProvider] = useState<Provider | null>(null);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [quarterlyHistory, setQuarterlyHistory] = useState<QuarterlySnapshot[]>([]);
  const [granularity, setGranularity] = useState<Granularity>("quarter");
  const [metricHistory, setMetricHistory] = useState<MetricSnapshot[]>([]);
  const [period, setPeriod] = useState<PeriodSelection>({ mode: "all" });
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [downloadMenuOpen, setDownloadMenuOpen] = useState(false);
  const [downloadMenuPos, setDownloadMenuPos] = useState<{ top: number; right: number } | null>(null);
  const downloadBtnRef = useRef<HTMLButtonElement>(null);
  const [emailOpen, setEmailOpen] = useState(false);
  const [bookingOpen, setBookingOpen] = useState(false);
  const [rootCauseOpen, setRootCauseOpen] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const tab = (searchParams.get("tab") as TabKey) || "overview";

  function loadProvider() {
    if (!id) return;
    setLoading(true);
    setLoadError(null);
    Promise.all([api.getProvider(id), api.getProviderQuarterlyHistory(id)])
      .then(([p, qh]) => {
        setProvider(p);
        setQuarterlyHistory(qh);
        addRecentlyViewed({
          id: p.id, name: p.name, specialty: p.specialty,
          performanceScore: p.performanceScore, riskLevel: p.riskLevel, practiceType: p.practiceType,
        });
      })
      .catch((err) => setLoadError(err instanceof Error ? err.message : "Failed to load this provider."))
      .finally(() => setLoading(false));
    // Agent-driven and can be slow -- must not block the rest of the panel
    // (score, metrics, claims) behind it; the Overview tab's insights card
    // just updates whenever this resolves.
    api.getInsights().then(setInsights).catch(() => {});
  }

  useEffect(loadProvider, [id]);

  useEffect(() => {
    if (!id) return;
    api.getProviderMetricHistory(id, granularity).then(setMetricHistory);
  }, [id, granularity]);

  function setTab(next: TabKey) {
    setSearchParams((prev) => {
      const params = new URLSearchParams(prev);
      params.set("tab", next);
      return params;
    });
  }

  async function handleActionStatusChange(actionId: string, status: ActionStatus) {
    if (!id) return;
    setActionError(null);
    try {
      const updated = await api.setActionStatus(id, actionId, status);
      setProvider(updated);
      notifyProviderDataChanged();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to update this action. Please try again.");
    }
  }

  function close() {
    const background = (location.state as { backgroundLocation?: { pathname?: string } } | null)?.backgroundLocation;
    navigate(background?.pathname || "/dashboard");
  }

  async function handleDownload(scope: "full" | "custom") {
    if (!id) return;
    setDownloadMenuOpen(false);
    setDownloading(true);
    setDownloadError(null);
    try {
      if (scope === "full") {
        await api.downloadProviderReport(id, "quarter");
      } else {
        const inRange = selectPeriods(metricHistory, period, granularity);
        await api.downloadProviderReport(id, granularity, inRange[0]?.period, inRange[inRange.length - 1]?.period);
      }
    } catch (err) {
      setDownloadError(err instanceof Error ? err.message : "Download failed. Please try again.");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <SlidePanel
      onClose={close}
      storageKey="ppd_panel_width"
      title={
        provider ? (
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-sm font-semibold text-ink-primary truncate">{provider.name}</h2>
              <RiskBadge level={provider.riskLevel} />
              <TrendBadge trend={provider.trend} />
              <StuckRiskBadge quarters={provider.stuckAtRiskQuarters} />
            </div>
            <p className="text-xs text-ink-muted truncate">{provider.specialty} · {provider.facility}</p>
          </div>
        ) : (
          <h2 className="text-sm font-semibold text-ink-primary">Loading...</h2>
        )
      }
      headerActions={
        provider && (
          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={() => setRootCauseOpen(true)}
              className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg border border-line-axis text-ink-secondary hover:bg-plane transition"
            >
              <Search className="w-3.5 h-3.5" /> Explain Root Cause
            </button>
            <button
              type="button"
              onClick={() => setEmailOpen(true)}
              disabled={!isAdmin}
              title={isAdmin ? undefined : "Requires Practice Administrator access"}
              className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg border border-line-axis text-ink-secondary hover:bg-plane transition disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-transparent"
            >
              <Mail className="w-3.5 h-3.5" /> Email
            </button>
            <button
              type="button"
              onClick={() => setBookingOpen(true)}
              disabled={!isAdmin}
              title={isAdmin ? undefined : "Requires Practice Administrator access"}
              className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg border border-line-axis text-ink-secondary hover:bg-plane transition disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-transparent"
            >
              <CalendarPlus className="w-3.5 h-3.5" /> Schedule
            </button>
            <div className="relative">
              <button
                ref={downloadBtnRef}
                type="button"
                onClick={() => {
                  if (!downloadMenuOpen && downloadBtnRef.current) {
                    const r = downloadBtnRef.current.getBoundingClientRect();
                    setDownloadMenuPos({ top: r.bottom + 8, right: window.innerWidth - r.right });
                  }
                  setDownloadMenuOpen((v) => !v);
                }}
                disabled={downloading}
                className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg border border-line-axis text-ink-secondary hover:bg-plane transition disabled:opacity-50"
              >
                <Download className="w-3.5 h-3.5" /> {downloading ? "Preparing..." : "Download Report"}
              </button>
              {downloadMenuOpen && downloadMenuPos &&
                createPortal(
                  <>
                    <div className="fixed inset-0 z-[9998]" onClick={() => setDownloadMenuOpen(false)} />
                    <div
                      className="fixed w-60 bg-surface border border-line-grid rounded-xl shadow-lg p-2 z-[9999]"
                      style={{ top: downloadMenuPos.top, right: downloadMenuPos.right }}
                    >
                      <button
                        type="button"
                        onClick={() => handleDownload("full")}
                        className="w-full text-left px-3 py-2 rounded-lg hover:bg-plane transition"
                      >
                        <span className="block text-sm font-medium text-ink-primary">Full Provider Report</span>
                        <span className="block text-xs text-ink-muted">All available history</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDownload("custom")}
                        className="w-full text-left px-3 py-2 rounded-lg hover:bg-plane transition"
                      >
                        <span className="block text-sm font-medium text-ink-primary">Custom Report</span>
                        <span className="block text-xs text-ink-muted">Matches your selected {granularity} view</span>
                      </button>
                    </div>
                  </>,
                  document.body
                )}
            </div>
          </div>
        )
      }
    >
      {loadError ? (
        <div className="p-6 flex flex-col items-center text-center gap-3">
          <div className="flex items-center gap-2 text-sm text-risk-critical">
            <AlertCircle className="w-4 h-4" /> {loadError}
          </div>
          <button
            type="button"
            onClick={loadProvider}
            className="flex items-center gap-2 text-sm px-4 py-2 rounded-lg bg-ink-primary text-white hover:bg-ink-primary/90 transition"
          >
            <RefreshCw className="w-4 h-4" /> Retry
          </button>
        </div>
      ) : loading || !provider ? (
        <div className="p-6 text-sm text-ink-muted">Loading provider...</div>
      ) : (
        <div className="p-6 space-y-5">
          {downloadError && (
            <div className="flex items-center gap-2 text-sm text-risk-critical bg-risk-critical/10 rounded-lg px-3 py-2">
              <AlertCircle className="w-4 h-4 shrink-0" /> {downloadError}
            </div>
          )}
          {actionError && (
            <div className="flex items-center gap-2 text-sm text-risk-critical bg-risk-critical/10 rounded-lg px-3 py-2">
              <AlertCircle className="w-4 h-4 shrink-0" /> {actionError}
            </div>
          )}

          <div className="flex gap-1 border-b border-line-grid">
            {TABS.map((t) => (
              <button
                type="button"
                key={t.key}
                onClick={() => setTab(t.key)}
                className={`px-4 py-2.5 text-sm font-medium border-b-2 transition ${
                  tab === t.key ? "border-chart-1 text-ink-primary" : "border-transparent text-ink-muted hover:text-ink-secondary"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          {tab === "overview" && <OverviewTab provider={provider} insights={insights} />}
          {tab === "metrics" && (
            <MetricsTab
              providerName={provider.name}
              metricHistory={metricHistory}
              granularity={granularity}
              onGranularityChange={setGranularity}
              period={period}
              onPeriodChange={setPeriod}
            />
          )}
          {tab === "claims" && <ClaimsHistoryTab providerId={provider.id} history={provider.claimsHistory} />}
          {tab === "actions" && (
            <ActionsTab
              actions={provider.actions}
              quarterlyHistory={quarterlyHistory}
              providerId={provider.id}
              providerName={provider.name}
              onStatusChange={handleActionStatusChange}
              isAdmin={isAdmin}
            />
          )}

          <EmailComposeModal
            open={emailOpen}
            onClose={() => setEmailOpen(false)}
            providerIds={[provider.id]}
            providerNames={[provider.name]}
            defaultTopic={provider.flagged ? provider.flagReason ?? "" : ""}
          />
          <AppointmentBookingModal
            open={bookingOpen}
            onClose={() => setBookingOpen(false)}
            providerIds={[provider.id]}
            providerNames={[provider.name]}
            defaultTopic="Performance review"
          />
          <RootCauseModal
            providerId={rootCauseOpen ? provider.id : null}
            providerName={provider.name}
            onClose={() => setRootCauseOpen(false)}
          />
        </div>
      )}
    </SlidePanel>
  );
}
