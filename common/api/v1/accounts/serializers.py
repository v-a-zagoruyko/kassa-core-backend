from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers


class SendCodeSerializer(serializers.Serializer):
    phone = PhoneNumberField(region="RU")

    def validate_phone(self, value):
        return value.as_e164


class VerifyCodeSerializer(serializers.Serializer):
    phone = PhoneNumberField(region="RU")
    code = serializers.CharField(max_length=6)

    def validate_phone(self, value):
        return value.as_e164
