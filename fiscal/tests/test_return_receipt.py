"""Тесты ReturnReceipt — чек возврата прихода по 54-ФЗ."""

from decimal import Decimal
from unittest.mock import patch

import pytest

from fiscal.models import Receipt, ReturnReceipt, ReturnReceiptItem
from fiscal.services import ReceiptService
from fiscal.tasks import send_return_receipt_to_ofd


# ─────────────────────────────────── Fixtures ────────────────────────────────


@pytest.fixture
def paid_order_for_return(db):
    """Оплаченный заказ с одной позицией (для тестов возврата)."""
    from django.contrib.auth import get_user_model
    from common.models import Address
    from products.models import Category, Product
    from stores.models import Store
    from orders.models import Order, OrderItem

    User = get_user_model()
    user = User.objects.create_user(username='ret_buyer', password='pass')
    address = Address.objects.create(city='Город', street='Улица', house='1')
    store = Store.objects.create(name='RetStore', address=address)
    category = Category.objects.create(name='RetCat', slug='ret-cat')
    product = Product.objects.create(
        name='Товар для возврата',
        slug='ret-product',
        category=category,
        price='100.00',
    )
    order = Order.objects.create(
        store=store,
        customer=user,
        status=Order.Status.PAID,
        total_amount='100.00',
        final_amount='100.00',
        payment_method=Order.PaymentMethod.CARD,
    )
    item = OrderItem.objects.create(
        order=order,
        product=product,
        quantity=1,
        price='100.00',
        subtotal='100.00',
    )
    order._test_item = item
    return order


@pytest.fixture
def cash_return(db, paid_order_for_return):
    """Возврат наличными для paid_order_for_return."""
    from returns.models import Return, ReturnItem

    ret = Return.objects.create(
        order=paid_order_for_return,
        refund_method=Return.RefundMethod.CASH,
        status=Return.Status.COMPLETED,
        total_amount=Decimal('100.00'),
    )
    ReturnItem.objects.create(
        return_obj=ret,
        order_item=paid_order_for_return._test_item,
        quantity=1,
        refund_amount=Decimal('100.00'),
    )
    return ret


@pytest.fixture
def card_return(db, paid_order_for_return):
    """Возврат по карте для paid_order_for_return."""
    from returns.models import Return, ReturnItem

    ret = Return.objects.create(
        order=paid_order_for_return,
        refund_method=Return.RefundMethod.CARD,
        status=Return.Status.PROCESSING,
        total_amount=Decimal('100.00'),
    )
    ReturnItem.objects.create(
        return_obj=ret,
        order_item=paid_order_for_return._test_item,
        quantity=1,
        refund_amount=Decimal('100.00'),
    )
    return ret


# ──────────────────────────── ReturnReceiptItem.save() ───────────────────────


@pytest.mark.django_db
class TestReturnReceiptItemSave:
    def _make_receipt(self, cash_return):
        return ReturnReceipt.objects.create(
            return_obj=cash_return,
            receipt_number='RET-20260101-000001',
            fiscal_data={'type': 'return_income', 'total': '100.00', 'items': []},
        )

    def test_auto_calculates_total(self, cash_return):
        receipt = self._make_receipt(cash_return)
        item = ReturnReceiptItem(
            receipt=receipt,
            product_name='Товар',
            quantity=2,
            price=Decimal('50.00'),
            tax_amount=Decimal('0.00'),  # будет пересчитан
        )
        item.save()
        assert item.total == Decimal('100.00')

    def test_auto_calculates_tax_amount(self, cash_return):
        receipt = self._make_receipt(cash_return)
        item = ReturnReceiptItem(
            receipt=receipt,
            product_name='Товар',
            quantity=1,
            price=Decimal('120.00'),
            tax_amount=Decimal('0.00'),  # будет пересчитан
        )
        item.save()
        # НДС 20% изнутри: 120 * 20 / 120 = 20.00
        assert item.tax_amount == Decimal('20.00')
        assert item.total == Decimal('120.00')


# ─────────────────────────── Unique / OneToOne constraints ───────────────────


@pytest.mark.django_db
class TestReturnReceiptConstraints:
    def test_receipt_number_unique(self, cash_return, card_return):
        ReturnReceipt.objects.create(
            return_obj=cash_return,
            receipt_number='RET-20260101-000001',
            fiscal_data={},
        )
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            ReturnReceipt.objects.create(
                return_obj=card_return,
                receipt_number='RET-20260101-000001',
                fiscal_data={},
            )

    def test_onetone_return_unique(self, cash_return):
        ReturnReceipt.objects.create(
            return_obj=cash_return,
            receipt_number='RET-20260101-000001',
            fiscal_data={},
        )
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            ReturnReceipt.objects.create(
                return_obj=cash_return,
                receipt_number='RET-20260101-000002',
                fiscal_data={},
            )


# ─────────────────────── ReceiptService.generate_return_receipt ──────────────


@pytest.mark.django_db
class TestGenerateReturnReceipt:
    def test_success_cash_return(self, cash_return):
        rr = ReceiptService.generate_return_receipt(return_id=cash_return.pk)

        assert rr.pk is not None
        assert rr.return_obj == cash_return
        assert rr.status == Receipt.Status.PENDING
        assert rr.receipt_number.startswith('RET-')
        assert rr.items.count() == 1

    def test_success_card_return(self, card_return):
        rr = ReceiptService.generate_return_receipt(return_id=card_return.pk)

        assert rr.pk is not None
        assert rr.return_obj == card_return

    def test_fiscal_data_type_is_return_income(self, cash_return):
        rr = ReceiptService.generate_return_receipt(return_id=cash_return.pk)
        assert rr.fiscal_data['type'] == 'return_income'

    def test_fiscal_data_total_matches_return(self, cash_return):
        rr = ReceiptService.generate_return_receipt(return_id=cash_return.pk)
        assert Decimal(rr.fiscal_data['total']) == cash_return.total_amount

    def test_duplicate_raises_value_error(self, cash_return):
        ReceiptService.generate_return_receipt(return_id=cash_return.pk)
        with pytest.raises(ValueError, match='уже существует'):
            ReceiptService.generate_return_receipt(return_id=cash_return.pk)

    def test_original_receipt_filled_when_order_has_receipt(self, cash_return, paid_order_for_return):
        # Создаём чек продажи для заказа
        original = Receipt.objects.create(
            order=paid_order_for_return,
            receipt_number='RCP-20260101-000001',
            fiscal_data={'type': 'income'},
        )
        rr = ReceiptService.generate_return_receipt(return_id=cash_return.pk)
        assert rr.original_receipt == original
        assert rr.fiscal_data['original_receipt_number'] == original.receipt_number

    def test_original_receipt_none_when_no_order_receipt(self, cash_return):
        rr = ReceiptService.generate_return_receipt(return_id=cash_return.pk)
        assert rr.original_receipt is None
        assert rr.fiscal_data['original_receipt_number'] is None

    def test_receipt_number_format(self, cash_return):
        from django.utils import timezone
        rr = ReceiptService.generate_return_receipt(return_id=cash_return.pk)
        date_str = timezone.now().strftime('%Y%m%d')
        assert rr.receipt_number == f'RET-{date_str}-000001'


# ─────────────────────── ReturnService.process_refund integration ────────────


@pytest.mark.django_db
class TestProcessRefundFiscalization:
    """Проверяем что process_refund создаёт ReturnReceipt через fiscalization."""

    def _create_pending_return(self, order, item, refund_method):
        from returns.models import Return, ReturnItem, ReturnStatus

        ret = Return.objects.create(
            order=order,
            refund_method=refund_method,
            status=Return.Status.PENDING,
            total_amount=Decimal('100.00'),
        )
        ReturnItem.objects.create(
            return_obj=ret,
            order_item=item,
            quantity=1,
            refund_amount=Decimal('100.00'),
        )
        ReturnStatus.objects.create(
            return_obj=ret,
            status=Return.Status.PENDING,
        )
        return ret

    @patch('fiscal.tasks.send_return_receipt_to_ofd.delay')
    def test_process_cash_refund_creates_return_receipt(self, mock_delay, paid_order_for_return):
        from returns.services import ReturnService

        ret = self._create_pending_return(
            paid_order_for_return,
            paid_order_for_return._test_item,
            'cash',
        )
        ReturnService.process_refund(ret.pk)
        assert ReturnReceipt.objects.filter(return_obj=ret).exists()
        mock_delay.assert_called_once()

    @patch('fiscal.tasks.send_return_receipt_to_ofd.delay')
    def test_process_card_refund_creates_return_receipt(self, mock_delay, paid_order_for_return):
        from returns.services import ReturnService

        ret = self._create_pending_return(
            paid_order_for_return,
            paid_order_for_return._test_item,
            'card',
        )
        ReturnService.process_refund(ret.pk)
        assert ReturnReceipt.objects.filter(return_obj=ret).exists()
        mock_delay.assert_called_once()

    @patch('fiscal.services.ReceiptService.generate_return_receipt', side_effect=RuntimeError('OFD down'))
    def test_fiscalization_failure_does_not_rollback_refund(self, mock_gen, paid_order_for_return):
        """Если фискализация падает — сам возврат НЕ откатывается."""
        from returns.models import Return
        from returns.services import ReturnService

        ret = self._create_pending_return(
            paid_order_for_return,
            paid_order_for_return._test_item,
            'cash',
        )
        processed = ReturnService.process_refund(ret.pk)
        # Возврат завершён несмотря на ошибку фискализации
        assert processed.status == Return.Status.COMPLETED
        assert not ReturnReceipt.objects.filter(return_obj=ret).exists()


# ──────────────────────── send_return_receipt_to_ofd task ────────────────────


@pytest.mark.django_db
class TestSendReturnReceiptToOfd:
    def _make_return_receipt(self, cash_return):
        return ReturnReceipt.objects.create(
            return_obj=cash_return,
            receipt_number='RET-20260101-000099',
            fiscal_data={'type': 'return_income', 'total': '100.00', 'items': []},
            status=Receipt.Status.PENDING,
        )

    def test_success_sets_confirmed(self, cash_return):
        rr = self._make_return_receipt(cash_return)
        # OFDClient.send_receipt заглушка возвращает {"status": "accepted"}
        send_return_receipt_to_ofd(str(rr.pk))
        rr.refresh_from_db()
        assert rr.status == Receipt.Status.CONFIRMED
        assert rr.confirmed_at is not None
        assert rr.sent_at is not None

    def test_already_confirmed_skips(self, cash_return):
        from django.utils import timezone as tz
        rr = self._make_return_receipt(cash_return)
        rr.status = Receipt.Status.CONFIRMED
        rr.confirmed_at = tz.now()
        rr.save()

        # Вызываем задачу — ничего не должно измениться
        send_return_receipt_to_ofd(str(rr.pk))
        rr.refresh_from_db()
        assert rr.status == Receipt.Status.CONFIRMED  # не изменился

    def test_ofd_error_sets_failed(self, cash_return):
        from fiscal.ofd_client import OFDClient
        rr = self._make_return_receipt(cash_return)

        with patch.object(OFDClient, 'send_receipt', side_effect=ConnectionError('OFD unavailable')):
            # В тестовом режиме Celery self.retry() поднимает Retry,
            # apply() его перехватывает — статус задачи будет RETRY/FAILURE
            result = send_return_receipt_to_ofd.apply(args=[str(rr.pk)])
            # Задача должна упасть (retry/failure)
            assert not result.successful()

        rr.refresh_from_db()
        assert rr.status == Receipt.Status.FAILED
        assert 'OFD unavailable' in rr.error_message
