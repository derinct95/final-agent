import io

import pandas as pd
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db import repo
from app.db.session import get_db

router = APIRouter(prefix="/api/providers", tags=["providers"])

EXPORT_COLUMNS = [
    "id", "name", "specialty", "facility", "npi", "performanceScore", "riskLevel",
    "trend", "flagged", "reviewed", "flagReason", "stuckAtRiskQuarters", "cleanClaimRate", "denialRate",
    "daysInAR", "firstPassResolutionRate", "codingAccuracy", "priorAuthApprovalRate",
    "netCollectionRate", "avgReimbursementPerClaim", "claimsVolumeMonthly",
    "documentationAccuracy", "patientSatisfactionScore",
    "clinicalQualityScore", "patientVisitsMonthly", "patientPortalAdoptionRate",
]


@router.get("/export")
def export_csv(scope: str = "all", db: Session = Depends(get_db)):
    providers = repo.list_providers(db)
    if scope == "flagged":
        providers = [p for p in providers if p.flagged and not p.reviewed]

    rows = []
    for s in providers:
        p = repo.get_provider(db, s.id)
        if p is None:
            continue
        rows.append({
            "id": p.id, "name": p.name, "specialty": p.specialty, "facility": p.facility,
            "npi": p.npi, "performanceScore": p.performanceScore, "riskLevel": p.riskLevel,
            "trend": p.trend, "flagged": p.flagged, "reviewed": p.reviewed,
            "flagReason": p.flagReason or "", "stuckAtRiskQuarters": p.stuckAtRiskQuarters,
            "cleanClaimRate": p.metrics.cleanClaimRate, "denialRate": p.metrics.denialRate,
            "daysInAR": p.metrics.daysInAR, "firstPassResolutionRate": p.metrics.firstPassResolutionRate,
            "codingAccuracy": p.metrics.codingAccuracy, "priorAuthApprovalRate": p.metrics.priorAuthApprovalRate,
            "netCollectionRate": p.metrics.netCollectionRate,
            "avgReimbursementPerClaim": p.metrics.avgReimbursementPerClaim,
            "claimsVolumeMonthly": p.metrics.claimsVolumeMonthly,
            "documentationAccuracy": p.metrics.documentationAccuracy,
            "patientSatisfactionScore": p.metrics.patientSatisfactionScore,
            "clinicalQualityScore": p.metrics.clinicalQualityScore,
            "patientVisitsMonthly": p.metrics.patientVisitsMonthly,
            "patientPortalAdoptionRate": p.metrics.patientPortalAdoptionRate,
        })

    df = pd.DataFrame(rows, columns=EXPORT_COLUMNS)
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)
    filename = "flagged_providers.csv" if scope == "flagged" else "providers.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
