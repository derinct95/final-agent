"""AI proactive insights: agent-driven (Claude Agent SDK, with tool use + policy
RAG) as the primary path, with a deterministic rule-based fallback only for
when the agent/API key is unavailable -- so the dashboard never breaks
offline, but the agent is the mechanism doing the actual analysis."""

import os

from app.agent.core import run_structured_task
from app.models import Insight, Provider

AGENTIC_SYSTEM_PROMPT = """You are an AI analyst embedded in a provider performance dashboard for Clearview \
Medical Group (100% synthetic data, no real PHI) that consolidates provider performance across clinical \
quality, productivity, patient engagement, documentation efficiency, revenue cycle, and patient satisfaction. \
Use your tools -- search_providers, compare_providers, get_provider_claims, summarize_department, \
search_policy_knowledge -- to investigate the current provider population before drawing conclusions. \
Identify the 4-8 most important, actionable insights across the whole provider population: prioritize \
revenue-impacting risks (rising denial rates, declining scores, compliance/coding risk) but also surface \
clinical-quality gaps (clinicalQualityScore), productivity concerns (patientVisitsMonthly), and patient-\
engagement gaps (patientPortalAdoptionRate) when they stand out -- do not limit yourself to revenue-cycle \
metrics alone. Call out standout top performers worth replicating. When a denial pattern is involved, cite \
the relevant policy via search_policy_knowledge. Use providerId "" and providerName "Organization-wide" for \
insights spanning multiple providers rather than one. Write narratives a revenue-cycle director would find \
credible and specific, referencing actual numbers you found via your tools -- do not guess or invent figures. \
Estimate confidenceScore as a 0-1 probability and estimatedFinancialImpact as a signed USD estimate (positive \
= opportunity/savings, negative = revenue at risk; use 0 if not estimable). Once your investigation is \
complete, call record_insights exactly once with your findings."""


def _rule_based_fallback(providers: list[Provider]) -> list[Insight]:
    insights = []
    sorted_by_score = sorted(providers, key=lambda p: p.performanceScore)

    worst = [p for p in sorted_by_score if p.riskLevel in ("critical", "high")][:3]
    for i, p in enumerate(worst):
        impact = round((p.peerAverageMetrics.denialRate - p.metrics.denialRate) * p.metrics.claimsVolumeMonthly * p.metrics.avgReimbursementPerClaim / 100 * 12, 0)
        insights.append(Insight(
            id=f"ins-rule-risk-{i}",
            providerId=p.id,
            providerName=p.name,
            severity="critical" if p.riskLevel == "critical" else "high",
            title=f"{p.name} showing elevated revenue risk",
            narrative=(
                f"{p.name} ({p.specialty}) has a performance score of {p.performanceScore}, "
                f"a denial rate of {p.metrics.denialRate}% versus a peer average of "
                f"{p.peerAverageMetrics.denialRate}%, and {p.metrics.daysInAR} days in AR."
            ),
            recommendedAction="Schedule a denial root-cause review and prioritize aged AR follow-up.",
            confidenceScore=0.72,
            estimatedFinancialImpact=impact,
            generatedBy="rule",
        ))

    top = max(providers, key=lambda p: p.performanceScore)
    insights.append(Insight(
        id="ins-rule-top",
        providerId=top.id,
        providerName=top.name,
        severity="info",
        title=f"{top.name} is the top performer this period",
        narrative=(
            f"{top.name} leads all providers with a score of {top.performanceScore}, "
            f"a clean claim rate of {top.metrics.cleanClaimRate}%, and a denial rate of only "
            f"{top.metrics.denialRate}%."
        ),
        recommendedAction="Document this provider's workflow as a best-practice template for peers.",
        confidenceScore=0.8,
        estimatedFinancialImpact=0,
        generatedBy="rule",
    ))

    declining = [p for p in providers if p.trend == "down"][:2]
    for i, p in enumerate(declining):
        insights.append(Insight(
            id=f"ins-rule-trend-{i}",
            providerId=p.id,
            providerName=p.name,
            severity="medium",
            title=f"{p.name} trending downward",
            narrative=f"{p.name}'s performance score has declined over the last 12 months, now at {p.performanceScore}.",
            recommendedAction="Review recent coding/documentation changes and schedule a check-in.",
            confidenceScore=0.6,
            estimatedFinancialImpact=0,
            generatedBy="rule",
        ))

    return insights


def _parse_agent_insights(data: dict) -> list[Insight] | None:
    insights = []
    for i, item in enumerate(data.get("insights", [])):
        try:
            insights.append(Insight(
                id=f"ins-agent-{i}",
                providerId=item["providerId"] or None,
                providerName=item["providerName"] or None,
                severity=item["severity"],
                title=item["title"],
                narrative=item["narrative"],
                recommendedAction=item["recommendedAction"],
                confidenceScore=item["confidenceScore"],
                estimatedFinancialImpact=item["estimatedFinancialImpact"],
                generatedBy="ai",
            ))
        except (KeyError, ValueError):
            continue
    return insights or None


async def _call_agent(providers: list[Provider]) -> list[Insight] | None:
    provider_ids = ", ".join(p.id for p in providers)
    prompt = (
        f"Investigate these {len(providers)} providers (ids: {provider_ids}) using your tools, then call "
        f"record_insights with 4-8 structured insights."
    )
    data = await run_structured_task(prompt, "record_insights", system_prompt=AGENTIC_SYSTEM_PROMPT)
    return _parse_agent_insights(data) if data else None


async def generate_insights(providers: list[Provider]) -> list[Insight]:
    if os.environ.get("ANTHROPIC_API_KEY"):
        agentic = await _call_agent(providers)
        if agentic:
            return agentic
    return _rule_based_fallback(providers)
