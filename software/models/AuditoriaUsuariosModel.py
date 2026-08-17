from django.db import models
from software.models.UsuarioModel import Usuario


class AuditoriaUsuarios(models.Model):
    idauditoria_usuario = models.AutoField(primary_key=True)
    usuario_afectado = models.ForeignKey(
        Usuario, on_delete=models.DO_NOTHING, db_column='usuario_afectado',
        related_name='auditorias_afectado'
    )
    usuario_responsable = models.ForeignKey(
        Usuario, on_delete=models.DO_NOTHING, db_column='usuario_responsable',
        related_name='auditorias_responsable', null=True, blank=True
    )
    accion = models.CharField(max_length=50)  # 'LOGIN', 'LOGOUT', 'CAMBIO_PERMISO', 'CAMBIO_CONTRASENA', etc.
    motivo = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    detalles = models.TextField(blank=True, null=True)
    fecha_auditoria = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        managed = True
        db_table = 'auditoria_usuarios'
        ordering = ['-fecha_auditoria']
        verbose_name = 'Auditoría de Usuario'
        verbose_name_plural = 'Auditorías de Usuarios'

    def __str__(self):
        return f"Auditoría {self.idauditoria_usuario} - Usuario {self.usuario_afectado_id} - {self.accion}"
