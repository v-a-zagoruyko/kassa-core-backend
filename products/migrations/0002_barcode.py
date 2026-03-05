# Generated migration for Barcode model

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0002_alter_category_options'),
    ]

    operations = [
        migrations.CreateModel(
            name='Barcode',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Дата создания')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Дата обновления')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='Дата удаления')),
                ('is_deleted', models.BooleanField(db_index=True, default=False, verbose_name='Удалено')),
                ('code', models.CharField(db_index=True, help_text='Уникальный код штрихкода (EAN-13, QR, Code-128 или Data Matrix)', max_length=200, unique=True, verbose_name='Код штрихкода')),
                ('barcode_type', models.CharField(choices=[('ean13', 'EAN-13'), ('qr', 'QR-код'), ('code128', 'Code-128'), ('datamatrix', 'Data Matrix')], db_index=True, default='ean13', help_text='Тип: EAN-13, QR-код, Code-128 или Data Matrix', max_length=20, verbose_name='Тип штрихкода')),
                ('is_primary', models.BooleanField(db_index=True, default=False, help_text='Только один основной штрихкод на товар', verbose_name='Основной штрихкод')),
                ('product', models.ForeignKey(help_text='Товар, к которому относится штрихкод', on_delete=django.db.models.deletion.CASCADE, related_name='barcodes', to='products.product', verbose_name='Товар')),
            ],
            options={
                'verbose_name': 'Штрихкод',
                'verbose_name_plural': 'Штрихкоды',
                'ordering': ('-is_primary', 'barcode_type', 'created_at'),
            },
        ),
        migrations.AddIndex(
            model_name='barcode',
            index=models.Index(fields=['code'], name='products_ba_code_idx'),
        ),
        migrations.AddIndex(
            model_name='barcode',
            index=models.Index(fields=['product_id'], name='products_ba_product_idx'),
        ),
        migrations.AddIndex(
            model_name='barcode',
            index=models.Index(fields=['barcode_type'], name='products_ba_barcode_idx'),
        ),
        migrations.AddIndex(
            model_name='barcode',
            index=models.Index(fields=['product_id', 'is_primary'], name='products_ba_product_primary_idx'),
        ),
        migrations.AddConstraint(
            model_name='barcode',
            constraint=models.UniqueConstraint(condition=models.Q(('is_primary', True)), fields=['product_id', 'is_primary'], name='uniq_primary_barcode_per_product'),
        ),
    ]
