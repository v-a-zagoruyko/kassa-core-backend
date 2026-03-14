"""Клиент для взаимодействия с ОФД (Оператором Фискальных Данных)."""

from uuid import UUID


class OFDClient:
    """
    Базовый клиент для работы с ОФД.
    Текущая реализация — заглушка. Полноценная интеграция в Milestone 3.
    """

    def send_receipt(self, receipt) -> dict:
        """
        Отправляет чек в ОФД.

        Заглушка: возвращает подтверждение приёма без реального HTTP-запроса.
        """
        return {"status": "accepted", "id": str(receipt.id)}

    def check_status(self, receipt_id: UUID) -> dict:
        """
        Проверяет статус чека в ОФД.

        Заглушка: всегда возвращает «confirmed».
        """
        return {"status": "confirmed"}

    def parse_response(self, response: dict) -> dict:
        """Разбирает ответ ОФД и возвращает нормализованный словарь."""
        return response
