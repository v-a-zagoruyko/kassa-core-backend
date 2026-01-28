from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "accounts"
    verbose_name = "Пользователи"

    def ready(self) -> None:
        from . import signals  # noqa: F401

        return super().ready()
