import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.models.disbursement import Disbursement
from app.models.loan_application import LoanApplication
from app.models.notification import NotificationLog
from app.models.pricing_config import PricingConfig
from app.models.repayment import RepaymentInstallment
from app.models.user import User
from app.routers.users import get_current_user
from app.schemas.disbursement import DisbursementCreate, DisbursementResponse
from app.schemas.loan_application import LoanApplicationResponse, LoanReviewRequest
from app.schemas.notification import NotificationLogResponse
from app.schemas.pricing_config import PricingConfigResponse, PricingConfigUpdate
from app.schemas.repayment import RepaymentInstallmentResponse
from app.services import notifications, repayment_schedule

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
    if loan.status != "approved":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Repayment schedule is only available for approved loans")
    return db.query(RepaymentInstallment).filter(RepaymentInstallment.loan_id == loan_id).order_by(RepaymentInstallment.installment_number).all()


@router.get("/loans", response_model=List[LoanApplicationResponse])
def list_all_loans(
    loan_status: Optional[str] = Query(None, alias="status", pattern="^(pending|approved|rejected)$"),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(LoanApplication)
    if loan_status:
        query = query.filter(LoanApplication.status == loan_status)
    return query.order_by(LoanApplication.created_at.desc()).all()


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

    return loan


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

    return loan


# ── Disbursement ──────────────────────────────────────────────────────────────

@router.post("/loans/{loan_id}/disburse", response_model=DisbursementResponse, status_code=status.HTTP_201_CREATED)
def disburse_loan(
    loan_id: uuid.UUID,
    payload: DisbursementCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    loan = db.query(LoanApplication).filter(LoanApplication.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan application not found")
    if loan.status != "approved":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only approved loans can be disbursed")

    existing = db.query(Disbursement).filter(Disbursement.loan_id == loan_id).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Loan has already been disbursed")

    gross_amount = float(loan.amount)
    net_amount = round(gross_amount - float(loan.processing_fee), 2)

    disbursement = Disbursement(
        loan_id=loan.id,
        gross_amount=gross_amount,
        net_amount=net_amount,
        bank_account_number=payload.bank_account_number,
        ifsc_code=payload.ifsc_code,
        reference_number=payload.reference_number,
        disbursed_by=admin.id,
        disbursed_at=datetime.now(timezone.utc),
    )
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
