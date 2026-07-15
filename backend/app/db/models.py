from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ProviderORM(Base):
    __tablename__ = "providers"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    specialty: Mapped[str] = mapped_column(String)
    facility: Mapped[str] = mapped_column(String)
    npi: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String, default="")
    practice_type: Mapped[str] = mapped_column(String, default="medical")
    flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    flag_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String, default="seed")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    score_history: Mapped[list["ScoreHistoryORM"]] = relationship(
        back_populates="provider", cascade="all, delete-orphan", order_by="ScoreHistoryORM.month"
    )
    quarters: Mapped[list["QuarterlySnapshotORM"]] = relationship(
        back_populates="provider", cascade="all, delete-orphan", order_by="QuarterlySnapshotORM.quarter"
    )
    claims: Mapped[list["ClaimORM"]] = relationship(
        back_populates="provider", cascade="all, delete-orphan", order_by="ClaimORM.claim_date"
    )
    actions: Mapped[list["ActionORM"]] = relationship(
        back_populates="provider", cascade="all, delete-orphan"
    )


class ScoreHistoryORM(Base):
    __tablename__ = "provider_score_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider_id: Mapped[str] = mapped_column(ForeignKey("providers.id"))
    month: Mapped[str] = mapped_column(String)
    score: Mapped[float] = mapped_column(Float)

    provider: Mapped[ProviderORM] = relationship(back_populates="score_history")


class QuarterlySnapshotORM(Base):
    __tablename__ = "quarterly_snapshots"
    __table_args__ = (UniqueConstraint("provider_id", "quarter", name="uq_provider_quarter"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider_id: Mapped[str] = mapped_column(ForeignKey("providers.id"))
    quarter: Mapped[str] = mapped_column(String)
    performance_score: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String)
    trend: Mapped[str] = mapped_column(String)

    clean_claim_rate: Mapped[float] = mapped_column(Float)
    denial_rate: Mapped[float] = mapped_column(Float)
    days_in_ar: Mapped[float] = mapped_column(Float)
    first_pass_resolution_rate: Mapped[float] = mapped_column(Float)
    coding_accuracy: Mapped[float] = mapped_column(Float)
    prior_auth_approval_rate: Mapped[float] = mapped_column(Float)
    net_collection_rate: Mapped[float] = mapped_column(Float)
    avg_reimbursement_per_claim: Mapped[float] = mapped_column(Float)
    claims_volume_monthly: Mapped[float] = mapped_column(Float)
    documentation_accuracy: Mapped[float] = mapped_column(Float)
    patient_satisfaction_score: Mapped[float] = mapped_column(Float)
    clinical_quality_score: Mapped[float] = mapped_column(Float)
    patient_visits_monthly: Mapped[float] = mapped_column(Float)
    patient_portal_adoption_rate: Mapped[float] = mapped_column(Float)

    peer_clean_claim_rate: Mapped[float] = mapped_column(Float)
    peer_denial_rate: Mapped[float] = mapped_column(Float)
    peer_days_in_ar: Mapped[float] = mapped_column(Float)
    peer_first_pass_resolution_rate: Mapped[float] = mapped_column(Float)
    peer_coding_accuracy: Mapped[float] = mapped_column(Float)
    peer_prior_auth_approval_rate: Mapped[float] = mapped_column(Float)
    peer_net_collection_rate: Mapped[float] = mapped_column(Float)
    peer_avg_reimbursement_per_claim: Mapped[float] = mapped_column(Float)
    peer_claims_volume_monthly: Mapped[float] = mapped_column(Float)
    peer_documentation_accuracy: Mapped[float] = mapped_column(Float)
    peer_patient_satisfaction_score: Mapped[float] = mapped_column(Float)
    peer_clinical_quality_score: Mapped[float] = mapped_column(Float)
    peer_patient_visits_monthly: Mapped[float] = mapped_column(Float)
    peer_patient_portal_adoption_rate: Mapped[float] = mapped_column(Float)

    provider: Mapped[ProviderORM] = relationship(back_populates="quarters")


class MonthlyClaimsSummaryORM(Base):
    __tablename__ = "monthly_claims_summary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider_id: Mapped[str] = mapped_column(ForeignKey("providers.id"))
    month: Mapped[str] = mapped_column(String)
    claims_submitted: Mapped[int] = mapped_column(Integer)
    claims_paid: Mapped[int] = mapped_column(Integer)
    claims_denied: Mapped[int] = mapped_column(Integer)
    claims_pending: Mapped[int] = mapped_column(Integer)
    revenue_collected: Mapped[float] = mapped_column(Float)
    denial_reasons_json: Mapped[str] = mapped_column(String)


class ClaimORM(Base):
    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    provider_id: Mapped[str] = mapped_column(ForeignKey("providers.id"))
    claim_date: Mapped[str] = mapped_column(String)
    quarter: Mapped[str] = mapped_column(String)
    month: Mapped[str] = mapped_column(String)
    payer: Mapped[str] = mapped_column(String)
    amount_billed: Mapped[float] = mapped_column(Float)
    amount_paid: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String)
    denial_reason: Mapped[str | None] = mapped_column(String, nullable=True)

    provider: Mapped[ProviderORM] = relationship(back_populates="claims")
    events: Mapped[list["ClaimStatusEventORM"]] = relationship(
        back_populates="claim", cascade="all, delete-orphan", order_by="ClaimStatusEventORM.sequence"
    )


class ClaimStatusEventORM(Base):
    __tablename__ = "claim_status_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"))
    status: Mapped[str] = mapped_column(String)
    event_date: Mapped[str] = mapped_column(String)
    note: Mapped[str | None] = mapped_column(String, nullable=True)
    sequence: Mapped[int] = mapped_column(Integer)

    claim: Mapped[ClaimORM] = relationship(back_populates="events")


class ActionORM(Base):
    __tablename__ = "actions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    provider_id: Mapped[str] = mapped_column(ForeignKey("providers.id"))
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)
    priority: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String)
    source: Mapped[str] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    consecutive_quarters: Mapped[int] = mapped_column(Integer, default=0)

    provider: Mapped[ProviderORM] = relationship(back_populates="actions")


class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True)
    display_name: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)


class EmailMessageORM(Base):
    __tablename__ = "email_messages"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    provider_ids_json: Mapped[str] = mapped_column(String)
    recipients_json: Mapped[str] = mapped_column(String)
    subject: Mapped[str] = mapped_column(String)
    body: Mapped[str] = mapped_column(String)
    related_appointment_id: Mapped[str | None] = mapped_column(String, nullable=True)
    sent_by: Mapped[str] = mapped_column(String, default="")
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class AppointmentORM(Base):
    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    provider_ids_json: Mapped[str] = mapped_column(String)
    topic: Mapped[str] = mapped_column(String)
    agenda: Mapped[str] = mapped_column(String, default="")
    scheduled_at: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="confirmed")
    created_by: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
