from dataclasses import dataclass
from typing import Literal, Optional

from sqlalchemy.orm import Session

from app.models.pricing_config import PricingConfig

CIBIL_AUTO_REJECT_BELOW = 650
CIBIL_AUTO_APPROVE_ABOVE = 750
MAX_DTI_PERCENT = 40


@dataclass
class PricingResult:
    annual_interest_rate: float
    processing_fee_pct: float
    early_closure_fee_pct: float
    late_payment_penalty_pct: float


@dataclass
class RulesResult:
    decision: Literal["approved", "rejected", "pending"]
    reason: str
    pricing: Optional[PricingResult] = None


def get_pricing(cibil_score: int, db: Session) -> Optional[PricingResult]:
    config = (
        db.query(PricingConfig)
        .filter(PricingConfig.cibil_min <= cibil_score, PricingConfig.cibil_max >= cibil_score)
        .first()
    )
    if not config:
        return None
    return PricingResult(
        annual_interest_rate=float(config.annual_interest_rate),
        processing_fee_pct=float(config.processing_fee_pct),
        early_closure_fee_pct=float(config.early_closure_fee_pct),
        late_payment_penalty_pct=float(config.late_payment_penalty_pct),
    )


def _calculate_emi(principal: float, tenure_months: int, annual_rate: float) -> float:
    r = annual_rate / 12 / 100
    return principal * r * (1 + r) ** tenure_months / ((1 + r) ** tenure_months - 1)


def evaluate(cibil_score: int, monthly_income: float, amount: float, tenure_months: int, db: Session) -> RulesResult:
    if cibil_score < CIBIL_AUTO_REJECT_BELOW:
        return RulesResult(
            decision="rejected",
            reason=f"CIBIL score {cibil_score} is below the minimum threshold of {CIBIL_AUTO_REJECT_BELOW}.",
        )

    pricing = get_pricing(cibil_score, db)
    if not pricing:
        return RulesResult(
            decision="pending",
            reason=f"No pricing tier configured for CIBIL score {cibil_score}. Referred for manual review.",
        )

    emi = _calculate_emi(amount, tenure_months, pricing.annual_interest_rate)
    dti = (emi / monthly_income) * 100

    if cibil_score >= CIBIL_AUTO_APPROVE_ABOVE and dti <= MAX_DTI_PERCENT:
        return RulesResult(
            decision="approved",
            reason=f"Auto-approved: CIBIL {cibil_score}, interest rate {pricing.annual_interest_rate}%, EMI-to-income ratio {dti:.1f}%.",
            pricing=pricing,
        )

    reasons = []
    if cibil_score < CIBIL_AUTO_APPROVE_ABOVE:
        reasons.append(f"CIBIL score {cibil_score} is below auto-approval threshold of {CIBIL_AUTO_APPROVE_ABOVE}")
    if dti > MAX_DTI_PERCENT:
        reasons.append(f"EMI-to-income ratio {dti:.1f}% exceeds {MAX_DTI_PERCENT}%")

    return RulesResult(
        decision="pending",
        reason="Referred for manual review: " + "; ".join(reasons) + ".",
        pricing=pricing,
    )
