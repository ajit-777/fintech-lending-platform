import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RepaymentInstallment(Base):
    __tablename__ = "repayment_installments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    loan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("loan_applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    installment_number: Mapped[int] = mapped_column(Integer, nullable=False)

    due_date: Mapped[datetime] = mapped_column(Date, nullable=False)

    emi_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    principal: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    interest: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    outstanding_principal: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    status: Mapped[str] = mapped_column(
        Enum("pending", "paid", "overdue", name="installment_status"),
        default="pending",
        nullable=False,
    )

    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_amount: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    penalty_amount: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)

    loan = relationship("LoanApplication", back_populates="repayment_schedule")
