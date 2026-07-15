# Clearview Medical Group — Provider Performance Agent

A healthcare revenue-cycle-management (RCM) analytics **agent** for a fictional practice, **Clearview Medical Group**, built on the **Claude Agent SDK** (the same SDK that powers Claude Code). It consolidates provider performance across six categories — clinical quality, productivity, patient engagement, documentation efficiency, revenue cycle, and patient satisfaction — into one agent-driven dashboard.

**All data is 100% synthetic — no real patient or provider PHI is used anywhere in this application** (see the persistent disclaimer on the login screen, sidebar, and topbar, and `COMPLIANCE.md` for the full safety note).

Stack: React + TypeScript + Vite + Tailwind (dashboard UI), FastAPI + Python + SQLite (backend), **Claude Agent SDK** running **Claude Sonnet 5** (the agent core — shared by the web app, the chat widget, and a standalone CLI).

---

## Prerequisites

| Requirement | Why | Check |
|---|---|---|
| Python 3.11+ | Backend | `python --version` |
| Node.js **22+** | Claude Code CLI requires it (below 22 installs but silently misbehaves) | `node --version` |
| Claude Code CLI | The Python `claude_agent_sdk` shells out to this binary | `npm install -g @anthropic-ai/claude-code`, then `claude --version` |
| `ANTHROPIC_API_KEY` | Powers every AI feature (chat, insights, practice review, root-cause, drafting) | See below |

Without the API key: every AI feature automatically falls back to a deterministic rule-based generator — **nothing breaks**, the dashboard, reports, and CSV/FHIR/HL7 import work fully offline.

---

## Setup

**Backend** (already has a `.venv` created and dependencies installed):

```
cd backend
copy .env.example .env
# edit .env and paste your ANTHROPIC_API_KEY=sk-ant-...
.venv\Scripts\python -m uvicorn app.main:app --port 8000
```

> **Do NOT add `--reload`.** Confirmed during development: uvicorn's `--reload` flag spawns the app in a separate reloader/worker process pair that does not reliably inherit the environment on Windows — the agent fails to launch the Claude Code CLI subprocess with an opaque `Failed to start Claude Code` error. Running as a single process (no `--reload`) is required for the agent to work. Restart the process manually after code changes.

Data persists in `backend/data/clearview.db` — seeded with 20 deterministic synthetic providers the first time the DB is empty, then persisted (imports/edits/emails/appointments) across restarts. **Delete the file and restart to reseed fresh** — required after any schema change (adding a column, etc.), since there is no migration framework in this project by design (hackathon-scale, not production).

**Frontend** (already has `node_modules` installed):

```
cd frontend
npm run dev
```

Open **http://localhost:5173** — sign in with one of the two demo account cards (Practice Administrator / Clinical Analyst), or use **Sign Up** to create an account and pick your own role, or expand "Use a different account" for free-form mock login.

---

## Expected runtime & cost

- **Startup**: backend ready in ~2s, frontend dev server in ~1s. First page load seeds the DB (~1-2s, one-time).
- **Rule-based features** (no API key, or as a fallback): instant, deterministic, $0.
- **Agent-driven features** (chat, Insights, Practice Review, Root-Cause Explainer, email/agenda drafting) — each is a real multi-turn Claude Sonnet 5 call via the Agent SDK, typically **3-10 seconds and a few cents** per interaction, depending on how many tool calls the agent makes. This is inherent to the Agent SDK spinning up a full Claude Code session per turn — noticeably slower/costlier than a single-shot completion, but with real tool-use and RAG behind it.
- Model is pinned to **`claude-sonnet-5`** (`backend/app/agent/core.py`) specifically to keep per-call cost low for demo/hackathon budgets — switch the `MODEL` constant if a different tier is needed.

---

## The Agent — one core, two surfaces, agent-first everywhere

`backend/app/agent/` is the single agent definition (system prompt, tools, security lockdown), shared by:

1. **The web chat widget** (floating button, bottom-right of the dashboard) — `POST /api/chat`.
2. **A standalone CLI agent**:
   ```
   cd backend
   .venv\Scripts\python agent_cli.py                                          # interactive REPL
   .venv\Scripts\python agent_cli.py "which providers are stuck at high risk?"  # one-shot
   ```

**Every AI feature routes through this same agent core**, not scattered single-shot API calls — chat, **AI Proactive Insights**, **AI Practice Review**, the **Root-Cause Explainer**, and **email/agenda drafting** all use `run_structured_task()` (`backend/app/agent/core.py`), which instructs the agent to investigate with its tools, then call a `record_*` tool with its structured findings. Each has a 2-tier fallback: **Agent (primary) → rule-based (only if the agent/key is unavailable)** — there is no middle "single-shot API" tier.

**Tools available to the agent:**
- `search_providers` (supports a `stuckAtRiskOnly` filter), `get_provider_claims`, `compare_providers`, `summarize_department`
- `search_policy_knowledge` — a small hand-rolled RAG (TF-IDF retrieval over a synthetic payer-policy corpus, no external embeddings dependency)
- `send_email`, `schedule_appointment` — write actions, gated to the Practice Administrator role (see RBAC below)
- `record_insights`, `record_practice_review`, `record_root_cause`, `record_email_draft` — output-only tools the agent calls once it's done investigating, used to capture structured results from the agent's ReAct loop

**Security note (found and fixed during development, worth knowing):** the Claude Agent SDK defaults to full Claude Code tool access (Bash/Read/Write/Edit/WebSearch/etc.) — `allowed_tools` alone does **not** restrict execution (confirmed empirically: a disallowed tool still executed in testing). The actual enforcement is a `PreToolUse` hook (`app/agent/security.py`) that denies anything outside the whitelisted tools by name, and additionally denies the two write tools unless the caller's role is `practice_admin`. This is what makes it safe to expose the agent through a web endpoint.

---

## Roles & Access Control

Two roles, chosen at Sign Up or via the demo account cards:

- **Practice Administrator** — full access, including write actions (send email, schedule appointment, resolve actions, commit data imports).
- **Clinical Analyst** — read-only. Write actions are disabled in the UI (with a tooltip) and rejected server-side with `403` — including via the chat agent, which is blocked by the same `PreToolUse` hook, not just the REST layer.

"Recently Viewed" and "Recent Activity" are personal per logged-in user; all core provider/practice data is shared practice-wide.

---

## What's in the demo

- **Login & onboarding**: demo-account cards, Sign Up with role selection, persistent synthetic-data-only disclaimer, first-visit guided tour, Ctrl+K command palette.
- **Main dashboard**: gradient hero header with an **Agent Refresh** button (re-runs the agent for Insights + refreshes all dashboard data in one click), colorful KPI tiles, an **AI Proactive Insights** panel (agent-driven, severity-colored cards, never just min/max), a searchable/sortable provider table with a Flagged-for-Review tab, and a **Stuck-at-Risk** badge (2+ consecutive quarters at high/critical risk).
- **Compare mode**: up to 4 providers side by side — scores, metrics table, radar overlay — as a shareable `/compare?ids=...` URL, with group email/scheduling actions.
- **Provider detail panel**: resizable/maximizable slide-over with Overview / Metrics / Claims History / Actions tabs, an **Explain Root Cause** button (agent investigates the provider, compares to peers, cites policy, proposes remediation), and Email / Schedule / Download Report actions.
- **AI chatbot**: full conversational agent access; replies render with safe markdown (bold, lists, headings) and colored chips showing which tools were used.
- **AI Practice Review** (`/practice-review`): weekly/monthly/quarterly agent-generated findings + priority actions, downloadable as PDF/CSV.
- **Data import wizard**: FHIR/HL7v2/CSV, auto-detected, previewed, committed on confirmation (admin-only).
- **CSV/PDF export** of the full or flagged-only table, provider reports, and comparisons.

Metrics span all 6 categories: `cleanClaimRate`, `denialRate`, `daysInAR`, `firstPassResolutionRate`, `codingAccuracy`, `priorAuthApprovalRate`, `netCollectionRate`, `avgReimbursementPerClaim`, `claimsVolumeMonthly`, `documentationAccuracy`, `patientSatisfactionScore`, `clinicalQualityScore`, `patientVisitsMonthly`, `patientPortalAdoptionRate`.

---

## Known limitations (disclosed, not hidden)

- Login is intentionally mock authentication — any email/password is accepted; there is no real credential store or session validation. Appropriate for a synthetic-data demo, not production-ready as-is.
- No rate limiting on the Claude-backed endpoints — acceptable for a hackathon demo's traffic volume.
- Email sending is simulated/logged (`email_messages` table), not real SMTP.
- FHIR/HL7v2 parsing is a pragmatic, best-effort subset, not a certified health-IT interoperability implementation.
- Individual claim records are a representative sample (~30-50 per provider across 8 quarters); monthly aggregates are independently generated, not strictly derived 1:1 from the sample.
- No formal DB migration framework — schema changes require deleting `clearview.db` and reseeding (synthetic data only, so no real data loss risk).

See `COMPLIANCE.md` for the full responsible-AI and risk/mitigation note.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Chat replies "AI agent is unavailable... Failed to start Claude Code" | Backend was started with `--reload` | Restart **without** `--reload` |
| Same error, and `claude --version` works fine in your terminal | `claude` CLI not on PATH for the backend's process specifically | Confirm `npm install -g @anthropic-ai/claude-code` succeeded; restart the backend from a terminal where `claude --version` works |
| Node-related install warnings from `npm install -g @anthropic-ai/claude-code` | Node version below 22 | Upgrade Node to 22+ (the CLI installs on older versions but the agent will misbehave) |
| Insights/Practice Review/Root-Cause always show "Rule-based analysis (offline mode)" | No `ANTHROPIC_API_KEY` set, or it's invalid | Check `backend/.env`, confirm the key doesn't have typos (keys start with `sk-ant-api03-`, all lowercase) |
| `no such column` SQLite error after pulling new code | DB schema changed (new metric/column added) | Stop the backend, delete `backend/data/clearview.db`, restart to reseed |
| Frontend shows stale data after a backend restart | Browser cache of an old session | Hard-refresh; `ppd_session`/`ppd_recently_viewed` are per-user in localStorage, unaffected by backend restarts |

---

## Security & responsible AI

See `COMPLIANCE.md` for the full write-up (PHI safety, agent sandboxing, injection/XSS surface, dependency audit, human-in-the-loop checkpoints, known risks and mitigations). Summary: 100% synthetic data, deny-by-default tool sandboxing verified empirically, SQLAlchemy ORM only (no raw SQL), no `dangerouslySetInnerHTML`, `pip-audit` clean.
