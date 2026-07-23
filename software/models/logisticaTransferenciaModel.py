from django.db import models
from software.models.transferenciaModel import Transferencia
from software.models.transporteVehiculoModel import TransporteVehiculo
from software.models.transporteConductorModel import TransporteConductor

class LogisticaTransferencia(models.Model):
    ESTADO_LOGISTICA = [
        ('activo', 'Activo'),
        ('sustituido', 'Sustituido'),
        ('completado', 'Completado'),
    ]

    id_logistica = models.AutoField(primary_key=True)
    id_transferencia = models.ForeignKey(Transferencia, on_delete=models.CASCADE, db_column='id_transferencia', related_name='logisticas')
    id_transporte_vehiculo = models.ForeignKey(TransporteVehiculo, on_delete=models.RESTRICT, db_column='id_transporte_vehiculo')
    id_transporte_conductor = models.ForeignKey(TransporteConductor, on_delete=models.RESTRICT, db_column='id_transporte_conductor')
    
    fecha_asignacion = models.DateTimeField(auto_now_add=True, db_column='fecha_asignacion')
    fecha_salida = models.DateTimeField(null=True, blank=True, db_column='fecha_salida')
    fecha_llegada_estimada = models.DateTimeField(null=True, blank=True, db_column='fecha_llegada_estimada')
    
    estado_logistica = models.CharField(max_length=20, choices=ESTADO_LOGISTICA, default='activo', db_column='estado_logistica')
    observaciones = models.TextField(null=True, blank=True, db_column='observaciones')

    class Meta:
        managed = True
        db_table = 'logistica_transferencia'

    def __str__(self):
        return f"Logística - Transf #{self.id_transferencia.id_transferencia} ({self.estado_logistica})"
