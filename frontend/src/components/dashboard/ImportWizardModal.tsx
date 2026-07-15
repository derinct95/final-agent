import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { useState } from "react";
import { api } from "../../api/client";
import { ADMIN_ROLE, useAuth } from "../../context/AuthContext";
import type { ImportPreviewResult, Provider } from "../../types";
import Modal from "../common/Modal";
import ImportPreviewTable from "./ImportPreviewTable";

interface ImportWizardModalProps {
  preview: ImportPreviewResult | null;
  onClose: () => void;
  onImported: (created: Provider[]) => void;
}

const FORMAT_LABEL: Record<string, string> = { fhir: "FHIR", hl7: "HL7v2", csv: "CSV" };

export default function ImportWizardModal({ preview, onClose, onImported }: ImportWizardModalProps) {
  const [committing, setCommitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { session } = useAuth();
  const isAdmin = session?.role === ADMIN_ROLE;

  async function handleConfirm() {
    if (!preview || !isAdmin) return;
    setCommitting(true);
    setError(null);
    try {
      const created = await api.commitImport(preview.importToken);
      onImported(created);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setCommitting(false);
    }
  }

  return (
    <Modal open={!!preview} onClose={onClose} title="Import Providers" widthClassName="max-w-2xl">
      {preview && (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-chart-1/10 text-chart-1">
              Detected format: {FORMAT_LABEL[preview.detectedFormat] ?? preview.detectedFormat}
            </span>
            <span className="text-xs text-ink-muted">{preview.rows.length} provider(s) found</span>
          </div>

          {preview.warnings.length > 0 && (
            <div className="rounded-lg border border-risk-medium/40 bg-risk-medium/5 p-3 space-y-1">
              {preview.warnings.map((w, i) => (
                <p key={i} className="text-xs text-ink-secondary flex items-start gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5 text-risk-medium" /> {w.message}
                </p>
              ))}
            </div>
          )}

          <ImportPreviewTable rows={preview.rows} />

          {error && <p className="text-sm text-risk-critical">{error}</p>}
          {!isAdmin && (
            <p className="text-sm text-risk-medium">Requires Practice Administrator access to commit this import.</p>
          )}

          <div className="flex justify-end gap-2">
            <button onClick={onClose} className="text-sm px-4 py-2 rounded-lg border border-line-axis hover:bg-plane transition">
              Cancel
            </button>
            <button
              onClick={handleConfirm}
              disabled={committing || preview.rows.length === 0 || !isAdmin}
              title={isAdmin ? undefined : "Requires Practice Administrator access"}
              className="flex items-center gap-2 text-sm px-4 py-2 rounded-lg bg-ink-primary text-white hover:bg-ink-primary/90 transition disabled:opacity-60"
            >
              <CheckCircle2 className="w-4 h-4" /> {committing ? "Importing..." : "Confirm Import"}
            </button>
          </div>
        </div>
      )}
    </Modal>
  );
}
