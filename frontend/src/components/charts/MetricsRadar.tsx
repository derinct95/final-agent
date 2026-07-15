import {
  Legend,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import type { Metrics } from "../../types";
import { GRID_LINE, INK_MUTED } from "./theme";

export interface RadarSeries {
  name: string;
  metrics: Metrics;
  color: string;
  dashed?: boolean;
}

const AXES: { axis: string; key: keyof Metrics; invert?: boolean }[] = [
  { axis: "Clean Claims", key: "cleanClaimRate" },
  { axis: "1st-Pass Res.", key: "firstPassResolutionRate" },
  { axis: "Coding Acc.", key: "codingAccuracy" },
  { axis: "Doc. Acc.", key: "documentationAccuracy" },
  { axis: "Prior-Auth", key: "priorAuthApprovalRate" },
  { axis: "Net Collect.", key: "netCollectionRate" },
  { axis: "Pt. Satisf.", key: "patientSatisfactionScore" },
  { axis: "Denial Ctrl", key: "denialRate", invert: true },
  { axis: "Clinical Qual.", key: "clinicalQualityScore" },
  { axis: "Portal Adopt.", key: "patientPortalAdoptionRate" },
];

function toRadarData(series: RadarSeries[]) {
  return AXES.map(({ axis, key, invert }) => {
    const row: Record<string, string | number> = { axis };
    for (const s of series) {
      const value = s.metrics[key];
      row[s.name] = Math.round(invert ? 100 - value : value);
    }
    return row;
  });
}

interface MetricsRadarProps {
  series: RadarSeries[];
}

export default function MetricsRadar({ series }: MetricsRadarProps) {
  const data = toRadarData(series);
  return (
    <ResponsiveContainer width="100%" height={340}>
      <RadarChart data={data} outerRadius="68%">
        <PolarGrid stroke={GRID_LINE} />
        <PolarAngleAxis dataKey="axis" tick={{ fontSize: 11, fill: INK_MUTED }} />
        <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 10, fill: INK_MUTED }} axisLine={false} />
        {series.map((s) => (
          <Radar
            key={s.name}
            name={s.name}
            dataKey={s.name}
            stroke={s.color}
            fill={s.color}
            fillOpacity={s.dashed ? 0.08 : 0.22}
            strokeWidth={2}
            strokeDasharray={s.dashed ? "4 3" : undefined}
          />
        ))}
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Tooltip />
      </RadarChart>
    </ResponsiveContainer>
  );
}
