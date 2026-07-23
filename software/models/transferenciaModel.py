from django.db import models
from software.models.almacenesModel import Almacenes
from software.models.UsuarioModel import Usuario


class Transferencia(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('en_transito', 'En Tránsito'),
        ('recibido', 'Recibido en Feria'),
        ('en_retorno', 'Retornando al Almacén'),
        ('completada', 'Completada / Recibida'),
        ('rechazada', 'Rechazada'),
    ]

    TIPOS = [
        ('sucursal_a_sucursal', 'Sucursal a Sucursal'),
        ('sucursal_a_exhibicion', 'Sucursal a Punto de Exhibición'),
        ('exhibicion_a_sucursal', 'Punto de Exhibición a Sucursal'),
    ]
    
    id_transferencia = models.AutoField(primary_key=True)
    id_almacen_origen = models.ForeignKey(Almacenes, on_delete=models.RESTRICT, db_column='id_almacen_origen', related_name='transferencias_salida', null=True, blank=True)
    id_almacen_destino = models.ForeignKey(Almacenes, on_delete=models.RESTRICT, db_column='id_almacen_destino', related_name='transferencias_entrada', null=True, blank=True)
    
    # Detalles de destino para exhibiciones o eventos temporales
    lugar_destino = models.CharField(max_length=255, blank=True, null=True, db_column='lugar_destino')
    direccion_destino = models.CharField(max_length=255, blank=True, null=True, db_column='direccion_destino')
    lugar_origen = models.CharField(max_length=255, blank=True, null=True, db_column='lugar_origen')
    direccion_origen = models.CharField(max_length=255, blank=True, null=True, db_column='direccion_origen')
    
    idusuario_solicita = models.ForeignKey(Usuario, on_delete=models.DO_NOTHING, db_column='idusuario_solicita', related_name='transferencias_solicitadas')
    idusuario_confirma = models.ForeignKey(Usuario, on_delete=models.RESTRICT, db_column='idusuario_confirma', related_name='transferencias_confirmadas', null=True, blank=True)
    
    fecha_transferencia = models.DateField(db_column='fecha_transferencia')
    fecha_confirmacion = models.DateTimeField(db_column='fecha_confirmacion', null=True, blank=True)
    
    numero_guia = models.CharField(max_length=50, db_column='numero_guia', null=True, blank=True)
    observaciones = models.TextField(db_column='observaciones', null=True, blank=True)
    
    tipo_transferencia = models.CharField(max_length=30, choices=TIPOS, default='sucursal_a_sucursal', db_column='tipo_transferencia')
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente', db_column='estado')
    
    class Meta:
        managed = True
        db_table = 'transferencias'
    
    def __str__(self):
        return f"Transferencia #{self.id_transferencia} - {self.id_almacen_origen.nombre_almacen} → {self.id_almacen_destino.nombre_almacen}"
    
    def puede_confirmar(self):
        """Verifica si la transferencia puede ser confirmada"""
        return self.estado == 'pendiente'