import pytest
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from django.test import RequestFactory
from rest_framework import exceptions as drf_exceptions, status
from rest_framework.request import Request

from common.api.exception_handler import custom_exception_handler
from common.exceptions import ConfigurationError
from common.middleware import ApiExceptionMiddleware


def test_custom_exception_handler_drf_validation_error_wraps_response():
    factory = RequestFactory()
    django_request = factory.post("/api/test/", data={})
    request = Request(django_request)

    exc = drf_exceptions.ValidationError({"field": ["Обязательное поле."]})
    response = custom_exception_handler(exc, {"request": request})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "error" in response.data
    assert response.data["error"]["code"] == "validation_error"
    assert "details" in response.data["error"]
    assert "field" in response.data["error"]["details"]


def test_custom_exception_handler_django_validation_error():
    factory = RequestFactory()
    django_request = factory.post("/api/test/", data={})
    request = Request(django_request)

    exc = DjangoValidationError({"field": ["Некорректное значение."]})
    response = custom_exception_handler(exc, {"request": request})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["error"]["code"] == "validation_error"
    assert response.data["error"]["details"]["field"] == ["Некорректное значение."]


def test_custom_exception_handler_http404():
    factory = RequestFactory()
    django_request = factory.get("/api/not-found/")
    request = Request(django_request)

    exc = Http404("Не найдено")
    response = custom_exception_handler(exc, {"request": request})

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data["error"]["code"] == "not_found"


def test_custom_exception_handler_configuration_error():
    factory = RequestFactory()
    django_request = factory.get("/api/test/")
    request = Request(django_request)

    exc = ConfigurationError("Некорректная конфигурация")
    response = custom_exception_handler(exc, {"request": request})

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.data["error"]["code"] == "configuration_error"


def test_api_exception_middleware_wraps_unhandled_exception_as_json_for_api_path():
    def get_response(_request):
        raise RuntimeError("Unexpected error")

    middleware = ApiExceptionMiddleware(get_response)
    factory = RequestFactory()
    request = factory.get("/api/test-middleware/")

    response = middleware(request)

    assert response.status_code == 500
    assert response["Content-Type"] == "application/json"
    assert "error" in response.json()
    assert response.json()["error"]["code"] == "server_error"
    assert "X-Request-ID" in response

