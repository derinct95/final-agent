from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import repo
from app.db.session import get_db
from app.models import Insight
from app.services.ai_insights import generate_insights

router = APIRouter(prefix="/api/insights", tags=["insights"])

_cache: dict[str, list[Insight]] = {}


@router.get("", response_model=list[Insight])
async def get_insights(
    refresh: bool = False,
    practiceType: str | None = Query(None, pattern="^(medical|dental)$"),
    db: Session = Depends(get_db),
) -> list[Insight]:
    cache_key = practiceType or "all"
    if cache_key not in _cache or refresh:
        full_providers = [repo.get_provider(db, s.id) for s in repo.list_providers(db, practiceType)]
        _cache[cache_key] = await generate_insights([p for p in full_providers if p is not None])
    return _cache[cache_key]
