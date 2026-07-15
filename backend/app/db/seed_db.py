import json

from sqlalchemy.orm import Session

from app.data.seed import demo_users, generate_providers
from app.db.models import (
    ActionORM,
    ClaimORM,
    ClaimStatusEventORM,
    MonthlyClaimsSummaryORM,
    ProviderORM,
    QuarterlySnapshotORM,
    ScoreHistoryORM,
    UserORM,
)


def insert_provider(db: Session, p: dict) -> None:
    """Insert one fully-generated provider dict (see app/data/seed.py::generate_one_provider)
    as ORM rows. Does not commit -- caller controls the transaction boundary."""
    provider = ProviderORM(
        id=p["id"], name=p["name"], specialty=p["specialty"], facility=p["facility"],
        npi=p["npi"], email=p.get("email", ""), practice_type=p.get("practice_type", "medical"),
        flagged=p["flagged"], flag_reason=p["flag_reason"],
        reviewed=p["reviewed"], source=p["source"],
    )
    db.add(provider)

    for month, score in zip(p["score_history_months"], p["score_history_monthly"]):
        db.add(ScoreHistoryORM(provider_id=p["id"], month=month, score=score))

    for q in p["quarters"]:
        m, peer = q["metrics"], q["peerMetrics"]
        db.add(QuarterlySnapshotORM(
            provider_id=p["id"], quarter=q["quarter"], performance_score=q["performanceScore"],
            risk_level=q["riskLevel"], trend=q["trend"],
            clean_claim_rate=m["cleanClaimRate"], denial_rate=m["denialRate"], days_in_ar=m["daysInAR"],
            first_pass_resolution_rate=m["firstPassResolutionRate"], coding_accuracy=m["codingAccuracy"],
            prior_auth_approval_rate=m["priorAuthApprovalRate"], net_collection_rate=m["netCollectionRate"],
            avg_reimbursement_per_claim=m["avgReimbursementPerClaim"], claims_volume_monthly=m["claimsVolumeMonthly"],
            documentation_accuracy=m["documentationAccuracy"], patient_satisfaction_score=m["patientSatisfactionScore"],
            clinical_quality_score=m["clinicalQualityScore"], patient_visits_monthly=m["patientVisitsMonthly"],
            patient_portal_adoption_rate=m["patientPortalAdoptionRate"],
            peer_clean_claim_rate=peer["cleanClaimRate"], peer_denial_rate=peer["denialRate"],
            peer_days_in_ar=peer["daysInAR"], peer_first_pass_resolution_rate=peer["firstPassResolutionRate"],
            peer_coding_accuracy=peer["codingAccuracy"], peer_prior_auth_approval_rate=peer["priorAuthApprovalRate"],
            peer_net_collection_rate=peer["netCollectionRate"], peer_avg_reimbursement_per_claim=peer["avgReimbursementPerClaim"],
            peer_claims_volume_monthly=peer["claimsVolumeMonthly"],
            peer_documentation_accuracy=peer["documentationAccuracy"],
            peer_patient_satisfaction_score=peer["patientSatisfactionScore"],
            peer_clinical_quality_score=peer["clinicalQualityScore"],
            peer_patient_visits_monthly=peer["patientVisitsMonthly"],
            peer_patient_portal_adoption_rate=peer["patientPortalAdoptionRate"],
        ))

    for c in p["claims"]:
        db.add(ClaimORM(
            id=c["id"], provider_id=p["id"], claim_date=c["claim_date"], quarter=c["quarter"],
            month=c["month"], payer=c["payer"], amount_billed=c["amount_billed"],
            amount_paid=c["amount_paid"], status=c["status"], denial_reason=c["denial_reason"],
        ))
        for ev in c["events"]:
            db.add(ClaimStatusEventORM(
                claim_id=c["id"], status=ev["status"], event_date=ev["event_date"],
                note=ev["note"], sequence=ev["sequence"],
            ))

    for mc in p["monthly_claims_history"]:
        db.add(MonthlyClaimsSummaryORM(
            provider_id=p["id"], month=mc["month"], claims_submitted=mc["claimsSubmitted"],
            claims_paid=mc["claimsPaid"], claims_denied=mc["claimsDenied"],
            claims_pending=mc["claimsPending"], revenue_collected=mc["revenueCollected"],
            denial_reasons_json=json.dumps(mc["denialReasons"]),
        ))

    for a in p["actions"]:
        db.add(ActionORM(
            id=a["id"], provider_id=p["id"], title=a["title"], description=a["description"],
            priority=a["priority"], status=a["status"], category=a["category"], source=a["source"],
            created_at=a["created_at"], is_recurring=a["is_recurring"],
            consecutive_quarters=a["consecutive_quarters"],
        ))


def seed_if_empty(db: Session) -> None:
    if db.query(ProviderORM).count() > 0:
        return

    for p in generate_providers():
        insert_provider(db, p)

    for u in demo_users():
        db.add(UserORM(id=u["id"], email=u["email"], display_name=u["display_name"], role=u["role"]))

    db.commit()
