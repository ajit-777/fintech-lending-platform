"""
Loan agreement endpoints — PDF download and OTP-based acceptance.

Flow:
  1. GET  /loans/{id}/agreement        → download PDF (loan must be approved/disbursed)
  2. POST /loans/{id}/agreement/send-otp → send OTP to registered mobile
  3. POST /loans/{id}/agreement/accept  → confirm OTP → mark agreement_accepted = True
"""
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.models.kyc_profile import KYCProfile
from app.models.loan_application import LoanApplication
from app.models.repayment import RepaymentInstallment
from app.models.user import User
from app.routers.users import get_current_user
from app.services import agreement_pdf

router = APIRouter(prefix="/loans", tags=["Agreement"])

_MOCK_OTP = "123456"  # fixed OTP in mock mode; replace with SMS gateway


class OTPConfirm(BaseModel):
    otp: str
    ref_id: str


def _get_loan_or_404(loan_id: uuid.UUID, user: User, db: Session) -> LoanApplication:
    loan = db.query(LoanApplication).filter(
        LoanApplication.id == loan_id,
        LoanApplication.user_id == user.id,
    ).first()
    if not loan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")
    return loan


@router.get("/{loan_id}/agreement", response_class=Response)
def download_agreement(
    loan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    loan = _get_loan_or_404(loan_id, current_user, db)
    if loan.status not in ("approved", "disbursed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agreement is only available for approved or disbursed loans",
        )

    kyc = db.query(KYCProfile).filter(KYCProfile.user_id == current_user.id).first()
    first_installment = (
        db.query(RepaymentInstallment)
        .filter(RepaymentInstallment.loan_id == loan_id)
        .order_by(RepaymentInstallment.installment_number)
        .first()
    )
    first_emi_amount = float(first_installment.emi_amount) if first_installment else 0.0
    first_emi_date = first_installment.due_date if first_installment else None

    address_parts = filter(None, [
        kyc.address_line1 if kyc else None,
        kyc.address_line2 if kyc else None,
        kyc.city if kyc else None,
        kyc.state if kyc else None,
        kyc.pincode if kyc else None,
    ])
    address = ", ".join(address_parts) or "Address not provided"

    pdf_bytes = agreement_pdf.generate(
        loan_id=str(loan.id),
        borrower_name=kyc.pan_name or current_user.email,
        borrower_pan=kyc.pan_number or "Not provided",
        borrower_email=current_user.email,
        borrower_phone=current_user.phone,
        borrower_address=address,
        loan_amount=float(loan.amount),
        tenure_months=loan.tenure_months,
        annual_interest_rate=float(loan.annual_interest_rate),
        processing_fee=float(loan.processing_fee),
        emi_amount=first_emi_amount,
        first_emi_date=first_emi_date,
        early_closure_fee_pct=float(loan.early_closure_fee_pct),
        late_payment_penalty_pct=float(loan.late_payment_penalty_pct),
    )

    filename = f"loan_agreement_{str(loan.id)[:8].upper()}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{loan_id}/agreement/send-otp")
def send_agreement_otp(
    loan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    loan = _get_loan_or_404(loan_id, current_user, db)
    if loan.status not in ("approved", "disbursed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agreement acceptance is only available for approved or disbursed loans",
        )
    if loan.agreement_accepted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Agreement has already been accepted",
        )

    ref_id = secrets.token_hex(16)
    loan.agreement_otp_ref = ref_id
    db.commit()

    # In production: send _MOCK_OTP via SMS gateway to current_user.phone
    # For now: return OTP in response (dev/test only — remove before production)
    return {
        "message": f"OTP sent to {current_user.phone}",
        "ref_id": ref_id,
        "_dev_otp": _MOCK_OTP,  # REMOVE IN PRODUCTION
    }


@router.post("/{loan_id}/agreement/accept")
def accept_agreement(
    loan_id: uuid.UUID,
    payload: OTPConfirm,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    loan = _get_loan_or_404(loan_id, current_user, db)
    if loan.agreement_accepted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Agreement has already been accepted",
        )
    if not loan.agreement_otp_ref:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request an OTP first via /loans/{id}/agreement/send-otp",
        )
    if loan.agreement_otp_ref != payload.ref_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ref_id does not match the pending OTP request",
        )
    if payload.otp != _MOCK_OTP:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid OTP",
        )

    now = datetime.now(timezone.utc)
    loan.agreement_accepted = True
    loan.agreement_accepted_at = now
    loan.agreement_otp_ref = None
    db.commit()

    return {"message": "Agreement accepted successfully", "accepted_at": now.isoformat()}
