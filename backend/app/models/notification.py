import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    loan_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("loan_applications.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    channel: Mapped[str] = mapped_column(
        Enum("email", "sms", name="notification_channel"),
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(String(100), nullable=False)

    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(
        Enum("sent", "failed", name="notification_status"),
        nullable=False,
    )

    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
