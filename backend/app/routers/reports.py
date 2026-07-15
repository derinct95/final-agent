from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db import repo
from app.db.session import get_db
from app.models import PracticeReviewReport
from app.services import report_pdf
from app.services.practice_review import generate_practice_review

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/practice-review", response_model=PracticeReviewReport)
async def practice_review(
    period: str = Query("quarterly", pattern="^(weekly|monthly|quarterly)$"),
    label: str | None = None,
    db: Session = Depends(get_db),
) -> PracticeReviewReport:
    return await generate_practice_review(db, period, label)


@router.get("/practice-review/download")
async def practice_review_download(
    period: str = Query("quarterly", pattern="^(weekly|monthly|quarterly)$"),
    label: str | None = None,
    format: str = Query("pdf", pattern="^(pdf|csv)$"),
    db: Session = Depends(get_db),
):
    report = await generate_practice_review(db, period, label)
    if format == "csv":
        content = report_pdf.build_practice_review_csv(report)
        media_type, ext = "text/csv", "csv"
    else:
        content = report_pdf.build_practice_review_pdf(report)
        media_type, ext = "application/pdf", "pdf"
    filename = f"clearview-practice-review-{period}.{ext}"
    return Response(content=content, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/compare")
def compare_report_download(
    providerIds: str,
    format: str = Query("pdf", pattern="^(pdf|csv)$"),
    db: Session = Depends(get_db),
):
    ids = [i for i in providerIds.split(",") if i]
    providers = repo.compare_providers(db, ids)
    if not providers:
        raise HTTPException(status_code=404, detail="No matching providers found")
    if format == "csv":
        content = report_pdf.build_compare_report_csv(providers)
        media_type, ext = "text/csv", "csv"
    else:
        content = report_pdf.build_compare_report_pdf(providers)
        media_type, ext = "application/pdf", "pdf"
    filename = f"clearview-comparison-{len(providers)}-providers.{ext}"
    return Response(content=content, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/providers/{provider_id}/report")
def provider_report_download(
    provider_id: str,
    periodStart: str | None = None,
    periodEnd: str | None = None,
    granularity: str = Query("quarter", pattern="^(week|month|quarter|year)$"),
    format: str = Query("pdf", pattern="^(pdf|csv)$"),
    db: Session = Depends(get_db),
):
    provider = repo.get_provider(db, provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    period_range = (periodStart, periodEnd) if periodStart and periodEnd else None
    if format == "csv":
        content = report_pdf.build_provider_report_csv(provider, period_range, granularity)
        media_type, ext = "text/csv", "csv"
    else:
        content = report_pdf.build_provider_report_pdf(provider, period_range, granularity)
        media_type, ext = "application/pdf", "pdf"
    filename = f"clearview-{provider.id}-report.{ext}"
    return Response(content=content, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})
