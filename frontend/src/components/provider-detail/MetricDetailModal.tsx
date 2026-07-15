import Modal from "../common/Modal";
import Value from "../common/Value";
import MetricBenchmarkChart from "../charts/MetricBenchmarkChart";
import type { Metrics, MetricSnapshot } from "../../types";
import MetricTrendChart from "./MetricTrendChart";

interface MetricInfo {
  description: string;
  calculation: string;
  improvement: string;
  target: number;
}

const METRIC_INFO: Record<keyof Metrics, MetricInfo> = {
  cleanClaimRate: {
    description: "Share of claims paid on first submission with no edits or rework. Higher means less administrative rework and faster cash flow.",
    calculation: "Clean Claim Rate = (Claims paid on first submission ÷ Total claims submitted) × 100.",
    improvement: "Improves with accurate coding, complete documentation, and verified eligibility/authorization before the claim goes out.",
    target: 95,
  },
  denialRate: {
    description: "Share of submitted claims that payers reject. Lower is better -- every denial means delayed or lost revenue and rework for billing staff.",
    calculation: "Denial Rate = (Claims denied ÷ Total claims submitted) × 100.",
    improvement: "Drops when prior authorizations are obtained up front, coding matches documentation, and claims are filed within the payer's timely-filing window.",
    target: 5,
  },
  daysInAR: {
    description: "Average number of days an unpaid claim sits in accounts receivable before payment. Lower means faster collections and healthier cash flow.",
    calculation: "Days in AR = Total accounts receivable balance ÷ Average daily charges, over the period.",
    improvement: "Falls with prompt claim follow-up, faster denial appeals, and fewer claims stuck in payer review.",
    target: 30,
  },
  firstPassResolutionRate: {
    description: "Share of claims resolved -- paid or appropriately closed -- without any resubmission. A proxy for overall billing and coding quality.",
    calculation: "First-Pass Resolution Rate = (Claims resolved on first submission ÷ Total claims submitted) × 100.",
    improvement: "Improves with fewer coding errors and complete supporting documentation at time of submission.",
    target: 92,
  },
  codingAccuracy: {
    description: "How often diagnosis/procedure codes are assigned correctly on the first pass, based on chart audits. Low accuracy drives denials and compliance risk.",
    calculation: "Coding Accuracy = (Correctly coded claims in the audit sample ÷ Total claims audited) × 100.",
    improvement: "Improves with coder training, up-to-date code-set references, and tighter coder-provider documentation feedback loops.",
    target: 97,
  },
  priorAuthApprovalRate: {
    description: "Share of prior-authorization requests approved by payers. A low rate signals workflow gaps that delay both care and payment.",
    calculation: "Prior-Auth Approval Rate = (Approved authorization requests ÷ Total requests submitted) × 100.",
    improvement: "Improves when clinical justification and payer-specific documentation requirements are met before the request is filed.",
    target: 95,
  },
  netCollectionRate: {
    description: "Share of contractually-owed (allowed) revenue actually collected. Widely considered the single best summary metric of RCM effectiveness.",
    calculation: "Net Collection Rate = (Payments received ÷ (Charges − Contractual adjustments)) × 100.",
    improvement: "Improves with fewer write-offs, faster denial recovery, and accurate posting of contracted rates.",
    target: 96,
  },
  avgReimbursementPerClaim: {
    description: "Average dollar amount collected per paid claim -- reflects payer mix, coding level, and service mix.",
    calculation: "Avg Reimbursement / Claim = Total revenue collected ÷ Number of paid claims.",
    improvement: "Rises with an appropriate case mix, accurate charge capture, and minimizing underpayments vs. the contracted rate.",
    target: 350,
  },
  claimsVolumeMonthly: {
    description: "Average number of claims submitted per month.",
    calculation: "Claims Volume = Total claims submitted ÷ Number of months in the period.",
    improvement: "Reflects patient volume and scheduling capacity -- not itself a quality metric.",
    target: 400,
  },
  documentationAccuracy: {
    description: "How completely clinical documentation supports the billed service, based on chart audits. Weak documentation is a leading root cause of denials.",
    calculation: "Documentation Accuracy = (Audited charts with fully-supporting documentation ÷ Total charts audited) × 100.",
    improvement: "Improves with point-of-care documentation checklists and closing the loop on denial-driven documentation gaps.",
    target: 95,
  },
  patientSatisfactionScore: {
    description: "Patient-reported satisfaction with their care experience -- a quality signal that is independent of revenue-cycle performance.",
    calculation: "Patient Satisfaction Score = Average of post-visit patient survey responses, normalized to 0-100.",
    improvement: "Improves with shorter wait times, clearer communication, and consistent follow-up.",
    target: 90,
  },
  clinicalQualityScore: {
    description: "A composite clinical-quality measure (in the spirit of P4P/MIPS quality-category scoring) reflecting adherence to evidence-based care measures, independent of billing/coding correctness.",
    calculation: "Clinical Quality Score = weighted average of applicable clinical quality measure pass rates, normalized to 0-100.",
    improvement: "Improves with better care-gap closure, adherence to clinical guidelines, and consistent quality-measure documentation at the point of care.",
    target: 90,
  },
  patientVisitsMonthly: {
    description: "Average number of patient visits per month -- a productivity/throughput measure of clinical capacity utilization.",
    calculation: "Patient Visits Monthly = Total patient visits ÷ Number of months in the period.",
    improvement: "Reflects scheduling efficiency and patient demand -- not itself a quality metric, but a capacity/productivity signal.",
    target: 320,
  },
  patientPortalAdoptionRate: {
    description: "Share of this provider's patients actively using the patient portal (messaging, scheduling, results) -- a proxy for patient engagement.",
    calculation: "Patient Portal Adoption Rate = (Patients with an active portal account ÷ Total active patients) × 100.",
    improvement: "Improves with proactive portal enrollment at check-in, staff prompts, and patient education on portal features.",
    target: 75,
  },
};

interface MetricDetailModalProps {
  metricKey: keyof Metrics | null;
  label: string;
  type: "percent" | "number" | "currency";
  points: MetricSnapshot[];
  current: MetricSnapshot;
  onClose: () => void;
}

export default function MetricDetailModal({ metricKey, label, type, points, current, onClose }: MetricDetailModalProps) {
  if (!metricKey) return null;
  const decimals = type === "currency" ? 0 : 1;
  const value = current.metrics[metricKey];
  const peerValue = current.peerAverageMetrics[metricKey];
  const info = METRIC_INFO[metricKey];

  return (
    <Modal open={!!metricKey} onClose={onClose} title={label} widthClassName="max-w-xl">
      <div className="space-y-4">
        <p className="text-sm text-ink-secondary leading-relaxed">{info.description}</p>
        <div className="grid grid-cols-2 gap-4">
          <div className="rounded-xl border border-line-grid p-3">
            <p className="text-xs text-ink-muted mb-1">Current ({current.label})</p>
            <p className="text-2xl font-semibold"><Value value={value} type={type} decimals={decimals} /></p>
          </div>
          <div className="rounded-xl border border-line-grid p-3">
            <p className="text-xs text-ink-muted mb-1">Peer Average</p>
            <p className="text-2xl font-semibold text-ink-secondary"><Value value={peerValue} type={type} decimals={decimals} /></p>
          </div>
        </div>

        <div className="rounded-lg border border-line-grid p-3">
          <p className="text-xs font-medium text-ink-secondary mb-1">Benchmark: You vs. Peer vs. Target</p>
          <p className="text-xs text-ink-muted mb-2">
            Practice target: <Value value={info.target} type={type} decimals={decimals} />
          </p>
          <MetricBenchmarkChart value={value} peerValue={peerValue} targetValue={info.target} />
        </div>

        <div className="rounded-lg border border-line-grid p-3 space-y-2">
          <div>
            <p className="text-xs font-medium text-ink-secondary mb-0.5">How it's calculated</p>
            <p className="text-xs text-ink-muted leading-relaxed">{info.calculation}</p>
          </div>
          <div>
            <p className="text-xs font-medium text-ink-secondary mb-0.5">What improves it</p>
            <p className="text-xs text-ink-muted leading-relaxed">{info.improvement}</p>
          </div>
        </div>

        <div>
          <p className="text-xs font-medium text-ink-secondary mb-2">Trend across selected period</p>
          <MetricTrendChart points={points} metricKey={metricKey} />
        </div>
      </div>
    </Modal>
  );
}
