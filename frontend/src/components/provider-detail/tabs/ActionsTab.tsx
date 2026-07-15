import { CheckCircle2, Circle, CircleDot, History, Sparkles, X } from "lucide-react";
import { useState } from "react";
import type { Action, ActionStatus, QuarterlySnapshot } from "../../../types";
import ActionCompletionModal, { type CompletionMethod } from "../ActionCompletionModal";
import ActionDetailModal from "../ActionDetailModal";
import AppointmentBookingModal from "../../communications/AppointmentBookingModal";
import EmailComposeModal from "../../communications/EmailComposeModal";

interface ActionsTabProps {
  actions: Action[];
  quarterlyHistory: QuarterlySnapshot[];
  providerId: string;
  providerName: string;
  onStatusChange: (actionId: string, status: ActionStatus) => void;
  isAdmin: boolean;
}

const STATUS_ORDER: ActionStatus[] = ["open", "in_progress", "resolved"];
const STATUS_LABEL: Record<ActionStatus, string> = {
  open: "Open",
  in_progress: "In Review",
  resolved: "Completed",
};
const PRIORITY_COLOR: Record<string, string> = {
  high: "#d03b3b",
  medium: "#fab219",
  low: "#0ca30c",
};

function StatusIcon({ status }: { status: ActionStatus }) {
  if (status === "resolved") return <CheckCircle2 className="w-4 h-4 text-risk-low" />;
  if (status === "in_progress") return <CircleDot className="w-4 h-4 text-chart-1" />;
  return <Circle className="w-4 h-4 text-ink-muted" />;
}

export default function ActionsTab({ actions, quarterlyHistory, providerId, providerName, onStatusChange, isAdmin }: ActionsTabProps) {
  const [openAction, setOpenAction] = useState<Action | null>(null);
  const [completingAction, setCompletingAction] = useState<Action | null>(null);
  const [emailAction, setEmailAction] = useState<Action | null>(null);
  const [bookingAction, setBookingAction] = useState<Action | null>(null);
  const [completionNote, setCompletionNote] = useState<string | null>(null);

  function nextStatus(current: ActionStatus): ActionStatus {
    const idx = STATUS_ORDER.indexOf(current);
    return STATUS_ORDER[(idx + 1) % STATUS_ORDER.length];
  }

  function requestAdvance(action: Action) {
    if (!isAdmin) return;
    const next = nextStatus(action.status);
    if (next === "resolved") {
      setOpenAction(null);
      setCompletingAction(action);
    } else {
      onStatusChange(action.id, next);
    }
  }

  function handleCompletionChoice(method: CompletionMethod) {
    if (!completingAction) return;
    const action = completingAction;
    onStatusChange(action.id, "resolved");
    setCompletingAction(null);
    setCompletionNote(null);
    if (method === "email") {
      setEmailAction(action);
    } else if (method === "in_person") {
      setBookingAction(action);
    } else if (method === "phone") {
      setCompletionNote(`"${action.title}" marked complete — logged as notified by phone call.`);
    } else {
      setCompletionNote(`"${action.title}" marked complete — no provider notification needed.`);
    }
  }

  if (actions.length === 0) {
    return <p className="text-sm text-ink-muted">No actions recorded for this provider.</p>;
  }

  return (
    <div className="space-y-3">
      {completionNote && (
        <div className="flex items-center justify-between gap-2 text-sm text-risk-low bg-risk-low/10 rounded-lg px-3 py-2">
          <span className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" /> {completionNote}
          </span>
          <button type="button" onClick={() => setCompletionNote(null)} className="text-ink-muted hover:text-ink-primary transition">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {actions.map((action) => (
        <div
          key={action.id}
          onClick={() => setOpenAction(action)}
          className="bg-surface border border-ink-primary/10 rounded-2xl p-4 flex items-start gap-4 cursor-pointer hover:border-chart-1/40 hover:shadow-md transition"
        >
          <button
            onClick={(e) => {
              e.stopPropagation();
              requestAdvance(action);
            }}
            disabled={!isAdmin}
            className="mt-0.5 shrink-0 disabled:opacity-40 disabled:cursor-not-allowed"
            title={isAdmin ? "Click to advance status" : "Requires Practice Administrator access"}
          >
            <StatusIcon status={action.status} />
          </button>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="text-sm font-medium text-ink-primary">{action.title}</h3>
              {action.source === "ai" && (
                <span className="inline-flex items-center gap-1 text-xs text-chart-5">
                  <Sparkles className="w-3 h-3" /> AI-suggested
                </span>
              )}
              {action.isRecurring && (
                <span className="inline-flex items-center gap-1 text-xs font-medium text-risk-high border border-risk-high rounded-md px-1.5 py-0.5">
                  <History className="w-3 h-3" /> Recurring — {action.consecutiveQuarters}Q
                </span>
              )}
            </div>
            <p className="text-xs text-ink-secondary mt-1">{action.description}</p>
            <div className="flex items-center gap-3 mt-2 text-xs text-ink-muted">
              <span
                className="inline-flex items-center gap-1 font-medium"
                style={{ color: PRIORITY_COLOR[action.priority] }}
              >
                {action.priority.toUpperCase()} PRIORITY
              </span>
              <span>·</span>
              <span className="capitalize">{action.category}</span>
              <span>·</span>
              <span>{action.createdAt}</span>
            </div>
          </div>
          <span className="text-xs font-medium text-ink-secondary bg-plane px-2.5 py-1 rounded-full shrink-0">
            {STATUS_LABEL[action.status]}
          </span>
        </div>
      ))}

      <ActionDetailModal
        action={openAction}
        quarterlyHistory={quarterlyHistory}
        onClose={() => setOpenAction(null)}
        onAdvanceToReview={() => {
          if (openAction && isAdmin) onStatusChange(openAction.id, "in_progress");
          setOpenAction(null);
        }}
        onRequestComplete={() => {
          if (openAction) requestAdvance({ ...openAction, status: "in_progress" });
        }}
      />

      <ActionCompletionModal
        action={completingAction}
        onClose={() => setCompletingAction(null)}
        onChoose={handleCompletionChoice}
      />

      <EmailComposeModal
        open={!!emailAction}
        onClose={() => setEmailAction(null)}
        providerIds={[providerId]}
        providerNames={[providerName]}
        defaultTopic={emailAction ? `Resolved: ${emailAction.title}` : ""}
      />

      <AppointmentBookingModal
        open={!!bookingAction}
        onClose={() => setBookingAction(null)}
        providerIds={[providerId]}
        providerNames={[providerName]}
        defaultTopic={bookingAction ? `Discuss: ${bookingAction.title}` : ""}
      />
    </div>
  );
}
