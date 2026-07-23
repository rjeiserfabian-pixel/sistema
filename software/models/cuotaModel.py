from django.db import models

from software.models.comprasModel import Compras

class Cuota(models.Model):
    id_cuota = models.AutoField(primary_key=True)
    idcompra = models.ForeignKey(Compras, on_delete=models.DO_NOTHING, db_column='idcompra', related_name='cuota',null=True, blank=True)
    numero_cuota = models.IntegerField()
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    tasa = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    interes = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    monto_adelanto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_vencimiento = models.DateField()
    
    # Nuevos campos para Cuentas por Pagar
    monto_pagado = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    saldo_cuota = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fecha_pago = models.DateTimeField(blank=True, null=True)
    estado_pago = models.CharField(max_length=20, default='Pendiente')
    
    estado = models.IntegerField(default=1) 
    
    def calcular_saldo(self):
        """Calcula el saldo pendiente de la cuota"""
        return self.total - self.monto_pagado
    
    def esta_vencida(self):
        """Verifica si la cuota está vencida"""
        from django.utils import timezone
        if self.estado_pago != 'Pagado' and self.fecha_vencimiento < timezone.now().date():
            return True
        return False

    class Meta:
        managed = True
        db_table = 'cuotas'