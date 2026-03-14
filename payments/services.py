"""PaymentService — бизнес-логика для управления платежами."""

import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from payments.acquiring import AcquiringService

logger = logging.getLogger(__name__)


class PaymentService:
    @staticmethod
    @transaction.atomic
    def initiate_payment(order_id, payment_method_id) -> tuple:
        """
        Инициировать платёж для заказа.

        1. Создаёт Payment(status=pending).
        2. Вызывает AcquiringService.initiate_payment().
        3. Сохраняет acquiring_payment_id и acquiring_data.

        Args:
            order_id: UUID заказа.
            payment_method_id: UUID метода оплаты.

        Returns:
            tuple(Payment, str): (payment, payment_url)
        """
        from orders.models import Order
        from payments.models import Payment, PaymentMethod

        order = Order.objects.get(id=order_id)
        method = PaymentMethod.objects.get(id=payment_method_id)

        payment = Payment.objects.create(
            order=order,
            amount=order.final_amount,
            method=method,
            status=Payment.Status.PENDING,
        )

        acquiring_response = AcquiringService.initiate_payment(payment)

        payment.acquiring_payment_id = acquiring_response["acquiring_payment_id"]
        payment.acquiring_data = acquiring_response
        payment.status = Payment.Status.PROCESSING
        payment.save(update_fields=["acquiring_payment_id", "acquiring_data", "status", "updated_at"])

        logger.info(
            "Payment %s initiated for order %s, acquiring_id=%s",
            payment.id,
            order_id,
            payment.acquiring_payment_id,
        )

        return payment, acquiring_response.get("payment_url", "")

    @staticmethod
    @transaction.atomic
    def process_webhook(payload: dict):
        """
        Обработать webhook от эквайера.

        1. AcquiringService.handle_webhook(payload) — разбирает payload.
        2. Находит Payment по acquiring_payment_id.
        3. Создаёт PaymentTransaction.
        4. Если completed → Payment.status=completed, Order.status=confirmed,
           ReservationService.complete_reservation для всех резервов.
        5. Если failed → Payment.status=failed, Order.status=cancelled,
           ReservationService.release_order_reservations.

        Args:
            payload: dict — сырой payload от эквайера.

        Returns:
            Payment: обновлённый объект.
        """
        from orders.models import Order
        from orders.services.reservation_service import ReservationService
        from payments.models import Payment, PaymentTransaction

        webhook_data = AcquiringService.handle_webhook(payload)

        acquiring_payment_id = webhook_data["acquiring_payment_id"]
        status = webhook_data["status"]

        payment = Payment.objects.select_for_update().get(
            acquiring_payment_id=acquiring_payment_id
        )

        # Создаём транзакцию
        txn = PaymentTransaction.objects.create(
            payment=payment,
            transaction_type=PaymentTransaction.TransactionType.CHARGE,
            amount=webhook_data["amount"],
            status=(
                PaymentTransaction.Status.SUCCESS
                if status == "completed"
                else PaymentTransaction.Status.FAILED
            ),
            acquiring_transaction_id=webhook_data.get("transaction_id"),
            raw_data=payload,
        )

        if status == "completed":
            payment.status = Payment.Status.COMPLETED
            payment.completed_at = timezone.now()
            payment.save(update_fields=["status", "completed_at", "updated_at"])

            # Обновляем заказ
            order = payment.order
            order.status = Order.Status.PAID
            order.save(update_fields=["status", "updated_at"])

            # Завершаем все активные резервы
            from orders.models import Reservation
            active_reservations = Reservation.objects.filter(
                order=order,
                status=Reservation.Status.ACTIVE,
            )
            for reservation in active_reservations:
                ReservationService.complete_reservation(reservation.id)

            logger.info("Payment %s completed, order %s confirmed", payment.id, order.id)

        elif status == "failed":
            payment.status = Payment.Status.FAILED
            payment.failed_at = timezone.now()
            payment.failure_reason = payload.get("failure_reason", "")
            payment.save(update_fields=["status", "failed_at", "failure_reason", "updated_at"])

            # Отменяем заказ
            order = payment.order
            order.status = Order.Status.CANCELLED
            order.save(update_fields=["status", "updated_at"])

            # Освобождаем резервы
            ReservationService.release_order_reservations(order.id)

            logger.info("Payment %s failed, order %s cancelled", payment.id, order.id)

        return payment

    @staticmethod
    @transaction.atomic
    def refund(payment_id, amount: Decimal = None):
        """
        Инициировать возврат.

        Args:
            payment_id: UUID платежа.
            amount: сумма возврата (None → полный возврат).

        Returns:
            PaymentTransaction: транзакция возврата.
        """
        from payments.models import Payment, PaymentTransaction

        payment = Payment.objects.select_for_update().get(id=payment_id)

        if amount is None:
            amount = payment.amount

        refund_response = AcquiringService.refund(payment, amount)

        # Serialize raw_data: convert Decimal → str for JSON compatibility
        raw_data_serializable = {
            k: str(v) if isinstance(v, Decimal) else v
            for k, v in refund_response.items()
        }

        txn = PaymentTransaction.objects.create(
            payment=payment,
            transaction_type=(
                PaymentTransaction.TransactionType.REFUND
                if amount == payment.amount
                else PaymentTransaction.TransactionType.PARTIAL_REFUND
            ),
            amount=amount,
            status=(
                PaymentTransaction.Status.SUCCESS
                if refund_response["status"] == "success"
                else PaymentTransaction.Status.FAILED
            ),
            acquiring_transaction_id=refund_response.get("transaction_id"),
            raw_data=raw_data_serializable,
        )

        if refund_response["status"] == "success":
            payment.status = Payment.Status.REFUNDED
            payment.save(update_fields=["status", "updated_at"])

        logger.info("Refund transaction %s for payment %s", txn.id, payment_id)
        return txn
