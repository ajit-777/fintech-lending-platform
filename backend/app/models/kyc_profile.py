import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class KYCProfile(Base):
    __tablename__ = "kyc_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )

    # PAN — stored in full (needed for verification and regulatory reporting)
    pan_number: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, index=True)
    pan_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    pan_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # name as per PAN

    # Aadhaar — only last 4 digits stored (UIDAI mandate)
    aadhaar_last4: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)
    aadhaar_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    # OTP reference token returned by aggregator, used to confirm OTP
    aadhaar_otp_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    date_of_birth: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # YYYY-MM-DD

    # Address
    address_line1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pincode: Mapped[Optional[str]] = mapped_column(String(6), nullable=True)

    # Overall KYC status
    kyc_status: Mapped[str] = mapped_column(String(20), default="pending")
    # pending → submitted → verified | rejected
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="kyc_profile")
