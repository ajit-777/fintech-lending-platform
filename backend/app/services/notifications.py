import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.device_token import DeviceToken
from app.models.notification import NotificationLog
from app.services import push_provider

logger = logging.getLogger("notifications")


def _send_push(db: Session, user_id: UUID, title: str, body: str, data: dict | None = None) -> None:
    """Fire push to all registered devices for this user."""
    tokens = db.query(DeviceToken).filter(DeviceToken.user_id == user_id).all()
    provider = push_provider.get_provider()
    for dt in tokens:
        result = provider.send(dt.token, title, body, data)
        if not result.success:
            logger.warning("Push failed for user %s token %s…: %s", user_id, dt.token[:20], result.error)


def send(
    db: Session,
    user_id: UUID,
    channel: str,
    event_type: str,
    recipient: str,
    body: str,
    subject: Optional[str] = None,
    loan_id: Optional[UUID] = None,
    push_title: Optional[str] = None,
    push_data: Optional[dict] = None,
) -> NotificationLog:
    """
    Sends a notification. Email/SMS currently mocked — swap send() body for
    SendGrid/Twilio later. Push fires via push_provider (mock → FCM swap).
    """
    logger.info("[MOCK %s] To: %s | Event: %s | Body: %s", channel.upper(), recipient, event_type, body)

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

    if push_title:
        _send_push(db, user_id, push_title, body, push_data)

    return log


def notify_loan_decision(db: Session, user, loan) -> None:
    if loan.status == "approved":
        subject = "Your loan application has been approved"
        body = (
            f"Your loan application for ₹{loan.amount} has been approved at "
            f"{loan.annual_interest_rate}% p.a. for {loan.tenure_months} months."
        )
        push_title = "Loan Approved 🎉"
    elif loan.status == "rejected":
        subject = "Update on your loan application"
        body = f"Your loan application for ₹{loan.amount} could not be approved. Reason: {loan.rejection_reason}"
        push_title = "Loan Application Update"
    else:
        return

    send(
        db=db, user_id=user.id, loan_id=loan.id,
        channel="email", event_type=f"loan_{loan.status}",
        recipient=user.email, subject=subject, body=body,
        push_title=push_title,
        push_data={"loan_id": str(loan.id), "event": f"loan_{loan.status}"},
    )


def notify_disbursement(db: Session, user, loan, disbursement) -> None:
    body = (
        f"₹{disbursement.net_amount} has been disbursed to your account ending "
        f"{disbursement.bank_account_number[-4:]}. Reference: {disbursement.reference_number}."
    )
    send(
        db=db, user_id=user.id, loan_id=loan.id,
        channel="email", event_type="loan_disbursed",
        recipient=user.email,
        subject="Your loan amount has been disbursed",
        body=body,
        push_title="Loan Disbursed 💸",
        push_data={"loan_id": str(loan.id), "event": "loan_disbursed"},
    )


def notify_payment_received(db: Session, user, loan, installment) -> None:
    body = (
        f"We have received your payment of ₹{installment.paid_amount} for EMI "
        f"#{installment.installment_number} (due {installment.due_date}). Thank you."
    )
    send(
        db=db, user_id=user.id, loan_id=loan.id,
        channel="email", event_type="installment_paid",
        recipient=user.email,
        subject=f"Payment received for EMI #{installment.installment_number}",
        body=body,
        push_title="Payment Confirmed ✓",
        push_data={"loan_id": str(loan.id), "event": "installment_paid"},
    )


def notify_emi_due_reminder(db: Session, user, loan, installment) -> None:
    body = (
        f"Your EMI #{ installment.installment_number} of ₹{installment.emi_amount} "
        f"is due tomorrow ({installment.due_date}). Please ensure funds are available."
    )
    send(
        db=db, user_id=user.id, loan_id=loan.id,
        channel="email", event_type="emi_due_reminder",
        recipient=user.email,
        subject=f"EMI due tomorrow — ₹{installment.emi_amount}",
        body=body,
        push_title="EMI Due Tomorrow 📅",
        push_data={"loan_id": str(loan.id), "event": "emi_due_reminder"},
    )
