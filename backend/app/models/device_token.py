import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    token: Mapped[str] = mapped_column(String(512), nullable=False)

    platform: Mapped[str] = mapped_column(
        Enum("android", "ios", name="device_platform"),
        nullable=False,
        default="android",
    )

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
