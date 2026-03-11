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

    roles = models.ManyToManyField(
        "Role",
        blank=True,
        related_name="users",
        verbose_name="Роли",
    )

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ["-created_at"]

    def __str__(self):
        return self.username

    @property
    def full_name(self):
        return " ".join(filter(None, [self.first_name, self.last_name]))

    def has_permission(self, codename: str) -> bool:
        for role in self.roles.filter(is_active=True):
            if role.get_all_permissions().filter(codename=codename).exists():
                return True
        return False

    def get_all_permissions(self):
        from django.db.models import QuerySet
        result = Permission.objects.none()
        for role in self.roles.filter(is_active=True):
            result = result | role.get_all_permissions()
        return result.distinct()


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
    language = models.CharField(max_length=10, default="ru")
    timezone = models.CharField(max_length=64, default="UTC")
    notifications_enabled = models.BooleanField(default=True)
    theme = models.CharField(max_length=20, default="light")
    extra = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Настройки пользователя"
        verbose_name_plural = "Настройки пользователей"

    def __str__(self):
        return f"Настройки пользователя {self.user}"

    @classmethod
    def get(cls, user):
        settings_obj, _ = cls.objects.get_or_create(user=user)
        return settings_obj


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


class Permission(BaseModel):
    name = models.CharField(max_length=100, verbose_name="Название")
    codename = models.CharField(max_length=100, unique=True, verbose_name="Кодовое имя")
    description = models.TextField(blank=True, verbose_name="Описание")

    class Meta:
        verbose_name = "Разрешение"
        verbose_name_plural = "Разрешения"
        ordering = ["codename"]

    def __str__(self):
        return self.codename


class Role(BaseModel):
    name = models.CharField(max_length=100, verbose_name="Название")
    codename = models.CharField(max_length=100, unique=True, verbose_name="Кодовое имя")
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
        verbose_name="Родительская роль",
    )
    description = models.TextField(blank=True, verbose_name="Описание")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    permissions = models.ManyToManyField(
        Permission,
        through="RolePermission",
        blank=True,
        verbose_name="Разрешения",
    )

    class Meta:
        verbose_name = "Роль"
        verbose_name_plural = "Роли"
        ordering = ["codename"]

    def __str__(self):
        return self.codename

    def get_ancestors(self):
        ancestors = []
        current = self.parent
        while current is not None:
            ancestors.append(current)
            current = current.parent
        return ancestors

    def get_all_permissions(self):
        role_ids = [self.pk] + [r.pk for r in self.get_ancestors()]
        return Permission.objects.filter(
            rolepermission__role_id__in=role_ids
        ).distinct()


class RolePermission(BaseModel):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, verbose_name="Роль")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, verbose_name="Разрешение")

    class Meta:
        verbose_name = "Разрешение роли"
        verbose_name_plural = "Разрешения ролей"
        unique_together = (("role", "permission"),)

    def __str__(self):
        return f"{self.role} → {self.permission}"


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
