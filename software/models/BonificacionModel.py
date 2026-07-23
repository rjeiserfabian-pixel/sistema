from django.db import models
from software.models.UsuarioModel import Usuario

class ReglaBonificacion(models.Model):
    TIPO_PRODUCTO_CHOICES = [
        ('Vehiculo', 'Vehculo'),
        ('Repuesto', 'Repuesto'),
    ]
    TIPO_COMISION_CHOICES = [
        ('Porcentaje', 'Porcentaje Directo (Vehculos)'),
        ('Escala', 'Escala por Volumen (Repuestos)'),
    ]
    
    id_regla = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=255)
    tipo_producto = models.CharField(max_length=20, choices=TIPO_PRODUCTO_CHOICES)
    tipo_comision = models.CharField(max_length=20, choices=TIPO_COMISION_CHOICES)
    porcentaje = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Porcentaje para vehculos (ej. 1.50)")
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    estado = models.BooleanField(default=True)

    class Meta:
        managed = True
        db_table = 'regla_bonificacion'

    def __str__(self):
        return f"{self.nombre} ({self.tipo_producto})"


class RangoBonificacion(models.Model):
    id_rango = models.AutoField(primary_key=True)
    regla = models.ForeignKey(ReglaBonificacion, on_delete=models.CASCADE, related_name='rangos')
    monto_minimo = models.DecimalField(max_digits=10, decimal_places=2)
    monto_maximo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    porcentaje = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        managed = True
        db_table = 'rango_bonificacion'
        ordering = ['monto_minimo']


class MetaVendedor(models.Model):
    CATEGORIA_CHOICES = [
        ('Vehiculos', 'Vehculos'),
        ('Repuestos', 'Repuestos'),
        ('Ambas', 'Ambas'),
    ]
    id_meta = models.AutoField(primary_key=True)
    vendedor = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='idusuario')
    mes_anio = models.DateField(help_text="Primer da del mes de la meta")
    meta_soles = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    meta_unidades = models.IntegerField(null=True, blank=True)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES)
    porcentaje_bono = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text="Porcentaje adicional de la comisión base si se cumple la meta")

    class Meta:
        managed = True
        db_table = 'meta_vendedor'


class CalculoBonificacion(models.Model):
    ESTADO_CHOICES = [
        ('Calculado', 'Calculado'),
        ('Observado', 'Observado'),
        ('Aprobado', 'Aprobado'),
        ('Pagado', 'Pagado'),
        ('Anulado', 'Anulado'),
    ]
    id_calculo = models.AutoField(primary_key=True)
    vendedor = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='idusuario')
    fecha_inicio_periodo = models.DateField()
    fecha_fin_periodo = models.DateField()
    total_vehiculos_vendidos = models.IntegerField(default=0)
    total_repuestos_vendidos = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    porcentaje_cumplimiento = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    comision_vehiculos = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    comision_repuestos = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bono_meta = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_pagar = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='Calculado')
    fecha_calculo = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'calculo_bonificacion'
        ordering = ['-fecha_inicio_periodo', '-fecha_calculo']
