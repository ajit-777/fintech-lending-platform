import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.models.disbursement import Disbursement
from app.models.kyc_profile import KYCProfile
from app.models.loan_application import LoanApplication
from app.models.repayment import RepaymentInstallment
from app.models.user import User
from app.routers.users import get_current_user
from app.schemas.disbursement import DisbursementResponse
from app.schemas.loan_application import LoanApplicationCreate, LoanApplicationResponse
from app.schemas.repayment import RepaymentInstallmentResponse, RepaymentPaymentRequest
from app.services import loan_rules, notifications, penny_drop, repayment_schedule, statement_pdf

router = APIRouter(prefix="/loans", tags=["Loans"])


@router.post("", response_model=LoanApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_loan_application(
    payload: LoanApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    kyc = db.query(KYCProfile).filter(KYCProfile.user_id == current_user.id).first()
    if not kyc or kyc.kyc_status != "verified":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="KYC verification is required before applying for a loan",
        )

    # Run penny drop verification against the bank account
    pd_provider = penny_drop.get_provider()
    pd_result = pd_provider.verify(payload.bank_account_number, payload.ifsc_code)

    if not pd_result.success:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Bank account verification failed: {pd_result.error or 'account inactive'}",
        )

    # Name match against PAN-verified name
    kyc_name = kyc.pan_name or ""
    bank_name = pd_result.account_holder_name or ""
    match_score = penny_drop.name_match_score(kyc_name, bank_name) if kyc_name and bank_name else 0.0
    account_verified = match_score >= 0.5

    result = loan_rules.evaluate(
        cibil_score=payload.cibil_score,
        monthly_income=payload.monthly_income,
        amount=payload.amount,
        tenure_months=payload.tenure_months,
        db=db,
    )

    pricing = result.pricing
    now = datetime.now(timezone.utc)
    loan = LoanApplication(
        user_id=current_user.id,
        amount=payload.amount,
        tenure_months=payload.tenure_months,
        purpose=payload.purpose,
        cibil_score=payload.cibil_score,
        monthly_income=payload.monthly_income,
        notes=payload.notes,
        bank_account_number=payload.bank_account_number,
        ifsc_code=payload.ifsc_code,
        bank_account_verified=account_verified,
        bank_account_holder_name=pd_result.account_holder_name,
        penny_drop_name_match_score=round(match_score, 3),
        status=result.decision,
        rejection_reason=result.reason if result.decision != "approved" else None,
        reviewed_at=now if result.decision != "pending" else None,
        annual_interest_rate=pricing.annual_interest_rate if pricing else 0,
        processing_fee=round(payload.amount * pricing.processing_fee_pct / 100, 2) if pricing else 0,
        early_closure_fee_pct=pricing.early_closure_fee_pct if pricing else 0,
        late_payment_penalty_pct=pricing.late_payment_penalty_pct if pricing else 0,
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)

    if result.decision == "approved":
        installments = repayment_schedule.generate(
            loan_id=loan.id,
            principal=float(loan.amount),
            tenure_months=loan.tenure_months,
            approval_date=loan.reviewed_at.date(),
            annual_interest_rate=float(loan.annual_interest_rate),
        )
        db.add_all(installments)
        db.commit()

    if result.decision in ("approved", "rejected"):
        notifications.notify_loan_decision(db, current_user, loan)

    return loan


@router.get("", response_model=List[LoanApplicationResponse])
def list_loan_applications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(LoanApplication)
        .filter(LoanApplication.user_id == current_user.id)
        .order_by(LoanApplication.created_at.desc())
        .all()
    )


@router.get("/{loan_id}/repayments", response_model=List[RepaymentInstallmentResponse])
def get_repayment_schedule(
    loan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    loan = (
        db.query(LoanApplication)
        .filter(LoanApplication.id == loan_id, LoanApplication.user_id == current_user.id)
        .first()
    )
    if not loan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan application not found")
    if loan.status not in ("approved", "disbursed", "closed"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Repayment schedule is only available for approved, disbursed, or closed loans")
    return db.query(RepaymentInstallment).filter(RepaymentInstallment.loan_id == loan_id).order_by(RepaymentInstallment.installment_number).all()


@router.post("/{loan_id}/repayments/{installment_id}/pay", response_model=RepaymentInstallmentResponse)
def pay_installment(
    loan_id: uuid.UUID,
    installment_id: uuid.UUID,
    payload: RepaymentPaymentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    loan = (
        db.query(LoanApplication)
        .filter(LoanApplication.id == loan_id, LoanApplication.user_id == current_user.id)
        .first()
    )
    if not loan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")
    if loan.status != "disbursed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payments can only be made on disbursed loans")

    installment = (
        db.query(RepaymentInstallment)
        .filter(RepaymentInstallment.id == installment_id, RepaymentInstallment.loan_id == loan_id)
        .first()
    )
    if not installment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Installment not found")
    if installment.status == "paid":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Installment already paid")

    now = datetime.now(timezone.utc)
    amount_due = float(installment.emi_amount) + float(installment.penalty_amount or 0)
    installment.paid_amount = payload.paid_amount if payload.paid_amount is not None else amount_due
    installment.paid_at = now
    installment.status = "paid"

    # Auto-close loan when all installments are paid
    all_paid = (
        db.query(RepaymentInstallment)
        .filter(
            RepaymentInstallment.loan_id == loan_id,
            RepaymentInstallment.id != installment_id,
            RepaymentInstallment.status != "paid",
        )
        .count()
        == 0
    )
    if all_paid:
        loan.status = "closed"

    db.commit()
    db.refresh(installment)

    notifications.notify_payment_received(db, current_user, loan, installment)

    return installment


@router.get("/{loan_id}/foreclosure-quote")
def get_foreclosure_quote(
    loan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    loan = (
        db.query(LoanApplication)
        .filter(LoanApplication.id == loan_id, LoanApplication.user_id == current_user.id)
        .first()
    )
    if not loan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")
    if loan.status != "disbursed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Foreclosure is only available for disbursed loans")

    unpaid = (
        db.query(RepaymentInstallment)
        .filter(RepaymentInstallment.loan_id == loan_id, RepaymentInstallment.status != "paid")
        .order_by(RepaymentInstallment.installment_number)
        .all()
    )
    if not unpaid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No outstanding installments")

    # Outstanding principal = balance after the last paid installment
    # = outstanding_principal on the earliest unpaid installment
    outstanding_principal = float(unpaid[0].outstanding_principal) + float(unpaid[0].principal)
    # More precisely: sum of principal portions remaining
    outstanding_principal = sum(float(i.principal) for i in unpaid)
    closure_fee = round(outstanding_principal * float(loan.early_closure_fee_pct) / 100, 2)
    total_payable = round(outstanding_principal + closure_fee, 2)

    return {
        "outstanding_principal": round(outstanding_principal, 2),
        "early_closure_fee_pct": float(loan.early_closure_fee_pct),
        "closure_fee": closure_fee,
        "total_payable": total_payable,
        "installments_remaining": len(unpaid),
    }


@router.post("/{loan_id}/foreclose", status_code=status.HTTP_200_OK)
def foreclose_loan(
    loan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    loan = (
        db.query(LoanApplication)
        .filter(LoanApplication.id == loan_id, LoanApplication.user_id == current_user.id)
        .first()
    )
    if not loan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")
    if loan.status != "disbursed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Foreclosure is only available for disbursed loans")

    unpaid = (
        db.query(RepaymentInstallment)
        .filter(RepaymentInstallment.loan_id == loan_id, RepaymentInstallment.status != "paid")
        .all()
    )
    if not unpaid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No outstanding installments")

    outstanding_principal = sum(float(i.principal) for i in unpaid)
    closure_fee = round(outstanding_principal * float(loan.early_closure_fee_pct) / 100, 2)
    total_payable = round(outstanding_principal + closure_fee, 2)

    now = datetime.now(timezone.utc)
    for installment in unpaid:
        installment.status = "paid"
        installment.paid_at = now
        # Borrower pays principal only (interest waived on prepayment) + fee absorbed at loan level
        installment.paid_amount = float(installment.principal)

    loan.status = "closed"
    loan.notes = (loan.notes or "") + f" | Foreclosed on {now.date()} — fee: ₹{closure_fee}"
    db.commit()

    notifications.send(
        db=db,
        user_id=current_user.id,
        loan_id=loan.id,
        channel="email",
        event_type="loan_foreclosed",
        recipient=current_user.email,
        subject="Loan foreclosure confirmed",
        body=(
            f"Your loan of ₹{loan.amount} has been foreclosed. "
            f"Outstanding principal: ₹{outstanding_principal:.2f}, "
            f"early closure fee: ₹{closure_fee:.2f}, "
            f"total paid: ₹{total_payable:.2f}."
        ),
        push_title="Loan Foreclosed ✓",
        push_data={"loan_id": str(loan.id), "event": "loan_foreclosed"},
    )

    return {
        "status": "closed",
        "outstanding_principal": round(outstanding_principal, 2),
        "closure_fee": closure_fee,
        "total_payable": total_payable,
    }


@router.get("/{loan_id}/disbursement", response_model=DisbursementResponse)
def get_disbursement(
    loan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    loan = (
        db.query(LoanApplication)
        .filter(LoanApplication.id == loan_id, LoanApplication.user_id == current_user.id)
        .first()
    )
    if not loan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan application not found")

    disbursement = db.query(Disbursement).filter(Disbursement.loan_id == loan_id).first()
    if not disbursement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Disbursement record not found")
    return disbursement


@router.get("/{loan_id}/statement.pdf")
def download_statement(
    loan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    loan = (
        db.query(LoanApplication)
        .filter(LoanApplication.id == loan_id, LoanApplication.user_id == current_user.id)
        .first()
    )
    if not loan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan application not found")
    if loan.status not in ("approved", "disbursed", "closed"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Statement is only available for approved or disbursed loans")

    installments = (
        db.query(RepaymentInstallment)
        .filter(RepaymentInstallment.loan_id == loan_id)
        .order_by(RepaymentInstallment.installment_number)
        .all()
    )
    disbursement = db.query(Disbursement).filter(Disbursement.loan_id == loan_id).first()

    pdf_bytes = statement_pdf.generate(loan, current_user, installments, disbursement)
    filename = f"statement_{str(loan_id)[:8].upper()}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{loan_id}", response_model=LoanApplicationResponse)
def get_loan_application(
    loan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    loan = (
        db.query(LoanApplication)
        .filter(
            LoanApplication.id == loan_id,
            LoanApplication.user_id == current_user.id,
        )
        .first()
    )
    if not loan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan application not found")
    return loan
