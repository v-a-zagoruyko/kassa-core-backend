import json
import logging
import uuid

from django.http import JsonResponse

from common.api.error_response import build_error_payload

logger = logging.getLogger(__name__)


class ApiJsonResponse(JsonResponse):
    """
    Расширенный JsonResponse с удобным методом .json(), как у requests.Response.
    """

    def json(self):
        return json.loads(self.content.decode(self.charset or "utf-8"))


class ApiExceptionMiddleware:
    """
    Middleware для централизованной обработки необработанных ошибок на уровне Django.

    - Присваивает каждому запросу request_id (из заголовка X-Request-ID или генерирует новый UUID).
    - Для путей, начинающихся с /api/, возвращает JSON-ответ в едином формате при необработанной ошибке.
    - Для остальных путей пробрасывает исключение дальше, чтобы сохранить стандартное поведение Django/админки.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.request_id = request_id

        try:
            response = self.get_response(request)
        except Exception as exc:  # noqa: BLE001
            if request.path.startswith("/api/"):
                logger.exception("Unhandled API exception", extra={"request_id": request_id})
                payload = build_error_payload(
                    code="server_error",
                    message="Внутренняя ошибка сервера.",
                    status_code=500,
                    request_id=request_id,
                )
                response = ApiJsonResponse(payload, status=500)
                # Для ошибочного ответа по API также добавляем X-Request-ID
                response["X-Request-ID"] = request_id
                return response

            # Для не-API путей даём стандартному обработчику поднять ошибку
            raise

        # Прокидываем request_id в ответ
        try:
            # DRF Response
            if hasattr(response, "headers"):
                response.headers.setdefault("X-Request-ID", request_id)
            else:
                response["X-Request-ID"] = request_id
        except Exception:  # noqa: BLE001
            # Не хотим ронять ответ, если объект Response нестандартный
            logger.debug("Не удалось добавить X-Request-ID в ответ", exc_info=True)

        return response

