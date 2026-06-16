import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Disbursement(Base):
    __tablename__ = "disbursements"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    loan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("loan_applications.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    gross_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    net_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    # Stored for transfer purposes — masked when returned via API.
    # TODO: encrypt at rest once a KMS/encryption layer is available.
    bank_account_number: Mapped[str] = mapped_column(String(34), nullable=False)
    ifsc_code: Mapped[str] = mapped_column(String(11), nullable=False)

    reference_number: Mapped[str] = mapped_column(String(100), nullable=False)

    status: Mapped[str] = mapped_column(
        Enum("completed", "failed", name="disbursement_status"),
        default="completed",
        nullable=False,
    )

    disbursed_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    disbursed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    loan = relationship("LoanApplication", back_populates="disbursement")
