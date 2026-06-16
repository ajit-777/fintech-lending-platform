import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.notification import NotificationLog

logger = logging.getLogger("notifications")


def send(
    db: Session,
    user_id: UUID,
    channel: str,
    event_type: str,
    recipient: str,
    body: str,
    subject: Optional[str] = None,
    loan_id: Optional[UUID] = None,
) -> NotificationLog:
    """
    Sends a notification. Currently mocked — logs and persists the attempt
    without calling a real provider. Swap the body of this function for a
    SendGrid/Twilio/SES call later; call sites do not need to change.
    """
    logger.info(f"[MOCK {channel.upper()}] To: {recipient} | Event: {event_type} | Subject: {subject} | Body: {body}")

    log = NotificationLog(
        user_id=user_id,
        loan_id=loan_id,
        channel=channel,
        event_type=event_type,
        recipient=recipient,
        subject=subject,
        body=body,
        status="sent",
        sent_at=datetime.now(timezone.utc),
    )
    db.add(log)
    db.commit()
    return log


def notify_loan_decision(db: Session, user, loan) -> None:
    if loan.status == "approved":
        subject = "Your loan application has been approved"
        body = (
            f"Your loan application for INR {loan.amount} has been approved at "
            f"{loan.annual_interest_rate}% p.a. for {loan.tenure_months} months."
        )
    elif loan.status == "rejected":
        subject = "Update on your loan application"
        body = f"Your loan application for INR {loan.amount} could not be approved. Reason: {loan.rejection_reason}"
    else:
        return  # no notification for pending/manual-review state

    send(
        db=db,
        user_id=user.id,
        loan_id=loan.id,
        channel="email",
        event_type=f"loan_{loan.status}",
        recipient=user.email,
        subject=subject,
        body=body,
    )


def notify_payment_received(db: Session, user, loan, installment) -> None:
    send(
        db=db,
        user_id=user.id,
        loan_id=loan.id,
        channel="email",
        event_type="installment_paid",
        recipient=user.email,
        subject=f"Payment received for installment #{installment.installment_number}",
        body=(
            f"We have received your payment of INR {installment.paid_amount} for installment "
            f"#{installment.installment_number} (due {installment.due_date}). Thank you."
        ),
    )


def notify_disbursement(db: Session, user, loan, disbursement) -> None:
    send(
        db=db,
        user_id=user.id,
        loan_id=loan.id,
        channel="email",
        event_type="loan_disbursed",
        recipient=user.email,
        subject="Your loan amount has been disbursed",
        body=(
            f"INR {disbursement.net_amount} has been disbursed to your account ending "
            f"{disbursement.bank_account_number[-4:]}. Reference: {disbursement.reference_number}."
        ),
    )
