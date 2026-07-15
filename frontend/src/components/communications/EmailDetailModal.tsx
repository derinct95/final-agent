import { Mail } from "lucide-react";
import Modal from "../common/Modal";
import type { EmailMessageRecord } from "../../types";
import { relativeTime } from "../../utils/relativeTime";

interface EmailDetailModalProps {
  email: EmailMessageRecord | null;
  onClose: () => void;
}

export default function EmailDetailModal({ email, onClose }: EmailDetailModalProps) {
  return (
    <Modal open={!!email} onClose={onClose} title="Email" widthClassName="max-w-lg">
      {email && (
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-xs text-ink-muted">
            <Mail className="w-3.5 h-3.5" />
            Sent {relativeTime(email.sentAt)}
          </div>
          <p className="text-xs text-ink-muted">To: {email.recipients.join(", ") || "No recipients"}</p>
          <div>
            <p className="text-xs font-medium text-ink-secondary mb-1">Subject</p>
            <p className="text-sm text-ink-primary">{email.subject}</p>
          </div>
          <div>
            <p className="text-xs font-medium text-ink-secondary mb-1">Body</p>
            <p className="text-sm text-ink-secondary whitespace-pre-wrap leading-relaxed">{email.body}</p>
          </div>
        </div>
      )}
    </Modal>
  );
}
