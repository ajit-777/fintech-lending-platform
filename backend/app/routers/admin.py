import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.models.disbursement import Disbursement
from app.models.loan_application import LoanApplication
from app.models.notification import NotificationLog
from app.models.pricing_config import PricingConfig
from app.models.repayment import RepaymentInstallment
from app.models.user import User
from app.routers.users import get_current_user
from app.schemas.disbursement import DisbursementResponse
from app.schemas.loan_application import LoanApplicationResponse, LoanReviewRequest
from app.schemas.notification import NotificationLogResponse
from app.schemas.pricing_config import PricingConfigResponse, PricingConfigUpdate
from app.schemas.repayment import RepaymentInstallmentResponse, RepaymentPaymentRequest
from app.services import notifications, overdue, repayment_schedule

router = APIRouter(prefix="/admin", tags=["Admin"])


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


@router.get("/loans/{loan_id}/repayments", response_model=List[RepaymentInstallmentResponse])
def get_repayment_schedule(
    loan_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    loan = db.query(LoanApplication).filter(LoanApplication.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan application not found")
    if loan.status not in ("approved", "disbursed"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Repayment schedule is only available for approved or disbursed loans")
    return db.query(RepaymentInstallment).filter(RepaymentInstallment.loan_id == loan_id).order_by(RepaymentInstallment.installment_number).all()


@router.patch("/loans/{loan_id}/repayments/{installment_id}/pay", response_model=RepaymentInstallmentResponse)
def mark_installment_paid(
    loan_id: uuid.UUID,
    installment_id: uuid.UUID,
    payload: RepaymentPaymentRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    loan = db.query(LoanApplication).filter(LoanApplication.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan application not found")

    installment = (
        db.query(RepaymentInstallment)
        .filter(RepaymentInstallment.id == installment_id, RepaymentInstallment.loan_id == loan_id)
        .first()
    )
    if not installment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Installment not found")
    if installment.status == "paid":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Installment is already marked as paid")
    if installment.status not in ("pending", "overdue"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot mark installment with status '{installment.status}' as paid")

    installment.status = "paid"
    installment.paid_at = datetime.now(timezone.utc)
    installment.paid_amount = payload.paid_amount if payload.paid_amount is not None else float(installment.emi_amount)
    db.commit()
    db.refresh(installment)

    notifications.notify_payment_received(db, loan.user, loan, installment)

    return installment


def _enrich(loan: LoanApplication, db: Session) -> LoanApplicationResponse:
    user = db.query(User).filter(User.id == loan.user_id).first()
    data = LoanApplicationResponse.model_validate(loan)
    if user:
        data.user_email = user.email
        data.user_phone = user.phone
    return data


@router.get("/loans", response_model=List[LoanApplicationResponse])
def list_all_loans(
    loan_status: Optional[str] = Query(None, alias="status", pattern="^(pending|approved|rejected|disbursed)$"),
    identifier: Optional[str] = Query(None, description="Filter by applicant's email or phone number"),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(LoanApplication)
    if loan_status:
        query = query.filter(LoanApplication.status == loan_status)
    if identifier:
        query = query.join(User, LoanApplication.user_id == User.id).filter(
            or_(User.email == identifier, User.phone == identifier)
        )
    loans = query.order_by(LoanApplication.created_at.desc()).all()
    return [_enrich(loan, db) for loan in loans]


@router.get("/loans/{loan_id}", response_model=LoanApplicationResponse)
def get_loan(
    loan_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    loan = db.query(LoanApplication).filter(LoanApplication.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan application not found")
    return _enrich(loan, db)


@router.patch("/loans/{loan_id}/approve", response_model=LoanApplicationResponse)
def approve_loan(
    loan_id: uuid.UUID,
    payload: LoanReviewRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    loan = db.query(LoanApplication).filter(LoanApplication.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan application not found")
    if loan.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Loan is already {loan.status} and cannot be reviewed again",
        )

    loan.status = "approved"
    loan.rejection_reason = None
    loan.reviewed_by = admin.id
    loan.reviewed_at = datetime.now(timezone.utc)
    loan.notes = payload.reason
    db.commit()
    db.refresh(loan)

    installments = repayment_schedule.generate(
        loan_id=loan.id,
        principal=float(loan.amount),
        tenure_months=loan.tenure_months,
        approval_date=loan.reviewed_at.date(),
        annual_interest_rate=float(loan.annual_interest_rate),
    )
    db.add_all(installments)
    db.commit()

    notifications.notify_loan_decision(db, loan.user, loan)

    return _enrich(loan, db)


@router.patch("/loans/{loan_id}/reject", response_model=LoanApplicationResponse)
def reject_loan(
    loan_id: uuid.UUID,
    payload: LoanReviewRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    loan = db.query(LoanApplication).filter(LoanApplication.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan application not found")
    if loan.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Loan is already {loan.status} and cannot be reviewed again",
        )

    loan.status = "rejected"
    loan.rejection_reason = payload.reason
    loan.reviewed_by = admin.id
    loan.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(loan)

    notifications.notify_loan_decision(db, loan.user, loan)

    return _enrich(loan, db)


# ── Disbursement ──────────────────────────────────────────────────────────────

class DisburseConfirm(BaseModel):
    reference_number: str = Field(..., min_length=3, max_length=100)


@router.post("/loans/{loan_id}/disburse", response_model=DisbursementResponse, status_code=status.HTTP_201_CREATED)
def disburse_loan(
    loan_id: uuid.UUID,
    payload: DisburseConfirm,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    loan = db.query(LoanApplication).filter(LoanApplication.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan application not found")
    if loan.status != "approved":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only approved loans can be disbursed")
    if not loan.bank_account_number or not loan.ifsc_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Borrower has not provided bank account details")

    existing = db.query(Disbursement).filter(Disbursement.loan_id == loan_id).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Loan has already been disbursed")

    gross_amount = float(loan.amount)
    net_amount = round(gross_amount - float(loan.processing_fee), 2)

    disbursement = Disbursement(
        loan_id=loan.id,
        gross_amount=gross_amount,
        net_amount=net_amount,
        bank_account_number=loan.bank_account_number,
        ifsc_code=loan.ifsc_code,
        reference_number=payload.reference_number,
        disbursed_by=admin.id,
        disbursed_at=datetime.now(timezone.utc),
    )
    loan.status = "disbursed"
    db.add(disbursement)
    db.commit()
    db.refresh(disbursement)

    notifications.notify_disbursement(db, loan.user, loan, disbursement)

    return disbursement


@router.get("/loans/{loan_id}/disbursement", response_model=DisbursementResponse)
def get_disbursement_admin(
    loan_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    disbursement = db.query(Disbursement).filter(Disbursement.loan_id == loan_id).first()
    if not disbursement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Disbursement record not found")
    return disbursement


# ── Notifications ─────────────────────────────────────────────────────────────

@router.get("/loans/{loan_id}/notifications", response_model=List[NotificationLogResponse])
def get_loan_notifications(
    loan_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return (
        db.query(NotificationLog)
        .filter(NotificationLog.loan_id == loan_id)
        .order_by(NotificationLog.sent_at.desc())
        .all()
    )


# ── Overdue job ──────────────────────────────────────────────────────────────

@router.post("/jobs/mark-overdue", status_code=status.HTTP_200_OK)
def run_mark_overdue(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    count = overdue.mark_overdue(db)
    return {"marked_overdue": count}


# ── Pricing config ────────────────────────────────────────────────────────────

@router.get("/pricing", response_model=List[PricingConfigResponse])
def list_pricing(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(PricingConfig).order_by(PricingConfig.cibil_min.desc()).all()


@router.patch("/pricing/{config_id}", response_model=PricingConfigResponse)
def update_pricing(
    config_id: uuid.UUID,
    payload: PricingConfigUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    config = db.query(PricingConfig).filter(PricingConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pricing config not found")

    config.annual_interest_rate = payload.annual_interest_rate
    config.processing_fee_pct = payload.processing_fee_pct
    config.early_closure_fee_pct = payload.early_closure_fee_pct
    config.late_payment_penalty_pct = payload.late_payment_penalty_pct
    config.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(config)
    return config
