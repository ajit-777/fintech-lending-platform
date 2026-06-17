from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.models.kyc_profile import KYCProfile
from app.models.user import User
from app.routers.users import get_current_user
from app.schemas.kyc import (
    AadhaarOTPConfirm,
    AadhaarOTPRequest,
    KYCProfileResponse,
    KYCSubmit,
)
from app.services import kyc_verification

router = APIRouter(prefix="/kyc", tags=["KYC"])


def _get_or_create_profile(user: User, db: Session) -> KYCProfile:
    profile = db.query(KYCProfile).filter(KYCProfile.user_id == user.id).first()
    if not profile:
        profile = KYCProfile(user_id=user.id)
        db.add(profile)
        db.flush()
    return profile


@router.get("/me", response_model=KYCProfileResponse)
def get_my_kyc(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(KYCProfile).filter(KYCProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="KYC profile not found. Please submit KYC details.")
    return profile


@router.post("/submit", response_model=KYCProfileResponse)
def submit_kyc(
    payload: KYCSubmit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _get_or_create_profile(current_user, db)

    if profile.kyc_status == "verified":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="KYC is already verified and cannot be re-submitted")

    now = datetime.now(timezone.utc)
    profile.pan_number = payload.pan_number
    profile.date_of_birth = payload.date_of_birth
    profile.address_line1 = payload.address_line1
    profile.address_line2 = payload.address_line2
    profile.city = payload.city
    profile.state = payload.state
    profile.pincode = payload.pincode
    profile.kyc_status = "submitted"
    profile.pan_verified = False
    profile.submitted_at = now
    profile.updated_at = now
    profile.rejection_reason = None

    db.commit()
    db.refresh(profile)
    return profile


@router.post("/verify-pan", response_model=KYCProfileResponse)
def verify_pan(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(KYCProfile).filter(KYCProfile.user_id == current_user.id).first()
    if not profile or not profile.pan_number:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Submit KYC details before verifying PAN")

    if profile.pan_verified:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="PAN is already verified")

    provider = kyc_verification.get_provider()
    result = provider.verify_pan(profile.pan_number)

    if not result.valid:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=result.error or "PAN verification failed")

    profile.pan_verified = True
    profile.pan_name = result.name
    profile.updated_at = datetime.now(timezone.utc)
    _update_kyc_status(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.post("/aadhaar/send-otp", response_model=dict)
def send_aadhaar_otp(
    payload: AadhaarOTPRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(KYCProfile).filter(KYCProfile.user_id == current_user.id).first()
    if not profile or profile.kyc_status not in ("submitted", "pending"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Submit KYC details before Aadhaar verification")

    if profile.aadhaar_verified:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Aadhaar is already verified")

    provider = kyc_verification.get_provider()
    result = provider.send_aadhaar_otp(payload.aadhaar_number)

    if not result.success:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=result.error or "Failed to send OTP")

    # Store ref_id and last4 temporarily for confirm step
    profile.aadhaar_otp_ref = result.ref_id
    profile.aadhaar_last4 = payload.aadhaar_number[-4:]
    profile.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {"message": "OTP sent to Aadhaar-linked mobile number", "ref_id": result.ref_id}


@router.post("/aadhaar/verify-otp", response_model=KYCProfileResponse)
def verify_aadhaar_otp(
    payload: AadhaarOTPConfirm,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(KYCProfile).filter(KYCProfile.user_id == current_user.id).first()
    if not profile or not profile.aadhaar_otp_ref:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request OTP first via /kyc/aadhaar/send-otp")

    if profile.aadhaar_otp_ref != payload.ref_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ref_id does not match the pending OTP request")

    provider = kyc_verification.get_provider()
    result = provider.confirm_aadhaar_otp(
        ref_id=payload.ref_id,
        otp=payload.otp,
        aadhaar=profile.aadhaar_last4 or "",
    )

    if not result.success:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=result.error or "OTP verification failed")

    now = datetime.now(timezone.utc)
    profile.aadhaar_verified = True
    profile.aadhaar_otp_ref = None  # clear — single use
    profile.updated_at = now
    _update_kyc_status(profile)
    db.commit()
    db.refresh(profile)
    return profile


def _update_kyc_status(profile: KYCProfile) -> None:
    """Auto-promote to verified once both PAN and Aadhaar are verified."""
    if profile.pan_verified and profile.aadhaar_verified:
        profile.kyc_status = "verified"
        profile.verified_at = datetime.now(timezone.utc)
