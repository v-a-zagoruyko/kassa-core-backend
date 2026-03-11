"""Signals for the orders app."""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver


@receiver(pre_save, sender='orders.Order')
def capture_previous_order_status(sender, instance, **kwargs):
    """Capture the previous status before saving, for change detection."""
    if instance.pk:
        try:
            previous = sender.objects.get(pk=instance.pk)
            instance._previous_status = previous.status
        except sender.DoesNotExist:
            instance._previous_status = None
    else:
        instance._previous_status = None


@receiver(post_save, sender='orders.Order')
def create_order_status_log(sender, instance, created, **kwargs):
    """Create an OrderStatusLog entry whenever Order.status changes."""
    from orders.models import OrderStatusLog

    if created:
        # Log the initial status on creation
        OrderStatusLog.objects.create(
            order=instance,
            status=instance.status,
            comment='Заказ создан',
        )
    else:
        previous = getattr(instance, '_previous_status', None)
        if previous is not None and previous != instance.status:
            OrderStatusLog.objects.create(
                order=instance,
                status=instance.status,
            )
