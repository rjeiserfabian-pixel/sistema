from django.db import models
from software.models.cajaModel import Caja
from software.models.UsuarioModel import Usuario
from software.models.VentasModel import Ventas
from software.models.AperturaCierreCajaModel import AperturaCierreCaja
from software.models.comprasModel import Compras


class MovimientoCaja(models.Model):
    TIPOS_MOVIMIENTO = [
        ('ingreso', 'Ingreso'),
        ('egreso', 'Egreso'),
    ]
    
    id_movimiento_caja = models.AutoField(primary_key=True)
    id_caja = models.ForeignKey(Caja, on_delete=models.RESTRICT, db_column='id_caja', related_name='movimientos')
    idusuario = models.ForeignKey(Usuario, on_delete=models.RESTRICT, db_column='idusuario', related_name='movimientos_caja')
    id_movimiento = models.ForeignKey( AperturaCierreCaja, on_delete=models.SET_NULL, db_column='id_movimiento', related_name='movimientos_caja', null=True, blank=True)
    
    # Relación opcional con venta (para ingresos por venta)
    idventa = models.ForeignKey(Ventas, on_delete=models.SET_NULL, db_column='idventa', related_name='movimientos_caja', null=True, blank=True)
    
    # Relación opcional con compra (para egresos por compra)
    idcompra = models.ForeignKey(Compras, on_delete=models.SET_NULL, db_column='idcompra', related_name='movimientos_caja', null=True, blank=True)
    
    tipo_movimiento = models.CharField(max_length=10, choices=TIPOS_MOVIMIENTO, db_column='tipo_movimiento', db_index=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2, db_column='monto')
    moneda = models.CharField(max_length=3, default='PEN', db_column='moneda')
    tipo_cambio_aplicado = models.DecimalField(max_digits=10, decimal_places=4, default=1.00, db_column='tipo_cambio_aplicado')
    monto_base_soles = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, db_column='monto_base_soles')
    descripcion = models.TextField(db_column='descripcion', null=True, blank=True)
    
    fecha_movimiento = models.DateTimeField(auto_now_add=True, db_column='fecha_movimiento', db_index=True)
    estado = models.IntegerField(default=1, db_column='estado', db_index=True)
    
    class Meta:
        managed = True
        db_table = 'movimientos_caja'
        ordering = ['-fecha_movimiento']
        indexes = [
            # Índice compuesto para el filtro más común del Reporte de Caja:
            # WHERE fecha_movimiento BETWEEN x AND y AND tipo_movimiento = z
            models.Index(fields=['fecha_movimiento', 'tipo_movimiento'], name='idx_caja_fecha_tipo'),
            # Índice compuesto para filtrar por caja + fecha (historial de cajas)
            models.Index(fields=['id_caja', 'fecha_movimiento'], name='idx_caja_id_fecha'),
        ]
    
    def __str__(self):
        return f"{self.tipo_movimiento.upper()} - S/ {self.monto} - {self.fecha_movimiento.strftime('%d/%m/%Y %H:%M')}"