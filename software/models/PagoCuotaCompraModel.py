from django.db import models
from software.models.cuotaModel import Cuota
from software.models.UsuarioModel import Usuario
from software.models.TipoPagoModel import TipoPago

class PagoCuotaCompra(models.Model):
    """
    Modelo para registrar cada abono/pago realizado a una cuota de compra
    Permite pagos parciales y múltiples pagos por cuota, igual que en ventas.
    """
    idpagocuotacompra = models.AutoField(primary_key=True)
    idcuota = models.ForeignKey(
        Cuota, 
        on_delete=models.CASCADE, 
        db_column='idcuota', 
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
    monto_pago = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_pago = models.DateTimeField(auto_now_add=True)
    numero_operacion = models.CharField(max_length=100, blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    estado = models.IntegerField(default=1)

    class Meta:
        managed = True
        db_table = 'pagos_cuota_compra'
        ordering = ['-fecha_pago']

    def __str__(self):
        return f"Pago S/ {self.monto_pago} - Cuota {self.idcuota.numero_cuota}"
