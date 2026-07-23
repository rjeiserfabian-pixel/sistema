from django.db import models

class TransporteConductor(models.Model):
    ESTADO_CHOICES = [
        ('disponible', 'Disponible'),
        ('en_viaje', 'En Viaje'),
        ('descanso', 'En Descanso'),
    ]

    id_transporte_conductor = models.AutoField(primary_key=True)
    nombre_completo = models.CharField(max_length=255, db_column='nombre_completo')
    dni = models.CharField(max_length=15, unique=True, db_column='dni')
    licencia_conducir = models.CharField(max_length=20, db_column='licencia_conducir')
    tipo_licencia = models.CharField(max_length=20, db_column='tipo_licencia')
    telefono = models.CharField(max_length=15, db_column='telefono', null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='disponible', db_column='estado')

    class Meta:
        managed = True
        db_table = 'transporte_conductor'

    def __str__(self):
        return f"{self.nombre_completo} (DNI: {self.dni})"
