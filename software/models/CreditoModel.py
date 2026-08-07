from django.db import models
from django.utils import timezone
from software.models.VentasModel import Ventas
from software.models.GaranteModel import Garante

class Credito(models.Model):
    """
    Modelo para gestionar créditos de ventas
    Cada venta a crédito genera un registro aquí con código único
    """
    idcredito = models.AutoField(primary_key=True)
    codigo_credito = models.CharField(max_length=50, unique=True)
    idventa = models.OneToOneField(
        'Ventas', 
        on_delete=models.CASCADE, 
        db_column='idventa', 
        related_name='credito',
        null=True,
        blank=True
    )
    # Campos para crédito directo (sin venta)
    idcliente = models.ForeignKey('Cliente', on_delete=models.CASCADE, db_column='idcliente', null=True, blank=True)
    es_directo = models.BooleanField(default=False)
    
    # Garante asociado al crédito
    id_garante = models.ForeignKey('Garante', on_delete=models.SET_NULL, db_column='id_garante', null=True, blank=True)
    
    # Rastro del producto en crédito directo
    tipo_item = models.CharField(max_length=20, null=True, blank=True) # 'vehiculo' o 'repuesto'
    id_vehiculo = models.ForeignKey('Vehiculo', on_delete=models.SET_NULL, db_column='id_vehiculo', null=True, blank=True)
    id_repuesto_comprado = models.ForeignKey('RepuestoComp', on_delete=models.SET_NULL, db_column='id_repuesto_comprado', null=True, blank=True)
    cantidad = models.IntegerField(default=1)
    
    # Contexto para crédito directo
    id_sucursal = models.ForeignKey('Sucursales', on_delete=models.SET_NULL, db_column='id_sucursal', null=True, blank=True)
    id_almacen = models.ForeignKey('Almacenes', on_delete=models.SET_NULL, db_column='id_almacen', null=True, blank=True)
    idusuario = models.ForeignKey('Usuario', on_delete=models.SET_NULL, db_column='idusuario', null=True, blank=True)
    monto_total = models.DecimalField(max_digits=10, decimal_places=2)
    monto_adelanto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    saldo_pendiente = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad_cuotas = models.IntegerField()
    fecha_credito = models.DateTimeField(default=timezone.now, db_index=True)

    estado_credito = models.CharField(
        max_length=20,
        default='activo',
        db_index=True,
    )  # activo, pagado, mora, retenido, cancelado, reparado
    estado = models.IntegerField(default=1, db_index=True)

    # Campos para flujo de retención
    fecha_retencion = models.DateTimeField(null=True, blank=True)
    dias_gracia = models.IntegerField(default=10)
    costo_reparacion = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    margen_recuperacion = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    margen_minimo_recuperacion = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    margen_maximo_recuperacion = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        managed = True
        db_table = 'creditos'
        ordering = ['-fecha_credito']

    def __str__(self):
        cliente_nombre = "Sin Cliente"
        if self.idventa:
            cliente_nombre = self.idventa.idcliente.razonsocial
        elif self.idcliente:
            cliente_nombre = self.idcliente.razonsocial
        return f"{self.codigo_credito} - {cliente_nombre}"
    
    def calcular_saldo_pendiente(self):
        """Calcula el saldo pendiente basado en la suma de saldos de todas las cuotas activas"""
        from software.models.CuotasVentaModel import CuotasVenta
        from django.db.models import Sum
        from decimal import Decimal
        
        if self.idventa:
            cuotas = CuotasVenta.objects.filter(idventa=self.idventa, estado=1)
        else:
            cuotas = CuotasVenta.objects.filter(idcredito=self, estado=1)
            
        resultado = cuotas.aggregate(total=Sum('saldo_cuota'))['total']
        return resultado if resultado is not None else Decimal('0')
    
    def actualizar_estado(self):
        """Actualiza el estado del crédito según el estado de las cuotas.
        No sobreescribe estados especiales del flujo de retención."""
        from software.models.CuotasVentaModel import CuotasVenta
        from django.utils import timezone

        # Estados del flujo de retención que no deben ser sobreescritos
        ESTADOS_BLOQUEADOS = ('retenido', 'cancelado', 'reparado', 'segunda')
        if self.estado_credito in ESTADOS_BLOQUEADOS:
            self.saldo_pendiente = self.calcular_saldo_pendiente()
            self.save()
            return

        if self.idventa:
            cuotas = CuotasVenta.objects.filter(idventa=self.idventa, estado=1)
        else:
            cuotas = CuotasVenta.objects.filter(idcredito=self, estado=1)
        
        # Si todas las cuotas están pagadas
        if all(cuota.estado_pago == 'Pagado' for cuota in cuotas):
            self.estado_credito = 'pagado'
            self.saldo_pendiente = 0
        else:
            # Verificar si hay cuotas vencidas
            hay_vencidas = cuotas.filter(
                estado_pago__in=['Pendiente', 'Parcial'],
                fecha_vencimiento__lt=timezone.now().date()
            ).exists()
            
            if hay_vencidas:
                self.estado_credito = 'mora'
            else:
                self.estado_credito = 'activo'
            
            self.saldo_pendiente = self.calcular_saldo_pendiente()
        
        self.save()

    def obtener_color_mora(self):
        """
        Determina el color (verde, amarillo, rojo) según los días de mora
        de la cuota vencida más antigua. Retorna None si no hay mora.
        """
        from software.models.CuotasVentaModel import CuotasVenta
        from software.models.empresaModel import Empresa
        from django.utils import timezone

        if self.idventa:
            cuotas = CuotasVenta.objects.filter(idventa=self.idventa, estado=1)
        else:
            cuotas = CuotasVenta.objects.filter(idcredito=self, estado=1)

        # Buscar la cuota vencida más antigua que no esté pagada
        cuota_vencida = cuotas.filter(
            estado_pago__in=['Pendiente', 'Parcial'],
            fecha_vencimiento__lt=timezone.now().date()
        ).order_by('fecha_vencimiento').first()

        if not cuota_vencida:
            return None

        # Calcular días de mora
        dias_mora = (timezone.now().date() - cuota_vencida.fecha_vencimiento).days

        # Obtener configuración de empresa
        empresa = Empresa.objects.first()
        if not empresa:
            return 'rojo' # Fallback si no hay configuración
            
        limite_verde = empresa.limite_dias_verde
        limite_amarillo = empresa.limite_dias_amarillo

        if dias_mora <= limite_verde:
            return 'verde'
        elif dias_mora <= limite_amarillo:
            return 'amarillo'
        else:
            return 'rojo'