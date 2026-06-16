from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401 — registers all models on Base
from app.db.base import Base
from app.models.pricing_config import PricingConfig


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    session.add_all([
        PricingConfig(
            cibil_min=750, cibil_max=900, tier_label="Prime",
            annual_interest_rate=10.0, processing_fee_pct=1.5,
            early_closure_fee_pct=2.0, late_payment_penalty_pct=2.0,
            updated_at=datetime.now(timezone.utc),
        ),
        PricingConfig(
            cibil_min=700, cibil_max=749, tier_label="Near-Prime",
            annual_interest_rate=13.0, processing_fee_pct=2.0,
            early_closure_fee_pct=3.0, late_payment_penalty_pct=2.0,
            updated_at=datetime.now(timezone.utc),
        ),
        PricingConfig(
            cibil_min=650, cibil_max=699, tier_label="Sub-Prime",
            annual_interest_rate=16.0, processing_fee_pct=3.0,
            early_closure_fee_pct=4.0, late_payment_penalty_pct=3.0,
            updated_at=datetime.now(timezone.utc),
        ),
    ])
    session.commit()

    yield session
    session.close()
