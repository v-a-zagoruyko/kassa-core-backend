import logging
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField  # noqa: F401

from accounts.models import PhoneVerificationCode, User, UserProfile
from common.exceptions import DomainValidationError

logger = logging.getLogger(__name__)


CODE_TTL_SECONDS = getattr(settings, "PHONE_VERIFICATION_CODE_TTL", 5 * 60)
RESEND_INTERVAL_SECONDS = getattr(settings, "PHONE_VERIFICATION_RESEND_INTERVAL", 30)
MAX_VERIFY_ATTEMPTS = getattr(settings, "PHONE_VERIFICATION_MAX_ATTEMPTS", 5)


def _now():
    return timezone.now()


def generate_verification_code() -> str:
    """
    Генерация кода подтверждения.

    На dev-стенде всегда возвращаем фиксированный код, чтобы упростить тестирование.
    При необходимости можно заменить на рандомную генерацию.
    """
    return "123456"


@dataclass
class VerificationResult:
    user: User
    is_new_user: bool


class SmsSender:
    """
    Заглушка SMS-сервиса.

    В dev-окружении просто логируем отправку кода. В будущем сюда можно
    подставить реального провайдера без изменения контроллеров.
    """

    def send_code(self, phone: str, code: str) -> None:
        logger.info("Sending verification code %s to phone %s", code, phone)


def send_verification_code(phone: str, sms_sender: SmsSender | None = None) -> None:
    """
    Создаёт/обновляет запись с кодом подтверждения и отправляет код через SMS-сервис.
    """
    if sms_sender is None:
        sms_sender = SmsSender()

    now = _now()

    last_code = (
        PhoneVerificationCode.objects.filter(phone=phone, is_used=False)
        .order_by("-created_at")
        .first()
    )

    if last_code and (now - last_code.created_at).total_seconds() < RESEND_INTERVAL_SECONDS:
        raise DomainValidationError("Слишком часто запрашивается код подтверждения. Попробуйте позже.")

    code = generate_verification_code()
    expires_at = now + timedelta(seconds=CODE_TTL_SECONDS)

    PhoneVerificationCode.objects.create(
        phone=phone,
        code=code,
        expires_at=expires_at,
    )

    sms_sender.send_code(phone=phone, code=code)


def verify_code(phone: str, code: str) -> VerificationResult:
    """
    Проверяет код подтверждения для телефона и возвращает пользователя.
    """
    now = _now()

    verification = (
        PhoneVerificationCode.objects.filter(phone=phone, is_used=False)
        .order_by("-created_at")
        .first()
    )

    if not verification:
        raise DomainValidationError("Код подтверждения не найден.")

    if verification.expires_at <= now:
        raise DomainValidationError("Срок действия кода подтверждения истёк.")

    if verification.attempts >= MAX_VERIFY_ATTEMPTS:
        raise DomainValidationError("Превышено максимальное количество попыток ввода кода.")

    if verification.code != code:
        verification.attempts += 1
        verification.save(update_fields=["attempts", "updated_at"])
        raise DomainValidationError("Неверный код подтверждения.")

    verification.is_used = True
    verification.attempts += 1
    verification.save(update_fields=["is_used", "attempts", "updated_at"])

    profile = UserProfile.objects.filter(phone=phone).select_related("user").first()

    is_new_user = False
    if profile:
        user = profile.user
    else:
        username = f"phone_{phone.replace('+', '')}"
        user = User.objects.create_user(username=username, password=None)
        UserProfile.objects.create(user=user, phone=phone)
        is_new_user = True

    return VerificationResult(user=user, is_new_user=is_new_user)

