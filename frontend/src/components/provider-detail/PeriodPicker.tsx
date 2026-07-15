import { useState } from "react";
import type { Granularity, Metrics, MetricSnapshot } from "../../types";
import SegmentedControl from "../common/SegmentedControl";

const METRIC_FIELDS: (keyof Metrics)[] = [
  "cleanClaimRate", "denialRate", "daysInAR", "firstPassResolutionRate", "codingAccuracy",
  "priorAuthApprovalRate", "netCollectionRate", "avgReimbursementPerClaim", "claimsVolumeMonthly",
  "documentationAccuracy", "patientSatisfactionScore",
  "clinicalQualityScore", "patientVisitsMonthly", "patientPortalAdoptionRate",
];

function averageMetrics(list: Metrics[]): Metrics {
  const out = {} as Metrics;
  for (const key of METRIC_FIELDS) {
    out[key] = Math.round((list.reduce((sum, m) => sum + m[key], 0) / list.length) * 100) / 100;
  }
  return out;
}

/** The metric cards show an aggregate (average) over the selected range, not just the
 * last point -- otherwise every granularity's "current" value converges on the same
 * quarter-end figure (since week/month are interpolated to match quarter boundaries)
 * and switching granularity would look like nothing changed. */
export function aggregatePeriods(points: MetricSnapshot[]): MetricSnapshot | null {
  if (points.length === 0) return null;
  if (points.length === 1) return points[0];
  const last = points[points.length - 1];
  const performanceScore = Math.round((points.reduce((sum, p) => sum + p.performanceScore, 0) / points.length) * 10) / 10;
  return {
    period: last.period,
    label: `${points[0].label} – ${last.label} (avg)`,
    performanceScore,
    riskLevel: last.riskLevel,
    trend: last.trend,
    metrics: averageMetrics(points.map((p) => p.metrics)),
    peerAverageMetrics: averageMetrics(points.map((p) => p.peerAverageMetrics)),
  };
}

export type PeriodMode = "recentSmall" | "recentLarge" | "all" | "custom";

export interface PeriodSelection {
  mode: PeriodMode;
  customStart?: string;
  customEnd?: string;
}

const PRESETS: Record<Granularity, { small: number; smallLabel: string; large: number; largeLabel: string }> = {
  week: { small: 8, smallLabel: "Last 8 Weeks", large: 26, largeLabel: "Last 26 Weeks" },
  month: { small: 3, smallLabel: "Last 3 Months", large: 12, largeLabel: "Last 12 Months" },
  quarter: { small: 1, smallLabel: "Last Quarter", large: 4, largeLabel: "Last 4 Quarters" },
  year: { small: 1, smallLabel: "Last Year", large: 3, largeLabel: "All Years" },
};

export function selectPeriods(history: MetricSnapshot[], selection: PeriodSelection, granularity: Granularity): MetricSnapshot[] {
  const preset = PRESETS[granularity];
  if (selection.mode === "recentSmall") return history.slice(-preset.small);
  if (selection.mode === "recentLarge") return history.slice(-preset.large);
  if (selection.mode === "custom" && selection.customStart && selection.customEnd) {
    return history.filter((p) => p.period >= selection.customStart! && p.period <= selection.customEnd!);
  }
  return history;
}

interface PeriodPickerProps {
  granularity: Granularity;
  onGranularityChange: (g: Granularity) => void;
  history: MetricSnapshot[];
  value: PeriodSelection;
  onChange: (value: PeriodSelection) => void;
}

export default function PeriodPicker({ granularity, onGranularityChange, history, value, onChange }: PeriodPickerProps) {
  const [showCustom, setShowCustom] = useState(value.mode === "custom");
  const preset = PRESETS[granularity];
  const periods = history.map((p) => p.period);
  const labels = new Map(history.map((p) => [p.period, p.label]));

  return (
    <div className="flex flex-col gap-2">
      <SegmentedControl
        options={[
          { value: "week", label: "Weekly" },
          { value: "month", label: "Monthly" },
          { value: "quarter", label: "Quarterly" },
          { value: "year", label: "Yearly" },
        ]}
        value={granularity}
        onChange={(g) => {
          setShowCustom(false);
          onGranularityChange(g as Granularity);
          onChange({ mode: "all" });
        }}
      />
      <div className="flex flex-col sm:flex-row sm:items-center gap-2">
        <SegmentedControl
          options={[
            { value: "recentSmall", label: preset.smallLabel },
            { value: "recentLarge", label: preset.largeLabel },
            { value: "all", label: "All" },
            { value: "custom", label: "Custom" },
          ]}
          value={showCustom ? "custom" : value.mode}
          onChange={(mode) => {
            if (mode === "custom") {
              setShowCustom(true);
              onChange({ mode: "custom", customStart: periods[0], customEnd: periods[periods.length - 1] });
            } else {
              setShowCustom(false);
              onChange({ mode: mode as PeriodMode });
            }
          }}
        />
        {showCustom && (
          <div className="flex items-center gap-2 text-sm">
            <select
              value={value.customStart ?? periods[0]}
              onChange={(e) => onChange({ mode: "custom", customStart: e.target.value, customEnd: value.customEnd })}
              className="rounded-lg border border-line-axis px-2 py-1.5 text-sm bg-surface"
            >
              {periods.map((p) => (
                <option key={p} value={p}>{labels.get(p)}</option>
              ))}
            </select>
            <span className="text-ink-muted">to</span>
            <select
              value={value.customEnd ?? periods[periods.length - 1]}
              onChange={(e) => onChange({ mode: "custom", customStart: value.customStart, customEnd: e.target.value })}
              className="rounded-lg border border-line-axis px-2 py-1.5 text-sm bg-surface"
            >
              {periods.map((p) => (
                <option key={p} value={p}>{labels.get(p)}</option>
              ))}
            </select>
          </div>
        )}
      </div>
    </div>
  );
}
