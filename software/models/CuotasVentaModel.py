from django.db import models
from software.models.VentasModel import Ventas

class CuotasVenta(models.Model):
    idcuotaventa = models.AutoField(primary_key=True)
    idventa = models.ForeignKey(Ventas, on_delete=models.CASCADE, db_column='idventa', null=True, blank=True)
    idcredito = models.ForeignKey('Credito', on_delete=models.CASCADE, db_column='idcredito', null=True, blank=True, related_name='cuotas')
    numero_cuota = models.IntegerField()
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    tasa = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    interes = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_vencimiento = models.DateField(db_index=True)
    monto_adelanto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    monto_pagado = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    saldo_cuota = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    interes_mora = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    interes_mora_manual = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    descuento = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fecha_pago = models.DateTimeField(blank=True, null=True)
    estado_pago = models.CharField(max_length=20, default='Pendiente', db_index=True)
    estado = models.IntegerField(default=1, db_index=True)

    class Meta:
        managed = True
        db_table = 'cuotasventa'
        ordering = ['numero_cuota']

    def __str__(self):
        identificador = ""
        if self.idventa:
            identificador = f"Venta {self.idventa.numero_comprobante}"
        elif self.idcredito:
            identificador = f"Crédito {self.idcredito.codigo_credito}"
        return f"Cuota {self.numero_cuota} - {identificador}"
    
    def calcular_saldo(self):
        """Calcula el saldo pendiente de la cuota"""
        return self.total - self.monto_pagado
    
    def esta_vencida(self):
        """Verifica si la cuota está vencida"""
        from django.utils import timezone
        if self.estado_pago != 'Pagado' and self.fecha_vencimiento < timezone.now().date():
            return True
        return False