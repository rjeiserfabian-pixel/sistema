from django.db import models
from .TipoCuentaModel import TipoCuenta

class CanalPago(models.Model):
    id_canal = models.AutoField(primary_key=True)
    banco = models.CharField(max_length=150, verbose_name="Banco")
    id_tipo_cuenta = models.ForeignKey(TipoCuenta, on_delete=models.RESTRICT, db_column='id_tipo_cuenta', verbose_name="Tipo de Cuenta")
    numero_cuenta = models.CharField(max_length=50, verbose_name="Número de Cuenta")
    cci = models.CharField(max_length=50, blank=True, null=True, verbose_name="CCI")
    codigo_agente = models.CharField(max_length=50, blank=True, null=True, verbose_name="Código de Agente")
    titular = models.CharField(max_length=255, blank=True, null=True, verbose_name="Titular de la Cuenta")
    orden = models.IntegerField(default=0, verbose_name="Orden de visualización")
    estado = models.BooleanField(default=True, verbose_name="Estado")

    class Meta:
        managed = True
        db_table = 'canales_pago'
        verbose_name = 'Canal de Pago'
        verbose_name_plural = 'Canales de Pago'
        ordering = ['orden', 'banco']

    def __str__(self):
        return f"{self.banco} - {self.numero_cuenta}"
