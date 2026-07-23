from django.db import models
from django.utils import timezone
from software.models.UsuarioModel import Usuario
import random
import string

class AutorizacionAccion(models.Model):
    ACCIONES = (
        ('EDICION', 'Edición'),
        ('ELIMINACION', 'Eliminación'),
    )

    idautorizacion = models.AutoField(primary_key=True)
    usuario_solicitante = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='idusuario')
    codigo = models.CharField(max_length=10)
    tipo_accion = models.CharField(max_length=20, choices=ACCIONES)
    modulo = models.CharField(max_length=100) # Ej: Ventas, Clientes
    id_registro = models.IntegerField(null=True, blank=True) # ID del objeto a afectar
    usado = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_expiracion = models.DateTimeField()

    class Meta:
        db_table = 'autorizacion_accion'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.tipo_accion} - {self.modulo} (#{self.id_registro}) - {self.usuario_solicitante.nombrecompleto}"

    @property
    def es_valido(self):
        return not self.usado and timezone.now() <= self.fecha_expiracion

    @staticmethod
    def generar_codigo(longitud=6):
        return ''.join(random.choices(string.digits, k=longitud))
