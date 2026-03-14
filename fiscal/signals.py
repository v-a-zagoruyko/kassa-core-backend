"""Сигналы фискального домена."""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Receipt, ReceiptStatus


@receiver(pre_save, sender=Receipt)
def capture_old_receipt_status(sender, instance, **kwargs):
    """Сохраняет предыдущий статус чека перед обновлением записи."""
    if instance.pk:
        try:
            old = Receipt.all_objects.get(pk=instance.pk)
            instance._old_status = old.status
        except Receipt.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Receipt)
def create_receipt_status_history(sender, instance, created, **kwargs):
    """Создаёт запись ReceiptStatus при создании или смене статуса чека."""
    old_status = getattr(instance, '_old_status', None)
    if created or (old_status is not None and old_status != instance.status):
        ReceiptStatus.objects.create(
            receipt=instance,
            status=instance.status,
        )
