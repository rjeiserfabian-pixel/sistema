
from django.db import models
from software.models.AperturaCierreCajaModel import AperturaCierreCaja
from software.models.UsuarioModel import Usuario

class ReaperturaCaja(models.Model):
    id_reapertura = models.AutoField(primary_key=True)
    id_movimiento = models.ForeignKey(
        AperturaCierreCaja, 
        on_delete=models.CASCADE, 
        db_column='id_movimiento',
        related_name='reaperturas'
    )
    usuario_solicitante = models.ForeignKey(
        Usuario, 
        on_delete=models.CASCADE,
        db_column='usuario_solicitante',
        related_name='reaperturas_solicitadas',
        null=True, 
        blank=True
    )
    motivo = models.TextField(null=True, blank=True)
    fecha_reapertura = models.DateTimeField(auto_now_add=True)
    fecha_cierre_reapertura = models.DateTimeField(null=True, blank=True)
    codigo_2fa_enviado = models.CharField(max_length=6, null=True, blank=True)
    estado = models.CharField(
        max_length=20,
        default='reabierta',
        choices=[
            ('reabierta', 'Reabierta'),
            ('cerrada_nuevamente', 'Cerrada Nuevamente')
        ]
    )
    
    class Meta:
        managed = True
        db_table = 'reapertura_caja'
        ordering = ['-fecha_reapertura']
    
    def __str__(self):
        return f"Reapertura #{self.id_reapertura} - {self.id_movimiento.id_caja.nombre_caja}"