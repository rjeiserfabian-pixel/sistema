from django.db import models
from software.models.UsuarioModel import Usuario
from software.models.cajaModel import Caja


class AuditoriaCajas(models.Model):
    idauditoria_caja = models.AutoField(primary_key=True)
    id_caja = models.ForeignKey(
        Caja, on_delete=models.DO_NOTHING, db_column='id_caja',
        related_name='auditorias_caja', null=True, blank=True
    )
    accion = models.CharField(max_length=50)  # 'APERTURA', 'CIERRE', 'MOVIMIENTO_EDITADO', etc.
    motivo = models.TextField(blank=True, null=True)
    idusuario = models.ForeignKey(
        Usuario, on_delete=models.DO_NOTHING, db_column='idusuario',
        related_name='auditorias_cajas'
    )
    datos_anteriores = models.JSONField(blank=True, null=True)
    detalles = models.TextField(blank=True, null=True)
    fecha_auditoria = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        managed = True
        db_table = 'auditoria_cajas'
        ordering = ['-fecha_auditoria']
        verbose_name = 'Auditoría de Caja'
        verbose_name_plural = 'Auditorías de Cajas'

    def __str__(self):
        return f"Auditoría {self.idauditoria_caja} - Acción {self.accion}"
