# software/models/cajaModel.py
from django.db import models
from software.models.sucursalesModel import Sucursales
from software.models.empresaModel import Empresa

class Caja(models.Model):
    id_caja = models.AutoField(primary_key=True)
    id_sucursal = models.ForeignKey(Sucursales, models.DO_NOTHING, db_column='id_sucursal', null=True, blank=True)
    id_empresa = models.ForeignKey(Empresa, models.DO_NOTHING, db_column='id_empresa', null=True, blank=True)
    nombre_caja = models.CharField(max_length=50)
    numero_caja = models.IntegerField()
    estado = models.IntegerField(default=1)

    
    class Meta:
        managed = True
        db_table = 'cajas'
    
    def __str__(self):
        return self.nombre_caja
    


