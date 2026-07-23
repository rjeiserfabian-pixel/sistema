
from django.db import models

from software.models.RepuestoModel import Repuesto

class RepuestoComp(models.Model):
    id_repuesto_comprado= models.AutoField(primary_key=True, db_column='id_repuesto_comprado')
    id_repuesto= models.ForeignKey(Repuesto, on_delete=models.DO_NOTHING, db_column='id_repuesto', related_name='repuestocomprados')
    ubicacion = models.CharField(max_length=200)
    estado = models.IntegerField(db_column='estado')
    

    def __str__(self):
        if self.id_repuesto:
             return self.id_repuesto.nombre
        return self.ubicacion or f"Repuesto {self.pk}"

    class Meta:
        managed = True
        db_table = 'repuestoscomprado'
