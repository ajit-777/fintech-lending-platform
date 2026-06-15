from dataclasses import dataclass
from typing import Literal

# Configurable thresholds (wire to config/env when needed)
CIBIL_AUTO_REJECT_BELOW = 650
CIBIL_AUTO_APPROVE_ABOVE = 750
MAX_DTI_PERCENT = 40        # EMI must not exceed 40% of monthly income
ANNUAL_INTEREST_RATE = 12.0  # % p.a. used for EMI estimation


@dataclass
class RulesResult:
    decision: Literal["approved", "rejected", "pending"]
    reason: str


def _calculate_emi(principal: float, tenure_months: int) -> float:
    r = ANNUAL_INTEREST_RATE / 12 / 100
    return principal * r * (1 + r) ** tenure_months / ((1 + r) ** tenure_months - 1)


def evaluate(cibil_score: int, monthly_income: float, amount: float, tenure_months: int) -> RulesResult:
    if cibil_score < CIBIL_AUTO_REJECT_BELOW:
        return RulesResult(
            decision="rejected",
            reason=f"CIBIL score {cibil_score} is below the minimum threshold of {CIBIL_AUTO_REJECT_BELOW}.",
        )

    emi = _calculate_emi(amount, tenure_months)
    dti = (emi / monthly_income) * 100

    if cibil_score >= CIBIL_AUTO_APPROVE_ABOVE and dti <= MAX_DTI_PERCENT:
        return RulesResult(
            decision="approved",
            reason=f"Auto-approved: CIBIL {cibil_score}, EMI-to-income ratio {dti:.1f}%.",
        )

    # Borderline — send for manual review
    reasons = []
    if cibil_score < CIBIL_AUTO_APPROVE_ABOVE:
        reasons.append(f"CIBIL score {cibil_score} is below auto-approval threshold of {CIBIL_AUTO_APPROVE_ABOVE}")
    if dti > MAX_DTI_PERCENT:
        reasons.append(f"EMI-to-income ratio {dti:.1f}% exceeds {MAX_DTI_PERCENT}%")

    return RulesResult(
        decision="pending",
        reason="Referred for manual review: " + "; ".join(reasons) + ".",
    )
