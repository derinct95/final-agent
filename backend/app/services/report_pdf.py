"""Missing-data-safe PDF/CSV report generation. Every cell is routed through
fmt_value() before rendering -- null/NaN/empty/"undefined" always become a
clear placeholder, never a blank cell or the literal string "undefined"."""

import csv
import io
import math

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models import PracticeReviewReport, Provider

PLACEHOLDER = "—"  # em dash

COMPARE_METRIC_DEFS = [
    ("Clean Claim Rate (%)", "cleanClaimRate"), ("Denial Rate (%)", "denialRate"),
    ("Days in AR", "daysInAR"), ("First-Pass Resolution (%)", "firstPassResolutionRate"),
    ("Coding Accuracy (%)", "codingAccuracy"), ("Prior-Auth Approval (%)", "priorAuthApprovalRate"),
    ("Net Collection Rate (%)", "netCollectionRate"), ("Avg Reimbursement / Claim ($)", "avgReimbursementPerClaim"),
    ("Documentation Accuracy (%)", "documentationAccuracy"), ("Patient Satisfaction (%)", "patientSatisfactionScore"),
    ("Clinical Quality Score (%)", "clinicalQualityScore"), ("Patient Visits / Month", "patientVisitsMonthly"),
    ("Patient Portal Adoption (%)", "patientPortalAdoptionRate"),
]

RISK_COLORS = {
    "low": colors.HexColor("#0ca30c"),
    "medium": colors.HexColor("#fab219"),
    "high": colors.HexColor("#ec835a"),
    "critical": colors.HexColor("#d03b3b"),
}
ACCENT_BLUE = colors.HexColor("#2a78d6")
ACCENT_GREY = colors.HexColor("#898781")


def fmt_value(value, suffix: str = "", placeholder: str = PLACEHOLDER) -> str:
    if value is None:
        return placeholder
    if isinstance(value, float) and math.isnan(value):
        return placeholder
    s = str(value)
    if s.strip() == "":
        return placeholder
    if s.strip().lower() in ("undefined", "nan", "none"):
        return placeholder
    return f"{s}{suffix}"


def _table(rows: list[list[str]], header: bool = False) -> Table:
    t = Table(rows, hAlign="LEFT")
    style = [
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e1e0d9")),
    ]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f4f3f0")))
        style.append(("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"))
    t.setStyle(TableStyle(style))
    return t


def _period_text(period_range: tuple[str, str] | None, granularity: str) -> str:
    if not period_range:
        return "All available history"
    unit = {"week": "Weeks", "month": "Months", "quarter": "Quarters", "year": "Years"}.get(granularity, "Periods")
    if period_range[0] == period_range[1]:
        return f"{unit[:-1]} {period_range[0]}"
    return f"{unit} {period_range[0]} to {period_range[1]}"


def _percent_metrics_chart(m, peer) -> Drawing:
    """Grouped bar chart of every 0-100-scale metric, provider vs. peer.
    Denial rate is inverted to 'denial control' so every bar reads higher-is-better,
    matching the same convention used by the dashboard's radar chart."""
    labels = [
        "Clean Claim", "Denial Ctrl", "1st-Pass Res.", "Coding Acc.",
        "Prior-Auth", "Net Collect.", "Doc. Acc.", "Pt. Satisfaction",
        "Clinical Qual.", "Portal Adopt.",
    ]
    provider_values = [
        m.cleanClaimRate, 100 - m.denialRate, m.firstPassResolutionRate, m.codingAccuracy,
        m.priorAuthApprovalRate, m.netCollectionRate, m.documentationAccuracy, m.patientSatisfactionScore,
        m.clinicalQualityScore, m.patientPortalAdoptionRate,
    ]
    peer_values = [
        peer.cleanClaimRate, 100 - peer.denialRate, peer.firstPassResolutionRate, peer.codingAccuracy,
        peer.priorAuthApprovalRate, peer.netCollectionRate, peer.documentationAccuracy, peer.patientSatisfactionScore,
        peer.clinicalQualityScore, peer.patientPortalAdoptionRate,
    ]

    drawing = Drawing(460, 210)
    chart = VerticalBarChart()
    chart.x = 40
    chart.y = 35
    chart.height = 140
    chart.width = 400
    chart.data = [provider_values, peer_values]
    chart.categoryAxis.categoryNames = labels
    chart.categoryAxis.labels.fontSize = 6.5
    chart.categoryAxis.labels.angle = 20
    chart.categoryAxis.labels.dy = -12
    chart.categoryAxis.labels.dx = -4
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = 100
    chart.valueAxis.labels.fontSize = 7
    chart.bars[0].fillColor = ACCENT_BLUE
    chart.bars[1].fillColor = ACCENT_GREY
    chart.barWidth = 6
    chart.groupSpacing = 10
    drawing.add(chart)

    legend = Legend()
    legend.x = 40
    legend.y = 195
    legend.dx = 8
    legend.dy = 8
    legend.fontSize = 7.5
    legend.colorNamePairs = [(ACCENT_BLUE, "Provider"), (ACCENT_GREY, "Peer Average")]
    drawing.add(legend)
    return drawing


def _claims_pie_chart(paid: float, denied: float, pending: float) -> Drawing | None:
    palette = [colors.HexColor("#0ca30c"), colors.HexColor("#d03b3b"), colors.HexColor("#fab219")]
    pairs = [("Paid", paid, palette[0]), ("Denied", denied, palette[1]), ("Pending", pending, palette[2])]
    pairs = [p for p in pairs if p[1] > 0]
    if not pairs:
        return None

    drawing = Drawing(260, 150)
    pie = Pie()
    pie.x = 55
    pie.y = 10
    pie.width = 130
    pie.height = 130
    pie.data = [p[1] for p in pairs]
    pie.labels = [f"{p[0]} ({int(p[1])})" for p in pairs]
    pie.slices.strokeWidth = 1
    pie.slices.strokeColor = colors.white
    pie.simpleLabels = True
    pie.slices.fontSize = 7.5
    for i, p in enumerate(pairs):
        pie.slices[i].fillColor = p[2]
    drawing.add(pie)
    return drawing


def _claims_totals(provider: Provider) -> dict:
    history = provider.claimsHistory
    denial_tally: dict[str, int] = {}
    for h in history:
        for d in h.denialReasons:
            denial_tally[d.reason] = denial_tally.get(d.reason, 0) + d.count
    top_reason = max(denial_tally.items(), key=lambda x: x[1])[0] if denial_tally else None
    return {
        "submitted": sum(h.claimsSubmitted for h in history),
        "paid": sum(h.claimsPaid for h in history),
        "denied": sum(h.claimsDenied for h in history),
        "pending": sum(h.claimsPending for h in history),
        "revenue": sum(h.revenueCollected for h in history),
        "topReason": top_reason,
        "hasHistory": bool(history),
    }


def _claims_summary_rows(totals: dict) -> list[list[str]]:
    has = totals["hasHistory"]
    return [
        ["Claims Submitted (trailing 12mo)", fmt_value(totals["submitted"] if has else None)],
        ["Claims Paid", fmt_value(totals["paid"] if has else None)],
        ["Claims Denied", fmt_value(totals["denied"] if has else None)],
        ["Claims Pending", fmt_value(totals["pending"] if has else None)],
        ["Revenue Collected", fmt_value(f"${totals['revenue']:,.0f}" if has else None)],
        ["Leading Denial Reason", fmt_value(totals["topReason"])],
    ]


def build_provider_report_pdf(
    provider: Provider, period_range: tuple[str, str] | None = None, granularity: str = "quarter",
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, title=f"{provider.name} Performance Report",
                             topMargin=0.6 * inch, bottomMargin=0.6 * inch)
    styles = getSampleStyleSheet()
    heading_style = ParagraphStyle("ColorHeading3", parent=styles["Heading3"], textColor=ACCENT_BLUE)
    elements = [
        Paragraph("Clearview Medical Group — Provider Performance Report", styles["Title"]),
        Paragraph("Synthetic data only — no real patient or provider PHI.", styles["Italic"]),
        Spacer(1, 12),
        Paragraph(f"{provider.name} — {provider.specialty} — {provider.facility}", styles["Heading2"]),
    ]
    elements.append(Paragraph(f"Reporting period: {fmt_value(_period_text(period_range, granularity))}", styles["Normal"]))
    elements.append(Spacer(1, 8))

    identity_table = _table([
        ["NPI", fmt_value(provider.npi)],
        ["Email", fmt_value(provider.email)],
        ["Performance Score", fmt_value(provider.performanceScore)],
        ["Risk Level", fmt_value(provider.riskLevel)],
        ["Trend", fmt_value(provider.trend)],
        ["Stuck at Risk (consecutive quarters)", fmt_value(provider.stuckAtRiskQuarters)],
        ["Flagged", fmt_value(provider.flagged)],
        ["Flag Reason", fmt_value(provider.flagReason)],
    ])
    risk_color = RISK_COLORS.get(provider.riskLevel)
    if risk_color:
        identity_table.setStyle(TableStyle([
            ("BACKGROUND", (1, 3), (1, 3), risk_color),
            ("TEXTCOLOR", (1, 3), (1, 3), colors.white),
            ("FONTNAME", (1, 3), (1, 3), "Helvetica-Bold"),
        ]))
    elements.append(identity_table)
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("Metrics vs. Peer Average", heading_style))
    m, peer = provider.metrics, provider.peerAverageMetrics
    metric_rows = [["Metric", "Provider", "Peer Average"]]
    for label, v, p in [
        ("Clean Claim Rate (%)", m.cleanClaimRate, peer.cleanClaimRate),
        ("Denial Rate (%)", m.denialRate, peer.denialRate),
        ("Days in AR", m.daysInAR, peer.daysInAR),
        ("First-Pass Resolution (%)", m.firstPassResolutionRate, peer.firstPassResolutionRate),
        ("Coding Accuracy (%)", m.codingAccuracy, peer.codingAccuracy),
        ("Prior-Auth Approval (%)", m.priorAuthApprovalRate, peer.priorAuthApprovalRate),
        ("Net Collection Rate (%)", m.netCollectionRate, peer.netCollectionRate),
        ("Avg Reimbursement / Claim ($)", m.avgReimbursementPerClaim, peer.avgReimbursementPerClaim),
        ("Documentation Accuracy (%)", m.documentationAccuracy, peer.documentationAccuracy),
        ("Patient Satisfaction (%)", m.patientSatisfactionScore, peer.patientSatisfactionScore),
    ]:
        metric_rows.append([label, fmt_value(v), fmt_value(p)])
    elements.append(_table(metric_rows, header=True))
    elements.append(Spacer(1, 10))
    elements.append(_percent_metrics_chart(m, peer))
    elements.append(Spacer(1, 14))

    totals = _claims_totals(provider)
    elements.append(Paragraph("Claims Summary", heading_style))
    elements.append(_table(_claims_summary_rows(totals)))
    elements.append(Spacer(1, 10))
    pie = _claims_pie_chart(totals["paid"], totals["denied"], totals["pending"])
    if pie:
        elements.append(pie)
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("Actions", heading_style))
    if provider.actions:
        action_rows = [["Title", "Priority", "Status", "Recurring"]]
        for a in provider.actions:
            action_rows.append([fmt_value(a.title), fmt_value(a.priority), fmt_value(a.status), "Yes" if a.isRecurring else "No"])
        elements.append(_table(action_rows, header=True))
    else:
        elements.append(Paragraph("No data for this period.", styles["Normal"]))

    doc.build(elements)
    return buffer.getvalue()


def build_provider_report_csv(
    provider: Provider, period_range: tuple[str, str] | None = None, granularity: str = "quarter",
) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Clearview Medical Group — Provider Performance Report (Synthetic Data Only)"])
    writer.writerow(["Provider", fmt_value(provider.name)])
    writer.writerow(["Specialty", fmt_value(provider.specialty)])
    writer.writerow(["Facility", fmt_value(provider.facility)])
    writer.writerow(["NPI", fmt_value(provider.npi)])
    writer.writerow(["Email", fmt_value(provider.email)])
    writer.writerow(["Reporting Period", fmt_value(_period_text(period_range, granularity))])
    writer.writerow([])
    writer.writerow(["Performance Score", fmt_value(provider.performanceScore)])
    writer.writerow(["Risk Level", fmt_value(provider.riskLevel)])
    writer.writerow(["Stuck at Risk (quarters)", fmt_value(provider.stuckAtRiskQuarters)])
    writer.writerow([])
    writer.writerow(["Metric", "Provider", "Peer Average"])
    m, peer = provider.metrics, provider.peerAverageMetrics
    for label, v, p in [
        ("Clean Claim Rate (%)", m.cleanClaimRate, peer.cleanClaimRate),
        ("Denial Rate (%)", m.denialRate, peer.denialRate),
        ("Days in AR", m.daysInAR, peer.daysInAR),
        ("First-Pass Resolution (%)", m.firstPassResolutionRate, peer.firstPassResolutionRate),
        ("Coding Accuracy (%)", m.codingAccuracy, peer.codingAccuracy),
        ("Prior-Auth Approval (%)", m.priorAuthApprovalRate, peer.priorAuthApprovalRate),
        ("Net Collection Rate (%)", m.netCollectionRate, peer.netCollectionRate),
        ("Avg Reimbursement / Claim ($)", m.avgReimbursementPerClaim, peer.avgReimbursementPerClaim),
        ("Documentation Accuracy (%)", m.documentationAccuracy, peer.documentationAccuracy),
        ("Patient Satisfaction (%)", m.patientSatisfactionScore, peer.patientSatisfactionScore),
    ]:
        writer.writerow([label, fmt_value(v), fmt_value(p)])
    writer.writerow([])
    writer.writerow(["Claims Summary"])
    for row in _claims_summary_rows(_claims_totals(provider)):
        writer.writerow(row)
    writer.writerow([])
    writer.writerow(["Actions"])
    writer.writerow(["Title", "Priority", "Status", "Recurring"])
    for a in provider.actions:
        writer.writerow([fmt_value(a.title), fmt_value(a.priority), fmt_value(a.status), "Yes" if a.isRecurring else "No"])
    return buf.getvalue().encode("utf-8")


def _score_comparison_chart(providers: list[Provider]) -> Drawing:
    values = [p.performanceScore for p in providers]
    names = [p.name.replace("Dr. ", "") for p in providers]

    drawing = Drawing(460, 190)
    chart = VerticalBarChart()
    chart.x = 50
    chart.y = 40
    chart.height = 125
    chart.width = 380
    chart.data = [values]
    chart.categoryAxis.categoryNames = names
    chart.categoryAxis.labels.fontSize = 7.5
    chart.categoryAxis.labels.angle = 15
    chart.categoryAxis.labels.dy = -10
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = 100
    chart.valueAxis.labels.fontSize = 7
    chart.barWidth = 16
    chart.groupSpacing = 14
    for i, p in enumerate(providers):
        chart.bars[(0, i)].fillColor = RISK_COLORS.get(p.riskLevel, ACCENT_GREY)
    drawing.add(chart)
    return drawing


def build_compare_report_pdf(providers: list[Provider]) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, title="Clearview Provider Comparison",
                             topMargin=0.6 * inch, bottomMargin=0.6 * inch)
    styles = getSampleStyleSheet()
    heading_style = ParagraphStyle("ColorHeading3", parent=styles["Heading3"], textColor=ACCENT_BLUE)
    elements = [
        Paragraph("Clearview Medical Group — Provider Comparison Report", styles["Title"]),
        Paragraph("Synthetic data only — no real patient or provider PHI.", styles["Italic"]),
        Spacer(1, 10),
        Paragraph(" vs. ".join(p.name for p in providers), styles["Heading2"]),
        Spacer(1, 8),
    ]

    identity_rows = [["Provider", "Specialty", "Facility", "Score", "Risk", "Trend"]]
    for p in providers:
        identity_rows.append([
            fmt_value(p.name), fmt_value(p.specialty), fmt_value(p.facility),
            fmt_value(p.performanceScore), fmt_value(p.riskLevel), fmt_value(p.trend),
        ])
    identity_table = _table(identity_rows, header=True)
    style_cmds = []
    for i, p in enumerate(providers, start=1):
        color = RISK_COLORS.get(p.riskLevel)
        if color:
            style_cmds += [
                ("BACKGROUND", (4, i), (4, i), color),
                ("TEXTCOLOR", (4, i), (4, i), colors.white),
                ("FONTNAME", (4, i), (4, i), "Helvetica-Bold"),
            ]
    if style_cmds:
        identity_table.setStyle(TableStyle(style_cmds))
    elements.append(identity_table)
    elements.append(Spacer(1, 10))
    elements.append(_score_comparison_chart(providers))
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("Metrics Comparison", heading_style))
    header = ["Metric"] + [p.name.replace("Dr. ", "") for p in providers]
    metric_rows = [header]
    for label, key in COMPARE_METRIC_DEFS:
        metric_rows.append([label] + [fmt_value(getattr(p.metrics, key)) for p in providers])
    elements.append(_table(metric_rows, header=True))

    doc.build(elements)
    return buffer.getvalue()


def build_compare_report_csv(providers: list[Provider]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Clearview Medical Group — Provider Comparison Report (Synthetic Data Only)"])
    writer.writerow(["Provider", "Specialty", "Facility", "Score", "Risk", "Trend"])
    for p in providers:
        writer.writerow([
            fmt_value(p.name), fmt_value(p.specialty), fmt_value(p.facility),
            fmt_value(p.performanceScore), fmt_value(p.riskLevel), fmt_value(p.trend),
        ])
    writer.writerow([])
    writer.writerow(["Metric"] + [p.name.replace("Dr. ", "") for p in providers])
    for label, key in COMPARE_METRIC_DEFS:
        writer.writerow([label] + [fmt_value(getattr(p.metrics, key)) for p in providers])
    return buf.getvalue().encode("utf-8")


def build_practice_review_pdf(report: PracticeReviewReport) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, title="Clearview Practice Review",
                             topMargin=0.6 * inch, bottomMargin=0.6 * inch)
    styles = getSampleStyleSheet()
    heading_style = ParagraphStyle("ColorHeading3", parent=styles["Heading3"], textColor=ACCENT_BLUE)
    severity_hex = {"critical": "#d03b3b", "high": "#ec835a", "medium": "#fab219", "info": "#2a78d6"}
    elements = [
        Paragraph("Clearview Medical Group — Practice Review", styles["Title"]),
        Paragraph("Synthetic data only — no real patient or provider PHI.", styles["Italic"]),
        Spacer(1, 6),
        Paragraph(f"{report.period.title()} review — {fmt_value(report.periodLabel)}", styles["Heading2"]),
        Paragraph(f"Generated {fmt_value(report.generatedAt)} ({'Claude-generated' if report.generatedBy == 'ai' else 'rule-based'})", styles["Normal"]),
        Spacer(1, 12),
        Paragraph("Key Findings", heading_style),
    ]
    if report.keyFindings:
        for f in report.keyFindings:
            color_hex = severity_hex.get(f.severity, "#898781")
            elements.append(Paragraph(
                f'<font color="{color_hex}"><b>[{f.severity.upper()}]</b></font> '
                f"<b>{fmt_value(f.title)}</b> — {fmt_value(f.narrative)}",
                styles["Normal"],
            ))
            elements.append(Spacer(1, 6))
    else:
        elements.append(Paragraph("No data for this period.", styles["Normal"]))

    elements.append(Spacer(1, 8))
    elements.append(Paragraph("Priority Actions", heading_style))
    if report.priorityActions:
        rows = [["Title", "Priority", "Description"]]
        for a in report.priorityActions:
            rows.append([fmt_value(a.title), fmt_value(a.priority), fmt_value(a.description)])
        elements.append(_table(rows, header=True))
    else:
        elements.append(Paragraph("No data for this period.", styles["Normal"]))

    doc.build(elements)
    return buffer.getvalue()


def build_practice_review_csv(report: PracticeReviewReport) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Clearview Medical Group — Practice Review (Synthetic Data Only)"])
    writer.writerow(["Period", fmt_value(report.period)])
    writer.writerow(["Period Label", fmt_value(report.periodLabel)])
    writer.writerow(["Generated At", fmt_value(report.generatedAt)])
    writer.writerow([])
    writer.writerow(["Key Findings"])
    writer.writerow(["Severity", "Title", "Narrative"])
    for f in report.keyFindings:
        writer.writerow([fmt_value(f.severity), fmt_value(f.title), fmt_value(f.narrative)])
    writer.writerow([])
    writer.writerow(["Priority Actions"])
    writer.writerow(["Priority", "Title", "Description"])
    for a in report.priorityActions:
        writer.writerow([fmt_value(a.priority), fmt_value(a.title), fmt_value(a.description)])
    return buf.getvalue().encode("utf-8")
