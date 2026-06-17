"""
KYC verification provider abstraction.

Swap MockKYCProvider for a real provider (Karza, IDfy, SETU) by implementing
the same interface and updating `get_provider()`.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass
class PANResult:
    valid: bool
    name: Optional[str] = None  # name as returned by bureau/provider
    error: Optional[str] = None


@dataclass
class AadhaarOTPResult:
    success: bool
    ref_id: Optional[str] = None  # opaque token to pass back on confirm
    error: Optional[str] = None


@dataclass
class AadhaarConfirmResult:
    success: bool
    last4: Optional[str] = None
    error: Optional[str] = None


class KYCProvider(Protocol):
    def verify_pan(self, pan: str, name_to_match: Optional[str] = None) -> PANResult: ...
    def send_aadhaar_otp(self, aadhaar: str) -> AadhaarOTPResult: ...
    def confirm_aadhaar_otp(self, ref_id: str, otp: str, aadhaar: str) -> AadhaarConfirmResult: ...


class MockKYCProvider:
    """
    Deterministic mock for development and testing.

    Rules:
    - PAN starting with 'F' → invalid (simulates failed verification)
    - All other valid-format PANs → verified, name = "MOCK NAME"
    - Aadhaar OTP always succeeds; OTP "000000" → fails confirm (simulate wrong OTP)
    """

    def verify_pan(self, pan: str, name_to_match: Optional[str] = None) -> PANResult:
        if pan.startswith("F"):
            return PANResult(valid=False, error="PAN not found in ITD records")
        return PANResult(valid=True, name="MOCK VERIFIED NAME")

    def send_aadhaar_otp(self, aadhaar: str) -> AadhaarOTPResult:
        ref_id = secrets.token_hex(16)
        return AadhaarOTPResult(success=True, ref_id=ref_id)

    def confirm_aadhaar_otp(self, ref_id: str, otp: str, aadhaar: str) -> AadhaarConfirmResult:
        if otp == "000000":
            return AadhaarConfirmResult(success=False, error="Invalid OTP")
        return AadhaarConfirmResult(success=True, last4=aadhaar[-4:])


# ── Provider registry ─────────────────────────────────────────────────────────

_provider: KYCProvider = MockKYCProvider()


def get_provider() -> KYCProvider:
    return _provider


def set_provider(provider: KYCProvider) -> None:
    """Call this at app startup to swap in a real provider."""
    global _provider
    _provider = provider
