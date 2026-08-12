from django.db import models
from software.models.cajaModel import Caja
from software.models.UsuarioModel import Usuario
from software.models.almacenesModel import Almacenes

class AperturaCierreCaja(models.Model):
    id_movimiento = models.AutoField(primary_key=True)
    id_caja = models.ForeignKey(Caja, models.DO_NOTHING, db_column='id_caja', null=True, blank=True)
    idusuario = models.ForeignKey(Usuario, models.DO_NOTHING, db_column='idusuario', null=True, blank=True)
    saldo_inicial = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    saldo_final = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    saldo_inicial_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, blank=True, null=True)
    saldo_final_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, blank=True, null=True)
    fecha_apertura = models.DateTimeField(blank=True, null=True)
    fecha_cierre = models.DateTimeField(blank=True, null=True)
    hora_apertura = models.TimeField(blank=True, null=True)
    hora_cierre = models.TimeField(blank=True, null=True)
    estado = models.CharField(max_length=10, blank=True, null=True)  # 'abierta', 'cerrada', 'reabierta'
    id_almacen = models.ForeignKey(Almacenes, models.SET_NULL, db_column='id_almacen', null=True, blank=True)
    
    class Meta:
        managed = True
        db_table = 'apertura_cierre_caja'
    