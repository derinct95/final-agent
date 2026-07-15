"""Deterministic mock-data generator for Clearview Medical Group.

Claims-first design: individual sample claims and quarterly metric snapshots
are generated per provider; the existing monthly claims-history aggregates
(used by the volume/revenue/denial charts) are generated independently by the
same statistical curve as before -- they are a separate, already-proven view,
not derived 1:1 from the small claims sample (see plan decision notes).

Everything here is seeded so the demo tells the same "story" every run: a
spread of specialties, risk levels, and improving/declining trends.
"""

import random
from datetime import date, timedelta

SPECIALTIES = [
    "Cardiology", "Orthopedics", "Family Medicine", "Internal Medicine",
    "General Surgery", "Dermatology", "Neurology", "Oncology", "Pediatrics",
    "Radiology", "Psychiatry", "Endocrinology", "Gastroenterology",
    "Pulmonology", "Nephrology", "Urology", "OB/GYN", "ENT",
    "Anesthesiology", "Emergency Medicine",
]

FACILITIES = [
    "Riverside Medical Center", "Lakeside Health Clinic", "Summit Regional Hospital",
    "Harborview Care Group", "Meridian Family Practice", "Cedar Grove Medical Associates",
]

DENTAL_SPECIALTIES = [
    "General Dentistry", "Orthodontics", "Endodontics", "Periodontics",
    "Oral & Maxillofacial Surgery", "Pediatric Dentistry", "Prosthodontics", "Cosmetic Dentistry",
]
DENTAL_FACILITIES = ["Clearview Family Dental — Riverside", "Clearview Family Dental — Lakeside"]

VERTICAL_SCORE_BANDS = [(90, 97), (90, 97), (78, 89), (78, 89), (78, 89), (65, 77), (65, 77), (50, 64)]

FIRST_NAMES = [
    "James", "Maria", "Robert", "Linda", "David", "Susan", "Michael", "Karen",
    "William", "Priya", "Wei", "Fatima", "Carlos", "Emily", "Ahmed", "Sofia",
    "Daniel", "Grace", "Thomas", "Nia",
]
LAST_NAMES = [
    "Chen", "Patel", "Nguyen", "Garcia", "Kim", "Johnson", "Okafor", "Rossi",
    "Nakamura", "Smith", "Alvarez", "Cohen", "Anderson", "Silva", "Novak",
    "Brooks", "Hassan", "Larsen", "Reyes", "Whitfield",
]

DENIAL_REASONS = [
    "Missing Prior Authorization", "Coding Error", "Duplicate Claim",
    "Eligibility Issue", "Timely Filing Expired", "Insufficient Documentation",
    "Non-Covered Service", "Medical Necessity Not Established",
]

PAYERS = ["Medicare", "Medicaid", "Aetna", "UnitedHealthcare", "Cigna", "Blue Cross Blue Shield", "Self-Pay"]

ACTION_CATALOG = {
    "denials": ("Launch denial root-cause review", "Denial rate is trending above peer benchmark; convene a 30-min root-cause review with billing to target the top 2 denial reasons."),
    "coding": ("Schedule coding accuracy audit", "Coding accuracy has slipped below target; schedule a chart audit with the coding team and refresher training."),
    "collections": ("Escalate aged AR follow-up", "Days in AR exceed the target threshold; prioritize outstanding claims over 60 days for collections follow-up."),
    "documentation": ("Tighten documentation at point of care", "Insufficient documentation is a recurring denial driver; deploy a point-of-care documentation checklist."),
    "compliance": ("Review prior-authorization workflow", "Prior-auth approval rate is lagging; audit the intake workflow for missed authorization steps."),
}

CATEGORY_CONDITIONS = {
    "denials": lambda m: m["denialRate"] > 12,
    "coding": lambda m: m["codingAccuracy"] < 88,
    "collections": lambda m: m["daysInAR"] > 45,
    "documentation": lambda m: m["documentationAccuracy"] < 88,
    "compliance": lambda m: m["priorAuthApprovalRate"] < 85,
}

# (min_score, max_score) bands, ordered to guarantee a realistic spread across 20 providers
SCORE_BANDS = (
    [(90, 97)] * 4
    + [(78, 89)] * 6
    + [(65, 77)] * 5
    + [(50, 64)] * 3
    + [(35, 49)] * 2
)

NUM_QUARTERS = 8
DEMO_USERS = [
    {"id": "usr-admin", "email": "admin@clearviewmedicalgroup.demo", "display_name": "Practice Administrator", "role": "practice_admin"},
    {"id": "usr-analyst", "email": "analyst@clearviewmedicalgroup.demo", "display_name": "Clinical Analyst", "role": "clinical_analyst"},
]


def _risk_level(score: float) -> str:
    if score >= 85:
        return "low"
    if score >= 70:
        return "medium"
    if score >= 55:
        return "high"
    return "critical"


def _trend_between(prev_score: float, score: float) -> str:
    delta = score - prev_score
    if delta > 3:
        return "up"
    if delta < -3:
        return "down"
    return "flat"


def _score_curve(rng: random.Random, final_score: float, months: int) -> list[float]:
    slope = rng.uniform(-1.2, 1.2)
    history = []
    start = final_score - slope * months
    for i in range(months):
        jitter = rng.uniform(-1.5, 1.5)
        history.append(round(max(0, min(100, start + slope * i + jitter)), 1))
    history[-1] = round(final_score, 1)
    return history


def _lerp(score: float, lo_score: float, hi_score: float, lo_val: float, hi_val: float) -> float:
    t = max(0.0, min(1.0, (score - lo_score) / (hi_score - lo_score)))
    return lo_val + t * (hi_val - lo_val)


def _metrics_for_score(rng: random.Random, score: float) -> dict:
    def jitter(v: float, spread: float) -> float:
        return v + rng.uniform(-spread, spread)

    return {
        "cleanClaimRate": round(max(0, min(100, jitter(_lerp(score, 35, 97, 66, 97), 2.5))), 1),
        "denialRate": round(max(0, min(100, jitter(_lerp(score, 35, 97, 29, 4), 1.5))), 1),
        "daysInAR": round(max(1, jitter(_lerp(score, 35, 97, 88, 27), 4)), 1),
        "firstPassResolutionRate": round(max(0, min(100, jitter(_lerp(score, 35, 97, 61, 96), 2.5))), 1),
        "codingAccuracy": round(max(0, min(100, jitter(_lerp(score, 35, 97, 71, 98), 2))), 1),
        "priorAuthApprovalRate": round(max(0, min(100, jitter(_lerp(score, 35, 97, 66, 97), 2.5))), 1),
        "netCollectionRate": round(max(0, min(100, jitter(_lerp(score, 35, 97, 76, 98.5), 2))), 1),
        "avgReimbursementPerClaim": round(rng.uniform(85, 420), 2),
        "claimsVolumeMonthly": round(rng.uniform(150, 600), 0),
        "documentationAccuracy": round(max(0, min(100, jitter(_lerp(score, 35, 97, 70, 98), 2.5))), 1),
        "patientSatisfactionScore": round(max(0, min(100, jitter(_lerp(score, 35, 97, 58, 96), 3.5))), 1),
        "clinicalQualityScore": round(max(0, min(100, jitter(_lerp(score, 35, 97, 68, 97), 2.5))), 1),
        "patientVisitsMonthly": round(rng.uniform(120, 480), 0),
        "patientPortalAdoptionRate": round(max(0, min(100, jitter(_lerp(score, 35, 97, 40, 92), 3.5))), 1),
    }


def _peer_benchmark(rng: random.Random, metrics: dict) -> dict:
    def jitter(v: float, spread: float) -> float:
        return v + rng.uniform(-spread, spread)

    baseline = {
        "cleanClaimRate": 87.0, "denialRate": 11.0, "daysInAR": 42.0,
        "firstPassResolutionRate": 83.0, "codingAccuracy": 89.0,
        "priorAuthApprovalRate": 86.0, "netCollectionRate": 91.0,
        "documentationAccuracy": 90.0, "patientSatisfactionScore": 82.0,
        "clinicalQualityScore": 85.0, "patientPortalAdoptionRate": 68.0,
    }
    return {
        "cleanClaimRate": round(jitter(baseline["cleanClaimRate"], 3), 1),
        "denialRate": round(max(0, jitter(baseline["denialRate"], 2)), 1),
        "daysInAR": round(max(1, jitter(baseline["daysInAR"], 5)), 1),
        "firstPassResolutionRate": round(jitter(baseline["firstPassResolutionRate"], 3), 1),
        "codingAccuracy": round(jitter(baseline["codingAccuracy"], 2.5), 1),
        "priorAuthApprovalRate": round(jitter(baseline["priorAuthApprovalRate"], 3), 1),
        "netCollectionRate": round(jitter(baseline["netCollectionRate"], 2), 1),
        "avgReimbursementPerClaim": metrics["avgReimbursementPerClaim"],
        "claimsVolumeMonthly": metrics["claimsVolumeMonthly"],
        "documentationAccuracy": round(jitter(baseline["documentationAccuracy"], 2.5), 1),
        "patientSatisfactionScore": round(jitter(baseline["patientSatisfactionScore"], 3.5), 1),
        "clinicalQualityScore": round(jitter(baseline["clinicalQualityScore"], 2.5), 1),
        "patientVisitsMonthly": metrics["patientVisitsMonthly"],
        "patientPortalAdoptionRate": round(jitter(baseline["patientPortalAdoptionRate"], 4), 1),
    }


def _synthetic_email(name: str) -> str:
    slug = name.replace("Dr. ", "").lower().replace(" ", ".")
    return f"{slug}@clearviewmedicalgroup.demo"


def _trailing_month_labels(n: int = 12) -> list[str]:
    today = date.today().replace(day=1)
    return [(today - timedelta(days=30 * i)).strftime("%Y-%m") for i in range(n - 1, -1, -1)]


def _quarter_labels(n: int = NUM_QUARTERS) -> list[str]:
    today = date.today()
    q0 = (today.month - 1) // 3
    labels = []
    for i in range(n):
        offset = q0 - i
        year = today.year
        while offset < 0:
            offset += 4
            year -= 1
        labels.append(f"{year}-Q{offset + 1}")
    labels.reverse()
    return labels


def _quarter_month_range(quarter: str) -> list[tuple[int, int]]:
    year_s, q_s = quarter.split("-Q")
    year, q = int(year_s), int(q_s)
    start_month = (q - 1) * 3 + 1
    return [(year, start_month), (year, start_month + 1), (year, start_month + 2)]


def _claims_history(rng: random.Random, metrics: dict, trend: str) -> list[dict]:
    """Independent monthly aggregate generator (unchanged shape/behavior from Phase 1)."""
    today = date.today().replace(day=1)
    months = [today - timedelta(days=30 * i) for i in range(11, -1, -1)]
    history = []
    base_volume = metrics["claimsVolumeMonthly"]
    base_denial_rate = metrics["denialRate"]

    for idx, month in enumerate(months):
        drift = (idx - 11) * (0.6 if trend == "down" else (-0.4 if trend == "up" else 0.05))
        month_denial_rate = max(1.5, min(45, base_denial_rate - drift + rng.uniform(-1.5, 1.5)))
        submitted = max(20, round(base_volume + rng.uniform(-25, 25)))
        denied = round(submitted * month_denial_rate / 100)
        pending = round(submitted * rng.uniform(0.02, 0.06))
        paid = max(0, submitted - denied - pending)
        revenue = round(paid * metrics["avgReimbursementPerClaim"] * rng.uniform(0.94, 1.06), 2)

        reason_pool = rng.sample(DENIAL_REASONS, k=rng.randint(2, 4))
        remaining = denied
        breakdown = []
        for i, reason in enumerate(reason_pool):
            count = remaining if i == len(reason_pool) - 1 else min(round(remaining * rng.uniform(0.2, 0.5)), remaining)
            remaining -= count
            if count > 0:
                breakdown.append({"reason": reason, "count": count})

        history.append({
            "month": month.strftime("%Y-%m"),
            "claimsSubmitted": submitted, "claimsPaid": paid, "claimsDenied": denied,
            "claimsPending": pending, "revenueCollected": revenue, "denialReasons": breakdown,
        })
    return history


def _generate_quarters(rng: random.Random, final_score: float) -> list[dict]:
    labels = _quarter_labels()
    monthly_scores = _score_curve(rng, final_score, months=NUM_QUARTERS * 3)
    quarters = []
    prev_score = None
    for qi, label in enumerate(labels):
        chunk = monthly_scores[qi * 3:(qi + 1) * 3]
        score = round(sum(chunk) / len(chunk), 1)
        metrics = _metrics_for_score(rng, score)
        peer = _peer_benchmark(rng, metrics)
        risk_level = _risk_level(score)
        trend = _trend_between(prev_score, score) if prev_score is not None else "flat"
        quarters.append({
            "quarter": label, "performanceScore": score, "riskLevel": risk_level,
            "trend": trend, "metrics": metrics, "peerMetrics": peer,
        })
        prev_score = score
    return quarters


def _claim_events(rng: random.Random, claim_date: date, status: str, denial_reason: str | None) -> list[dict]:
    events = [{"status": "submitted", "event_date": claim_date.isoformat(), "note": None, "sequence": 1}]
    if status == "paid":
        events.append({"status": "paid", "event_date": (claim_date + timedelta(days=rng.randint(14, 45))).isoformat(), "note": None, "sequence": 2})
    elif status == "denied":
        events.append({"status": "denied", "event_date": (claim_date + timedelta(days=rng.randint(10, 30))).isoformat(), "note": denial_reason, "sequence": 2})
    elif status == "resubmitted":
        denied_date = claim_date + timedelta(days=rng.randint(10, 25))
        resub_date = denied_date + timedelta(days=rng.randint(5, 20))
        events.append({"status": "denied", "event_date": denied_date.isoformat(), "note": denial_reason, "sequence": 2})
        events.append({"status": "resubmitted", "event_date": resub_date.isoformat(), "note": None, "sequence": 3})
    return events


def _generate_claims(rng: random.Random, provider_idx: int, quarters: list[dict], primary_denial_reason: str) -> list[dict]:
    total_claims = rng.randint(30, 50)
    weights = [max(q["metrics"]["claimsVolumeMonthly"], 1) for q in quarters]
    claims = []
    for i in range(total_claims):
        quarter = rng.choices(quarters, weights=weights, k=1)[0]
        year, month = rng.choice(_quarter_month_range(quarter["quarter"]))
        claim_date = date(year, month, rng.randint(1, 28))
        dr = quarter["metrics"]["denialRate"]

        r = rng.uniform(0, 100)
        if r < dr * 0.65:
            status = "denied"
        elif r < dr * 0.65 + 7:
            status = "resubmitted"
        elif r < dr * 0.65 + 7 + 5:
            status = "pending"
        else:
            status = "paid"

        amount_billed = round(quarter["metrics"]["avgReimbursementPerClaim"] * rng.uniform(0.5, 2.2), 2)
        denial_reason = None
        if status in ("denied", "resubmitted"):
            denial_reason = primary_denial_reason if rng.random() < 0.6 else rng.choice(DENIAL_REASONS)

        if status == "paid":
            amount_paid = round(amount_billed * rng.uniform(0.75, 1.0), 2)
        elif status == "resubmitted" and rng.random() < 0.5:
            amount_paid = round(amount_billed * rng.uniform(0.6, 0.95), 2)
        else:
            amount_paid = 0.0

        claims.append({
            "id": f"clm-{provider_idx:02d}-{i:04d}",
            "claim_date": claim_date.isoformat(),
            "quarter": quarter["quarter"],
            "month": f"{year:04d}-{month:02d}",
            "payer": rng.choice(PAYERS),
            "amount_billed": amount_billed,
            "amount_paid": amount_paid,
            "status": status,
            "denial_reason": denial_reason,
            "events": _claim_events(rng, claim_date, status, denial_reason),
        })
    claims.sort(key=lambda c: c["claim_date"])
    return claims


def _generate_actions(rng: random.Random, quarters: list[dict]) -> list[dict]:
    current = quarters[-1]
    metrics, risk_level = current["metrics"], current["riskLevel"]
    candidates = [cat for cat, cond in CATEGORY_CONDITIONS.items() if cond(metrics)]
    if not candidates:
        candidates = rng.sample(list(ACTION_CATALOG.keys()), k=2)

    priority = {"critical": "high", "high": "high", "medium": "medium", "low": "low"}[risk_level]
    actions = []
    for i, category in enumerate(candidates[:4]):
        title, description = ACTION_CATALOG[category]
        created = date.today() - timedelta(days=rng.randint(1, 60))
        status = rng.choices(["open", "in_progress", "resolved"], weights=[0.5, 0.3, 0.2])[0]

        consecutive = 0
        for q in reversed(quarters):
            if CATEGORY_CONDITIONS[category](q["metrics"]):
                consecutive += 1
            else:
                break

        actions.append({
            "id": f"act-{i}-{rng.randint(1000, 9999)}",
            "title": title, "description": description, "priority": priority,
            "status": status, "category": category,
            "source": rng.choices(["manual", "ai"], weights=[0.6, 0.4])[0],
            "created_at": created.isoformat(),
            "is_recurring": consecutive >= 2,
            "consecutive_quarters": consecutive,
        })
    return actions


def generate_one_provider(
    rng: random.Random,
    provider_id: str,
    name: str,
    specialty: str,
    facility: str,
    npi: str,
    final_score: float,
    source: str = "seed",
    claims_seed_index: int = 0,
    practice_type: str = "medical",
) -> dict:
    """Build one fully-fleshed provider record (quarters/claims/actions/etc.) from
    just an identity + a final performance score. Reused by both the deterministic
    20-provider seed and the CSV/FHIR/HL7 import backfill path, so imported
    providers get complete, consistent synthetic data regardless of source."""
    quarters = _generate_quarters(rng, final_score)
    current = quarters[-1]

    primary_denial_reason = rng.choice(DENIAL_REASONS)
    claims = _generate_claims(rng, claims_seed_index, quarters, primary_denial_reason)
    actions = _generate_actions(rng, quarters)
    monthly_claims_history = _claims_history(rng, current["metrics"], current["trend"])
    score_history_24mo = _score_curve(rng, final_score, months=NUM_QUARTERS * 3)

    risk_level = current["riskLevel"]
    flagged = risk_level in ("high", "critical")
    flag_reason = None
    if flagged:
        m, peer = current["metrics"], current["peerMetrics"]
        worst = min(
            [
                ("denial rate", m["denialRate"], m["denialRate"] > 15),
                ("days in AR", m["daysInAR"], m["daysInAR"] > 55),
                ("coding accuracy", m["codingAccuracy"], m["codingAccuracy"] < 80),
            ],
            key=lambda x: x[1] if x[2] else 999,
        )
        flag_reason = {
            "denial rate": f"Denial rate elevated at {m['denialRate']}% (peer avg {peer['denialRate']}%)",
            "days in AR": f"Days in AR elevated at {m['daysInAR']} days (peer avg {peer['daysInAR']})",
            "coding accuracy": f"Coding accuracy low at {m['codingAccuracy']}% (peer avg {peer['codingAccuracy']})",
        }[worst[0]]

    return {
        "id": provider_id,
        "name": name,
        "specialty": specialty,
        "facility": facility,
        "npi": npi,
        "email": _synthetic_email(name),
        "flagged": flagged,
        "flag_reason": flag_reason,
        "reviewed": flagged and rng.random() < 0.3,
        "source": source,
        "practice_type": practice_type,
        "score_history_monthly": score_history_24mo[-12:],
        "score_history_months": _trailing_month_labels(12),
        "quarters": quarters,
        "claims": claims,
        "monthly_claims_history": monthly_claims_history,
        "actions": actions,
    }


def _generate_vertical_providers(
    rng: random.Random, specialties: list[str], facilities: list[str], practice_type: str,
    id_prefix: str, count: int, first_names: list[str], last_names: list[str], claims_seed_offset: int,
) -> list[dict]:
    """Generates an additional provider cohort for a non-medical vertical (dental),
    reusing the same generate_one_provider pipeline so these providers get fully
    consistent synthetic quarters/claims/actions data. Name pairing is offset from
    the medical cohort's so full names don't exactly repeat."""
    specialties = specialties[:]
    rng.shuffle(specialties)
    bands = VERTICAL_SCORE_BANDS[:]
    rng.shuffle(bands)

    providers = []
    for i in range(count):
        lo, hi = bands[i % len(bands)]
        final_score = round(rng.uniform(lo, hi), 1)
        first = first_names[i % len(first_names)]
        last = last_names[(i + 7) % len(last_names)]
        providers.append(generate_one_provider(
            rng,
            provider_id=f"{id_prefix}-{i + 1:03d}",
            name=f"Dr. {first} {last}",
            specialty=specialties[i % len(specialties)],
            facility=rng.choice(facilities),
            npi=f"{rng.randint(1000000000, 9999999999)}",
            final_score=final_score,
            source="seed",
            claims_seed_index=claims_seed_offset + i,
            practice_type=practice_type,
        ))
    return providers


def generate_providers(seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    specialties = SPECIALTIES[:]
    rng.shuffle(specialties)
    bands = SCORE_BANDS[:]
    rng.shuffle(bands)
    first_names = FIRST_NAMES[:]
    last_names = LAST_NAMES[:]
    rng.shuffle(first_names)
    rng.shuffle(last_names)

    providers = []
    for i in range(20):
        lo, hi = bands[i]
        final_score = round(rng.uniform(lo, hi), 1)
        providers.append(generate_one_provider(
            rng,
            provider_id=f"prov-{i + 1:03d}",
            name=f"Dr. {first_names[i]} {last_names[i]}",
            specialty=specialties[i],
            facility=rng.choice(FACILITIES),
            npi=f"{rng.randint(1000000000, 9999999999)}",
            final_score=final_score,
            source="seed",
            claims_seed_index=i,
            practice_type="medical",
        ))

    providers += _generate_vertical_providers(
        rng, DENTAL_SPECIALTIES, DENTAL_FACILITIES, "dental", "dent", 8, first_names, last_names, 1000,
    )

    return providers


def demo_users() -> list[dict]:
    return DEMO_USERS
