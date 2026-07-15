import { CalendarCheck, Mail, Radio } from "lucide-react";
import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api } from "../../api/client";
import type { EmailMessageRecord } from "../../types";
import { relativeTime } from "../../utils/relativeTime";
import EmailDetailModal from "../communications/EmailDetailModal";

interface ActivityItem {
  key: string;
  icon: typeof Mail;
  text: string;
  at: string;
  providerId?: string;
  email?: EmailMessageRecord;
}

interface RecentActivityFeedProps {
  providerIds: string[];
}

export default function RecentActivityFeed({ providerIds }: RecentActivityFeedProps) {
  const [items, setItems] = useState<ActivityItem[]>([]);
  const [openEmail, setOpenEmail] = useState<EmailMessageRecord | null>(null);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const idSet = new Set(providerIds);
    Promise.all([api.listEmails(), api.listAppointments()]).then(([emails, appointments]) => {
      const emailItems: ActivityItem[] = emails
        .filter((e) => e.providerIds.some((id) => idSet.has(id)))
        .map((e) => ({
          key: `email-${e.id}`,
          icon: Mail,
          text: `Email sent: "${e.subject}" to ${e.recipients.length} recipient(s)`,
          at: e.sentAt,
          providerId: e.providerIds[0],
          email: e,
        }));
      const apptItems: ActivityItem[] = appointments
        .filter((a) => a.providerIds.some((id) => idSet.has(id)))
        .map((a) => ({
          key: `appt-${a.id}`,
          icon: CalendarCheck,
          text: `Meeting scheduled: "${a.topic}" with ${a.providerNames.join(", ") || "provider(s)"}`,
          at: a.createdAt,
          providerId: a.providerIds[0],
        }));
      const merged = [...emailItems, ...apptItems]
        .sort((a, b) => new Date(b.at).getTime() - new Date(a.at).getTime())
        .slice(0, 5);
      setItems(merged);
    });
  }, [providerIds.join(",")]);

  if (items.length === 0) return null;

  return (
    <section className="bg-surface border border-ink-primary/10 rounded-2xl p-4">
      <div className="flex items-center gap-2 mb-3">
        <Radio className="w-4 h-4 text-ink-muted" />
        <h2 className="text-sm font-semibold text-ink-primary">Recent Activity</h2>
      </div>
      <ul className="space-y-2">
        {items.map((item) => (
          <li key={item.key}>
            <button
              type="button"
              onClick={() =>
                item.email
                  ? setOpenEmail(item.email)
                  : item.providerId && navigate(`/providers/${item.providerId}`, { state: { backgroundLocation: location } })
              }
              className="w-full flex items-start gap-2 text-left px-2 py-1.5 rounded-lg hover:bg-plane/60 transition"
            >
              <item.icon className="w-3.5 h-3.5 mt-0.5 text-chart-1 shrink-0" />
              <span className="text-xs text-ink-secondary flex-1 min-w-0">{item.text}</span>
              <span className="text-xs text-ink-muted shrink-0">{relativeTime(item.at)}</span>
            </button>
          </li>
        ))}
      </ul>
      <EmailDetailModal email={openEmail} onClose={() => setOpenEmail(null)} />
    </section>
  );
}
