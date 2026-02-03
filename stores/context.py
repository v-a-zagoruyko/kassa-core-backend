"""Функции для формирования контекста шаблонов (админка Store: карта, адрес)."""

from typing import Any, Dict, Optional

from django.urls import reverse


def get_store_map_context(store_obj: Any, admin_site: Optional[Any] = None) -> Dict[str, str]:
    """
    Формирует контекст для виджета карты в форме редактирования Store.

    :param store_obj: экземпляр Store или None (форма создания)
    :param admin_site: опционально admin site для построения URL (current_app)
    :return: словарь с ключами latitude, longitude, delivery_radius_km,
             address_id, address_coordinates_url
    """
    ctx: Dict[str, str] = {
        "latitude": "",
        "longitude": "",
        "delivery_radius_km": "",
        "address_id": "",
        "address_coordinates_url": "",
    }
    if store_obj and getattr(store_obj, "address_id", None):
        addr = store_obj.address
        if addr.latitude is not None and addr.longitude is not None:
            ctx["latitude"] = str(addr.latitude)
            ctx["longitude"] = str(addr.longitude)
        ctx["delivery_radius_km"] = str(store_obj.delivery_radius_km)
        ctx["address_id"] = str(store_obj.address_id)
    elif store_obj and getattr(store_obj, "delivery_radius_km", None) is not None:
        ctx["delivery_radius_km"] = str(store_obj.delivery_radius_km)
    try:
        ctx["address_coordinates_url"] = reverse(
            "admin:stores_store_address_coordinates",
            kwargs={"address_id": 0},
            current_app=admin_site.name if admin_site else None,
        )
    except Exception:
        pass
    return ctx
