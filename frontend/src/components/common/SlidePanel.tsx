import { Maximize2, Minimize2, X } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";

interface SlidePanelProps {
  onClose: () => void;
  title?: ReactNode;
  headerActions?: ReactNode;
  children: ReactNode;
  storageKey?: string;
  defaultWidth?: number;
  minWidth?: number;
  resizable?: boolean;
  startMaximized?: boolean;
}

const MAX_WIDTH_VW = 92;

export default function SlidePanel({
  onClose, title, headerActions, children, storageKey, defaultWidth = 520,
  minWidth = 420, resizable = true, startMaximized = false,
}: SlidePanelProps) {
  const [width, setWidth] = useState<number>(() => {
    if (storageKey) {
      const stored = Number(localStorage.getItem(storageKey));
      if (stored && stored >= minWidth) return stored;
    }
    return defaultWidth;
  });
  const [isMaximized, setIsMaximized] = useState(startMaximized);
  const draggingRef = useRef(false);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  useEffect(() => {
    function onMove(e: MouseEvent) {
      if (!draggingRef.current) return;
      const maxPx = (window.innerWidth * MAX_WIDTH_VW) / 100;
      const next = Math.min(maxPx, Math.max(minWidth, window.innerWidth - e.clientX));
      setWidth(next);
    }
    function onUp() {
      if (!draggingRef.current) return;
      draggingRef.current = false;
      if (storageKey) localStorage.setItem(storageKey, String(width));
      document.body.style.cursor = "";
    }
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, [minWidth, storageKey, width]);

  const panelWidth = isMaximized ? `${MAX_WIDTH_VW}vw` : `${width}px`;

  return (
    <div className="fixed inset-0 z-[9997]">
      <div className="fixed inset-0 bg-ink-primary/30" onClick={onClose} />
      <div
        className="fixed right-0 top-0 h-screen bg-surface shadow-2xl flex flex-col"
        style={{ width: panelWidth, maxWidth: "100vw" }}
      >
        {resizable && !isMaximized && (
          <div
            onMouseDown={() => {
              draggingRef.current = true;
              document.body.style.cursor = "col-resize";
            }}
            className="absolute left-0 top-0 bottom-0 w-1.5 cursor-col-resize hover:bg-chart-1/30 transition"
          />
        )}
        <div className="min-h-16 shrink-0 flex items-center gap-3 px-5 py-2.5 border-b border-line-grid">
          <div className="flex-1 min-w-[140px]">{title}</div>
          {headerActions && (
            <div className="flex items-center gap-2 min-w-0 overflow-x-auto">{headerActions}</div>
          )}
          <div className="flex items-center gap-1 shrink-0">
            <button
              type="button"
              onClick={() => setIsMaximized((v) => !v)}
              className="w-8 h-8 flex items-center justify-center rounded-lg text-ink-muted hover:bg-plane hover:text-ink-primary transition"
              title={isMaximized ? "Restore" : "Maximize"}
            >
              {isMaximized ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="w-8 h-8 flex items-center justify-center rounded-lg text-ink-muted hover:bg-plane hover:text-ink-primary transition"
              title="Close"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto">{children}</div>
      </div>
    </div>
  );
}
