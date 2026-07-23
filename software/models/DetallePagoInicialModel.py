from django.db import models
from software.models.PreCreditoModel import PreCredito
from software.models.TipoPagoModel import TipoPago


class DetallePagoInicial(models.Model):
    """
    Detalle de los métodos de pago usados en el pago inicial de un PreCredito.
    Permite pagos mixtos: ej. S/ 300 en efectivo + S/ 200 por Yape.
    """
    id_detalle_pago = models.AutoField(primary_key=True)

    id_pre_credito = models.ForeignKey(
        PreCredito,
        on_delete=models.CASCADE,
        db_column='id_pre_credito',
        related_name='detalles_pago',
        verbose_name='Pre-Crédito'
    )
    id_tipo_pago = models.ForeignKey(
        TipoPago,
        on_delete=models.SET_NULL,
        db_column='id_tipo_pago',
        related_name='detalles_pago_inicial',
        null=True,
        blank=True,
        verbose_name='Método de Pago'
    )
    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Monto'
    )
    numero_operacion = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='N° Operación'
    )

    class Meta:
        managed = True
        db_table = 'detalle_pago_inicial'
        verbose_name = 'Detalle de Pago Inicial'
        verbose_name_plural = 'Detalles de Pago Inicial'

    def __str__(self):
        tipo = self.id_tipo_pago.nombre if self.id_tipo_pago else 'Sin método'
        return f"Detalle #{self.id_detalle_pago} - {tipo}: S/ {self.monto}"
