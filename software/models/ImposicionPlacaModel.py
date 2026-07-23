from django.db import models
from software.models.VentasModel import Ventas
from software.models.VehiculosModel import Vehiculo
from software.models.ClienteModel import Cliente
from software.models.UsuarioModel import Usuario
from django.utils import timezone


class ImposicionPlaca(models.Model):

    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('en_tramite', 'En Trámite'),
        ('completado', 'Completado'),
        ('cancelado', 'Cancelado'),
    ]
    
    TIPO_PLACA_CHOICES = [
        ('nueva', 'Placa Nueva'),
        ('transferencia', 'Transferencia'),
        ('duplicado', 'Duplicado'),
    ]
    
    id_imposicion = models.AutoField(primary_key=True)
    
    # Relaciones principales
    idventa = models.ForeignKey(
        Ventas, 
        on_delete=models.CASCADE, 
        db_column='idventa',
        related_name='imposiciones_placa'
    )
    id_vehiculo = models.ForeignKey(
        Vehiculo, 
        on_delete=models.CASCADE, 
        db_column='id_vehiculo',
        related_name='imposiciones_placa'
    )
    idcliente = models.ForeignKey(
        Cliente, 
        on_delete=models.CASCADE, 
        db_column='idcliente',
        related_name='imposiciones_placa'
    )
    idusuario = models.ForeignKey(
        Usuario, 
        on_delete=models.CASCADE, 
        db_column='idusuario',
        related_name='imposiciones_registradas'
    )
    
    # Datos de la placa
    numero_placa = models.CharField(max_length=10, blank=True, null=True)
    tipo_placa = models.CharField(max_length=20, choices=TIPO_PLACA_CHOICES, default='nueva')
    
    # Fechas importantes
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_tramite = models.DateField(blank=True, null=True)
    fecha_entrega = models.DateField(blank=True, null=True)
    
    # Costos
    costo_tramite = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    costo_placa = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    otros_costos = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_costo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Documentación
    tiene_tarjeta_propiedad = models.BooleanField(default=False)
    tiene_soat = models.BooleanField(default=False)
    tiene_revision_tecnica = models.BooleanField(default=False)
    con_garantia_mobiliaria = models.BooleanField(default=False)
    numero_expediente = models.CharField(max_length=50, blank=True, null=True)
    
    # Estado y observaciones
    estado_tramite = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    observaciones = models.TextField(blank=True, null=True)
    motivo_cancelacion = models.TextField(blank=True, null=True)
    
    # Sucursal (heredada de la venta)
    id_sucursal = models.ForeignKey(
        'Sucursales', 
        on_delete=models.DO_NOTHING, 
        db_column='id_sucursal', 
        null=True, 
        blank=True
    )
    
    # Control
    estado = models.IntegerField(default=1)  # 1=Activo, 0=Eliminado
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'imposicion_placas'
        ordering = ['-fecha_solicitud']
        verbose_name = 'Imposición de Placa'
        verbose_name_plural = 'Imposiciones de Placas'

    def __str__(self):
        placa = self.numero_placa if self.numero_placa else 'Sin asignar'
        return f"Imposición {self.id_imposicion} - Placa: {placa}"
    
    def save(self, *args, **kwargs):
        # Calcular total automáticamente
        self.total_costo = self.costo_tramite + self.costo_placa + self.otros_costos
        super().save(*args, **kwargs)
    
    @property
    def dias_en_tramite(self):
        "Calcula los días transcurridos desde la solicitud"
        if self.fecha_solicitud:
            delta = timezone.now() - self.fecha_solicitud
            return delta.days
        return 0