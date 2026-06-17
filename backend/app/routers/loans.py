import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.models.disbursement import Disbursement
from app.models.loan_application import LoanApplication
from app.models.repayment import RepaymentInstallment
from app.models.user import User
from app.routers.users import get_current_user
from app.schemas.disbursement import DisbursementResponse
from app.schemas.loan_application import LoanApplicationCreate, LoanApplicationResponse
from app.schemas.repayment import RepaymentInstallmentResponse
from app.services import loan_rules, notifications, repayment_schedule

router = APIRouter(prefix="/loans", tags=["Loans"])


@router.post("", response_model=LoanApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_loan_application(
    payload: LoanApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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
    if loan.status not in ("approved", "disbursed"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Repayment schedule is only available for approved or disbursed loans")
    return db.query(RepaymentInstallment).filter(RepaymentInstallment.loan_id == loan_id).order_by(RepaymentInstallment.installment_number).all()


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
