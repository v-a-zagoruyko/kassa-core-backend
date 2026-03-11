from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import UserSettings
from accounts.serializers import UserSettingsSerializer
from accounts.services.phone_auth_service import VerificationResult, send_verification_code, verify_code

from .serializers import SendCodeSerializer, VerifyCodeSerializer


class SendCodeView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        serializer = SendCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data["phone"]
        send_verification_code(phone=phone)

        return Response(
            {"detail": "Код подтверждения отправлен."},
            status=status.HTTP_200_OK,
        )


class VerifyCodeView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        serializer = VerifyCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data["phone"]
        code = serializer.validated_data["code"]

        result: VerificationResult = verify_code(phone=phone, code=code)
        user = result.user

        refresh = RefreshToken.for_user(user)

        profile = getattr(user, "profile", None)
        is_profile_name_required = not bool(user.first_name or user.last_name)

        user_payload = {
            "id": str(user.id),
            "phone": str(profile.phone) if profile else None,
            "full_name": user.full_name,
            "is_profile_name_required": is_profile_name_required,
        }

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": user_payload,
                "is_new_user": result.is_new_user,
            },
            status=status.HTTP_200_OK,
        )


class UserSettingsView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        settings_obj = UserSettings.get(request.user)
        serializer = UserSettingsSerializer(settings_obj)
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        settings_obj = UserSettings.get(request.user)
        serializer = UserSettingsSerializer(settings_obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
