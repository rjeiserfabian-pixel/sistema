from django.db import models


class DetalleColor(models.Model):
    iddetalle_color = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    estado = models.IntegerField()

    class Meta:
        managed = True
        db_table = 'detalle_color'

    def __str__(self):
        return self.nombre
