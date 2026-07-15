import { GitCompareArrows, X } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";
import { useCompare } from "../../context/CompareContext";

export default function CompareBar() {
  const { selectedIds, clear, max } = useCompare();
  const navigate = useNavigate();
  const location = useLocation();

  if (selectedIds.length === 0) return null;

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[9990] bg-ink-primary text-white rounded-full shadow-2xl pl-5 pr-2 py-2 flex items-center gap-3">
      <GitCompareArrows className="w-4 h-4" />
      <span className="text-sm">Compare ({selectedIds.length}/{max})</span>
      <button
        onClick={() => navigate(`/compare?ids=${selectedIds.join(",")}`, { state: { backgroundLocation: location } })}
        disabled={selectedIds.length < 2}
        className="text-sm font-medium bg-white text-ink-primary rounded-full px-3 py-1.5 disabled:opacity-40"
      >
        Compare
      </button>
      <button onClick={clear} className="w-7 h-7 flex items-center justify-center rounded-full hover:bg-white/10 transition">
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}
