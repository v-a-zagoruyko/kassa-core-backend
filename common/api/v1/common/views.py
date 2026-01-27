from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from common.services.dadata_service import DadataService
from .serializers import (
    DadataAddressSuggestRequestSerializer,
    DadataAddressSuggestionSerializer,
)


class DadataAddressSuggestView(APIView):
    def post(self, request, *args, **kwargs):
        request_serializer = DadataAddressSuggestRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        service = DadataService()
        query = request_serializer.validated_data["query"]
        count = request_serializer.validated_data.get("count")
        suggestions = service.suggest_addresses(query=query, count=count)

        response_serializer = DadataAddressSuggestionSerializer(
            suggestions,
            many=True,
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)

