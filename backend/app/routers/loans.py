import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.models.loan_application import LoanApplication
from app.models.user import User
from app.routers.users import get_current_user
from app.schemas.loan_application import LoanApplicationCreate, LoanApplicationResponse
from app.services import loan_rules

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
    )

    now = datetime.now(timezone.utc)
    loan = LoanApplication(
        user_id=current_user.id,
        amount=payload.amount,
        tenure_months=payload.tenure_months,
        purpose=payload.purpose,
        cibil_score=payload.cibil_score,
        monthly_income=payload.monthly_income,
        notes=payload.notes,
        status=result.decision,
        rejection_reason=result.reason if result.decision != "approved" else None,
        reviewed_at=now if result.decision != "pending" else None,
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)
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
