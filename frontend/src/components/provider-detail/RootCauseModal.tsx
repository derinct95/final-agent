import { AlertCircle, AlertTriangle, CheckCircle2, ListChecks, ScrollText, Search, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { RISK_COLORS } from "../charts/theme";
import type { RootCauseAnalysis } from "../../types";
import Modal from "../common/Modal";

interface RootCauseModalProps {
  providerId: string | null;
  providerName: string;
  onClose: () => void;
}

function severityFromFactorCount(count: number): { color: string; label: string } {
  if (count >= 3) return { color: RISK_COLORS.critical, label: "Significant risk factors identified" };
  if (count >= 1) return { color: RISK_COLORS.medium, label: "Some gaps versus peers" };
  return { color: RISK_COLORS.low, label: "No major gaps versus peers" };
}

export default function RootCauseModal({ providerId, providerName, onClose }: RootCauseModalProps) {
  const [result, setResult] = useState<RootCauseAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!providerId) {
      setResult(null);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    api
      .getRootCause(providerId)
      .then(setResult)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to generate root-cause analysis."))
      .finally(() => setLoading(false));
  }, [providerId]);

  const severity = result ? severityFromFactorCount(result.contributingFactors.length) : null;

  return (
    <Modal open={!!providerId} onClose={onClose} title={`Root Cause: ${providerName}`} widthClassName="max-w-xl">
      <div className="space-y-4">
        {loading && (
          <div className="space-y-3">
            <div className="h-4 w-2/3 rounded bg-plane animate-pulse" />
            <div className="h-16 rounded bg-plane animate-pulse" />
            <div className="h-16 rounded bg-plane animate-pulse" />
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 text-sm text-risk-critical">
            <AlertCircle className="w-4 h-4 shrink-0" /> {error}
          </div>
        )}

        {result && severity && !loading && (
          <>
            <div
              className="rounded-xl p-3 flex items-center gap-2"
              style={{ backgroundColor: `${severity.color}14`, border: `1px solid ${severity.color}40` }}
            >
              {severity.color === RISK_COLORS.low ? (
                <CheckCircle2 className="w-4 h-4 shrink-0" style={{ color: severity.color }} />
              ) : (
                <AlertTriangle className="w-4 h-4 shrink-0" style={{ color: severity.color }} />
              )}
              <span className="text-sm font-semibold" style={{ color: severity.color }}>{severity.label}</span>
            </div>

            <p className="text-xs text-ink-muted flex items-center gap-1.5">
              {result.generatedBy === "ai" ? (
                <>
                  <Sparkles className="w-3.5 h-3.5 text-chart-5" /> Investigated live by the Clearview AI agent
                </>
              ) : (
                "Rule-based analysis (offline mode)"
              )}
            </p>

            <p className="text-sm text-ink-secondary leading-relaxed">{result.narrative}</p>

            {result.contributingFactors.length > 0 && (
              <div className="rounded-lg border border-line-grid p-3">
                <p className="text-xs font-medium text-ink-secondary mb-2 flex items-center gap-1.5">
                  <span
                    className="w-5 h-5 rounded-md flex items-center justify-center"
                    style={{ backgroundColor: `${severity.color}1a` }}
                  >
                    <Search className="w-3 h-3" style={{ color: severity.color }} />
                  </span>
                  Contributing Factors
                </p>
                <ul className="space-y-1.5 text-xs text-ink-secondary">
                  {result.contributingFactors.map((f, i) => (
                    <li key={i} className="flex items-start gap-1.5">
                      <AlertTriangle className="w-3 h-3 mt-0.5 shrink-0" style={{ color: severity.color }} />
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {result.citedPolicies.length > 0 && (
              <div className="rounded-lg border border-line-grid p-3">
                <p className="text-xs font-medium text-ink-secondary mb-2 flex items-center gap-1.5">
                  <span className="w-5 h-5 rounded-md bg-chart-1/10 flex items-center justify-center">
                    <ScrollText className="w-3 h-3 text-chart-1" />
                  </span>
                  Cited Policy
                </p>
                <ul className="space-y-1.5 text-xs text-ink-secondary list-disc list-inside">
                  {result.citedPolicies.map((p, i) => (
                    <li key={i}>{p}</li>
                  ))}
                </ul>
              </div>
            )}

            {result.recommendedRemediation.length > 0 && (
              <div className="rounded-lg border border-line-grid p-3">
                <p className="text-xs font-medium text-ink-secondary mb-2 flex items-center gap-1.5">
                  <span className="w-5 h-5 rounded-md bg-risk-low/10 flex items-center justify-center">
                    <ListChecks className="w-3 h-3 text-risk-low" />
                  </span>
                  Recommended Remediation
                </p>
                <ol className="space-y-1.5 text-xs text-ink-secondary list-decimal list-inside">
                  {result.recommendedRemediation.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ol>
              </div>
            )}
          </>
        )}
      </div>
    </Modal>
  );
}
