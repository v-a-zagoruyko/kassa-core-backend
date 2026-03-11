from decimal import Decimal
import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0004_marking"),
    ]

    operations = [
        # Change quantity from PositiveIntegerField to DecimalField
        migrations.AlterField(
            model_name="stock",
            name="quantity",
            field=models.DecimalField(
                decimal_places=3,
                default=0,
                max_digits=12,
                verbose_name="Количество на складе",
                validators=[
                    django.core.validators.MinValueValidator(
                        0, message="Количество не может быть отрицательным."
                    )
                ],
            ),
        ),
        # Add reserved_quantity field
        migrations.AddField(
            model_name="stock",
            name="reserved_quantity",
            field=models.DecimalField(
                decimal_places=3,
                default=0,
                max_digits=12,
                verbose_name="Зарезервировано",
                validators=[
                    django.core.validators.MinValueValidator(
                        0,
                        message="Зарезервированное количество не может быть отрицательным.",
                    )
                ],
            ),
        ),
    ]
