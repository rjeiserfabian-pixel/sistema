# software/models/almacenesModel.py
from django.db import models
from software.models.sucursalesModel import Sucursales

class Almacenes(models.Model):
    id_almacen = models.AutoField(primary_key=True)
    id_sucursal = models.ForeignKey(Sucursales, models.DO_NOTHING, db_column='id_sucursal',related_name='almacenes')
    nombre_almacen = models.CharField(max_length=100)
    codigo_almacen = models.CharField(max_length=20)
    descripcion = models.TextField(blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    capacidad_maxima = models.IntegerField(blank=True, null=True)
    estado = models.IntegerField()
    
    class Meta:
        managed = True
        db_table = 'almacenes'
    
    def __str__(self):
        return self.nombre_almacen