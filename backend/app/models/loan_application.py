import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LoanApplication(Base):
    __tablename__ = "loan_applications"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    amount: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    tenure_months: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    purpose: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    loan_type: Mapped[str] = mapped_column(
        Enum("personal", "msme", name="loan_type"),
        default="personal",
        nullable=False,
    )

    cibil_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    monthly_income: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    # Pricing locked at application time from pricing_config
    annual_interest_rate: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=12.0)
    processing_fee: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    early_closure_fee_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    late_payment_penalty_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)

    status: Mapped[str] = mapped_column(
        Enum("pending", "approved", "rejected", "disbursed", name="loan_status"),
        default="pending",
        nullable=False,
    )

    # Set by rules engine or admin
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Populated only for manual decisions
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    bank_account_number: Mapped[Optional[str]] = mapped_column(String(34), nullable=True)
    ifsc_code: Mapped[Optional[str]] = mapped_column(String(11), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.utcnow(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
        nullable=False,
    )

    user = relationship("User", back_populates="loan_applications", foreign_keys=[user_id])
    repayment_schedule = relationship("RepaymentInstallment", back_populates="loan", order_by="RepaymentInstallment.installment_number")
    disbursement = relationship("Disbursement", back_populates="loan", uselist=False)
