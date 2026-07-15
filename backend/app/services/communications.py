"""Email/agenda drafting -- agent-driven (Claude Agent SDK) as the primary
path so it can cite relevant payer policy via search_policy_knowledge when
the topic is denial-related, with a deterministic rule-based fallback only
for when the agent/API key is unavailable."""

import os

from app.agent.core import run_structured_task
from app.models import Provider

AGENTIC_SYSTEM_PROMPT = """You are drafting a professional email on behalf of Clearview Medical Group's \
practice administration to one or more providers, about a revenue-cycle-management performance topic. All \
data is synthetic. Reference concrete figures from the provided provider data. If the topic relates to a \
denial reason or payer policy, use search_policy_knowledge to cite the relevant (synthetic) policy guidance \
in the email. Be respectful, specific, and concise -- a real practice administrator would send this as \
written. Once drafted, call record_email_draft exactly once with the subject and body."""


def _rule_based_email(providers: list[Provider], topic: str) -> tuple[str, str]:
    names = ", ".join(p.name for p in providers)
    subject = f"Performance discussion: {topic}"
    lines = [f"Dear {names},", "", f"I'd like to connect regarding: {topic}.", ""]
    for p in providers:
        lines.append(
            f"- {p.name}: performance score {p.performanceScore} ({p.riskLevel} risk), "
            f"denial rate {p.metrics.denialRate}%, days in AR {p.metrics.daysInAR}."
        )
    lines += ["", "Please let me know a convenient time to discuss.", "", "Best regards,", "Clearview Medical Group"]
    return subject, "\n".join(lines)


async def _call_agent_for_draft(providers: list[Provider], topic: str) -> tuple[str, str] | None:
    provider_summary = "\n".join(
        f"{p.name} ({p.specialty}): score={p.performanceScore}, risk={p.riskLevel}, "
        f"denialRate={p.metrics.denialRate}%, daysInAR={p.metrics.daysInAR}, "
        f"stuckAtRiskQuarters={p.stuckAtRiskQuarters}"
        for p in providers
    )
    prompt = f"Topic: {topic}\n\nProviders:\n{provider_summary}"
    data = await run_structured_task(prompt, "record_email_draft", system_prompt=AGENTIC_SYSTEM_PROMPT)
    if not data:
        return None
    try:
        return data["subject"], data["body"]
    except (KeyError, TypeError):
        return None


async def draft_email(providers: list[Provider], topic: str) -> tuple[str, str, str]:
    if os.environ.get("ANTHROPIC_API_KEY"):
        agentic = await _call_agent_for_draft(providers, topic)
        if agentic:
            return agentic[0], agentic[1], "ai"
    subject, body = _rule_based_email(providers, topic)
    return subject, body, "rule"
