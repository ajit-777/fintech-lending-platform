from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 — registers all models on Base
from app.db.base import Base
from app.db.dependencies import get_db
from app.main import app
from app.models.kyc_profile import KYCProfile
from app.models.pricing_config import PricingConfig
from app.models.user import User as UserModel


def _make_engine():
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def _seed_pricing(session):
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


@pytest.fixture
def db_session():
    engine = _make_engine()
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    _seed_pricing(session)
    yield session
    session.close()


@pytest.fixture
def client():
    """FastAPI TestClient backed by an isolated in-memory SQLite DB."""
    engine = _make_engine()
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app, raise_server_exceptions=False) as c:
        # Seed pricing tiers via a direct session
        db = Session()
        _seed_pricing(db)
        db.close()
        yield c

    app.dependency_overrides.clear()


# ── Helpers used across test files ────────────────────────────────────────────

def register(client, email="user@test.com", phone="+919000000001", password="Test@1234", verified_kyc=True):
    r = client.post("/auth/register", json={"email": email, "phone": phone, "password": password})
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    if verified_kyc:
        _seed_verified_kyc(email)
    return token


def _seed_verified_kyc(email: str) -> None:
    """Directly insert a verified KYC profile for a test user via the DB override."""
    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    user = db.query(UserModel).filter(UserModel.email == email).first()
    if user:
        existing = db.query(KYCProfile).filter(KYCProfile.user_id == user.id).first()
        if not existing:
            now = datetime.now(timezone.utc)
            profile = KYCProfile(
                user_id=user.id,
                pan_number="ABCDE1234F",
                pan_verified=True,
                pan_name="MOCK ACCOUNT HOLDER",
                aadhaar_last4="1234",
                aadhaar_verified=True,
                date_of_birth="1990-01-01",
                address_line1="123 Test Street",
                city="Mumbai",
                state="Maharashtra",
                pincode="400001",
                kyc_status="verified",
                submitted_at=now,
                verified_at=now,
                updated_at=now,
            )
            db.add(profile)
            db.commit()
    try:
        next(db_gen)
    except StopIteration:
        pass


def register_admin(client, email="admin@test.com", phone="+919000000099", password="Admin@1234"):
    """Register a user then promote to admin directly via DB override."""
    token = register(client, email=email, phone=phone, password=password)
    # Promote via login to get user, then patch role through a raw DB call
    from app.models.user import User
    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    user = db.query(User).filter(User.email == email).first()
    user.role = "admin"
    db.commit()
    try:
        next(db_gen)
    except StopIteration:
        pass
    return token


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


LOAN_PAYLOAD = {
    "amount": 100000,
    "tenure_months": 12,
    "purpose": "Home renovation",
    "cibil_score": 780,
    "monthly_income": 80000,
    "bank_account_number": "1234567890",
    "ifsc_code": "SBIN0001234",
}
