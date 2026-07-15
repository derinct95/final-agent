import os
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.agent.core import run_structured_task
from app.db import repo
from app.models import PracticeReviewAction, PracticeReviewFinding, PracticeReviewReport

AGENTIC_SYSTEM_PROMPT = """You are an AI practice-operations analyst for Clearview Medical Group, a fictional \
(100% synthetic, no real PHI) medical practice. You are given aggregate revenue-cycle statistics for a \
reporting period. Use your tools -- search_providers, compare_providers, summarize_department, \
search_policy_knowledge -- to investigate further where useful (e.g. drill into a specific decliner or the \
leading denial reason) before writing your review. Write 3-6 key findings and 3-5 priority actions a \
practice administrator would find credible and specific, referencing the actual numbers provided or found \
via your tools. Do not invent figures not present in the data. Once your investigation is complete, call \
record_practice_review exactly once with your findings."""


def _default_period_label(db: Session, period_type: str) -> str:
    providers = repo.list_providers(db)
    if not providers:
        return "Current period"
    full = repo.get_provider(db, providers[0].id)
    if period_type == "quarterly" and full.quarterlyHistory:
        return full.quarterlyHistory[-1].quarter
    if full.claimsHistory:
        latest_month = full.claimsHistory[-1].month
        if period_type == "weekly":
            return f"Week of {datetime.now(timezone.utc).date().isoformat()} (rolled up from {latest_month})"
        return latest_month
    return "Current period"


def aggregate_practice_stats(db: Session, period_type: str) -> dict:
    providers = repo.list_providers(db)
    total = len(providers)
    avg_score = round(sum(p.performanceScore for p in providers) / total, 1) if total else 0.0
    stuck_count = sum(1 for p in providers if p.stuckAtRiskQuarters >= repo.STUCK_AT_RISK_THRESHOLD)
    flagged_count = sum(1 for p in providers if p.flagged and not p.reviewed)

    total_revenue = total_denied = total_submitted = 0.0
    denial_tally: dict[str, int] = {}
    movers: list[tuple[str, float]] = []

    for s in providers:
        full = repo.get_provider(db, s.id)
        if full.claimsHistory:
            latest_month = full.claimsHistory[-1]
            total_revenue += latest_month.revenueCollected
            total_denied += latest_month.claimsDenied
            total_submitted += latest_month.claimsSubmitted
            for d in latest_month.denialReasons:
                denial_tally[d.reason] = denial_tally.get(d.reason, 0) + d.count
        if len(full.quarterlyHistory) >= 2:
            delta = full.quarterlyHistory[-1].performanceScore - full.quarterlyHistory[-2].performanceScore
            movers.append((s.name, round(delta, 1)))

    scale = 1.0
    if period_type == "weekly":
        scale = 1 / 4.33
    total_revenue *= scale
    total_denied = round(total_denied * scale)
    total_submitted = round(total_submitted * scale)
    denial_tally = {k: round(v * scale) for k, v in denial_tally.items()}

    movers.sort(key=lambda x: x[1])
    decliners = [m for m in movers if m[1] < -3][:3]
    improvers = sorted([m for m in movers if m[1] > 3], key=lambda x: -x[1])[:3]
    top_denial_reasons = sorted(denial_tally.items(), key=lambda x: -x[1])[:3]

    return {
        "totalProviders": total, "averageScore": avg_score, "stuckAtRiskCount": stuck_count,
        "flaggedCount": flagged_count, "totalRevenue": round(total_revenue, 2),
        "totalDenied": total_denied, "totalSubmitted": total_submitted,
        "topDenialReasons": top_denial_reasons, "decliners": decliners, "improvers": improvers,
    }


def _rule_based_review(stats: dict, period_type: str, label: str) -> PracticeReviewReport:
    findings = [
        PracticeReviewFinding(
            title="Practice-wide performance snapshot",
            narrative=f"Average performance score across {stats['totalProviders']} providers is {stats['averageScore']}. "
                      f"{stats['stuckAtRiskCount']} provider(s) have been stuck at high/critical risk for multiple consecutive quarters.",
            severity="high" if stats["stuckAtRiskCount"] > 0 else "info",
        ),
        PracticeReviewFinding(
            title="Claims volume and revenue",
            narrative=f"{stats['totalSubmitted']} claims submitted with {stats['totalDenied']} denied, "
                      f"collecting ${stats['totalRevenue']:,.0f} in revenue this {period_type} period.",
            severity="medium",
        ),
    ]
    if stats["topDenialReasons"]:
        top = stats["topDenialReasons"][0]
        findings.append(PracticeReviewFinding(
            title="Leading denial reason",
            narrative=f"\"{top[0]}\" is the most common denial reason org-wide, accounting for {top[1]} denied claims this period.",
            severity="medium",
        ))
    if stats["decliners"]:
        names = ", ".join(f"{n} ({d:+.1f})" for n, d in stats["decliners"])
        findings.append(PracticeReviewFinding(title="Providers trending down", narrative=names, severity="high"))
    if stats["improvers"]:
        names = ", ".join(f"{n} ({d:+.1f})" for n, d in stats["improvers"])
        findings.append(PracticeReviewFinding(title="Providers trending up", narrative=names, severity="info"))
    if stats["flaggedCount"] > 0:
        findings.append(PracticeReviewFinding(
            title="Providers awaiting review",
            narrative=f"{stats['flaggedCount']} flagged provider(s) have not yet been reviewed.",
            severity="medium",
        ))

    actions = [
        PracticeReviewAction(
            title="Review stuck-at-risk providers", priority="high",
            description="Schedule 1:1 check-ins with providers stuck at high/critical risk for 2+ consecutive quarters.",
        ) if stats["stuckAtRiskCount"] > 0 else None,
        PracticeReviewAction(
            title="Address the leading denial reason", priority="high",
            description=f"Investigate root cause of \"{stats['topDenialReasons'][0][0]}\" denials across the practice."
            if stats["topDenialReasons"] else "Investigate denial trends across the practice.",
        ),
        PracticeReviewAction(
            title="Clear the flagged-provider review queue", priority="medium",
            description=f"{stats['flaggedCount']} provider(s) are awaiting review — assign an owner to clear the queue.",
        ) if stats["flaggedCount"] > 0 else None,
    ]
    actions = [a for a in actions if a is not None]
    if not actions:
        actions = [PracticeReviewAction(title="Maintain current cadence", priority="low", description="No urgent priority actions this period — continue routine monitoring.")]

    return PracticeReviewReport(
        period=period_type, periodLabel=label, generatedAt=datetime.now(timezone.utc).isoformat(),
        keyFindings=findings, priorityActions=actions, generatedBy="rule",
    )


async def _call_agent_for_review(stats: dict, period_type: str, label: str) -> PracticeReviewReport | None:
    prompt = (
        f"Practice-wide stats for the {period_type} period ({label}): {stats}\n\n"
        f"Investigate further with your tools if useful, then call record_practice_review with 3-6 key "
        f"findings and 3-5 priority actions."
    )
    data = await run_structured_task(prompt, "record_practice_review", system_prompt=AGENTIC_SYSTEM_PROMPT)
    if not data:
        return None
    try:
        return PracticeReviewReport(
            period=period_type, periodLabel=label, generatedAt=datetime.now(timezone.utc).isoformat(),
            keyFindings=[PracticeReviewFinding(**f) for f in data["keyFindings"]],
            priorityActions=[PracticeReviewAction(**a) for a in data["priorityActions"]],
            generatedBy="ai",
        )
    except (KeyError, TypeError, ValueError):
        return None


async def generate_practice_review(db: Session, period_type: str, period_label: str | None = None) -> PracticeReviewReport:
    stats = aggregate_practice_stats(db, period_type)
    label = period_label or _default_period_label(db, period_type)
    if os.environ.get("ANTHROPIC_API_KEY"):
        agentic = await _call_agent_for_review(stats, period_type, label)
        if agentic:
            return agentic
    return _rule_based_review(stats, period_type, label)
