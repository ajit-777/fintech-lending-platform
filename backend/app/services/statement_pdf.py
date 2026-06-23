"""Generates a borrower account statement PDF for a loan."""
import io
from datetime import date, datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models.disbursement import Disbursement
from app.models.loan_application import LoanApplication
from app.models.repayment import RepaymentInstallment
from app.models.user import User

_BRAND = colors.HexColor("#4338ca")   # indigo-700
_LIGHT = colors.HexColor("#f0f4ff")
_GREY  = colors.HexColor("#6b7280")
_RED   = colors.HexColor("#dc2626")
_GREEN = colors.HexColor("#16a34a")


def _fmt_date(d) -> str:
    if d is None:
        return "—"
    if isinstance(d, (datetime,)):
        d = d.date()
    return d.strftime("%d %b %Y")


def _fmt_inr(amount) -> str:
    return f"₹{float(amount):,.2f}"


def generate(
    loan: LoanApplication,
    user: User,
    installments: list[RepaymentInstallment],
    disbursement: Disbursement | None,
) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"Loan Statement — {str(loan.id)[:8].upper()}",
    )

    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    heading = ParagraphStyle("heading", fontSize=18, textColor=_BRAND, spaceAfter=2, fontName="Helvetica-Bold")
    sub     = ParagraphStyle("sub", fontSize=9, textColor=_GREY, spaceAfter=8)
    label   = ParagraphStyle("label", fontSize=8, textColor=_GREY, fontName="Helvetica")
    value   = ParagraphStyle("value", fontSize=10, fontName="Helvetica-Bold", spaceAfter=4)
    section = ParagraphStyle("section", fontSize=11, textColor=_BRAND, fontName="Helvetica-Bold", spaceBefore=12, spaceAfter=6)

    generated_on = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    loan_ref = str(loan.id)[:8].upper()

    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    story.append(Paragraph("Fintech Lending Platform", heading))
    story.append(Paragraph(f"Loan Account Statement  •  Ref: {loan_ref}  •  Generated: {generated_on}", sub))
    story.append(HRFlowable(width="100%", thickness=1, color=_BRAND, spaceAfter=10))

    # ── Borrower + Loan summary grid ─────────────────────────────────────────
    summary_data = [
        ["Borrower", user.email, "Loan Amount", _fmt_inr(loan.amount)],
        ["Phone", user.phone, "Tenure", f"{loan.tenure_months} months"],
        ["Interest Rate", f"{float(loan.annual_interest_rate):.1f}% p.a.", "Processing Fee", _fmt_inr(loan.processing_fee)],
        ["Status", loan.status.upper(), "Disbursal Date",
         _fmt_date(disbursement.disbursed_at if disbursement else None)],
    ]

    col_w = [28*mm, 57*mm, 38*mm, 47*mm]
    summary_table = Table(summary_data, colWidths=col_w)
    summary_table.setStyle(TableStyle([
        ("FONTNAME",    (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 0), (-1, -1), 9),
        ("TEXTCOLOR",   (0, 0), (0, -1), _GREY),
        ("TEXTCOLOR",   (2, 0), (2, -1), _GREY),
        ("FONTNAME",    (1, 0), (1, -1), "Helvetica-Bold"),
        ("FONTNAME",    (3, 0), (3, -1), "Helvetica-Bold"),
        ("TOPPADDING",  (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, _LIGHT]),
        ("GRID",        (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
        ("ROUNDEDCORNERS", [4]),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 10))

    # ── Repayment schedule ────────────────────────────────────────────────────
    story.append(Paragraph("Repayment Schedule", section))

    paid_count   = sum(1 for i in installments if i.status == "paid")
    overdue_count = sum(1 for i in installments if i.status == "overdue")
    total_paid   = sum(float(i.paid_amount or 0) for i in installments if i.status == "paid")
    total_due    = sum(float(i.emi_amount) + float(i.penalty_amount or 0)
                       for i in installments if i.status != "paid")

    summary_row = [
        f"Total EMIs: {len(installments)}",
        f"Paid: {paid_count}",
        f"Overdue: {overdue_count}",
        f"Pending: {len(installments) - paid_count - overdue_count}",
        f"Amount Paid: {_fmt_inr(total_paid)}",
        f"Outstanding: {_fmt_inr(total_due)}",
    ]
    story.append(Paragraph("  |  ".join(summary_row),
                            ParagraphStyle("sm", fontSize=8, textColor=_GREY, spaceAfter=6)))

    headers = ["#", "Due Date", "EMI (₹)", "Principal", "Interest", "Penalty", "Paid On", "Status"]
    col_widths = [8*mm, 24*mm, 22*mm, 22*mm, 20*mm, 18*mm, 24*mm, 18*mm]

    rows = [headers]
    for i in installments:
        status_label = i.status.upper()
        paid_on = _fmt_date(i.paid_at) if i.paid_at else "—"
        rows.append([
            str(i.installment_number),
            _fmt_date(i.due_date),
            f"{float(i.emi_amount):,.0f}",
            f"{float(i.principal):,.0f}",
            f"{float(i.interest):,.0f}",
            f"{float(i.penalty_amount or 0):,.0f}" if float(i.penalty_amount or 0) > 0 else "—",
            paid_on,
            status_label,
        ])

    table = Table(rows, colWidths=col_widths, repeatRows=1)

    cell_styles = [
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("BACKGROUND",    (0, 0), (-1, 0),  _BRAND),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("ALIGN",         (1, 1), (1, -1),  "LEFT"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("GRID",          (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _LIGHT]),
    ]

    # Colour-code status column (last col) per row
    for row_idx, inst in enumerate(installments, start=1):
        if inst.status == "paid":
            cell_styles.append(("TEXTCOLOR", (7, row_idx), (7, row_idx), _GREEN))
        elif inst.status == "overdue":
            cell_styles.append(("TEXTCOLOR", (7, row_idx), (7, row_idx), _RED))

    table.setStyle(TableStyle(cell_styles))
    story.append(table)

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=0.5, color=_GREY))
    story.append(Paragraph(
        "This is a system-generated statement and does not require a signature. "
        "For queries contact support@fintech.com.",
        ParagraphStyle("footer", fontSize=7, textColor=_GREY, spaceBefore=4),
    ))

    doc.build(story)
    return buf.getvalue()
