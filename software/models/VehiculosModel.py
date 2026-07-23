from django.db import models

from software.models.ProductoModel import Producto
from software.models.estadoproductoModel import EstadoProducto
from software.models.SituacionVehiculoModel import SituacionVehiculo


class Vehiculo(models.Model):
    id_vehiculo = models.AutoField(primary_key=True,  db_column='id_vehiculo')
    idproducto = models.ForeignKey(Producto, on_delete=models.DO_NOTHING, db_column='idproducto', related_name='vehiculos')
    idestadoproducto = models.ForeignKey(EstadoProducto, on_delete=models.DO_NOTHING, db_column='idestadoproducto', related_name='vehiculos')
    id_situacion = models.ForeignKey(SituacionVehiculo, on_delete=models.SET_NULL, db_column='id_situacion', related_name='vehiculos', null=True, blank=True)
    imperfecciones = models.TextField(blank=True)
    placas = models.TextField(blank=True)
    serie_chasis = models.CharField(max_length=50, db_index=True)
    serie_motor = models.CharField(max_length=50, db_index=True)
    anio = models.PositiveIntegerField(null=True, blank=True)
    estado = models.IntegerField(db_column='estado')


    def __str__(self):
        return self.idproducto.nomproducto if self.idproducto else f"Vehículo {self.pk}"

    class Meta:
        managed = True 
        db_table = 'vehiculos'


        