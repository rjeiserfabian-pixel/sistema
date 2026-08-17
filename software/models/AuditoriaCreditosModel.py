from django.db import models
from software.models.UsuarioModel import Usuario


class AuditoriaCreditos(models.Model):
    idauditoria_credito = models.AutoField(primary_key=True)
    idcredito = models.IntegerField(db_index=True)
    accion = models.CharField(max_length=50)  # 'MODIFICACION', 'CONDONACION', 'REESTRUCTURACION', 'ELIMINACION', etc.
    motivo = models.TextField(blank=True, null=True)
    idusuario = models.ForeignKey(
        Usuario, on_delete=models.DO_NOTHING, db_column='idusuario',
        related_name='auditorias_creditos'
    )
    datos_anteriores = models.JSONField(blank=True, null=True)
    detalles = models.TextField(blank=True, null=True)
    fecha_auditoria = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        managed = True
        db_table = 'auditoria_creditos'
        ordering = ['-fecha_auditoria']
        verbose_name = 'Auditoría de Crédito'
        verbose_name_plural = 'Auditorías de Créditos'

    def __str__(self):
        return f"Auditoría {self.idauditoria_credito} - Crédito {self.idcredito} - {self.accion}"
