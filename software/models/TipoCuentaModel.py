from django.db import models

class TipoCuenta(models.Model):
    id_tipo_cuenta = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, verbose_name="Nombre del Tipo de Cuenta")
    estado = models.BooleanField(default=True, verbose_name="Estado")

    class Meta:
        managed = True
        db_table = 'tipo_cuenta'
        verbose_name = 'Tipo de Cuenta'
        verbose_name_plural = 'Tipos de Cuenta'

    def __str__(self):
        return self.nombre
