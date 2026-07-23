from django.db import models

from software.models.VentasModel import Ventas
from software.models.VehiculosModel import Vehiculo
from software.models.RespuestoCompModel import RepuestoComp
from software.models.ServicioModel import Servicio

class VentaDetalle(models.Model):
    idventadetalle = models.AutoField(primary_key=True)
    idventa = models.ForeignKey(Ventas, on_delete=models.CASCADE, db_column='idventa')
    tipo_item = models.CharField(max_length=20, db_index=True)  # 'vehiculo', 'repuesto' o 'servicio'
    id_vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, db_column='id_vehiculo', blank=True, null=True)
    id_repuesto_comprado = models.ForeignKey(RepuestoComp, on_delete=models.CASCADE, db_column='id_repuesto_comprado', blank=True, null=True)
    id_servicio = models.ForeignKey(Servicio, on_delete=models.SET_NULL, db_column='id_servicio', blank=True, null=True)
    cantidad = models.IntegerField(default=1)
    precio_venta_contado = models.DecimalField(max_digits=10, decimal_places=2)
    precio_venta_descuento = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    precio_venta_credito = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    precio_maximo = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    precio_compra = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    ganancia = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.IntegerField(default=1, db_index=True)

    class Meta:
        managed = True
        db_table = 'ventadetalle'

    def __str__(self):
        return f"Detalle {self.idventadetalle} - Venta {self.idventa.numcomprobante}"