from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def api_version(request):
    """
    GET /api/v1/

    Returns API version info.
    """
    return Response(
        {
            "version": "1.0.0",
            "status": "ok",
            "api": "kassa-core",
        }
    )
