from app.services import loan_rules


def test_auto_reject_below_minimum_cibil(db_session):
    result = loan_rules.evaluate(
        cibil_score=600, monthly_income=80000, amount=100000, tenure_months=12, db=db_session,
    )
    assert result.decision == "rejected"
    assert "below the minimum threshold" in result.reason


def test_auto_approve_high_cibil_low_dti(db_session):
    result = loan_rules.evaluate(
        cibil_score=780, monthly_income=80000, amount=100000, tenure_months=12, db=db_session,
    )
    assert result.decision == "approved"
    assert result.pricing.annual_interest_rate == 10.0
    assert result.pricing.processing_fee_pct == 1.5


def test_high_cibil_but_high_dti_goes_to_manual_review(db_session):
    # Same high CIBIL, but a much larger loan relative to income pushes DTI over 40%
    result = loan_rules.evaluate(
        cibil_score=780, monthly_income=20000, amount=500000, tenure_months=12, db=db_session,
    )
    assert result.decision == "pending"
    assert "EMI-to-income ratio" in result.reason


def test_borderline_cibil_goes_to_manual_review(db_session):
    result = loan_rules.evaluate(
        cibil_score=720, monthly_income=80000, amount=100000, tenure_months=12, db=db_session,
    )
    assert result.decision == "pending"
    assert result.pricing.annual_interest_rate == 13.0


def test_cibil_with_no_matching_tier_goes_to_manual_review(db_session):
    # 900-901 doesn't exist as a tier in this test fixture's edge case — use a gap value
    result = loan_rules.evaluate(
        cibil_score=901, monthly_income=80000, amount=100000, tenure_months=12, db=db_session,
    )
    assert result.decision == "pending"
    assert "No pricing tier configured" in result.reason


def test_exact_boundary_cibil_650_is_not_rejected(db_session):
    # 650 is the inclusive lower bound of Sub-Prime — should not be auto-rejected
    result = loan_rules.evaluate(
        cibil_score=650, monthly_income=80000, amount=100000, tenure_months=12, db=db_session,
    )
    assert result.decision != "rejected"


def test_exact_boundary_cibil_649_is_rejected(db_session):
    result = loan_rules.evaluate(
        cibil_score=649, monthly_income=80000, amount=100000, tenure_months=12, db=db_session,
    )
    assert result.decision == "rejected"
