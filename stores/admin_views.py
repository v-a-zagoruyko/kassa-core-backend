import json
import logging

from django.http import HttpRequest, JsonResponse

from common.api.v1.common.serializers import (
    AddressFromDadataSerializer,
    DadataSuggestionNormalizerSerializer,
)
from common.models import Address
from common.services.dadata_service import DadataService

logger = logging.getLogger(__name__)


def address_coordinates_view(request: HttpRequest, address_id: int) -> JsonResponse:
    try:
        addr = Address.objects.get(pk=address_id)
    except Address.DoesNotExist:
        return JsonResponse({"error": "not_found"}, status=404)
    return JsonResponse({
        "latitude": str(addr.latitude) if addr.latitude is not None else None,
        "longitude": str(addr.longitude) if addr.longitude is not None else None,
    })


def dadata_address_suggest_view(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        return JsonResponse({"error": "method_not_allowed"}, status=405)
    query = (request.GET.get("query") or "").strip()
    if len(query) < 2:
        return JsonResponse([], safe=False)
    try:
        service = DadataService()
        suggestions = service.suggest_addresses(query=query, count=10)
    except Exception as e:
        logger.exception("Ошибка при запросе подсказок Dadata: %s", e)
        return JsonResponse(
            {"error": "suggest_failed", "message": "Сервис подсказок адресов временно недоступен."},
            status=502,
        )
    result = [
        DadataSuggestionNormalizerSerializer(instance=s).data
        for s in suggestions
    ]
    return JsonResponse(result, safe=False)


def create_address_from_dadata_view(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse({"error": "method_not_allowed"}, status=405)
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({"error": "invalid_json"}, status=400)
    serializer = AddressFromDadataSerializer(data=body)
    if not serializer.is_valid():
        return JsonResponse(
            {"error": "validation_error", "details": serializer.errors},
            status=400,
        )
    data = serializer.validated_data
    apartment = data.get("apartment")
    address, _ = Address.objects.get_or_create(
        city=data["city"],
        street=data["street"],
        house=data["house"],
        apartment=apartment if apartment else None,
        defaults={
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
        },
    )
    return JsonResponse({"address_id": str(address.pk)})
