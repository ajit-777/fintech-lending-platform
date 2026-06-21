import uuid as _uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import decode_access_token, verify_password
from app.db.dependencies import get_db
from app.models.device_token import DeviceToken
from app.models.notification import NotificationLog
from app.models.user import User
from app.schemas.notification import NotificationLogResponse
from app.schemas.user import UserResponse, UserUpdate


class DeviceTokenRequest(BaseModel):
    token: str
    platform: str = "android"

router = APIRouter(prefix="/users", tags=["Users"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    token_data = decode_access_token(token)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.id == _uuid.UUID(token_data.user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.get("/health")
def user_health():
    return {"status": "users router active"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    if payload.email is None and payload.phone is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one of email or phone to update",
        )

    if payload.email and payload.email != current_user.email:
        existing = db.query(User).filter(User.email == payload.email, User.id != current_user.id).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")
        current_user.email = payload.email

    if payload.phone and payload.phone != current_user.phone:
        existing = db.query(User).filter(User.phone == payload.phone, User.id != current_user.id).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phone already in use")
        current_user.phone = payload.phone

    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/me/device-token", status_code=status.HTTP_204_NO_CONTENT)
def register_device_token(
    payload: DeviceTokenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upsert FCM device token for the current user."""
    existing = db.query(DeviceToken).filter(DeviceToken.user_id == current_user.id).first()
    if existing:
        existing.token = payload.token
        existing.platform = payload.platform
        existing.updated_at = datetime.now(timezone.utc)
    else:
        db.add(DeviceToken(
            user_id=current_user.id,
            token=payload.token,
            platform=payload.platform,
            updated_at=datetime.now(timezone.utc),
        ))
    db.commit()


@router.get("/me/notifications", response_model=list[NotificationLogResponse])
def get_my_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(NotificationLog)
        .filter(NotificationLog.user_id == current_user.id)
        .order_by(NotificationLog.sent_at.desc())
        .limit(20)
        .all()
    )
