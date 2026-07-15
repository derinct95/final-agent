# Compliance & Responsible AI Note

## PHI / PII Safety

- **100% synthetic data.** Every provider, claim, metric, and imported record is deterministically generated (`backend/app/data/seed.py`) or synthetically backfilled on import (`backend/app/services/import_detect.py`). There is no real patient or provider health information anywhere in this system — seeded, imported, or agent-generated.
- **Persistent disclaimer**, not a one-time notice: shown on the login screen, sidebar, and topbar at all times (`SyntheticDataBadge` component).
- **Upload handling**: import files (FHIR/HL7v2/CSV) are parsed entirely in memory, never written to disk (no path traversal risk), and capped at 5MB to prevent memory-exhaustion from an oversized upload.
- No approval workflow was needed for real sample data because **no real data is used or requested anywhere in this project.**

## Agent Sandboxing (the core safety control)

The Claude Agent SDK defaults to full Claude Code tool access (Bash, Read, Write, Edit, WebFetch, WebSearch, etc.). **This was tested and confirmed to be a real risk**: setting `allowed_tools` on `ClaudeAgentOptions` alone does *not* prevent execution of these built-in tools — a disallowed tool still executed in local testing.

**Mitigation**: a `PreToolUse` hook (`backend/app/agent/security.py`) that denies-by-default anything outside an explicit whitelist of 10 tools, by name. This was verified empirically: PowerShell, Read, Write, WebSearch, and ToolSearch were all confirmed blocked in testing, while the app's own tools executed normally. Without this hook, exposing the agent through a web endpoint would be a remote-code-execution vector.

**Role enforcement at the same layer**: the two write tools (`send_email`, `schedule_appointment`) are additionally denied for any caller whose role isn't `practice_admin` — enforced inside the same hook, not only at the REST layer, so a Clinical Analyst cannot use the chat agent to route around the REST-level restriction.

## Human-in-the-Loop Checkpoints

- **Email drafting is never auto-sent.** The agent's system prompt (`backend/app/agent/core.py`) explicitly instructs it to draft and share the subject/body first, and only call the `send_email` tool once the user has clearly confirmed — it does not send unprompted.
- **The `EmailComposeModal` and `AppointmentBookingModal`** always present the AI-drafted content in an editable form before the user clicks Send/Schedule — the human reviews and can edit or cancel every outbound communication.
- **Data import** requires an explicit "Confirm Import" click after previewing every row and any parsing warnings — nothing commits automatically from an uploaded file.
- **Action status changes** (marking a recommendation resolved) are a manual user click, even when the recommendation itself was AI-suggested.
- **Root-Cause Explainer and Insights are advisory only** — they surface a recommendation; no automated action is taken as a result of the agent's analysis.

## Injection & Application Security

- **No SQL injection surface**: all database access goes through the SQLAlchemy ORM — no raw or string-interpolated SQL anywhere in the backend.
- **No dangerous code execution**: no `subprocess`, `eval`, `exec`, `pickle`, or unsafe YAML loading anywhere in the backend (reviewed).
- **No XSS surface**: no `dangerouslySetInnerHTML` anywhere in the frontend. AI-generated chat replies render through `react-markdown` with HTML passthrough disabled — markdown syntax (bold, lists, headings) renders, but raw HTML/script tags cannot execute.
- **Dependency audit**: `pip-audit` reports zero known vulnerabilities in the Python dependencies. `npm audit` flags one moderate/high pair in `esbuild`/`vite` — a **dev-server-only** issue, not present in the built static output, and only relevant if the Vite dev server is exposed beyond localhost.

## Known Risks & Mitigations

| Risk | Mitigation / Status |
|---|---|
| Agent given uncontrolled tool access could execute arbitrary code | `PreToolUse` deny-by-default hook, empirically verified (see above) |
| Clinical Analyst role bypassing write restrictions via chat | Same security hook enforces role checks at the tool-execution layer, not just REST |
| Mock authentication (any email/password accepted) | Disclosed limitation — acceptable for a synthetic-data demo; not production-ready without a real credential store and session validation |
| No rate limiting on Claude-backed endpoints | Disclosed limitation — acceptable for hackathon-scale traffic; would need addressing (e.g. per-user request throttling) before real deployment |
| API cost exposure from unauthenticated/repeated agent calls | Model pinned to Claude Sonnet 5 (lower cost tier) specifically to bound per-call cost during development and demo; no public deployment of this instance |
| Hallucinated or incorrect AI-generated figures | Every agent system prompt explicitly instructs it to reference only numbers retrieved via its tools, never invent figures; rule-based fallback is fully deterministic if the agent path fails |
| FHIR/HL7v2 parsing is a best-effort subset, not certified | Disclosed limitation — explicitly documented as a pragmatic subset in README, not presented as certified health-IT interoperability |
