from django.db import models
from software.models.UsuarioModel import Usuario
from software.models.ProductoModel import Producto


class AuditoriaProductos(models.Model):
    idauditoria_producto = models.AutoField(primary_key=True)
    idproducto = models.ForeignKey(
        Producto, on_delete=models.DO_NOTHING, db_column='idproducto',
        related_name='auditorias_producto'
    )
    accion = models.CharField(max_length=50)  # 'EDICION', 'ELIMINACION', etc.
    motivo = models.TextField(blank=True, null=True)
    idusuario = models.ForeignKey(
        Usuario, on_delete=models.DO_NOTHING, db_column='idusuario',
        related_name='auditorias_productos'
    )
    datos_anteriores = models.JSONField(blank=True, null=True)
    datos_nuevos = models.JSONField(blank=True, null=True)
    fecha_auditoria = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        managed = True
        db_table = 'auditoria_productos'
        ordering = ['-fecha_auditoria']
        verbose_name = 'Auditoría de Producto'
        verbose_name_plural = 'Auditorías de Productos'

    def __str__(self):
        return f"Auditoría {self.idauditoria_producto} - Producto {self.idproducto_id}"
