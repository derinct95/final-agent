import { AlertCircle, MapPin, Phone, RefreshCw, Sparkles } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import AiInsightsPanel from "../components/dashboard/AiInsightsPanel";
import ExportImportBar from "../components/dashboard/ExportImportBar";
import KpiRow from "../components/dashboard/KpiRow";
import PerformerLeaderboard from "../components/dashboard/PerformerLeaderboard";
import ProviderTable from "../components/dashboard/ProviderTable";
import RecentActivityFeed from "../components/dashboard/RecentActivityFeed";
import RecentlyViewedRail from "../components/dashboard/RecentlyViewedRail";
import { VERTICAL_CONTACT } from "../config/practiceContact";
import { onProviderDataChanged } from "../utils/events";
import type { DashboardSummary, Insight, PracticeType, ProviderSummary } from "../types";

const VERTICAL_COPY: Record<PracticeType, { name: string; tagline: string }> = {
  medical: { name: "Clearview Medical Group", tagline: "AI-powered revenue cycle performance" },
  dental: { name: "Clearview Family Dental", tagline: "AI-powered dental practice performance" },
};

interface DashboardPageProps {
  practiceType?: PracticeType;
}

export default function DashboardPage({ practiceType = "medical" }: DashboardPageProps) {
  const [providers, setProviders] = useState<ProviderSummary[]>([]);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [insightsLoading, setInsightsLoading] = useState(true);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [agentRefreshing, setAgentRefreshing] = useState(false);

  const loadProviders = useCallback(async () => {
    const [providerList, summaryData] = await Promise.all([
      api.listProviders(practiceType),
      api.getSummary(practiceType),
    ]);
    setProviders(providerList);
    setSummary(summaryData);
  }, [practiceType]);

  const loadInsights = useCallback(async (refresh = false) => {
    setInsightsLoading(true);
    try {
      const data = await api.getInsights(refresh, practiceType);
      setInsights(data);
    } finally {
      setInsightsLoading(false);
    }
  }, [practiceType]);

  // Insights is agent-driven and can take much longer than the plain data
  // load -- it has its own independent loading skeleton (AiInsightsPanel), so
  // it must NOT gate the rest of the dashboard (KPIs, table, guided tour)
  // behind its completion.
  useEffect(() => {
    setLoading(true);
    setLoadError(null);
    loadProviders()
      .catch((err) => setLoadError(err instanceof Error ? err.message : "Failed to load the dashboard."))
      .finally(() => setLoading(false));
    loadInsights();
  }, [loadProviders, loadInsights]);

  useEffect(() => onProviderDataChanged(() => { loadProviders(); }), [loadProviders]);

  function retryLoad() {
    setLoading(true);
    setLoadError(null);
    loadProviders()
      .catch((err) => setLoadError(err instanceof Error ? err.message : "Failed to load the dashboard."))
      .finally(() => setLoading(false));
    loadInsights();
  }

  async function handleMarkReviewed(id: string) {
    await api.setFlag(id, { reviewed: true });
    await loadProviders();
  }

  async function handleImported() {
    await loadProviders();
  }

  async function handleAgentRefresh() {
    setAgentRefreshing(true);
    try {
      await Promise.all([loadInsights(true), loadProviders()]);
    } finally {
      setAgentRefreshing(false);
    }
  }

  if (loadError) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3 text-center">
        <div className="flex items-center gap-2 text-sm text-risk-critical">
          <AlertCircle className="w-4 h-4" /> {loadError}
        </div>
        <button
          type="button"
          onClick={retryLoad}
          className="flex items-center gap-2 text-sm px-4 py-2 rounded-lg bg-ink-primary text-white hover:bg-ink-primary/90 transition"
        >
          <RefreshCw className="w-4 h-4" /> Retry
        </button>
      </div>
    );
  }

  if (loading || !summary) {
    return <div className="flex items-center justify-center h-64 text-ink-muted text-sm">Loading dashboard...</div>;
  }

  const facilityCount = new Set(providers.map((p) => p.facility)).size;
  const specialtyCount = new Set(providers.map((p) => p.specialty)).size;
  const openActionsCount = providers.reduce((sum, p) => sum + p.pendingActionsCount, 0);
  const stuckAtRiskCount = providers.filter((p) => p.stuckAtRiskQuarters >= 2).length;
  const copy = VERTICAL_COPY[practiceType];
  const contact = VERTICAL_CONTACT[practiceType];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div
        id="overview"
        className="relative overflow-hidden rounded-2xl p-6 flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4"
        style={{ background: "linear-gradient(120deg, #1c3a5e 0%, #2a78d6 55%, #1baf7a 120%)" }}
      >
        <div className="relative z-10">
          <h1 className="text-2xl font-bold text-white">{copy.name}</h1>
          <p className="text-sm text-white/85 mt-1">
            {copy.tagline} across {summary.totalProviders} providers
          </p>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-xs text-white/80">
            <span className="flex items-center gap-1"><Phone className="w-3 h-3" /> {contact.phone}</span>
            <span className="w-1 h-1 rounded-full bg-white/40" />
            <span className="flex items-center gap-1"><MapPin className="w-3 h-3" /> {contact.address}</span>
          </div>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-3 text-xs text-white/80">
            <span>{facilityCount} facilities</span>
            <span className="w-1 h-1 rounded-full bg-white/40" />
            <span>{specialtyCount} specialties</span>
            <span className="w-1 h-1 rounded-full bg-white/40" />
            <span>{summary.flaggedCount} flagged awaiting review</span>
            <span className="w-1 h-1 rounded-full bg-white/40" />
            <span>{openActionsCount} open action items practice-wide</span>
            <span className="w-1 h-1 rounded-full bg-white/40" />
            <span>{stuckAtRiskCount} stuck at risk 2+ quarters</span>
            <span className="w-1 h-1 rounded-full bg-white/40" />
            <span>Synthetic data only — no real patient or provider PHI</span>
          </div>
        </div>
        <div className="relative z-10 flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
          <button
            type="button"
            onClick={handleAgentRefresh}
            disabled={agentRefreshing}
            title="Re-run the AI agent to refresh insights and dashboard data in one pass"
            className="flex items-center justify-center gap-2 text-sm font-medium px-4 py-2.5 rounded-xl bg-white/95 text-ink-primary hover:bg-white transition disabled:opacity-70"
          >
            <Sparkles className={`w-4 h-4 text-chart-5 ${agentRefreshing ? "animate-pulse" : ""}`} />
            {agentRefreshing ? "Agent refreshing..." : "Agent Refresh"}
          </button>
          <div className="bg-white/95 rounded-xl p-2 backdrop-blur-sm">
            <ExportImportBar onImported={handleImported} />
          </div>
        </div>
      </div>

      <div data-tour="recent-panels" className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <RecentlyViewedRail practiceType={practiceType} />
        <RecentActivityFeed providerIds={providers.map((p) => p.id)} />
      </div>

      <KpiRow summary={summary} providers={providers} />

      <AiInsightsPanel insights={insights} loading={insightsLoading} onRefresh={() => loadInsights(true)} />

      <PerformerLeaderboard providers={providers} />

      <ProviderTable providers={providers} onMarkReviewed={handleMarkReviewed} />
    </div>
  );
}
