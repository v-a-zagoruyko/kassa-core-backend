import logging
from typing import Any, Dict, Optional

from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import exceptions as drf_exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from common.exceptions import AppError, ConfigurationError, DomainValidationError, ExternalServiceError

logger = logging.getLogger(__name__)


def _get_request_id_from_context(context: Dict[str, Any]) -> Optional[str]:
    request = context.get("request")
    if not request:
        return None

    request_id = getattr(request, "request_id", None) or request.META.get("HTTP_X_REQUEST_ID")
    return str(request_id) if request_id else None


def _build_error_payload(
    *,
    code: str,
    message: str,
    status_code: int,
    request_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "status": status_code,
        }
    }
    if request_id:
        payload["error"]["request_id"] = request_id
    if details is not None:
        payload["error"]["details"] = details
    return payload


def custom_exception_handler(exc: Exception, context: Dict[str, Any]) -> Response:
    """
    Централизованный обработчик ошибок DRF, приводящий ответы к единому формату.
    """

    request_id = _get_request_id_from_context(context)

    # Стандартная DRF-валидация
    if isinstance(exc, drf_exceptions.ValidationError):
        drf_response = drf_exception_handler(exc, context)
        assert drf_response is not None

        payload = _build_error_payload(
            code="validation_error",
            message="Ошибка валидации данных.",
            status_code=drf_response.status_code,
            request_id=request_id,
            details=drf_response.data,
        )
        return Response(payload, status=drf_response.status_code)

    # Django ValidationError (например, из model.clean())
    if isinstance(exc, DjangoValidationError):
        details = exc.message_dict if hasattr(exc, "message_dict") else {"non_field_errors": exc.messages}
        payload = _build_error_payload(
            code="validation_error",
            message="Ошибка валидации данных.",
            status_code=status.HTTP_400_BAD_REQUEST,
            request_id=request_id,
            details=details,
        )
        return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    # HTTP ошибки
    if isinstance(exc, Http404):
        payload = _build_error_payload(
            code="not_found",
            message="Ресурс не найден.",
            status_code=status.HTTP_404_NOT_FOUND,
            request_id=request_id,
        )
        return Response(payload, status=status.HTTP_404_NOT_FOUND)

    if isinstance(exc, PermissionDenied):
        payload = _build_error_payload(
            code="permission_denied",
            message="Доступ запрещён.",
            status_code=status.HTTP_403_FORBIDDEN,
            request_id=request_id,
        )
        return Response(payload, status=status.HTTP_403_FORBIDDEN)

    # Кастомные исключения проекта
    if isinstance(exc, AppError):
        if isinstance(exc, ConfigurationError):
            code = "configuration_error"
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        elif isinstance(exc, ExternalServiceError):
            code = "external_service_error"
            status_code = status.HTTP_502_BAD_GATEWAY
        elif isinstance(exc, DomainValidationError):
            code = "domain_validation_error"
            status_code = status.HTTP_400_BAD_REQUEST
        else:
            code = "application_error"
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

        logger.error("Application error: %s", exc, extra={"request_id": request_id})

        payload = _build_error_payload(
            code=code,
            message=str(exc) or "Ошибка приложения.",
            status_code=status_code,
            request_id=request_id,
        )
        return Response(payload, status=status_code)

    # Попробовать стандартный DRF handler (например, аутентификация/авторизация)
    drf_response = drf_exception_handler(exc, context)
    if drf_response is not None:
        # DRF уже знает статус и тело, просто оборачиваем
        # Попробуем извлечь код из ответа, если он есть
        default_code = getattr(getattr(exc, "default_code", None), "__str__", lambda: None)()
        code = default_code or "error"

        payload = _build_error_payload(
            code=code,
            message=str(exc) or "Ошибка запроса.",
            status_code=drf_response.status_code,
            request_id=request_id,
            details=drf_response.data if isinstance(drf_response.data, dict) else None,
        )
        return Response(payload, status=drf_response.status_code)

    # Непредвиденная ошибка — логируем и возвращаем generic 500
    logger.exception("Unexpected server error", exc_info=exc, extra={"request_id": request_id})

    payload = _build_error_payload(
        code="server_error",
        message="Внутренняя ошибка сервера.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        request_id=request_id,
    )
    return Response(payload, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

