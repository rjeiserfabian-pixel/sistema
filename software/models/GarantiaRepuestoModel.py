from django.db import models

class GarantiaRepuesto(models.Model):
    id_garantia_repuesto = models.AutoField(primary_key=True, db_column='id_garantia_repuesto')
    nombre = models.CharField(max_length=255, db_column='nombre')
    estado = models.IntegerField(db_column='estado', default=1)

    class Meta:
        managed = True
        db_table = 'garantia_repuesto'

    def __str__(self):
        return self.nombre
