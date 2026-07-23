from django.db import models

class TransporteVehiculo(models.Model):
    TIPO_CHOICES = [
        ('camion', 'Camión'),
        ('moto', 'Moto'),
        ('furgon', 'Furgón'),
    ]
    ESTADO_CHOICES = [
        ('disponible', 'Disponible'),
        ('en_uso', 'En Uso'),
        ('mantenimiento', 'En Mantenimiento'),
    ]

    id_transporte_vehiculo = models.AutoField(primary_key=True)
    placa = models.CharField(max_length=20, unique=True, db_column='placa')
    marca = models.CharField(max_length=50, db_column='marca')
    modelo = models.CharField(max_length=50, db_column='modelo')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, db_column='tipo')
    capacidad = models.CharField(max_length=50, db_column='capacidad', null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='disponible', db_column='estado')

    class Meta:
        managed = True
        db_table = 'transporte_vehiculo'

    def __str__(self):
        return f"{self.placa} - {self.marca} {self.modelo} ({self.get_tipo_display()})"
