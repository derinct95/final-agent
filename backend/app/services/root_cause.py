"""Root-cause explainer: agent-driven investigation of why a specific
provider is flagged/at-risk, with a deterministic rule-based fallback so the
feature never breaks offline or when ANTHROPIC_API_KEY is missing."""

import os

from sqlalchemy.orm import Session

from app.agent.core import run_structured_task
from app.db import repo
from app.models import RootCauseAnalysis

AGENTIC_SYSTEM_PROMPT = """You are an AI RCM analyst investigating why a specific healthcare provider is \
underperforming or flagged for review, for Clearview Medical Group (100% synthetic data, no real PHI). Use \
your tools -- get_provider_claims, compare_providers, search_policy_knowledge -- to build a specific, \
evidence-based root-cause explanation: compare the provider against peers, pull their denial-reason pattern \
from claims, and cite the relevant (synthetic) payer policy for any denial pattern you find. Reference actual \
numbers you found via your tools -- do not guess or invent figures. Once your investigation is complete, call \
record_root_cause exactly once with: a narrative explaining the root cause, a list of specific contributing \
factors, a list of cited policy titles (empty list if none apply), and a list of concrete remediation steps."""


def _parse_agent_root_cause(provider_id: str, data: dict) -> RootCauseAnalysis | None:
    try:
        return RootCauseAnalysis(
            providerId=provider_id,
            narrative=data["narrative"],
            contributingFactors=data["contributingFactors"],
            citedPolicies=data["citedPolicies"],
            recommendedRemediation=data["recommendedRemediation"],
            generatedBy="ai",
        )
    except (KeyError, TypeError, ValueError):
        return None


async def _call_agent(provider_id: str, provider_name: str) -> RootCauseAnalysis | None:
    prompt = (
        f"Investigate provider {provider_id} ({provider_name}). Compare them to peers, pull their claims/"
        f"denial pattern, look up relevant policy, then call record_root_cause with your findings."
    )
    data = await run_structured_task(prompt, "record_root_cause", system_prompt=AGENTIC_SYSTEM_PROMPT)
    return _parse_agent_root_cause(provider_id, data) if data else None


def _rule_based(provider) -> RootCauseAnalysis:
    m, peer = provider.metrics, provider.peerAverageMetrics
    factors = []
    if m.denialRate > peer.denialRate:
        factors.append(f"Denial rate {m.denialRate}% is above the peer average of {peer.denialRate}%.")
    if m.daysInAR > peer.daysInAR:
        factors.append(f"Days in AR ({m.daysInAR}) exceeds the peer average of {peer.daysInAR}.")
    if m.codingAccuracy < peer.codingAccuracy:
        factors.append(f"Coding accuracy ({m.codingAccuracy}%) trails the peer average of {peer.codingAccuracy}%.")
    if m.priorAuthApprovalRate < peer.priorAuthApprovalRate:
        factors.append(
            f"Prior-auth approval rate ({m.priorAuthApprovalRate}%) is below the peer average of "
            f"{peer.priorAuthApprovalRate}%."
        )
    if m.clinicalQualityScore < peer.clinicalQualityScore:
        factors.append(
            f"Clinical quality score ({m.clinicalQualityScore}%) trails the peer average of "
            f"{peer.clinicalQualityScore}%."
        )
    if m.patientPortalAdoptionRate < peer.patientPortalAdoptionRate:
        factors.append(
            f"Patient portal adoption ({m.patientPortalAdoptionRate}%) is below the peer average of "
            f"{peer.patientPortalAdoptionRate}%, suggesting an engagement gap."
        )
    if not factors:
        factors.append("No single metric stands out sharply versus peer average; risk likely reflects a combination of smaller gaps.")

    narrative = (
        f"{provider.name} ({provider.specialty}) is flagged at {provider.riskLevel} risk with a performance "
        f"score of {provider.performanceScore}. Most notable gaps versus peers: {' '.join(factors)}"
    )
    return RootCauseAnalysis(
        providerId=provider.id,
        narrative=narrative,
        contributingFactors=factors,
        citedPolicies=[],
        recommendedRemediation=[
            "Schedule a denial root-cause review with the provider.",
            "Audit recent coding/documentation for the affected claim types.",
            "Re-verify eligibility and prior authorization workflows before submission.",
        ],
        generatedBy="rule",
    )


async def generate_root_cause(db: Session, provider_id: str) -> RootCauseAnalysis | None:
    provider = repo.get_provider(db, provider_id)
    if provider is None:
        return None
    if os.environ.get("ANTHROPIC_API_KEY"):
        agentic = await _call_agent(provider_id, provider.name)
        if agentic:
            return agentic
    return _rule_based(provider)
