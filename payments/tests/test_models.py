"""
Базовые тесты для Payment моделей.
"""
import pytest
from decimal import Decimal


@pytest.fixture
def store(db):
    from stores.models import Store
    from common.models import Address
    address = Address.objects.create(city="Тюмень", street="Ленина", house="1")
    return Store.objects.create(name="Test Store", address=address)


@pytest.fixture
def user(db):
    from accounts.models import User
    return User.objects.create_user(username="testuser", password="testpass123")


@pytest.fixture
def order(db, store, user):
    from orders.models import Order
    return Order.objects.create(store=store, customer=user)


@pytest.fixture
def payment_method(db):
    from payments.models import PaymentMethod
    return PaymentMethod.objects.create(name="card", display_name="Банковская карта")


@pytest.mark.django_db
def test_payment_method_creation(payment_method):
    """PaymentMethod создаётся корректно."""
    from payments.models import PaymentMethod
    pm = PaymentMethod.objects.get(name="card")
    assert pm.display_name == "Банковская карта"
    assert pm.is_active is True


@pytest.mark.django_db
def test_payment_creation(order, payment_method):
    """Payment создаётся в статусе pending."""
    from payments.models import Payment
    payment = Payment.objects.create(
        order=order,
        amount=Decimal("500.00"),
        method=payment_method,
    )
    assert payment.status == Payment.Status.PENDING
    assert payment.currency == "RUB"
    assert payment.acquiring_data == {}
    assert payment.acquiring_payment_id is None


@pytest.mark.django_db
def test_payment_transaction_creation(order, payment_method):
    """PaymentTransaction создаётся и связана с Payment."""
    from payments.models import Payment, PaymentTransaction
    payment = Payment.objects.create(
        order=order,
        amount=Decimal("500.00"),
        method=payment_method,
    )
    txn = PaymentTransaction.objects.create(
        payment=payment,
        transaction_type=PaymentTransaction.TransactionType.CHARGE,
        amount=Decimal("500.00"),
        status=PaymentTransaction.Status.SUCCESS,
        acquiring_transaction_id="txn_123",
    )
    assert txn.payment == payment
    assert txn.raw_data == {}
    assert str(txn)


@pytest.mark.django_db
def test_payment_method_inactive():
    """Можно создать неактивный PaymentMethod."""
    from payments.models import PaymentMethod
    pm = PaymentMethod.objects.create(name="cash", display_name="Наличные", is_active=False)
    assert pm.is_active is False


@pytest.mark.django_db
def test_payment_str_repr(order, payment_method):
    """__str__ возвращает строку."""
    from payments.models import Payment
    payment = Payment.objects.create(
        order=order,
        amount=Decimal("100.00"),
        method=payment_method,
    )
    assert "100.00" in str(payment)
    assert "pending" in str(payment).lower() or "Ожидает" in str(payment)
