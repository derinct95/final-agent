import json
import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.db import seed_db
from app.db.models import (
    ActionORM,
    AppointmentORM,
    ClaimORM,
    EmailMessageORM,
    MonthlyClaimsSummaryORM,
    ProviderORM,
    QuarterlySnapshotORM,
    UserORM,
)
from app.models import (
    Action,
    Appointment,
    ClaimDetail,
    ClaimsHistoryPoint,
    ClaimStatusEvent,
    ClaimSummary,
    ClaimsPage,
    ClaimsStatusSummary,
    DashboardSummary,
    DemoAccount,
    DenialReasonBreakdown,
    EmailMessage,
    Metrics,
    MetricSnapshot,
    Provider,
    ProviderSummary,
    QuarterlySnapshot,
)

STUCK_AT_RISK_THRESHOLD = 2

METRIC_FIELDS = [
    "cleanClaimRate", "denialRate", "daysInAR", "firstPassResolutionRate", "codingAccuracy",
    "priorAuthApprovalRate", "netCollectionRate", "avgReimbursementPerClaim", "claimsVolumeMonthly",
    "documentationAccuracy", "patientSatisfactionScore",
    "clinicalQualityScore", "patientVisitsMonthly", "patientPortalAdoptionRate",
]

PROCEDURE_CATALOG = [
    ("99213", "Office visit, established patient (Level 3)"),
    ("99214", "Office visit, established patient (Level 4)"),
    ("99203", "Office visit, new patient (Level 3)"),
    ("93000", "Electrocardiogram, routine ECG"),
    ("71046", "Chest X-ray, 2 views"),
    ("80053", "Comprehensive metabolic panel"),
    ("36415", "Routine venipuncture"),
    ("20610", "Arthrocentesis, major joint"),
    ("45378", "Colonoscopy, diagnostic"),
    ("29881", "Knee arthroscopy with meniscectomy"),
]


def _procedure_for_claim(claim_id: str) -> tuple[str, str]:
    idx = sum(ord(c) for c in claim_id) % len(PROCEDURE_CATALOG)
    return PROCEDURE_CATALOG[idx]


def _metrics(q: QuarterlySnapshotORM) -> Metrics:
    return Metrics(
        cleanClaimRate=q.clean_claim_rate, denialRate=q.denial_rate, daysInAR=q.days_in_ar,
        firstPassResolutionRate=q.first_pass_resolution_rate, codingAccuracy=q.coding_accuracy,
        priorAuthApprovalRate=q.prior_auth_approval_rate, netCollectionRate=q.net_collection_rate,
        avgReimbursementPerClaim=q.avg_reimbursement_per_claim, claimsVolumeMonthly=q.claims_volume_monthly,
        documentationAccuracy=q.documentation_accuracy, patientSatisfactionScore=q.patient_satisfaction_score,
        clinicalQualityScore=q.clinical_quality_score, patientVisitsMonthly=q.patient_visits_monthly,
        patientPortalAdoptionRate=q.patient_portal_adoption_rate,
    )


def _peer_metrics(q: QuarterlySnapshotORM) -> Metrics:
    return Metrics(
        cleanClaimRate=q.peer_clean_claim_rate, denialRate=q.peer_denial_rate, daysInAR=q.peer_days_in_ar,
        firstPassResolutionRate=q.peer_first_pass_resolution_rate, codingAccuracy=q.peer_coding_accuracy,
        priorAuthApprovalRate=q.peer_prior_auth_approval_rate, netCollectionRate=q.peer_net_collection_rate,
        avgReimbursementPerClaim=q.peer_avg_reimbursement_per_claim, claimsVolumeMonthly=q.peer_claims_volume_monthly,
        documentationAccuracy=q.peer_documentation_accuracy, patientSatisfactionScore=q.peer_patient_satisfaction_score,
        clinicalQualityScore=q.peer_clinical_quality_score, patientVisitsMonthly=q.peer_patient_visits_monthly,
        patientPortalAdoptionRate=q.peer_patient_portal_adoption_rate,
    )


def _sorted_quarters(p: ProviderORM) -> list[QuarterlySnapshotORM]:
    return sorted(p.quarters, key=lambda q: q.quarter)


def _quarter_month_labels(quarter: str) -> list[str]:
    year_s, q_s = quarter.split("-Q")
    year, q = int(year_s), int(q_s)
    start_month = (q - 1) * 3 + 1
    return [f"{year:04d}-{start_month + i:02d}" for i in range(3)]


def _month_label(month: str) -> str:
    y, m = month.split("-")
    return date(int(y), int(m), 1).strftime("%b %Y")


def _interp_metrics(a: dict, b: dict, t: float) -> Metrics:
    return Metrics(**{k: round(a[k] + (b[k] - a[k]) * t, 2) for k in METRIC_FIELDS})


def _quarterly_snapshots(quarters: list[QuarterlySnapshotORM]) -> list[MetricSnapshot]:
    return [
        MetricSnapshot(
            period=q.quarter, label=q.quarter, performanceScore=q.performance_score,
            riskLevel=q.risk_level, trend=q.trend, metrics=_metrics(q), peerAverageMetrics=_peer_metrics(q),
        )
        for q in quarters
    ]


def _monthly_snapshots(quarters: list[QuarterlySnapshotORM]) -> list[MetricSnapshot]:
    points: list[MetricSnapshot] = []
    for i, q in enumerate(quarters):
        months = _quarter_month_labels(q.quarter)
        prev = quarters[i - 1] if i > 0 else q
        prev_m, prev_p = _metrics(prev).model_dump(), _peer_metrics(prev).model_dump()
        cur_m, cur_p = _metrics(q).model_dump(), _peer_metrics(q).model_dump()
        for j, month in enumerate(months):
            t = (j + 1) / 3
            score = round(prev.performance_score + (q.performance_score - prev.performance_score) * t, 1)
            points.append(MetricSnapshot(
                period=month, label=_month_label(month), performanceScore=score,
                riskLevel=q.risk_level, trend=q.trend,
                metrics=_interp_metrics(prev_m, cur_m, t), peerAverageMetrics=_interp_metrics(prev_p, cur_p, t),
            ))
    return points


def _weekly_snapshots(monthly: list[MetricSnapshot]) -> list[MetricSnapshot]:
    points: list[MetricSnapshot] = []
    for i, m in enumerate(monthly):
        prev = monthly[i - 1] if i > 0 else m
        prev_m, prev_p = prev.metrics.model_dump(), prev.peerAverageMetrics.model_dump()
        cur_m, cur_p = m.metrics.model_dump(), m.peerAverageMetrics.model_dump()
        for w in range(4):
            t = (w + 1) / 4
            score = round(prev.performanceScore + (m.performanceScore - prev.performanceScore) * t, 1)
            points.append(MetricSnapshot(
                period=f"{m.period}-W{w + 1}", label=f"Week {w + 1}, {m.label}", performanceScore=score,
                riskLevel=m.riskLevel, trend=m.trend,
                metrics=_interp_metrics(prev_m, cur_m, t), peerAverageMetrics=_interp_metrics(prev_p, cur_p, t),
            ))
    return points


def _yearly_snapshots(quarters: list[QuarterlySnapshotORM]) -> list[MetricSnapshot]:
    by_year: dict[str, list[QuarterlySnapshotORM]] = {}
    for q in quarters:
        by_year.setdefault(q.quarter.split("-Q")[0], []).append(q)

    points: list[MetricSnapshot] = []
    for year in sorted(by_year):
        qs = by_year[year]
        m_dicts = [_metrics(q).model_dump() for q in qs]
        p_dicts = [_peer_metrics(q).model_dump() for q in qs]
        avg_m = Metrics(**{k: round(sum(d[k] for d in m_dicts) / len(m_dicts), 1) for k in METRIC_FIELDS})
        avg_p = Metrics(**{k: round(sum(d[k] for d in p_dicts) / len(p_dicts), 1) for k in METRIC_FIELDS})
        last = qs[-1]
        points.append(MetricSnapshot(
            period=year, label=year, performanceScore=round(sum(q.performance_score for q in qs) / len(qs), 1),
            riskLevel=last.risk_level, trend=last.trend, metrics=avg_m, peerAverageMetrics=avg_p,
        ))
    return points


def get_metric_history(db: Session, provider_id: str, granularity: str) -> list[MetricSnapshot] | None:
    """Weekly/monthly/yearly views are derived on the fly from the real quarterly
    snapshots (linear interpolation converging exactly on each quarter's actual
    values; yearly is a straight average of its 4 quarters) rather than stored
    independently -- the quarterly snapshot remains the single source of truth."""
    p = db.get(ProviderORM, provider_id)
    if p is None:
        return None
    quarters = _sorted_quarters(p)
    if not quarters:
        return []
    if granularity == "year":
        return _yearly_snapshots(quarters)
    if granularity == "month":
        return _monthly_snapshots(quarters)
    if granularity == "week":
        return _weekly_snapshots(_monthly_snapshots(quarters))
    return _quarterly_snapshots(quarters)


def _stuck_at_risk_quarters(quarters: list[QuarterlySnapshotORM]) -> int:
    count = 0
    for q in reversed(quarters):
        if q.risk_level in ("high", "critical"):
            count += 1
        else:
            break
    return count


def _to_summary(p: ProviderORM) -> ProviderSummary | None:
    quarters = _sorted_quarters(p)
    if not quarters:
        return None
    latest = quarters[-1]
    score_history = [s.score for s in sorted(p.score_history, key=lambda s: s.month)]
    pending_actions = sum(1 for a in p.actions if a.status != "resolved")
    return ProviderSummary(
        id=p.id, name=p.name, specialty=p.specialty, facility=p.facility, email=p.email,
        practiceType=p.practice_type,
        performanceScore=latest.performance_score, riskLevel=latest.risk_level, trend=latest.trend,
        scoreHistory=score_history, flagged=p.flagged, flagReason=p.flag_reason, reviewed=p.reviewed,
        stuckAtRiskQuarters=_stuck_at_risk_quarters(quarters),
        denialRate=latest.denial_rate, netCollectionRate=latest.net_collection_rate,
        pendingActionsCount=pending_actions,
    )


def list_providers(db: Session, practice_type: str | None = None) -> list[ProviderSummary]:
    query = db.query(ProviderORM)
    if practice_type:
        query = query.filter_by(practice_type=practice_type)
    providers = query.all()
    summaries = [s for s in (_to_summary(p) for p in providers) if s is not None]
    summaries.sort(key=lambda p: -p.performanceScore)
    return summaries


def get_provider_orm(db: Session, provider_id: str) -> ProviderORM | None:
    return db.get(ProviderORM, provider_id)


def get_provider(db: Session, provider_id: str) -> Provider | None:
    p = db.get(ProviderORM, provider_id)
    if p is None:
        return None
    quarters = _sorted_quarters(p)
    if not quarters:
        return None
    latest = quarters[-1]
    score_history = [s.score for s in sorted(p.score_history, key=lambda s: s.month)]

    monthly = (
        db.query(MonthlyClaimsSummaryORM)
        .filter_by(provider_id=provider_id)
        .order_by(MonthlyClaimsSummaryORM.month)
        .all()
    )
    claims_history = [
        ClaimsHistoryPoint(
            month=m.month, claimsSubmitted=m.claims_submitted, claimsPaid=m.claims_paid,
            claimsDenied=m.claims_denied, claimsPending=m.claims_pending, revenueCollected=m.revenue_collected,
            denialReasons=[DenialReasonBreakdown(**d) for d in json.loads(m.denial_reasons_json)],
        )
        for m in monthly
    ]

    actions = [
        Action(
            id=a.id, title=a.title, description=a.description, priority=a.priority, status=a.status,
            category=a.category, source=a.source, createdAt=a.created_at,
            isRecurring=a.is_recurring, consecutiveQuarters=a.consecutive_quarters,
        )
        for a in p.actions
    ]

    quarterly_history = [
        QuarterlySnapshot(
            quarter=q.quarter, performanceScore=q.performance_score, riskLevel=q.risk_level, trend=q.trend,
            metrics=_metrics(q), peerAverageMetrics=_peer_metrics(q),
        )
        for q in quarters
    ]

    return Provider(
        id=p.id, name=p.name, specialty=p.specialty, facility=p.facility, npi=p.npi, email=p.email,
        practiceType=p.practice_type,
        performanceScore=latest.performance_score, riskLevel=latest.risk_level, trend=latest.trend,
        scoreHistory=score_history, flagged=p.flagged, flagReason=p.flag_reason, reviewed=p.reviewed,
        stuckAtRiskQuarters=_stuck_at_risk_quarters(quarters),
        metrics=_metrics(latest), peerAverageMetrics=_peer_metrics(latest),
        claimsHistory=claims_history, actions=actions, quarterlyHistory=quarterly_history,
    )


def set_flag(db: Session, provider_id: str, flagged: bool | None, reviewed: bool | None) -> Provider | None:
    p = db.get(ProviderORM, provider_id)
    if p is None:
        return None
    if flagged is not None:
        p.flagged = flagged
    if reviewed is not None:
        p.reviewed = reviewed
    db.commit()
    return get_provider(db, provider_id)


def set_action_status(db: Session, provider_id: str, action_id: str, status: str) -> Provider | None:
    action = db.query(ActionORM).filter_by(id=action_id, provider_id=provider_id).first()
    if action is None:
        return None
    action.status = status
    db.commit()
    return get_provider(db, provider_id)


def summary(db: Session, practice_type: str | None = None) -> DashboardSummary:
    providers = list_providers(db, practice_type)
    if not providers:
        return DashboardSummary(
            totalProviders=0, averageScore=0, criticalHighRiskCount=0, flaggedCount=0,
            topPerformerId="", topPerformerName="", topPerformerScore=0,
        )
    total = len(providers)
    avg_score = round(sum(p.performanceScore for p in providers) / total, 1)
    critical_high = sum(1 for p in providers if p.riskLevel in ("critical", "high"))
    flagged_count = sum(1 for p in providers if p.flagged and not p.reviewed)
    top = providers[0]
    return DashboardSummary(
        totalProviders=total, averageScore=avg_score, criticalHighRiskCount=critical_high,
        flaggedCount=flagged_count, topPerformerId=top.id, topPerformerName=top.name,
        topPerformerScore=top.performanceScore,
    )


def get_quarterly_history(db: Session, provider_id: str) -> list[QuarterlySnapshot] | None:
    p = db.get(ProviderORM, provider_id)
    if p is None:
        return None
    return [
        QuarterlySnapshot(
            quarter=q.quarter, performanceScore=q.performance_score, riskLevel=q.risk_level, trend=q.trend,
            metrics=_metrics(q), peerAverageMetrics=_peer_metrics(q),
        )
        for q in _sorted_quarters(p)
    ]


def get_claims(
    db: Session, provider_id: str, page: int = 1, page_size: int = 20,
    status: str | None = None, quarter: str | None = None,
) -> ClaimsPage | None:
    p = db.get(ProviderORM, provider_id)
    if p is None:
        return None
    query = db.query(ClaimORM).filter_by(provider_id=provider_id)
    if status:
        query = query.filter_by(status=status)
    if quarter:
        query = query.filter_by(quarter=quarter)
    total = query.count()
    rows = query.order_by(ClaimORM.claim_date.desc()).offset((page - 1) * page_size).limit(page_size).all()
    claims = [
        ClaimSummary(
            id=c.id, providerId=c.provider_id, claimDate=c.claim_date, quarter=c.quarter, payer=c.payer,
            amountBilled=c.amount_billed, amountPaid=c.amount_paid, status=c.status, denialReason=c.denial_reason,
        )
        for c in rows
    ]
    return ClaimsPage(claims=claims, total=total, page=page, pageSize=page_size)


def get_claim_detail(db: Session, provider_id: str, claim_id: str) -> ClaimDetail | None:
    c = db.query(ClaimORM).filter_by(provider_id=provider_id, id=claim_id).first()
    if c is None:
        return None
    events = sorted(c.events, key=lambda e: e.sequence)
    status_history = [ClaimStatusEvent(status=e.status, eventDate=e.event_date, note=e.note) for e in events]

    is_recurring = False
    if c.denial_reason:
        other_quarters = (
            db.query(ClaimORM.quarter)
            .filter(
                ClaimORM.provider_id == provider_id,
                ClaimORM.denial_reason == c.denial_reason,
                ClaimORM.id != c.id,
            )
            .distinct()
            .count()
        )
        is_recurring = other_quarters >= 2

    related_action_ids: list[str] = []
    if c.status in ("denied", "resubmitted"):
        related_action_ids = [
            a.id for a in db.query(ActionORM).filter_by(provider_id=provider_id, category="denials").all()
        ]

    procedure_code, procedure_description = _procedure_for_claim(c.id)
    is_clean_claim = c.status == "paid" and not any(e.status == "denied" for e in events)
    days_to_resolution = None
    if len(events) >= 2:
        first = date.fromisoformat(events[0].event_date)
        last = date.fromisoformat(events[-1].event_date)
        days_to_resolution = (last - first).days

    return ClaimDetail(
        id=c.id, providerId=c.provider_id, claimDate=c.claim_date, quarter=c.quarter, payer=c.payer,
        amountBilled=c.amount_billed, amountPaid=c.amount_paid, status=c.status, denialReason=c.denial_reason,
        statusHistory=status_history, isRecurringDenial=is_recurring, relatedActionIds=related_action_ids,
        procedureCode=procedure_code, procedureDescription=procedure_description,
        isCleanClaim=is_clean_claim, daysToResolution=days_to_resolution,
    )


def get_claims_status_summary(db: Session, provider_id: str, quarter: str | None = None) -> ClaimsStatusSummary | None:
    p = db.get(ProviderORM, provider_id)
    if p is None:
        return None
    query = db.query(ClaimORM).filter_by(provider_id=provider_id)
    if quarter:
        query = query.filter_by(quarter=quarter)
    counts = {"paid": 0, "denied": 0, "pending": 0, "resubmitted": 0}
    total = 0
    for (status,) in query.with_entities(ClaimORM.status).all():
        counts[status] = counts.get(status, 0) + 1
        total += 1
    return ClaimsStatusSummary(
        paid=counts["paid"], denied=counts["denied"], pending=counts["pending"],
        resubmitted=counts["resubmitted"], total=total,
    )


def search_providers(
    db: Session, query: str | None = None, specialty: str | None = None, facility: str | None = None,
    risk_level: str | None = None, flagged_only: bool = False, stuck_at_risk_only: bool = False, limit: int = 20,
) -> list[ProviderSummary]:
    results = list_providers(db)
    if query:
        q = query.lower()
        results = [p for p in results if q in p.name.lower() or q in p.specialty.lower() or q in p.facility.lower()]
    if specialty:
        results = [p for p in results if p.specialty.lower() == specialty.lower()]
    if facility:
        results = [p for p in results if p.facility.lower() == facility.lower()]
    if risk_level:
        results = [p for p in results if p.riskLevel == risk_level]
    if flagged_only:
        results = [p for p in results if p.flagged and not p.reviewed]
    if stuck_at_risk_only:
        results = [p for p in results if p.stuckAtRiskQuarters >= STUCK_AT_RISK_THRESHOLD]
    return results[:limit]


def compare_providers(db: Session, provider_ids: list[str]) -> list[Provider]:
    out = []
    for pid in provider_ids:
        p = get_provider(db, pid)
        if p is not None:
            out.append(p)
    return out


def summarize_department(db: Session, group_by: str, value: str) -> dict | None:
    providers = list_providers(db)
    if group_by == "facility":
        group = [p for p in providers if p.facility.lower() == value.lower()]
    else:
        group = [p for p in providers if p.specialty.lower() == value.lower()]
    if not group:
        return None
    avg_score = round(sum(p.performanceScore for p in group) / len(group), 1)
    avg_denial = round(sum(p.denialRate for p in group) / len(group), 1)
    stuck_count = sum(1 for p in group if p.stuckAtRiskQuarters >= STUCK_AT_RISK_THRESHOLD)
    top = max(group, key=lambda p: p.performanceScore)
    bottom = min(group, key=lambda p: p.performanceScore)
    return {
        "groupBy": group_by, "value": value, "providerCount": len(group),
        "averageScore": avg_score, "averageDenialRate": avg_denial, "stuckAtRiskCount": stuck_count,
        "topPerformer": top.name, "bottomPerformer": bottom.name,
    }


def get_demo_accounts(db: Session) -> list[DemoAccount]:
    descriptions = {
        "practice_admin": "Full access to every provider, report, and admin action.",
        "clinical_analyst": "Reviews performance data and generates reports.",
    }
    return [
        DemoAccount(id=u.id, email=u.email, displayName=u.display_name, role=u.role, description=descriptions.get(u.role, ""))
        for u in db.query(UserORM).all()
    ]


def next_provider_id(db: Session) -> str:
    max_n = 0
    for (pid,) in db.query(ProviderORM.id).all():
        try:
            n = int(pid.split("-")[-1])
        except ValueError:
            continue
        max_n = max(max_n, n)
    return f"prov-{max_n + 1:03d}"


def add_generated_provider(db: Session, generated: dict) -> Provider:
    seed_db.insert_provider(db, generated)
    db.commit()
    return get_provider(db, generated["id"])


def _provider_names(db: Session, provider_ids: list[str]) -> list[str]:
    rows = db.query(ProviderORM.id, ProviderORM.name).filter(ProviderORM.id.in_(provider_ids)).all()
    by_id = {pid: name for pid, name in rows}
    return [by_id.get(pid, pid) for pid in provider_ids]


def _provider_emails(db: Session, provider_ids: list[str]) -> list[str]:
    rows = db.query(ProviderORM.id, ProviderORM.email).filter(ProviderORM.id.in_(provider_ids)).all()
    by_id = {pid: email for pid, email in rows}
    return [by_id.get(pid, "") for pid in provider_ids if by_id.get(pid, "")]


def send_email(
    db: Session, provider_ids: list[str], subject: str, body: str,
    related_appointment_id: str | None = None, sent_by: str = "",
) -> EmailMessage:
    recipients = _provider_emails(db, provider_ids)
    row = EmailMessageORM(
        id=f"eml-{uuid.uuid4().hex[:10]}",
        provider_ids_json=json.dumps(provider_ids),
        recipients_json=json.dumps(recipients),
        subject=subject, body=body,
        related_appointment_id=related_appointment_id, sent_by=sent_by,
    )
    db.add(row)
    db.commit()
    return EmailMessage(
        id=row.id, providerIds=provider_ids, recipients=recipients, subject=subject, body=body,
        relatedAppointmentId=related_appointment_id, sentAt=row.sent_at.isoformat(),
    )


def list_emails(db: Session, provider_id: str | None = None, sent_by: str | None = None) -> list[EmailMessage]:
    rows = db.query(EmailMessageORM).order_by(EmailMessageORM.sent_at.desc()).all()
    out = []
    for row in rows:
        provider_ids = json.loads(row.provider_ids_json)
        if provider_id and provider_id not in provider_ids:
            continue
        if sent_by and row.sent_by != sent_by:
            continue
        out.append(EmailMessage(
            id=row.id, providerIds=provider_ids, recipients=json.loads(row.recipients_json),
            subject=row.subject, body=row.body, relatedAppointmentId=row.related_appointment_id,
            sentAt=row.sent_at.isoformat(),
        ))
    return out


def create_appointment(
    db: Session, provider_ids: list[str], topic: str, agenda: str, scheduled_at: str,
    send_confirmation_email: bool = True, created_by: str = "",
) -> Appointment:
    appt_id = f"apt-{uuid.uuid4().hex[:10]}"
    row = AppointmentORM(
        id=appt_id, provider_ids_json=json.dumps(provider_ids), topic=topic,
        agenda=agenda, scheduled_at=scheduled_at, status="confirmed", created_by=created_by,
    )
    db.add(row)
    db.commit()

    names = _provider_names(db, provider_ids)
    if send_confirmation_email:
        subject = f"Meeting scheduled: {topic}"
        body = (
            f"Hello,\n\nA meeting has been scheduled to discuss: {topic}\n"
            f"When: {scheduled_at}\n"
            f"Attendees: {', '.join(names)}\n\n"
            f"Agenda:\n{agenda or '(no agenda provided)'}\n\n"
            f"-- Clearview Medical Group"
        )
        send_email(db, provider_ids, subject, body, related_appointment_id=appt_id, sent_by=created_by or "system")

    return Appointment(
        id=row.id, providerIds=provider_ids, providerNames=names, topic=topic, agenda=agenda,
        scheduledAt=scheduled_at, status=row.status, createdAt=row.created_at.isoformat(),
    )


def list_appointments(
    db: Session, provider_id: str | None = None, created_by: str | None = None
) -> list[Appointment]:
    rows = db.query(AppointmentORM).order_by(AppointmentORM.scheduled_at.desc()).all()
    out = []
    for row in rows:
        provider_ids = json.loads(row.provider_ids_json)
        if provider_id and provider_id not in provider_ids:
            continue
        if created_by and row.created_by != created_by:
            continue
        out.append(Appointment(
            id=row.id, providerIds=provider_ids, providerNames=_provider_names(db, provider_ids),
            topic=row.topic, agenda=row.agenda, scheduledAt=row.scheduled_at, status=row.status,
            createdAt=row.created_at.isoformat(),
        ))
    return out
