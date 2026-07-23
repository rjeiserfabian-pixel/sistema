from django.db import models

class SituacionVehiculo(models.Model):
    id_situacion = models.AutoField(primary_key=True, db_column='id_situacion')
    nombre_situacion = models.CharField(max_length=50, db_column='nombre_situacion')
    estado = models.IntegerField(default=1, db_column='estado')

    def __str__(self):
        return self.nombre_situacion

    class Meta:
        managed = True
        db_table = 'situacion_vehiculo'
