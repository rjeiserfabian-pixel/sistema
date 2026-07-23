from django.db import models
from django.core.validators import MinValueValidator
from software.models.ProformaModel import Proforma
from software.models.VehiculosModel import Vehiculo
from software.models.RepuestoModel import Repuesto


class ProformaDetalle(models.Model):
    """
    Detalle de cada ítem de una Proforma.
    Puede referenciar un Vehículo o un Repuesto, igual que VentaDetalle.
    """

    TIPO_ITEM_CHOICES = [
        ('vehiculo', 'Vehículo'),
        ('repuesto', 'Repuesto'),
    ]

    idproformadetalle = models.AutoField(primary_key=True, db_column='idproformadetalle')
    idproforma = models.ForeignKey(
        Proforma,
        on_delete=models.CASCADE,
        db_column='idproforma',
        related_name='detalles',
        verbose_name='Proforma'
    )
    tipo_item = models.CharField(
        max_length=20,
        choices=TIPO_ITEM_CHOICES,
        verbose_name='Tipo de Ítem'
    )
    id_vehiculo = models.ForeignKey(
        Vehiculo,
        on_delete=models.PROTECT,
        db_column='id_vehiculo',
        null=True, blank=True,
        related_name='proformas_detalle',
        verbose_name='Vehículo'
    )
    id_repuesto = models.ForeignKey(
        Repuesto,
        on_delete=models.PROTECT,
        db_column='id_repuesto',
        null=True, blank=True,
        related_name='proformas_detalle',
        verbose_name='Repuesto'
    )
    cantidad = models.PositiveIntegerField(
        default=1,
        verbose_name='Cantidad'
    )
    precio_unitario = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Precio Unitario'
    )
    descuento_item = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Descuento por Ítem'
    )
    subtotal = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Subtotal'
    )

    class Meta:
        managed = True
        db_table = 'proforma_detalle'
        verbose_name = 'Detalle de Proforma'
        verbose_name_plural = 'Detalles de Proforma'

    def __str__(self):
        return f"Detalle {self.idproformadetalle} - Proforma {self.idproforma.numero_proforma}"
