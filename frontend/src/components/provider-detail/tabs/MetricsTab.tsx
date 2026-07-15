import { useState } from "react";
import MetricsRadar from "../../charts/MetricsRadar";
import { CATEGORICAL, INK_MUTED } from "../../charts/theme";
import Value from "../../common/Value";
import MetricDetailModal from "../MetricDetailModal";
import MetricTrendChart from "../MetricTrendChart";
import PeriodPicker, { aggregatePeriods, selectPeriods, type PeriodSelection } from "../PeriodPicker";
import type { Granularity, Metrics, MetricSnapshot } from "../../../types";

interface MetricsTabProps {
  providerName: string;
  metricHistory: MetricSnapshot[];
  granularity: Granularity;
  onGranularityChange: (g: Granularity) => void;
  period: PeriodSelection;
  onPeriodChange: (p: PeriodSelection) => void;
}

const CARDS: { key: keyof Metrics; label: string; type: "percent" | "number" | "currency"; higherIsBetter: boolean }[] = [
  { key: "cleanClaimRate", label: "Clean Claim Rate", type: "percent", higherIsBetter: true },
  { key: "denialRate", label: "Denial Rate", type: "percent", higherIsBetter: false },
  { key: "daysInAR", label: "Days in AR", type: "number", higherIsBetter: false },
  { key: "firstPassResolutionRate", label: "First-Pass Resolution", type: "percent", higherIsBetter: true },
  { key: "codingAccuracy", label: "Coding Accuracy", type: "percent", higherIsBetter: true },
  { key: "priorAuthApprovalRate", label: "Prior-Auth Approval", type: "percent", higherIsBetter: true },
  { key: "netCollectionRate", label: "Net Collection Rate", type: "percent", higherIsBetter: true },
  { key: "avgReimbursementPerClaim", label: "Avg Reimbursement / Claim", type: "currency", higherIsBetter: true },
  { key: "documentationAccuracy", label: "Documentation Accuracy", type: "percent", higherIsBetter: true },
  { key: "patientSatisfactionScore", label: "Patient Satisfaction", type: "percent", higherIsBetter: true },
  { key: "clinicalQualityScore", label: "Clinical Quality Score", type: "percent", higherIsBetter: true },
  { key: "patientVisitsMonthly", label: "Patient Visits / Month", type: "number", higherIsBetter: true },
  { key: "patientPortalAdoptionRate", label: "Patient Portal Adoption", type: "percent", higherIsBetter: true },
];

export default function MetricsTab({
  providerName, metricHistory, granularity, onGranularityChange, period, onPeriodChange,
}: MetricsTabProps) {
  const [openKey, setOpenKey] = useState<keyof Metrics | null>(null);
  const inRange = selectPeriods(metricHistory, period, granularity);
  const current = aggregatePeriods(inRange) ?? aggregatePeriods(metricHistory);

  if (!current) {
    return <p className="text-sm text-ink-muted">No data for this period.</p>;
  }

  const metrics = current.metrics;
  const peer = current.peerAverageMetrics;
  const openCard = CARDS.find((c) => c.key === openKey);

  return (
    <div className="space-y-4">
      <PeriodPicker
        granularity={granularity}
        onGranularityChange={onGranularityChange}
        history={metricHistory}
        value={period}
        onChange={onPeriodChange}
      />

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
        <div className="lg:col-span-3 grid grid-cols-2 sm:grid-cols-4 gap-3 content-start">
          {CARDS.map((card) => {
            const value = metrics[card.key];
            const peerValue = peer[card.key];
            const delta = value - peerValue;
            const good = card.higherIsBetter ? delta >= 0 : delta <= 0;
            return (
              <button
                type="button"
                key={card.key}
                onClick={() => setOpenKey(card.key)}
                className="bg-surface border border-ink-primary/10 rounded-xl p-4 text-left hover:border-chart-1/40 hover:shadow-md transition"
              >
                <p className="text-xs text-ink-muted mb-1">{card.label}</p>
                <p className="text-lg font-semibold">
                  <Value value={value} type={card.type} decimals={card.type === "currency" ? 0 : 1} />
                </p>
                <p className={`text-xs tabular-nums mt-1 ${good ? "text-risk-low" : "text-risk-critical"}`}>
                  peer avg <Value value={peerValue} type={card.type} decimals={card.type === "currency" ? 0 : 1} />
                </p>
              </button>
            );
          })}
        </div>

        <div className="lg:col-span-2 bg-surface border border-ink-primary/10 rounded-2xl p-5">
          {openCard ? (
            <>
              <h3 className="text-sm font-semibold text-ink-primary mb-1">{openCard.label} — Trend</h3>
              <p className="text-xs text-ink-muted mb-2">
                Updates to whichever metric card you click. Click the same card again, or the radar-overview toggle below, to go back.
              </p>
              <MetricTrendChart points={inRange.length ? inRange : metricHistory} metricKey={openCard.key} />
              <button
                type="button"
                onClick={() => setOpenKey(null)}
                className="mt-2 text-xs font-medium text-chart-1 hover:underline"
              >
                ← Back to full metrics overview
              </button>
            </>
          ) : (
            <>
              <h3 className="text-sm font-semibold text-ink-primary mb-1">{current.label} vs. Peer Average</h3>
              <p className="text-xs text-ink-muted mb-2">
                Overview across every metric at once, normalized 0-100. Click any card on the left for that metric's own trend here.
              </p>
              <MetricsRadar
                series={[
                  { name: providerName, metrics, color: CATEGORICAL[0] },
                  { name: "Peer Average", metrics: peer, color: INK_MUTED, dashed: true },
                ]}
              />
            </>
          )}
        </div>
      </div>

      {openCard && (
        <MetricDetailModal
          metricKey={openKey}
          label={openCard.label}
          type={openCard.type}
          points={inRange.length ? inRange : metricHistory}
          current={current}
          onClose={() => setOpenKey(null)}
        />
      )}
    </div>
  );
}
