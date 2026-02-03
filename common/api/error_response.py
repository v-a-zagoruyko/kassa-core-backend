"""
Единый формат тела ошибки для API (DRF exception_handler и middleware).
"""

from typing import Any, Dict, Optional


def build_error_payload(
    *,
    code: str,
    message: str,
    status_code: int,
    request_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Собирает словарь тела ответа об ошибке в едином формате."""
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
