"""
Penny drop verification provider abstraction.

Swap MockPennyDropProvider for a real provider (Karza, SETU, Razorpay) by
implementing the same interface and updating get_provider().

Real API call: POST account number + IFSC → provider transfers ₹1, returns
registered account holder name and account status.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass
class PennyDropResult:
    success: bool
    account_holder_name: Optional[str] = None  # name as returned by bank
    account_active: bool = True
    error: Optional[str] = None


class PennyDropProvider(Protocol):
    def verify(self, account_number: str, ifsc_code: str) -> PennyDropResult: ...


class MockPennyDropProvider:
    """
    Deterministic mock for development and testing.

    Rules:
    - Account numbers starting with '0' → inactive account (fail)
    - Account numbers starting with '9' → active but name = "DIFFERENT NAME"
      (simulates name mismatch against KYC)
    - All others → success, name = "MOCK ACCOUNT HOLDER"
    """

    def verify(self, account_number: str, ifsc_code: str) -> PennyDropResult:
        if account_number.startswith("0"):
            return PennyDropResult(
                success=False,
                account_active=False,
                error="Account not found or inactive",
            )
        if account_number.startswith("9"):
            return PennyDropResult(
                success=True,
                account_holder_name="DIFFERENT NAME",
                account_active=True,
            )
        return PennyDropResult(
            success=True,
            account_holder_name="MOCK ACCOUNT HOLDER",
            account_active=True,
        )


# ── Name match ────────────────────────────────────────────────────────────────

def _normalise(name: str) -> set[str]:
    """Lower-case, remove punctuation, split into word tokens."""
    name = re.sub(r"[^a-z\s]", "", name.lower())
    return set(name.split())


def name_match_score(kyc_name: str, bank_name: str) -> float:
    """
    Simple token overlap score between 0 and 1.
    Score ≥ 0.5 is considered a match (majority of name tokens overlap).
    """
    a = _normalise(kyc_name)
    b = _normalise(bank_name)
    if not a or not b:
        return 0.0
    overlap = len(a & b)
    return overlap / max(len(a), len(b))


# ── Provider registry ─────────────────────────────────────────────────────────

_provider: PennyDropProvider = MockPennyDropProvider()


def get_provider() -> PennyDropProvider:
    return _provider


def set_provider(provider: PennyDropProvider) -> None:
    global _provider
    _provider = provider
