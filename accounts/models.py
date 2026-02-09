from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager, PermissionsMixin
from common.models import Address, BaseModel
from phonenumber_field.modelfields import PhoneNumberField


class UserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)

        if not username:
            raise ValueError("Необходимо указать username")

        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Суперпользователь должен иметь is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Суперпользователь должен иметь is_superuser=True.")

        if not username:
            raise ValueError("Необходимо указать username")

        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user


class User(BaseModel, AbstractUser):
    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ["-created_at"]

    def __str__(self):
        return self.username

    @property
    def full_name(self):
        return " ".join(filter(None, [self.first_name, self.last_name]))


class UserProfile(BaseModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="Пользователь",
    )
    phone = PhoneNumberField(
        region="RU",
        unique=True,
        verbose_name="Телефон",
    )

    class Meta:
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"

    def __str__(self):
        return f"Профиль пользователя {self.user}"


class UserSettings(BaseModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="settings",
        verbose_name="Пользователь",
    )
    is_order_push_notifications_enabled = models.BooleanField(
        default=True,
        verbose_name="Push уведомления о заказах",
    )
    is_promo_push_notifications_enabled = models.BooleanField(
        default=True,
        verbose_name="Push уведомления о скидках",
    )
    is_promo_sms_notifications_enabled = models.BooleanField(
        default=True,
        verbose_name="SMS уведомления о скидках",
    )
    is_promo_email_notifications_enabled = models.BooleanField(
        default=True,
        verbose_name="Email уведомления о скидках",
    )

    class Meta:
        verbose_name = "Настройки пользователя"
        verbose_name_plural = "Настройки пользователей"

    def __str__(self):
        return f"Настройки пользователя {self.user}"


class UserAddress(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="addresses",
        verbose_name="Пользователь",
    )
    address = models.ForeignKey(
        Address,
        on_delete=models.CASCADE,
        related_name="addresses",
        verbose_name="Адрес",
    )

    class Meta:
        verbose_name = "Адрес пользователя"
        verbose_name_plural = "Адреса пользователей"

    def __str__(self):
        return f"Адрес пользователя {self.user}"


class PhoneVerificationCode(BaseModel):
    phone = PhoneNumberField(
        region="RU",
        verbose_name="Телефон",
        db_index=True,
    )
    code = models.CharField(
        max_length=6,
        verbose_name="Код подтверждения",
    )
    expires_at = models.DateTimeField(
        verbose_name="Время истечения кода",
    )
    attempts = models.PositiveIntegerField(
        default=0,
        verbose_name="Количество попыток проверки",
    )
    is_used = models.BooleanField(
        default=False,
        verbose_name="Код использован",
    )

    class Meta:
        verbose_name = "Код подтверждения телефона"
        verbose_name_plural = "Коды подтверждения телефона"
        indexes = [
            models.Index(fields=["phone", "is_used", "expires_at"]),
        ]

    def __str__(self):
        return f"Код для {self.phone}"
