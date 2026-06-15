import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.models.loan_application import LoanApplication
from app.models.user import User
from app.routers.users import get_current_user
from app.schemas.loan_application import LoanApplicationResponse, LoanReviewRequest

router = APIRouter(prefix="/admin", tags=["Admin"])


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


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
    return loan
