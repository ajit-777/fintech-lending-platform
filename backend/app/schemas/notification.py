import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NotificationLogResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    loan_id: Optional[uuid.UUID]
    channel: str
    event_type: str
    recipient: str
    subject: Optional[str]
    body: str
    status: str
    sent_at: datetime

    class Config:
        from_attributes = True
