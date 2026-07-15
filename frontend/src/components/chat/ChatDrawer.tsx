import {
  Building2,
  CalendarPlus,
  FileText,
  GitCompareArrows,
  Mail,
  Search,
  Send,
  Sparkles,
  Wrench,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import SlidePanel from "../common/SlidePanel";
import { useChat } from "../../context/ChatContext";

const TOOL_CONFIG: Record<string, { icon: typeof Search; color: string; label: string }> = {
  search_providers: { icon: Search, color: "#2a78d6", label: "Search providers" },
  get_provider_claims: { icon: FileText, color: "#2a78d6", label: "Claims lookup" },
  compare_providers: { icon: GitCompareArrows, color: "#2a78d6", label: "Compare" },
  summarize_department: { icon: Building2, color: "#2a78d6", label: "Department summary" },
  search_policy_knowledge: { icon: FileText, color: "#7b5ce0", label: "Policy lookup" },
  send_email: { icon: Mail, color: "#d99a2b", label: "Email sent" },
  schedule_appointment: { icon: CalendarPlus, color: "#d99a2b", label: "Meeting scheduled" },
};

function ToolChip({ tool }: { tool: string }) {
  const config = TOOL_CONFIG[tool] ?? { icon: Wrench, color: "#8a8a8a", label: tool };
  const Icon = config.icon;
  return (
    <span
      className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full"
      style={{ backgroundColor: `${config.color}1a`, color: config.color }}
    >
      <Icon className="w-3 h-3" />
      {config.label}
    </span>
  );
}

const MARKDOWN_COMPONENTS = {
  p: ({ children }: { children?: React.ReactNode }) => <p className="leading-relaxed">{children}</p>,
  strong: ({ children }: { children?: React.ReactNode }) => <strong className="font-semibold text-ink-primary">{children}</strong>,
  ul: ({ children }: { children?: React.ReactNode }) => <ul className="list-disc list-inside space-y-0.5 my-1">{children}</ul>,
  ol: ({ children }: { children?: React.ReactNode }) => <ol className="list-decimal list-inside space-y-0.5 my-1">{children}</ol>,
  li: ({ children }: { children?: React.ReactNode }) => <li>{children}</li>,
  h1: ({ children }: { children?: React.ReactNode }) => <h1 className="text-sm font-semibold mt-1 mb-0.5">{children}</h1>,
  h2: ({ children }: { children?: React.ReactNode }) => <h2 className="text-sm font-semibold mt-1 mb-0.5">{children}</h2>,
  h3: ({ children }: { children?: React.ReactNode }) => <h3 className="text-sm font-semibold mt-1 mb-0.5">{children}</h3>,
  code: ({ children }: { children?: React.ReactNode }) => (
    <code className="bg-ink-primary/10 rounded px-1 py-0.5 text-xs font-mono">{children}</code>
  ),
  table: ({ children }: { children?: React.ReactNode }) => (
    <div className="overflow-x-auto my-1">
      <table className="text-xs border-collapse">{children}</table>
    </div>
  ),
  th: ({ children }: { children?: React.ReactNode }) => (
    <th className="border border-line-grid px-2 py-1 text-left bg-plane font-medium">{children}</th>
  ),
  td: ({ children }: { children?: React.ReactNode }) => <td className="border border-line-grid px-2 py-1">{children}</td>,
};

export default function ChatDrawer() {
  const { close, messages, sending, available, sendMessage } = useChat();
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, sending]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text) return;
    setInput("");
    await sendMessage(text);
  }

  return (
    <SlidePanel
      onClose={close}
      resizable={false}
      defaultWidth={420}
      title={
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-chart-5" />
          <h2 className="text-sm font-semibold text-ink-primary">Clearview AI Assistant</h2>
        </div>
      }
    >
      <div className="flex flex-col h-full">
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3">
          {messages.length === 0 && (
            <p className="text-sm text-ink-muted">
              Ask me to search providers, pull claims, compare providers, summarize a department, or explain a denial
              reason against synthetic payer policy.
            </p>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[85%] rounded-xl px-3 py-2 text-sm ${
                  m.role === "user"
                    ? "bg-chart-1 text-white"
                    : "bg-plane border-l-4 border border-line-grid text-ink-primary"
                }`}
                style={m.role === "assistant" ? { borderLeftColor: "#7b5ce0" } : undefined}
              >
                {m.role === "assistant" ? (
                  <div className="flex items-start gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 shrink-0 mt-0.5 text-chart-5" />
                    <div className="min-w-0 flex-1">
                      <ReactMarkdown components={MARKDOWN_COMPONENTS}>{m.content}</ReactMarkdown>
                    </div>
                  </div>
                ) : (
                  <p className="whitespace-pre-wrap">{m.content}</p>
                )}
                {m.toolsUsed && m.toolsUsed.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2 pt-2 border-t border-line-grid/60">
                    {m.toolsUsed.map((tool, ti) => (
                      <ToolChip key={ti} tool={tool} />
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          {sending && (
            <div className="flex justify-start">
              <div className="bg-plane border border-line-grid rounded-xl px-3 py-2 text-sm text-ink-muted animate-pulse">
                Thinking...
              </div>
            </div>
          )}
          {!available && (
            <p className="text-xs text-risk-high">AI chat requires an ANTHROPIC_API_KEY on the server.</p>
          )}
        </div>

        <form onSubmit={handleSubmit} className="border-t border-line-grid p-3 flex items-center gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about providers, claims, or denials..."
            className="flex-1 text-sm border border-line-axis rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-chart-1/40"
          />
          <button
            type="submit"
            disabled={sending || !input.trim()}
            className="w-9 h-9 flex items-center justify-center rounded-lg bg-ink-primary text-white disabled:opacity-40"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </SlidePanel>
  );
}
