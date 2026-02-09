import pytest
from django.utils import timezone

from accounts.models import PhoneVerificationCode, UserProfile
from accounts.services.phone_auth_service import (
    VerificationResult,
    generate_verification_code,
    send_verification_code,
    verify_code,
)


class DummySmsSender:
    def __init__(self):
        self.sent = []

    def send_code(self, phone: str, code: str) -> None:
        self.sent.append((phone, code))


@pytest.mark.django_db
def test_generate_verification_code_is_static_in_dev():
    assert generate_verification_code() == "123456"


@pytest.mark.django_db
def test_send_verification_code_creates_record_and_sends_sms():
    phone = "+79998887766"
    sms_sender = DummySmsSender()

    send_verification_code(phone=phone, sms_sender=sms_sender)

    assert PhoneVerificationCode.objects.filter(phone=phone).count() == 1
    assert sms_sender.sent[0][0] == phone
    assert sms_sender.sent[0][1] == "123456"


@pytest.mark.django_db
def test_verify_code_creates_user_and_profile_for_new_phone():
    phone = "+79998887766"
    sms_sender = DummySmsSender()

    send_verification_code(phone=phone, sms_sender=sms_sender)
    verification = PhoneVerificationCode.objects.get(phone=phone)

    result: VerificationResult = verify_code(phone=phone, code=verification.code)

    assert result.is_new_user is True
    assert UserProfile.objects.filter(phone=phone).exists()
    profile = UserProfile.objects.get(phone=phone)
    assert result.user == profile.user


@pytest.mark.django_db
def test_verify_code_uses_existing_user_profile():
    phone = "+79998887766"
    sms_sender = DummySmsSender()

    send_verification_code(phone=phone, sms_sender=sms_sender)
    verification = PhoneVerificationCode.objects.get(phone=phone)

    first_result: VerificationResult = verify_code(phone=phone, code=verification.code)
    profile = UserProfile.objects.get(phone=phone)

    # Создаём новый код для того же телефона
    send_verification_code(phone=phone, sms_sender=sms_sender)
    new_verification = (
        PhoneVerificationCode.objects.filter(phone=phone, is_used=False)
        .order_by("-created_at")
        .first()
    )

    second_result: VerificationResult = verify_code(phone=phone, code=new_verification.code)

    assert second_result.is_new_user is False
    assert second_result.user == profile.user

