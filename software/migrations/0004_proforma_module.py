"""
Migración manual: Creación de las tablas proformas y proforma_detalle.
Estas tablas soportan el módulo de Proformas (cotizaciones comerciales).
"""
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('software', '0003_almacenes_aperturacierrecaja_caja_cilindrada_cliente_and_more'),
    ]

    operations = [
        # ─── Tabla proformas ──────────────────────────────────────────
        migrations.CreateModel(
            name='Proforma',
            fields=[
                ('idproforma', models.AutoField(db_column='idproforma', primary_key=True, serialize=False)),
                ('numero_proforma', models.CharField(
                    default='',
                    help_text='Número correlativo (ej: PRO-000001)',
                    max_length=20,
                    unique=True,
                    verbose_name='Número de Proforma',
                )),
                ('idcliente', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='proformas',
                    to='software.cliente',
                    db_column='idcliente',
                    verbose_name='Cliente',
                )),
                ('idusuario', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='proformas',
                    to='software.usuario',
                    db_column='idusuario',
                    verbose_name='Asesor Comercial',
                )),
                ('fecha_emision', models.DateField(
                    auto_now_add=True,
                    verbose_name='Fecha de Emisión',
                )),
                ('fecha_vencimiento', models.DateField(
                    blank=True,
                    null=True,
                    verbose_name='Fecha de Vencimiento',
                )),
                ('idempresa', models.IntegerField(
                    blank=True,
                    null=True,
                    verbose_name='ID Empresa',
                )),
                ('forma_pago', models.CharField(
                    default='Contado',
                    max_length=255,
                    verbose_name='Forma de Pago',
                )),
                ('tiempo_entrega', models.CharField(
                    default='Inmediata',
                    max_length=255,
                    verbose_name='Tiempo de Entrega',
                )),
                ('garantia', models.CharField(
                    default='Según fabricante',
                    max_length=255,
                    verbose_name='Garantía',
                )),
                ('observaciones', models.TextField(
                    blank=True,
                    null=True,
                    verbose_name='Observaciones',
                )),
                ('subtotal', models.DecimalField(
                    decimal_places=2,
                    default=0,
                    max_digits=12,
                    validators=[django.core.validators.MinValueValidator(0)],
                    verbose_name='Subtotal',
                )),
                ('igv', models.DecimalField(
                    decimal_places=2,
                    default=0,
                    max_digits=12,
                    validators=[django.core.validators.MinValueValidator(0)],
                    verbose_name='IGV (18%)',
                )),
                ('descuento', models.DecimalField(
                    decimal_places=2,
                    default=0,
                    max_digits=12,
                    validators=[django.core.validators.MinValueValidator(0)],
                    verbose_name='Descuento Total',
                )),
                ('total', models.DecimalField(
                    decimal_places=2,
                    default=0,
                    max_digits=12,
                    validators=[django.core.validators.MinValueValidator(0)],
                    verbose_name='Total',
                )),
                ('estado', models.IntegerField(
                    choices=[(1, 'Activa'), (2, 'Convertida en Venta'), (3, 'Anulada')],
                    default=1,
                    verbose_name='Estado',
                )),
            ],
            options={
                'verbose_name': 'Proforma',
                'verbose_name_plural': 'Proformas',
                'db_table': 'proformas',
                'ordering': ['-idproforma'],
                'managed': True,
            },
        ),
        # ─── Tabla proforma_detalle ───────────────────────────────────
        migrations.CreateModel(
            name='ProformaDetalle',
            fields=[
                ('idproformadetalle', models.AutoField(db_column='idproformadetalle', primary_key=True, serialize=False)),
                ('idproforma', models.ForeignKey(
                    db_column='idproforma',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='detalles',
                    to='software.proforma',
                    verbose_name='Proforma',
                )),
                ('tipo_item', models.CharField(
                    choices=[('vehiculo', 'Vehículo'), ('repuesto', 'Repuesto')],
                    max_length=20,
                    verbose_name='Tipo de Ítem',
                )),
                ('id_vehiculo', models.ForeignKey(
                    blank=True,
                    db_column='id_vehiculo',
                    null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='proformas_detalle',
                    to='software.vehiculo',
                    verbose_name='Vehículo',
                )),
                ('id_repuesto', models.ForeignKey(
                    blank=True,
                    db_column='id_repuesto',
                    null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='proformas_detalle',
                    to='software.repuesto',
                    verbose_name='Repuesto',
                )),
                ('cantidad', models.PositiveIntegerField(
                    default=1,
                    verbose_name='Cantidad',
                )),
                ('precio_unitario', models.DecimalField(
                    decimal_places=2,
                    max_digits=12,
                    validators=[django.core.validators.MinValueValidator(0)],
                    verbose_name='Precio Unitario',
                )),
                ('descuento_item', models.DecimalField(
                    decimal_places=2,
                    default=0,
                    max_digits=12,
                    validators=[django.core.validators.MinValueValidator(0)],
                    verbose_name='Descuento por Ítem',
                )),
                ('subtotal', models.DecimalField(
                    decimal_places=2,
                    max_digits=12,
                    validators=[django.core.validators.MinValueValidator(0)],
                    verbose_name='Subtotal',
                )),
            ],
            options={
                'verbose_name': 'Detalle de Proforma',
                'verbose_name_plural': 'Detalles de Proforma',
                'db_table': 'proforma_detalle',
                'managed': True,
            },
        ),
    ]
