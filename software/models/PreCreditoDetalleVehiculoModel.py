from django.db import models
from software.models.PreCreditoModel import PreCredito
from software.models.VehiculosModel import Vehiculo

class PreCreditoDetalleVehiculo(models.Model):
    """
    Tabla intermedia para soportar múltiples vehículos en una solicitud
    de pre-financiamiento.
    """
    id_detalle = models.AutoField(primary_key=True)
    id_pre_credito = models.ForeignKey(
        PreCredito,
        on_delete=models.CASCADE,
        db_column='id_pre_credito',
        related_name='detalles_vehiculos',
        verbose_name='Pre-Crédito'
    )
    id_vehiculo = models.ForeignKey(
        Vehiculo,
        on_delete=models.CASCADE,
        db_column='id_vehiculo',
        related_name='detalles_precreditos',
        verbose_name='Vehículo'
    )

    class Meta:
        managed = True
        db_table = 'pre_credito_detalle_vehiculo'
        verbose_name = 'Detalle de Vehículo de Pre-Crédito'
        verbose_name_plural = 'Detalles de Vehículos de Pre-Crédito'
        indexes = [
            models.Index(fields=['id_pre_credito']),
            models.Index(fields=['id_vehiculo']),
        ]

    def __str__(self):
        return f"PreCrédito #{self.id_pre_credito_id} - Vehículo #{self.id_vehiculo_id}"
