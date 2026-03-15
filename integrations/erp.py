"""Интеграция с ERP (1С, МойСклад). Заглушка — реализация в Milestone 3."""


class ERPService:
    """Интеграция с ERP (1С, МойСклад). Заглушка — реализация в Milestone 3."""

    def sync_products(self) -> dict:
        """Синхронизировать номенклатуру. Заглушка: {"synced": 0}"""
        return {"synced": 0}

    def sync_orders(self) -> dict:
        """Синхронизировать заказы. Заглушка: {"synced": 0}"""
        return {"synced": 0}

    def push_sales(self, date_from, date_to) -> dict:
        """Выгрузить продажи в ERP. Заглушка: {"pushed": 0}"""
        return {"pushed": 0}
