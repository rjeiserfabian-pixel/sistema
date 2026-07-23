from django.db import models
from django.utils import timezone
from software.models.CuotasVentaModel import CuotasVenta
from software.models.UsuarioModel import Usuario
from software.models.TipoPagoModel import TipoPago

class PagoCuota(models.Model):
    """
    Modelo para registrar cada pago realizado a una cuota
    Permite pagos parciales y múltiples pagos por cuota
    """
    idpagocuota = models.AutoField(primary_key=True)
    idcuotaventa = models.ForeignKey(
        CuotasVenta, 
        on_delete=models.CASCADE, 
        db_column='idcuotaventa', 
        related_name='pagos'
    )
    idusuario = models.ForeignKey(
        Usuario, 
        on_delete=models.CASCADE, 
        db_column='idusuario'
    )
    id_tipo_pago = models.ForeignKey(
        TipoPago, 
        on_delete=models.CASCADE, 
        db_column='id_tipo_pago'
    )
    # Vínculo con el movimiento de caja para trazabilidad y edición
    id_movimiento_caja = models.ForeignKey(
        'MovimientoCaja', 
        on_delete=models.SET_NULL, 
        db_column='id_movimiento_caja',
        null=True, 
        blank=True,
        related_name='pagos_cuota'
    )
    monto_pago = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_pago = models.DateTimeField(default=timezone.now, db_index=True)
    numero_operacion = models.CharField(max_length=100, blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    estado = models.IntegerField(default=1, db_index=True)

    class Meta:
        managed = True
        db_table = 'pagos_cuota'
        ordering = ['-fecha_pago']
        indexes = [
            # Índice compuesto para el lookup más frecuente:
            # SELECT * FROM pagos_cuota WHERE id_movimiento_caja = X AND estado = 1
            models.Index(fields=['id_movimiento_caja', 'estado'], name='idx_pagocuota_mov_estado'),
            # Índice para consultas por cuota + estado (historial de pagos de créditos)
            models.Index(fields=['idcuotaventa', 'estado'], name='idx_pagocuota_cuota_estado'),
        ]

    def __str__(self):
        return f"Pago S/ {self.monto_pago} - Cuota {self.idcuotaventa.numero_cuota}"
    


    