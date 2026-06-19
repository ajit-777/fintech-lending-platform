"""
Loan agreement PDF generator using ReportLab.
Returns PDF bytes — caller decides whether to stream or save to disk.
"""
from __future__ import annotations

import io
from datetime import date
from typing import Optional

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

PAGE_W, PAGE_H = A4
MARGIN = 20 * mm


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title",
            parent=base["Heading1"],
            fontSize=16,
            spaceAfter=4,
            textColor=colors.HexColor("#1e3a5f"),
            alignment=1,  # centre
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            parent=base["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#555555"),
            alignment=1,
            spaceAfter=12,
        ),
        "section": ParagraphStyle(
            "section",
            parent=base["Heading2"],
            fontSize=11,
            spaceBefore=12,
            spaceAfter=4,
            textColor=colors.HexColor("#1e3a5f"),
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["Normal"],
            fontSize=9,
            leading=14,
            spaceAfter=6,
        ),
        "bold": ParagraphStyle(
            "bold",
            parent=base["Normal"],
            fontSize=9,
            leading=14,
            fontName="Helvetica-Bold",
        ),
        "footer": ParagraphStyle(
            "footer",
            parent=base["Normal"],
            fontSize=7,
            textColor=colors.grey,
            alignment=1,
        ),
    }


def _kv_table(rows: list[tuple[str, str]]) -> Table:
    """Two-column key-value table for loan details."""
    data = [[k, v] for k, v in rows]
    t = Table(data, colWidths=[65 * mm, 100 * mm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#444444")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f4f8")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#f9fafb"), colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def generate(
    *,
    loan_id: str,
    borrower_name: str,
    borrower_pan: str,
    borrower_email: str,
    borrower_phone: str,
    borrower_address: str,
    loan_amount: float,
    tenure_months: int,
    annual_interest_rate: float,
    processing_fee: float,
    emi_amount: float,
    first_emi_date: Optional[date],
    early_closure_fee_pct: float,
    late_payment_penalty_pct: float,
    lender_name: str = "FinLend NBFC Private Limited",
    lender_cin: str = "U65929MH2024PTC000001",
    agreement_date: Optional[date] = None,
) -> bytes:
    """Return PDF bytes for the loan sanction letter / agreement."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )

    s = _styles()
    today = agreement_date or date.today()
    net_disbursement = round(loan_amount - processing_fee, 2)

    story = []

    # ── Header ─────────────────────────────────────────────────────────────────
    story.append(Paragraph(lender_name, s["title"]))
    story.append(Paragraph(
        f"CIN: {lender_cin} | RBI NBFC Reg. No.: N-13.02042 | www.finlend.in",
        s["subtitle"],
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1e3a5f")))
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("LOAN SANCTION LETTER & AGREEMENT", s["title"]))
    story.append(Spacer(1, 4 * mm))

    # ── Reference & date ──────────────────────────────────────────────────────
    story.append(_kv_table([
        ("Loan Reference No.", loan_id[:8].upper()),
        ("Agreement Date", today.strftime("%d %B %Y")),
        ("Document Type", "Personal Loan Agreement"),
    ]))
    story.append(Spacer(1, 4 * mm))

    # ── Parties ────────────────────────────────────────────────────────────────
    story.append(Paragraph("1. PARTIES", s["section"]))
    story.append(Paragraph(
        f'This Loan Agreement ("Agreement") is entered into on <b>{today.strftime("%d %B %Y")}</b> between:',
        s["body"],
    ))
    story.append(Paragraph(
        f"<b>Lender:</b> {lender_name}, a Non-Banking Financial Company registered with the Reserve Bank "
        f"of India under Section 45-IA of the RBI Act, 1934, having CIN {lender_cin} "
        f"(hereinafter referred to as the \"Lender\");",
        s["body"],
    ))
    story.append(Paragraph(
        f"<b>Borrower:</b> {borrower_name}, PAN: {borrower_pan}, residing at {borrower_address}, "
        f"reachable at {borrower_email} / {borrower_phone} "
        f"(hereinafter referred to as the \"Borrower\").",
        s["body"],
    ))

    # ── Loan details ───────────────────────────────────────────────────────────
    story.append(Paragraph("2. LOAN DETAILS", s["section"]))
    story.append(_kv_table([
        ("Loan Amount (Principal)", f"INR {loan_amount:,.2f}"),
        ("Processing Fee (deducted upfront)", f"INR {processing_fee:,.2f}"),
        ("Net Disbursement Amount", f"INR {net_disbursement:,.2f}"),
        ("Loan Tenure", f"{tenure_months} months"),
        ("Annual Interest Rate", f"{annual_interest_rate:.2f}% p.a. (reducing balance)"),
        ("Monthly EMI", f"INR {emi_amount:,.2f}"),
        ("First EMI Due Date", first_emi_date.strftime("%d %B %Y") if first_emi_date else "As per schedule"),
        ("Early Closure Fee", f"{early_closure_fee_pct:.2f}% of outstanding principal"),
        ("Late Payment Penalty", f"{late_payment_penalty_pct:.2f}% p.a. on overdue amount"),
    ]))
    story.append(Spacer(1, 2 * mm))

    # ── Terms ──────────────────────────────────────────────────────────────────
    story.append(Paragraph("3. TERMS AND CONDITIONS", s["section"]))

    terms = [
        ("<b>Disbursement.</b> The net disbursement amount (after deducting the processing fee) shall be "
         "credited to the bank account provided by the Borrower within 2 working days of agreement execution."),
        ("<b>Repayment.</b> The Borrower shall repay the loan in equal monthly instalments (EMI) as per "
         "the repayment schedule provided separately. EMIs are due on the same date each month as the "
         "first EMI date."),
        ("<b>Interest.</b> Interest is computed on a daily reducing balance basis. The Annual Percentage "
         "Rate (APR) disclosed above is the applicable rate for this loan."),
        ("<b>Prepayment.</b> The Borrower may prepay the outstanding principal at any time subject to an "
         f"early closure fee of {early_closure_fee_pct:.2f}% on the outstanding principal amount."),
        ("<b>Late Payment.</b> In the event of delay beyond the due date, a late payment penalty of "
         f"{late_payment_penalty_pct:.2f}% per annum shall be levied on the overdue amount for each day "
         "of delay."),
        ("<b>Default.</b> Non-payment of two or more consecutive EMIs shall constitute an event of default. "
         "The Lender may, upon default, recall the entire outstanding loan amount and report the default "
         "to credit bureaus (CIBIL, Experian, Equifax, CRIF)."),
        ("<b>KYC & Data.</b> The Borrower consents to the Lender sharing KYC and repayment data with "
         "credit information companies as required under the Credit Information Companies (Regulation) "
         "Act, 2005."),
        ("<b>Grievance Redressal.</b> For any complaints, the Borrower may contact the Grievance Officer "
         "at grievance@finlend.in. If unresolved within 30 days, the Borrower may approach the RBI "
         "Ombudsman under the Integrated Ombudsman Scheme, 2021."),
        ("<b>Governing Law.</b> This Agreement shall be governed by the laws of India. Any disputes shall "
         "be subject to the exclusive jurisdiction of courts in Mumbai, Maharashtra."),
    ]
    for i, term in enumerate(terms, 1):
        story.append(Paragraph(f"{i}. {term}", s["body"]))

    # ── Acceptance ─────────────────────────────────────────────────────────────
    story.append(Paragraph("4. BORROWER ACCEPTANCE", s["section"]))
    story.append(Paragraph(
        "By accepting this Agreement (electronically via OTP confirmation on the registered mobile number), "
        "the Borrower confirms that they have read, understood, and agree to be bound by all terms and "
        "conditions of this Agreement. This electronic acceptance is valid under the Information Technology "
        "Act, 2000.",
        s["body"],
    ))

    story.append(Spacer(1, 8 * mm))
    story.append(_kv_table([
        ("Borrower Name", borrower_name),
        ("Accepted Via", "Electronic acceptance — OTP on registered mobile"),
        ("Acceptance Date", "As recorded in system"),
    ]))

    story.append(Spacer(1, 12 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "This is a system-generated document. For queries, contact support@finlend.in | 1800-XXX-XXXX (toll-free).",
        s["footer"],
    ))

    doc.build(story)
    return buf.getvalue()
