# Architecture & Key Highlights

## What it is

An AI-assisted analytics dashboard for a fictional healthcare practice (Clearview Medical Group) that consolidates provider performance across **6 categories** — clinical quality, productivity, patient engagement, documentation efficiency, revenue cycle, and patient satisfaction — into one unified, agent-powered view. All data is 100% synthetic (no real PHI).

---

## 1. Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React + TypeScript + Vite + Tailwind CSS |
| Backend | FastAPI + Python + SQLAlchemy + SQLite |
| Agent Core | **Claude Agent SDK** (the same SDK that powers Claude Code) |
| AI Model | Claude Sonnet 5 |
| Reports | ReportLab (PDF), pandas (CSV) |

---

## 2. Request Flow

```
┌──────────────────┐     ┌──────────────────────┐
│  Web Dashboard    │     │   CLI (agent_cli.py)  │
│  (React + Vite)   │     └──────────┬───────────┘
└────────┬──────────┘                │
         │ REST (fetch)              │ direct
         ▼                           ▼
┌──────────────────┐        ┌─────────────────────┐
│  FastAPI Backend  │◄──────►│   Agent Core          │
│  (routers, repo)  │        │   (Claude Agent SDK)  │
└────────┬──────────┘        └──────────┬───────────┘
         │                              │
         ▼                              ▼
┌──────────────────┐        ┌─────────────────────┐
│   SQLite DB       │        │  10 Whitelisted Tools │
│ (providers, claims,│        │  + PreToolUse Security │
│  emails, appts)    │        │  Hook (deny-by-default)│
└──────────────────┘        └──────────┬───────────┘
                                        ▼
                              ┌─────────────────────┐
                              │   Claude Sonnet 5      │
                              │  + Policy RAG search   │
                              └─────────────────────┘
```

**Key architectural decision:** every AI feature (chat, Insights, Practice Review, Root-Cause Explainer, email/agenda drafting) goes through this same agent core, not scattered single-shot API calls. Each has a **2-tier fallback**: Agent (primary, uses tools + RAG) → Rule-based (deterministic, only if the agent/API key is unavailable). There is no middle "single-shot Claude API" tier — that would dilute the "this dashboard is agent-driven" story.

---

## 3. The Agent — Why This Is a Real Agent, Not Just an LLM Call

- **`backend/app/agent/core.py`** — builds `ClaudeAgentOptions` and calls `query()`, which spins up a real Claude Code CLI subprocess and streams a multi-turn conversation.
- **`backend/app/agent/tools.py`** — 10 custom tools registered as an in-process MCP server:
  - Read: `search_providers` (with a `stuckAtRiskOnly` filter), `get_provider_claims`, `compare_providers`, `summarize_department`, `search_policy_knowledge` (TF-IDF RAG over synthetic payer policy)
  - Write: `send_email`, `schedule_appointment`
  - Output-only: `record_insights`, `record_practice_review`, `record_root_cause`, `record_email_draft`
- **The ReAct loop**: the model reasons → calls a tool → observes the result → repeats (up to `max_turns`) → final answer. This is the `async for message in query(...)` iteration in `core.py` — each pass can produce an `AssistantMessage` containing a `ToolUseBlock` (act), whose result feeds back as the next message (observe).
- **`run_structured_task()`** — a reusable helper that lets any headless task (Insights, Practice Review, Root-Cause, drafting) instruct the agent to investigate with tools, then call a `record_*` tool as its final step, capturing that as typed output.

### Security

`backend/app/agent/security.py` — a `PreToolUse` hook that **denies by default** anything outside the whitelist. Empirically confirmed: `allowed_tools` alone does NOT stop Claude Code's built-in tools (Bash, Read, Write, etc.) from executing — this hook is the actual enforcement boundary.

---

## 4. Role-Based Access Control (RBAC)

Two roles: **Practice Administrator** (full access) and **Clinical Analyst** (read-only).

- **Backend**: `auth_deps.py`'s `require_admin` dependency gates 4 write routes (send email, schedule appointment, resolve actions, commit imports) — returns `403` for non-admins, secure-by-default.
- **Agent-side**: the same restriction is enforced inside the `PreToolUse` hook, so a Clinical Analyst can't bypass the REST gate by asking the chatbot to send an email instead.
- **Frontend**: write buttons are disabled with tooltips for analysts; `X-User-Role` sent with every request.
- **Sign Up**: a new user explicitly picks their role.

---

## 5. Per-User Personalization

- **Recently Viewed**: scoped to `ppd_recently_viewed:{email}` in localStorage — each login sees only their own history.
- **Recent Activity** (emails/appointments): backend filters by `X-User-Email`, so two different logged-in users each see only what *they* did — while all core provider/practice data stays fully shared (it's a real practice-wide dashboard, not siloed).

---

## 6. Data Model — All 6 Categories, Genuinely Backed

| Category | Metric(s) |
|---|---|
| Clinical Quality | `clinicalQualityScore` |
| Productivity | `patientVisitsMonthly` |
| Patient Engagement | `patientPortalAdoptionRate` |
| Documentation Efficiency | `documentationAccuracy` ⚠️ (accuracy, not time) |
| Revenue Cycle | `cleanClaimRate`, `denialRate`, `daysInAR`, `firstPassResolutionRate`, `priorAuthApprovalRate`, `netCollectionRate`, `avgReimbursementPerClaim`, `claimsVolumeMonthly` |
| Patient Satisfaction | `patientSatisfactionScore` |

Every provider carries `peerAverageMetrics` alongside its own `metrics` for department/practice benchmarking, and `performanceScore` + `riskLevel` + `trend` for composite scoring, risk classification, and trend indicators.

---

## 7. Key Features

| Feature | What it does |
|---|---|
| Dashboard | KPI tiles, AI Proactive Insights (agent-driven), sortable/filterable provider table |
| Agent Refresh | One-click button that re-runs the agent for Insights + refreshes all dashboard data |
| Compare Mode | Side-by-side up to 4 providers, radar chart, shareable URL |
| Provider Detail | Overview / Metrics (with popups + trend charts) / Claims History / Actions |
| Root-Cause Explainer | Agent investigates a flagged provider — compares to peers, pulls claims, cites policy |
| Chat Widget/CLI | Full conversational agent access, safe markdown rendering, colored tool-use chips |
| AI Practice Review | Weekly/monthly/quarterly agent-generated findings + priority actions |
| Data Import | FHIR/HL7/CSV auto-detected, previewed, then committed |
| CSV/PDF Export | Full/flagged roster, provider reports, comparison reports |

---

## 8. Known, Disclosed Gaps

- Documentation efficiency is an accuracy metric, not a time/throughput measure.
- This is one self-contained synthetic dataset, not a literal consolidation layer over pre-existing P4P/MIPS/EHR systems (see `DEFINITION_OF_DONE.md` for the full breakdown).
- Mock authentication, no rate limiting, simulated (not real) email delivery — acceptable for a hackathon demo; see `COMPLIANCE.md`.

---

## 9. Related Documents

- `README.md` — setup, prerequisites, commands, troubleshooting
- `PROMPTS.md` — every system prompt used by the agent, consolidated
- `DEFINITION_OF_DONE.md` — mapped checklist with evidence
- `COMPLIANCE.md` — responsible AI, human-in-the-loop, PHI safety, risks
- `DEMO_SCRIPT.md` — the recorded walkthrough, step by step
