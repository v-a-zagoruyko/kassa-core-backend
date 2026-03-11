import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0004_order_status_log'),
    ]

    operations = [
        migrations.CreateModel(
            name='PromoCode',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Дата создания')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Дата обновления')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='Дата удаления')),
                ('is_deleted', models.BooleanField(db_index=True, default=False, verbose_name='Удалено')),
                ('code', models.CharField(db_index=True, max_length=50, unique=True, verbose_name='Код промокода')),
                ('discount_type', models.CharField(choices=[('percent', 'Процент'), ('fixed', 'Фиксированная сумма')], max_length=10, verbose_name='Тип скидки')),
                ('discount_value', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Размер скидки')),
                ('min_order_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Минимальная сумма заказа')),
                ('valid_from', models.DateTimeField(verbose_name='Действует с')),
                ('valid_until', models.DateTimeField(verbose_name='Действует до')),
                ('max_uses', models.IntegerField(blank=True, null=True, verbose_name='Максимальное количество использований')),
                ('uses_count', models.IntegerField(default=0, verbose_name='Количество использований')),
                ('order_types', models.CharField(choices=[('all', 'Все типы'), ('delivery', 'Доставка'), ('pickup', 'Самовывоз')], default='all', max_length=10, verbose_name='Типы заказов')),
                ('is_active', models.BooleanField(db_index=True, default=True, verbose_name='Активен')),
            ],
            options={
                'verbose_name': 'Промокод',
                'verbose_name_plural': 'Промокоды',
                'ordering': ['-created_at'],
                'abstract': False,
            },
        ),
    ]
