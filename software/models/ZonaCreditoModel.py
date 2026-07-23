from django.db import models

class ZonaCredito(models.Model):
    id_zona = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=255)
    estado = models.IntegerField(default=1)

    class Meta:
        managed = True
        db_table = 'zonas_credito'

    def __str__(self):
        return self.nombre
