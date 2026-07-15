import random
import secrets
import time

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth_deps import require_admin
from app.data.seed import FACILITIES, SPECIALTIES, generate_one_provider
from app.db import repo
from app.db.session import get_db
from app.models import ImportCommitRequest, ImportPreviewResult, ImportPreviewRow, ImportWarning, Provider
from app.services.import_detect import parse_upload

router = APIRouter(prefix="/api/import", tags=["import"])

_PREVIEW_TTL_SECONDS = 600
_preview_cache: dict[str, dict] = {}

_SOURCE_BY_FORMAT = {"fhir": "fhir_import", "hl7": "hl7_import", "csv": "csv_import"}

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5MB -- generous for a CSV/FHIR/HL7 provider-directory file


def _evict_expired() -> None:
    now = time.time()
    for token in [t for t, v in _preview_cache.items() if now - v["created"] > _PREVIEW_TTL_SECONDS]:
        del _preview_cache[token]


async def _read_limited(file: UploadFile, max_bytes: int) -> bytes:
    chunks = []
    total = 0
    while True:
        chunk = await file.read(65536)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(status_code=413, detail=f"File too large (max {max_bytes // (1024 * 1024)}MB).")
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("/preview", response_model=ImportPreviewResult)
async def import_preview(file: UploadFile) -> ImportPreviewResult:
    raw = await _read_limited(file, MAX_UPLOAD_BYTES)
    fmt, rows, warnings = parse_upload(raw)
    _evict_expired()
    token = secrets.token_hex(8)
    _preview_cache[token] = {"rows": rows, "format": fmt, "created": time.time()}
    return ImportPreviewResult(
        detectedFormat=fmt,
        importToken=token,
        rows=[ImportPreviewRow(**r) for r in rows],
        warnings=[ImportWarning(message=w) for w in warnings],
    )


@router.post("/commit", response_model=list[Provider])
def import_commit(
    payload: ImportCommitRequest, db: Session = Depends(get_db), _role: str = Depends(require_admin)
) -> list[Provider]:
    cached = _preview_cache.pop(payload.importToken, None)
    if cached is None:
        raise HTTPException(status_code=400, detail="Import preview expired or not found. Please re-upload.")

    rng = random.Random()
    source = _SOURCE_BY_FORMAT.get(cached["format"], "manual")
    created: list[Provider] = []

    for row in cached["rows"]:
        if not row.get("name"):
            continue
        score = row.get("performanceScore")
        if score is None:
            score = round(rng.uniform(55, 90), 1)
        provider_id = repo.next_provider_id(db)
        generated = generate_one_provider(
            rng,
            provider_id=provider_id,
            name=row["name"],
            specialty=row.get("specialty") or rng.choice(SPECIALTIES),
            facility=row.get("facility") or rng.choice(FACILITIES),
            npi=row.get("npi") or f"{rng.randint(1000000000, 9999999999)}",
            final_score=score,
            source=source,
            claims_seed_index=rng.randint(1000, 9999),
        )
        created.append(repo.add_generated_provider(db, generated))

    return created
