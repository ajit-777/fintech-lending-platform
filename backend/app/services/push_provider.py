"""
Push notification provider — mock now, swap for real FCM before production.

To enable real FCM:
1. pip install firebase-admin
2. Download service account JSON from Firebase console
3. Set FIREBASE_CREDENTIALS_PATH=/path/to/serviceAccount.json in .env
4. Change get_provider() to return FCMPushProvider()
"""
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class PushResult:
    def __init__(self, success: bool, error: str | None = None):
        self.success = success
        self.error = error


class BasePushProvider(ABC):
    @abstractmethod
    def send(self, token: str, title: str, body: str, data: dict | None = None) -> PushResult:
        ...


class MockPushProvider(BasePushProvider):
    def send(self, token: str, title: str, body: str, data: dict | None = None) -> PushResult:
        logger.info("[MOCK PUSH] token=%s… | %s | %s", token[:20], title, body)
        return PushResult(success=True)


class FCMPushProvider(BasePushProvider):
    """Real FCM provider — activate when Firebase is configured."""

    def __init__(self, credentials_path: str):
        import firebase_admin
        from firebase_admin import credentials
        if not firebase_admin._apps:
            cred = credentials.Certificate(credentials_path)
            firebase_admin.initialize_app(cred)

    def send(self, token: str, title: str, body: str, data: dict | None = None) -> PushResult:
        from firebase_admin import messaging
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            token=token,
        )
        try:
            messaging.send(message)
            return PushResult(success=True)
        except Exception as e:
            logger.error("FCM send failed: %s", e)
            return PushResult(success=False, error=str(e))


_provider: BasePushProvider = MockPushProvider()


def get_provider() -> BasePushProvider:
    return _provider


def set_provider(p: BasePushProvider) -> None:
    global _provider
    _provider = p
