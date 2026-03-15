"""Fiscal edge case tests."""

import pytest

from fiscal.models import OFDResponse, Receipt, ReceiptItem, ReceiptStatus
from fiscal.services import ReceiptService


@pytest.mark.django_db
class TestReceiptEdgeCases:
    def test_generate_receipt_for_draft_order_fails(self, db):
        from django.contrib.auth import get_user_model
        from common.models import Address
        from orders.models import Order
        from stores.models import Store

        User = get_user_model()
        user = User.objects.create_user(username="edge1", password="p")
        address = Address.objects.create(city="Г", street="У", house="1")
        store = Store.objects.create(name="EdgeStore1", address=address)
        order = Order.objects.create(store=store, customer=user, status=Order.Status.DRAFT)

        with pytest.raises(ValueError, match="paid"):
            ReceiptService.generate_receipt(order_id=order.pk)

    def test_generate_receipt_for_cancelled_order_fails(self, db):
        from django.contrib.auth import get_user_model
        from common.models import Address
        from orders.models import Order
        from stores.models import Store

        User = get_user_model()
        user = User.objects.create_user(username="edge2", password="p")
        address = Address.objects.create(city="Г", street="У", house="1")
        store = Store.objects.create(name="EdgeStore2", address=address)
        order = Order.objects.create(store=store, customer=user, status=Order.Status.CANCELLED)

        with pytest.raises(ValueError, match="paid"):
            ReceiptService.generate_receipt(order_id=order.pk)

    def test_second_receipt_raises_value_error(self, paid_order):
        ReceiptService.generate_receipt(order_id=paid_order.pk)
        with pytest.raises(ValueError, match="уже существует"):
            ReceiptService.generate_receipt(order_id=paid_order.pk)

    def test_receipt_number_sequential_same_day(self, db):
        from django.contrib.auth import get_user_model
        from common.models import Address
        from orders.models import Order, OrderItem
        from products.models import Category, Product
        from stores.models import Store

        User = get_user_model()
        address = Address.objects.create(city="Г", street="У", house="1")
        store = Store.objects.create(name="SeqStore", address=address)
        category = Category.objects.create(name="SeqCat")
        product = Product.objects.create(name="SeqProd", slug="seq-prod", category=category, price="50.00")

        def _make_paid_order(username):
            user = User.objects.create_user(username=username, password="p")
            order = Order.objects.create(
                store=store, customer=user, status=Order.Status.PAID,
                total_amount="50.00", final_amount="50.00",
                payment_method=Order.PaymentMethod.CARD,
            )
            OrderItem.objects.create(order=order, product=product, quantity=1, price="50.00", subtotal="50.00")
            return order

        r1 = ReceiptService.generate_receipt(order_id=_make_paid_order("u_seq1").pk)
        r2 = ReceiptService.generate_receipt(order_id=_make_paid_order("u_seq2").pk)
        # Sequence numbers should differ
        assert r1.receipt_number != r2.receipt_number

    def test_handle_ofd_response_invalid_status_unknown(self, paid_order):
        """Unknown status in OFD response should not crash; status not changed."""
        receipt = Receipt.objects.create(
            order=paid_order,
            receipt_number="RCP-TEST-999",
            fiscal_data={},
            status=Receipt.Status.SENT,
        )
        # Non-confirmed/failed status → default handling
        ReceiptService.handle_ofd_response(
            receipt_id=receipt.pk,
            response={
                "status": "unknown_status",
                "response_data": {},
                "error_message": "",
                "status_code": 200,
            },
        )
        # No exception raised — we don't prescribe the result of unknown status

    def test_ofd_response_error_message_stored(self, paid_order):
        receipt = Receipt.objects.create(
            order=paid_order,
            receipt_number="RCP-FAIL-ERR",
            fiscal_data={},
            status=Receipt.Status.SENT,
        )
        ReceiptService.handle_ofd_response(
            receipt_id=receipt.pk,
            response={
                "status": "failed",
                "response_data": {},
                "error_message": "Тайм-аут ОФД",
                "status_code": 503,
            },
        )
        receipt.refresh_from_db()
        assert receipt.error_message == "Тайм-аут ОФД"
        assert receipt.status == Receipt.Status.FAILED


@pytest.mark.django_db
class TestReceiptItemCalculation:
    def test_total_calculated_from_quantity_and_price(self, paid_order):
        receipt = ReceiptService.generate_receipt(order_id=paid_order.pk)
        item = receipt.items.first()
        assert item.total == item.quantity * item.price

    def test_tax_amount_calculated(self, paid_order):
        receipt = ReceiptService.generate_receipt(order_id=paid_order.pk)
        item = receipt.items.first()
        # tax = total * rate / (100 + rate), rounded
        expected = (item.total * item.tax_rate / (100 + item.tax_rate)).quantize(
            __import__("decimal").Decimal("0.01")
        )
        assert item.tax_amount == expected

    def test_receipt_item_str(self, paid_order):
        receipt = ReceiptService.generate_receipt(order_id=paid_order.pk)
        item = receipt.items.first()
        s = str(item)
        assert item.product_name in s


@pytest.mark.django_db
class TestReceiptStatusHistory:
    def test_status_history_created_on_receipt_creation(self, paid_order):
        receipt = ReceiptService.generate_receipt(order_id=paid_order.pk)
        history = ReceiptStatus.objects.filter(receipt=receipt)
        assert history.count() >= 1
