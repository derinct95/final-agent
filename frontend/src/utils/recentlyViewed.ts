import { useEffect, useState } from "react";
import type { PracticeType, RiskLevel } from "../types";

export interface RecentlyViewedEntry {
  id: string;
  name: string;
  specialty: string;
  performanceScore: number;
  riskLevel: RiskLevel;
  practiceType: PracticeType;
  viewedAt: number;
}

const SESSION_STORAGE_KEY = "ppd_session";
const STORAGE_PREFIX = "ppd_recently_viewed";
const MAX_ENTRIES = 15;
const EVENT_NAME = "clearview:recently-viewed-changed";

function getStorageKey(): string {
  try {
    const raw = localStorage.getItem(SESSION_STORAGE_KEY);
    if (!raw) return STORAGE_PREFIX;
    const session = JSON.parse(raw) as { email?: string };
    return session.email ? `${STORAGE_PREFIX}:${session.email}` : STORAGE_PREFIX;
  } catch {
    return STORAGE_PREFIX;
  }
}

export function getRecentlyViewed(): RecentlyViewedEntry[] {
  try {
    const raw = localStorage.getItem(getStorageKey());
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function addRecentlyViewed(entry: Omit<RecentlyViewedEntry, "viewedAt">): void {
  const existing = getRecentlyViewed().filter((e) => e.id !== entry.id);
  const next = [{ ...entry, viewedAt: Date.now() }, ...existing].slice(0, MAX_ENTRIES);
  localStorage.setItem(getStorageKey(), JSON.stringify(next));
  window.dispatchEvent(new Event(EVENT_NAME));
}

export function useRecentlyViewed(practiceType?: PracticeType): RecentlyViewedEntry[] {
  const [entries, setEntries] = useState<RecentlyViewedEntry[]>(() => getRecentlyViewed());

  useEffect(() => {
    function refresh() {
      setEntries(getRecentlyViewed());
    }
    window.addEventListener(EVENT_NAME, refresh);
    window.addEventListener("storage", refresh);
    return () => {
      window.removeEventListener(EVENT_NAME, refresh);
      window.removeEventListener("storage", refresh);
    };
  }, []);

  const filtered = practiceType ? entries.filter((e) => e.practiceType === practiceType) : entries;
  return filtered.slice(0, 6);
}
