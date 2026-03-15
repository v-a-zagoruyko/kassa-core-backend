"""Интеграция со складом. Заглушка — реализация в Milestone 3."""


class WarehouseService:
    """Интеграция со складом. Заглушка — реализация в Milestone 3."""

    def get_stock(self, product_id, store_id) -> dict:
        """Получить остаток. Возвращает {"quantity": 0, "reserved": 0}"""
        return {"quantity": 0, "reserved": 0}

    def reserve_item(self, product_id, store_id, quantity) -> bool:
        """Зарезервировать товар. Заглушка: True"""
        return True

    def release_item(self, product_id, store_id, quantity) -> bool:
        """Освободить резерв. Заглушка: True"""
        return True

    def sync_inventory(self, store_id=None) -> dict:
        """Синхронизировать остатки. Заглушка: {"synced": 0}"""
        return {"synced": 0}
