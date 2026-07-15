import secrets

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import repo
from app.db.session import get_db
from app.models import DemoAccount, LoginRequest, LoginResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    name = payload.name or payload.email.split("@")[0].replace(".", " ").replace("_", " ").title() or "Demo User"
    return LoginResponse(token=secrets.token_hex(16), name=name, email=payload.email)


@router.get("/demo-accounts", response_model=list[DemoAccount])
def demo_accounts(db: Session = Depends(get_db)) -> list[DemoAccount]:
    return repo.get_demo_accounts(db)
