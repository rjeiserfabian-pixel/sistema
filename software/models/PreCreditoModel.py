from django.db import models
from software.models.ClienteModel import Cliente
from software.models.VehiculosModel import Vehiculo
from software.models.UsuarioModel import Usuario
from software.models.sucursalesModel import Sucursales


class PreCredito(models.Model):
    """
    Modelo para gestionar solicitudes de pre-financiamiento.
    Registra el cliente, el vehículo de interés y el pago inicial
    antes de que se evalúe y se convierta en una venta a crédito.
    """
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
        ('completado', 'Completado'),
    ]

    id_pre_credito = models.AutoField(primary_key=True)

    idcliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        db_column='idcliente',
        related_name='pre_creditos',
        verbose_name='Cliente'
    )
    monto_inicial = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Monto Inicial (Adelanto)'
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='pendiente',
        verbose_name='Estado'
    )
    idusuario = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        db_column='idusuario',
        related_name='pre_creditos',
        null=True,
        blank=True,
        verbose_name='Usuario Registrador'
    )
    id_sucursal = models.ForeignKey(
        Sucursales,
        on_delete=models.SET_NULL,
        db_column='id_sucursal',
        related_name='pre_creditos',
        null=True,
        blank=True,
        verbose_name='Sucursal'
    )
    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Registro'
    )
    observaciones = models.TextField(
        blank=True,
        null=True,
        verbose_name='Observaciones'
    )
    cobrado = models.BooleanField(
        default=False,
        verbose_name='Cobrado'
    )
    observacion_evaluacion = models.TextField(
        blank=True,
        null=True,
        verbose_name='Observación de Evaluación'
    )

    class Meta:
        managed = True
        db_table = 'pre_creditos'
        ordering = ['-fecha_registro']
        verbose_name = 'Pre-Crédito'
        verbose_name_plural = 'Pre-Créditos'

    def __str__(self):
        return f"PreCrédito #{self.id_pre_credito} - {self.idcliente.razonsocial} ({self.get_estado_display()})"

    @property
    def nombre_vehiculo(self):
        """Retorna el nombre del producto del vehículo asociado o de los vehículos si son múltiples."""
        nombres = []
        
        # Nuevos datos de la tabla de detalle
        if hasattr(self, 'detalles_vehiculos'):
            for detalle in self.detalles_vehiculos.all():
                if detalle.id_vehiculo and detalle.id_vehiculo.idproducto:
                    nombres.append(detalle.id_vehiculo.idproducto.nomproducto)
        
        # Filtrar duplicados en caso de que un registro tenga múltiples del mismo (poco probable)
        nombres = list(dict.fromkeys(nombres))
        
        if nombres:
            return ', '.join(nombres)
        return 'Sin vehículo'

    @property
    def vehiculos_asociados(self):
        """Retorna una lista con todos los objetos de Vehiculo asociados."""
        vehiculos = []
        
        if hasattr(self, 'detalles_vehiculos'):
            for detalle in self.detalles_vehiculos.all():
                if detalle.id_vehiculo not in vehiculos:
                    vehiculos.append(detalle.id_vehiculo)
        return vehiculos

    @property
    def tiene_pagos_mixtos(self):
        """Retorna True si hay más de un método de pago registrado."""
        return self.detalles_pago.count() > 1
