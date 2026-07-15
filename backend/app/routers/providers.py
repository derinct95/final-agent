from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth_deps import require_admin
from app.db import repo
from app.db.session import get_db
from app.models import (
    ActionUpdateRequest,
    ClaimDetail,
    ClaimsPage,
    ClaimsStatusSummary,
    DashboardSummary,
    FlagUpdateRequest,
    MetricSnapshot,
    Provider,
    ProviderSummary,
    QuarterlySnapshot,
    RootCauseAnalysis,
)
from app.services.root_cause import generate_root_cause

router = APIRouter(prefix="/api/providers", tags=["providers"])


@router.get("", response_model=list[ProviderSummary])
def list_providers(
    practiceType: str | None = Query(None, pattern="^(medical|dental)$"),
    db: Session = Depends(get_db),
) -> list[ProviderSummary]:
    return repo.list_providers(db, practiceType)


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(
    practiceType: str | None = Query(None, pattern="^(medical|dental)$"),
    db: Session = Depends(get_db),
) -> DashboardSummary:
    return repo.summary(db, practiceType)


@router.get("/{provider_id}", response_model=Provider)
def get_provider(provider_id: str, db: Session = Depends(get_db)) -> Provider:
    provider = repo.get_provider(db, provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


@router.get("/{provider_id}/quarterly-history", response_model=list[QuarterlySnapshot])
def get_quarterly_history(provider_id: str, db: Session = Depends(get_db)) -> list[QuarterlySnapshot]:
    history = repo.get_quarterly_history(db, provider_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    return history


@router.get("/{provider_id}/metric-history", response_model=list[MetricSnapshot])
def get_metric_history(
    provider_id: str,
    granularity: str = Query("quarter", pattern="^(week|month|quarter|year)$"),
    db: Session = Depends(get_db),
) -> list[MetricSnapshot]:
    history = repo.get_metric_history(db, provider_id, granularity)
    if history is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    return history


@router.get("/{provider_id}/claims/summary", response_model=ClaimsStatusSummary)
def get_claims_summary(provider_id: str, quarter: str | None = None, db: Session = Depends(get_db)) -> ClaimsStatusSummary:
    summary = repo.get_claims_status_summary(db, provider_id, quarter)
    if summary is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    return summary


@router.get("/{provider_id}/claims", response_model=ClaimsPage)
def get_claims(
    provider_id: str,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    status: str | None = None,
    quarter: str | None = None,
    db: Session = Depends(get_db),
) -> ClaimsPage:
    result = repo.get_claims(db, provider_id, page=page, page_size=pageSize, status=status, quarter=quarter)
    if result is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    return result


@router.get("/{provider_id}/claims/{claim_id}", response_model=ClaimDetail)
def get_claim_detail(provider_id: str, claim_id: str, db: Session = Depends(get_db)) -> ClaimDetail:
    detail = repo.get_claim_detail(db, provider_id, claim_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    return detail


@router.post("/{provider_id}/root-cause", response_model=RootCauseAnalysis)
async def root_cause_endpoint(provider_id: str, db: Session = Depends(get_db)) -> RootCauseAnalysis:
    result = await generate_root_cause(db, provider_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    return result


@router.patch("/{provider_id}/flag", response_model=Provider)
def update_flag(provider_id: str, payload: FlagUpdateRequest, db: Session = Depends(get_db)) -> Provider:
    provider = repo.set_flag(db, provider_id, payload.flagged, payload.reviewed)
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


@router.patch("/{provider_id}/actions/{action_id}", response_model=Provider)
def update_action(
    provider_id: str,
    action_id: str,
    payload: ActionUpdateRequest,
    db: Session = Depends(get_db),
    _role: str = Depends(require_admin),
) -> Provider:
    provider = repo.set_action_status(db, provider_id, action_id, payload.status)
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider or action not found")
    return provider
