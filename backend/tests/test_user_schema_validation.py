import pytest
from pydantic import ValidationError

from app.schemas.user import UserCreate


def _make_user(**overrides):
    base = {"email": "test@example.com", "phone": "9876543210", "password": "Test@1234"}
    base.update(overrides)
    return UserCreate(**base)


def test_valid_user_passes():
    user = _make_user()
    assert user.phone == "9876543210"


@pytest.mark.parametrize("phone", ["12345", "5876543210", "98765432101", "987654321"])
def test_invalid_phone_formats_rejected(phone):
    with pytest.raises(ValidationError):
        _make_user(phone=phone)


def test_phone_with_country_code_prefix_is_normalized():
    user = _make_user(phone="+919876543210")
    assert user.phone == "9876543210"


@pytest.mark.parametrize("password", [
    "short1!",       # too short
    "alllowercase1!",  # no uppercase
    "ALLUPPERCASE1!",  # no lowercase
    "NoDigitsHere!",   # no digit
    "NoSpecialChar123",  # no special character
])
def test_weak_passwords_rejected(password):
    with pytest.raises(ValidationError):
        _make_user(password=password)


def test_strong_password_accepted():
    user = _make_user(password="Str0ng@Pass")
    assert user.password == "Str0ng@Pass"
