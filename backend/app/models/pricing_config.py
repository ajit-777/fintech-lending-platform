import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PricingConfig(Base):
    """
    One row per CIBIL tier. Admin-editable via API.
    Rates and fees stored here are applied to new loan applications only —
    existing loans retain the rate locked at application time.
    """
    __tablename__ = "pricing_config"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # CIBIL tier bounds (inclusive)
    cibil_min: Mapped[int] = mapped_column(Integer, nullable=False)
    cibil_max: Mapped[int] = mapped_column(Integer, nullable=False)

    tier_label: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "Prime", "Near-Prime"

    annual_interest_rate: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)  # % p.a.
    processing_fee_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)    # % of loan amount
    origination_fee_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)   # % of loan amount
    early_closure_fee_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False) # % of outstanding principal
    late_payment_penalty_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)  # % p.m. on overdue

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
