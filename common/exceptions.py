"""
Общие кастомные исключения проекта.
"""


class AppError(Exception):
    """
    Базовое приложение-специфичное исключение.
    """


class ConfigurationError(AppError):
    """
    Ошибка конфигурации приложения (например, отсутствуют обязательные настройки).
    """


class ExternalServiceError(AppError):
    """
    Ошибка при обращении к внешнему сервису.
    """


class DomainValidationError(AppError):
    """
    Ошибка доменной валидации, не покрываемая стандартными ValidationError.
    """

