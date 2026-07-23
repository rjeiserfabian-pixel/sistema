from django.db import models
from software.models.ZonaCreditoModel import ZonaCredito

class FactorCredito(models.Model):
    id_factor = models.AutoField(primary_key=True)
    id_zona = models.ForeignKey(ZonaCredito, on_delete=models.CASCADE, db_column='id_zona')
    numero_cuotas = models.IntegerField()
    factor = models.DecimalField(max_digits=10, decimal_places=4)
    estado = models.IntegerField(default=1)

    class Meta:
        managed = True
        db_table = 'factores_credito'

    def __str__(self):
        return f"{self.id_zona.nombre} - {self.numero_cuotas} cuotas"
