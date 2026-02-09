from django.urls import path

from .views import SendCodeView, VerifyCodeView


urlpatterns = [
    path("auth/send_code/", SendCodeView.as_view(), name="accounts-auth-send-code"),
    path("auth/verify_code/", VerifyCodeView.as_view(), name="accounts-auth-verify-code"),
]
