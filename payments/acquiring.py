"""
Заглушка для интеграции с эквайером.

Заменить на реального провайдера (Tinkoff, Сбер, ЮKassa и т.д.) —
достаточно подменить методы AcquiringService, сохранив сигнатуру.

ВАЖНО: В реальной интеграции необходимо проверять подпись (HMAC/RSA)
входящих webhook-запросов. Текущая реализация принимает всё — только для разработки.
"""

import uuid
from decimal import Decimal


class AcquiringService:
    """Сервис-заглушка для работы с эквайером."""

    @staticmethod
    def initiate_payment(payment) -> dict:
        """
        Инициировать платёж у эквайера.

        Args:
            payment: экземпляр Payment.

        Returns:
            dict с ключами:
                - acquiring_payment_id (str)
                - payment_url (str) — URL для редиректа клиента
                - status (str) — всегда 'pending' при инициировании
        """
        # STUB: возвращает mock-данные
        mock_id = f"mock_{uuid.uuid4().hex[:8]}"
        return {
            "acquiring_payment_id": mock_id,
            "payment_url": f"https://mock-acquiring.example.com/pay/{mock_id}",
            "status": "pending",
        }

    @staticmethod
    def handle_webhook(payload: dict) -> dict:
        """
        Обработать webhook от эквайера.

        Args:
            payload: сырой словарь из тела запроса.

        Returns:
            dict с ключами:
                - acquiring_payment_id (str)
                - status (str) — 'completed' или 'failed'
                - transaction_id (str)
                - amount (Decimal)

        NOTE: В продакшне здесь должна быть проверка подписи (HMAC/подпись эквайера).
        """
        # STUB: парсим mock-payload
        return {
            "acquiring_payment_id": payload.get("payment_id", ""),
            "status": payload.get("status", "completed"),
            "transaction_id": payload.get(
                "transaction_id", f"txn_{uuid.uuid4().hex[:8]}"
            ),
            "amount": Decimal(str(payload.get("amount", 0))),
        }

    @staticmethod
    def refund(payment, amount: Decimal) -> dict:
        """
        Инициировать возврат у эквайера.

        Args:
            payment: экземпляр Payment.
            amount: сумма возврата.

        Returns:
            dict с ключами:
                - transaction_id (str)
                - status (str) — 'success' при удаче
                - amount (Decimal)
        """
        # STUB: возвращает mock-данные
        return {
            "transaction_id": f"refund_{uuid.uuid4().hex[:8]}",
            "status": "success",
            "amount": amount,
        }
