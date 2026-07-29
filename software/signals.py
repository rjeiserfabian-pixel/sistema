# software/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.db import transaction

from software.models.compradetalleModel import CompraDetalle
from software.models.VentaDetalleModel import VentaDetalle
from software.models.VentasModel import Ventas
from software.models.transferenciaModel import Transferencia
from software.models.detalleTransferenciaModel import DetalleTransferencia
from software.models.stockModel import Stock
from software.models.movimientoCajaModel import MovimientoCaja


# ============================================
# SIGNAL 1: Crear Stock al registrar Compra
# ============================================
@receiver(post_save, sender=CompraDetalle)
def crear_stock_compra(sender, instance, created, **kwargs):
    """
    Cuando se registra un detalle de compra, crea o actualiza el stock
    en el almacén de la sucursal principal
    """
    if created:
        # IGNORAR SI ES UN INGRESO DIRECTO DE STOCK (STOCKDIR) PARA EVITAR DUPLICADOS
        if instance.idcompra and instance.idcompra.numcorrelativo == 'STOCKDIR':
            print("[WARN] SIGNAL IGNORADO: Es un ingreso directo de stock (STOCKDIR), stock manejado manualmente.")
            return

        # Obtener almacén de la sucursal principal (o de la compra si está definido)
        if hasattr(instance.idcompra, 'id_almacen') and instance.idcompra.id_almacen:
            almacen = instance.idcompra.id_almacen
        elif instance.idcompra.id_sucursal:
            almacen = instance.idcompra.id_sucursal.almacenes.filter(estado=1).first()
        else:
            # Si no hay sucursal en la compra, usar la primera sucursal principal
            from software.models.sucursalesModel import Sucursales
            sucursal_principal = Sucursales.objects.filter(es_principal=True, estado=1).first()
            if sucursal_principal:
                almacen = sucursal_principal.almacenes.filter(estado=1).first()
            else:
                print("[ERROR] ERROR: No se encontró sucursal principal")
                return
        
        if not almacen:
            print("[ERROR] ERROR: No se encontró almacén para la sucursal")
            return
        
        # Determinar si es vehículo o repuesto
        if instance.id_vehiculo:
            # VEHÍCULO: Cantidad siempre es 1 (unidad individual)
            stock, created = Stock.objects.get_or_create(
                id_almacen=almacen,
                id_vehiculo=instance.id_vehiculo,
                defaults={'cantidad_disponible': 1, 'estado': 1}
            )
            if not created:
                stock.agregar_stock(1)
            
            print(f"[OK] Stock creado/actualizado: Vehículo {instance.id_vehiculo.id_vehiculo} en {almacen.nombre_almacen}")
        
        elif instance.id_repuesto_comprado:
            # REPUESTO: Usar cantidad del detalle
            stock, created = Stock.objects.get_or_create(
                id_almacen=almacen,
                id_repuesto_comprado=instance.id_repuesto_comprado,
                defaults={'cantidad_disponible': instance.cantidad, 'estado': 1}
            )
            if not created:
                stock.agregar_stock(instance.cantidad)
            
            print(f"[OK] Stock creado/actualizado: Repuesto {instance.id_repuesto_comprado.id_repuesto_comprado} - Cantidad: {instance.cantidad}")


# ============================================
# SIGNAL 2: Actualizar Stock en Transferencias
# ============================================
@receiver(post_save, sender=Transferencia)
def actualizar_stock_transferencia(sender, instance, created, **kwargs):
    """
    Cuando una transferencia es CONFIRMADA, actualiza el stock:
    - Descuenta del almacén origen
    - Aumenta en el almacén destino
    """
    # Solo ejecutar cuando la transferencia pasa a estado 'confirmada'
    if not created and instance.estado == 'confirmada' and instance.puede_confirmar():
        # Actualizar fecha de confirmación
        if not instance.fecha_confirmacion:
            instance.fecha_confirmacion = timezone.now()
            instance.save(update_fields=['fecha_confirmacion'])
        
        # Procesar cada detalle de la transferencia
        for detalle in instance.detalles.filter(estado=1):
            if detalle.id_vehiculo:
                # VEHÍCULO
                # Descontar del origen
                stock_origen = Stock.objects.filter(
                    id_almacen=instance.id_almacen_origen,
                    id_vehiculo=detalle.id_vehiculo,
                    estado=1
                ).first()
                
                if stock_origen and stock_origen.descontar_stock(detalle.cantidad):
                    # Agregar al destino
                    stock_destino, created = Stock.objects.get_or_create(
                        id_almacen=instance.id_almacen_destino,
                        id_vehiculo=detalle.id_vehiculo,
                        defaults={'cantidad_disponible': 0, 'estado': 1}
                    )
                    stock_destino.agregar_stock(detalle.cantidad)
                    
                    print(f"[OK] Transferencia confirmada: Vehículo {detalle.id_vehiculo.id_vehiculo}")
                    print(f"   Origen: {instance.id_almacen_origen.nombre_almacen} ({stock_origen.cantidad_disponible})")
                    print(f"   Destino: {instance.id_almacen_destino.nombre_almacen} ({stock_destino.cantidad_disponible})")
                else:
                    print(f"[ERROR] ERROR: Stock insuficiente en origen para vehículo {detalle.id_vehiculo.id_vehiculo}")
            
            elif detalle.id_repuesto_comprado:
                # REPUESTO
                stock_origen = Stock.objects.filter(
                    id_almacen=instance.id_almacen_origen,
                    id_repuesto_comprado=detalle.id_repuesto_comprado,
                    estado=1
                ).first()
                
                if stock_origen and stock_origen.descontar_stock(detalle.cantidad):
                    stock_destino, created = Stock.objects.get_or_create(
                        id_almacen=instance.id_almacen_destino,
                        id_repuesto_comprado=detalle.id_repuesto_comprado,
                        defaults={'cantidad_disponible': 0, 'estado': 1}
                    )
                    stock_destino.agregar_stock(detalle.cantidad)
                    
                    print(f"[OK] Transferencia confirmada: Repuesto {detalle.id_repuesto_comprado.id_repuesto_comprado} - Cantidad: {detalle.cantidad}")
                else:
                    print(f"[ERROR] ERROR: Stock insuficiente en origen para repuesto {detalle.id_repuesto_comprado.id_repuesto_comprado}")


# ============================================
# SIGNAL 3: Descontar Stock y Crear Movimiento de Caja
# ============================================
@receiver(post_save, sender=VentaDetalle)
def procesar_venta_detalle(sender, instance, created, **kwargs):
    """
    Cuando se registra un detalle de venta:
    1. Descuenta el stock del almacén
    2. Crea el movimiento de caja (solo una vez, al último detalle)
    """
    if not created:
        return
    
    venta = instance.idventa
    
    # ========================================
    # PARTE 1: DESCONTAR STOCK
    # ========================================
    if not hasattr(venta, 'id_almacen') or not venta.id_almacen:
        print(f"[ERROR] SIGNAL: La venta #{venta.idventa} no tiene almacén asignado")
        return
    
    almacen = venta.id_almacen
    
    if instance.id_vehiculo:
        # VEHÍCULO
        stock = Stock.objects.filter(
            id_almacen=almacen,
            id_vehiculo=instance.id_vehiculo,
            estado=1
        ).first()
        
        if stock and stock.descontar_stock(instance.cantidad):
            print(f"[OK] SIGNAL: Stock descontado - Vehículo {instance.id_vehiculo.id_vehiculo}")
            print(f"   Almacén: {almacen.nombre_almacen}, Stock restante: {stock.cantidad_disponible}")
        else:
            print(f"[WARN] SIGNAL: No se pudo descontar stock para vehículo {instance.id_vehiculo.id_vehiculo}")
    
    elif instance.id_repuesto_comprado:
        # REPUESTO
        stock = Stock.objects.filter(
            id_almacen=almacen,
            id_repuesto_comprado=instance.id_repuesto_comprado,
            estado=1
        ).first()
        
        if stock and stock.descontar_stock(instance.cantidad):
            print(f"[OK] SIGNAL: Stock descontado - Repuesto {instance.id_repuesto_comprado.id_repuesto_comprado}")
            print(f"   Cantidad: {instance.cantidad}, Stock restante: {stock.cantidad_disponible}")
        else:
            print(f"[WARN] SIGNAL: No se pudo descontar stock para repuesto")
    
    # ========================================
    # PARTE 2: CREAR MOVIMIENTO DE CAJA (solo una vez)
    # ========================================
    def crear_movimiento_caja():
        # Refrescar la venta desde la BD para obtener el total actualizado
        venta.refresh_from_db()

        # 🔥 VALIDACIÓN CLAVE: Si la venta NO está pagada, NO generar movimiento
        if getattr(venta, 'estado_cobro', '') != 'Pagado':
            return
        
        # Verificar que no exista ya un movimiento
        existe_movimiento = MovimientoCaja.objects.filter(
            idventa=venta,
            tipo_movimiento='ingreso'
        ).exists()
        
        if existe_movimiento:
            return
        
        # Verificar que tiene caja asignada
        if not hasattr(venta, 'id_caja') or not venta.id_caja:
            print(f"[ERROR] SIGNAL: La venta #{venta.idventa} no tiene caja asignada")
            return
        
        # Verificar que el total no sea 0
        if venta.total_venta <= 0:
            print(f"[WARN] SIGNAL: La venta #{venta.idventa} tiene total S/ 0")
            return

        # Intentar obtener la apertura actual para que no quede flotante
        apertura = None
        try:
            from software.models.cajaModel import AperturaCierreCaja
            apertura = AperturaCierreCaja.objects.filter(
                idusuario=venta.idusuario,
                id_caja=venta.id_caja,
                estado__in=['abierta', 'reabierta']
            ).first()
        except Exception:
            pass
        
        # [OK] CREAR MOVIMIENTO DE CAJA
        movimiento = MovimientoCaja.objects.create(
            id_caja=venta.id_caja,
            id_movimiento=apertura,
            idusuario=venta.idusuario,
            idventa=venta,
            tipo_movimiento='ingreso',
            monto=venta.total_venta,
            descripcion=f"Venta {venta.numero_comprobante} - Cliente: {venta.idcliente.razonsocial}",
            estado=1
        )
        
        print(f"[OK] SIGNAL: Movimiento de caja creado - Ingreso S/ {venta.total_venta} (Venta #{venta.idventa})")
    
    # Ejecutar después de que termine la transacción
    transaction.on_commit(crear_movimiento_caja)