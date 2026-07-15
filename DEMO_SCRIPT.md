# Demo Script — Clearview Provider Performance Agent

This is the walkthrough recorded in `Clearview_Demo_Walkthrough.mp4`. Each step is marked **FREE** (deterministic, no LLM call) or **AGENT** (a real Claude Sonnet 5 call via the Agent SDK — costs a small amount of API credit). The whole demo makes exactly **5 real agent calls** total, by design, to stay budget-conscious.

| # | Step | Cost | What it shows |
|---|---|---|---|
| 1 | Land on login screen | FREE | Persistent synthetic-data disclaimer, demo account cards |
| 2 | **Sign Up** as a new user, choose "Practice Administrator" | FREE | Real-role signup flow (not just the two canned demo accounts) |
| 3 | First-visit guided tour plays automatically | FREE | Onboarding UX — KPIs, AI Insights, Recently Viewed, Quick Nav, filters, Compare, Open Actions, Export/Import, Help menu |
| 4 | Dashboard: KPI tiles, provider table | FREE | Composite score, risk level, trend — all providers in one view |
| 5 | Click **Agent Refresh** | **AGENT (1)** | The agent investigates the provider population with its tools and returns severity-colored Proactive Insights |
| 6 | Flagged-for-Review tab, then back to All Providers | FREE | Risk-area identification |
| 7 | Toggle Compare on 2 providers, open Compare view | FREE | Side-by-side scores, metrics table, radar overlay, benchmarking |
| 8 | Open a provider's detail panel → Metrics tab → click a metric card | FREE | Popup with current-vs-peer value, benchmark chart, trend chart across all 14 metrics (all 6 categories) |
| 9 | Claims History tab | FREE | Paginated real claims, denial reasons |
| 10 | Click **Explain Root Cause** | **AGENT (2)** | The agent compares the provider to peers, pulls their claims/denial pattern, cites synthetic payer policy via RAG, proposes remediation |
| 11 | Close panel, open the **chat widget** | FREE (open) | — |
| 12 | Ask the agent a question | **AGENT (3)** | Full ReAct loop: reasons → calls tools → answers, rendered with safe markdown + colored tool-use chips |
| 13 | Navigate to **Practice Review**, generate a report | **AGENT (4)** | Multi-finding practice-wide review + priority actions |
| 14 | Open Email compose on a provider, click **AI Draft** | **AGENT (5)** | Agent drafts a policy-aware email; human reviews before sending |
| 15 | Click Send | FREE | Human-in-the-loop: nothing sends without this explicit click; logged to in-app outbox, not real SMTP |
| 16 | Data Import wizard: preview a CSV, confirm import | FREE | FHIR/HL7v2/CSV auto-detection, preview-before-commit |
| 17 | Export CSV / download a PDF report | FREE | Deterministic report generation |
| 18 | Log out, sign in as **Clinical Analyst** | FREE | RBAC: write buttons (Email/Schedule/Import confirm) now disabled with tooltips |
| 19 | Attempt a write action as Analyst (shown disabled) | FREE | Confirms role enforcement is real, not cosmetic (backend returns 403 for the same action) |

## Reproducing this yourself

1. Follow `README.md` to get both servers running with a valid `ANTHROPIC_API_KEY`.
2. Open http://localhost:5173 and follow the steps above in order.
3. Steps marked **AGENT** will take 3-10 seconds each and use a small amount of API credit — everything else is instant and free.

## Key decisions reflected in this script

- **Agent-first, not chat-only**: 4 of the 5 paid interactions are dashboard features (Insights, Root-Cause, Practice Review, Email Draft), not just the chatbot — demonstrating the agent is the mechanism behind the whole product, not a bolt-on widget.
- **Human-in-the-loop is shown, not just claimed**: step 15 explicitly shows the send action requiring a manual click after the AI draft.
- **RBAC is demonstrated working, not just described**: steps 18-19 show the same restriction from both the Practice Administrator and Clinical Analyst perspective.
