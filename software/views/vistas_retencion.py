from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
from decimal import Decimal

from software.models.CreditoModel import Credito
from software.models.VehiculosModel import Vehiculo
from software.models.estadoproductoModel import EstadoProducto
from software.models.SituacionVehiculoModel import SituacionVehiculo
from software.models.stockModel import Stock
from software.models.almacenesModel import Almacenes
from software.models.compradetalleModel import CompraDetalle
from software.models.comprasModel import Compras
from software.models.ProveedoresModel import Proveedor
from software.models.Tipo_entidadModel import TipoEntidad
from software.models.AperturaCierreCajaModel import AperturaCierreCaja
from software.models.movimientoCajaModel import MovimientoCaja


# ── helpers ─────────────────────────────────────────────────────────────────

def _get_estado(nombre: str) -> EstadoProducto | None:
    """Retorna el EstadoProducto cuyo nombre contenga 'nombre' (case-insensitive)."""
    return EstadoProducto.objects.filter(
        nombreestadoproducto__iexact=nombre, estado=1
    ).first()


def _ensure_estado_producto(nombre_canon: str) -> EstadoProducto:
    """
    Garantiza un EstadoProducto existente y activo (estado=1), igual que _get_situacion.
    Evita 500 cuando falta p.ej. 'Segunda' en instalaciones antiguas.
    """
    obj = (
        EstadoProducto.objects.filter(nombreestadoproducto__iexact=nombre_canon)
        .order_by('-estado', 'idestadoproducto')
        .first()
    )
    if obj:
        if obj.estado != 1:
            obj.estado = 1
            obj.save(update_fields=['estado'])
        return obj
    return EstadoProducto.objects.create(
        nombreestadoproducto=nombre_canon,
        estado=1,
    )


def _get_situacion(nombre: str) -> SituacionVehiculo | None:
    """Retorna o crea la SituacionVehiculo cuyo nombre coincida."""
    situacion, created = SituacionVehiculo.objects.get_or_create(
        nombre_situacion=nombre,
        defaults={'estado': 1}
    )
    return situacion


def _vehiculo_del_credito(credito: Credito) -> Vehiculo | None:
    """Devuelve el vehículo asociado a un crédito, sea directo o por venta."""
    if credito.id_vehiculo_id:
        return credito.id_vehiculo
    if credito.idventa:
        from software.models.VentaDetalleModel import VentaDetalle
        det = VentaDetalle.objects.filter(
            idventa=credito.idventa,
            id_vehiculo__isnull=False,
            estado=1
        ).select_related('id_vehiculo').first()
        if det:
            return det.id_vehiculo
    return None


def _almacen_del_credito(credito: Credito) -> Almacenes | None:
    """Devuelve el almacén asociado al crédito."""
    if credito.id_almacen:
        return credito.id_almacen
    if credito.idventa:
        return credito.idventa.id_almacen
    return None


# ── 1. RETENER VEHÍCULO ──────────────────────────────────────────────────────

@transaction.atomic
def retener_vehiculo(request, idcredito):
    """
    Acción manual: cambia crédito→RETENIDO y vehículo→RETENIDO.
    Solo permitido si el crédito está en mora.
    """
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)

    credito = get_object_or_404(Credito, idcredito=idcredito)

    if credito.estado_credito != 'mora':
        return JsonResponse({
            'ok': False,
            'error': f'Solo se puede retener un crédito en MORA. Estado actual: {credito.estado_credito}'
        }, status=400)

    vehiculo = _vehiculo_del_credito(credito)
    situacion_retenida = _get_situacion('RETENIDO')

    if vehiculo:
        vehiculo.id_situacion = situacion_retenida
        vehiculo.save()
        
        # Actualizar stock: poner en 1 porque ya lo tenemos nosotros
        almacen = _almacen_del_credito(credito)
        # Limpieza masiva anti N+1: vaciar stock en otros almacenes
        Stock.objects.filter(id_vehiculo=vehiculo).exclude(id_almacen=almacen).update(cantidad_disponible=0)

        stock_obj = Stock.objects.filter(id_vehiculo=vehiculo, id_almacen=almacen).first()
        if stock_obj:
            stock_obj.cantidad_disponible = 1
            stock_obj.estado = 1
            stock_obj.save()
        else:
            # Si no hay stock previo en ese almacén, creamos uno
            Stock.objects.create(
                id_vehiculo=vehiculo,
                id_almacen=almacen,
                cantidad_disponible=1,
                estado=1
            )

    credito.estado_credito = 'retenido'
    credito.fecha_retencion = timezone.now()
    credito.save()

    return JsonResponse({
        'ok': True,
        'message': 'Vehículo retenido correctamente. Periodo de gracia iniciado.',
        'fecha_retencion': credito.fecha_retencion.strftime('%d/%m/%Y %H:%M'),
        'dias_gracia': credito.dias_gracia
    })


# ── 2. LIBERAR VEHÍCULO (cliente pagó durante gracia) ────────────────────────

@transaction.atomic
def liberar_vehiculo(request, idcredito):
    """
    Si el cliente paga durante el periodo de gracia:
    crédito → ACTIVO, vehículo → EN_CREDITO.
    """
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)

    credito = get_object_or_404(Credito, idcredito=idcredito)

    if credito.estado_credito != 'retenido':
        return JsonResponse({
            'ok': False,
            'error': f'Solo se puede liberar un crédito RETENIDO. Estado actual: {credito.estado_credito}'
        }, status=400)

    vehiculo = _vehiculo_del_credito(credito)
    situacion_en_credito = _get_situacion('EN CREDITO')

    if vehiculo:
        vehiculo.id_situacion = situacion_en_credito
        vehiculo.save()
        
        # Actualizar stock: poner en 0 porque se lo lleva el cliente
        almacen = _almacen_del_credito(credito)
        # Limpieza masiva anti N+1: vaciar stock en todos los almacenes
        Stock.objects.filter(id_vehiculo=vehiculo).update(cantidad_disponible=0)

    credito.estado_credito = 'activo'
    credito.fecha_retencion = None
    credito.save()

    return JsonResponse({
        'ok': True,
        'message': 'Crédito liberado. El vehículo vuelve a estar EN CRÉDITO.'
    })


# ── 3. CONFIRMAR INCUMPLIMIENTO (no pagó en el periodo de gracia) ────────────

@transaction.atomic
def ejecutar_incumplimiento(request, idcredito):
    """
    Si el cliente NO pagó: crédito → CANCELADO, vehículo → EN_REPARACION.
    """
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)

    credito = get_object_or_404(Credito, idcredito=idcredito)

    if credito.estado_credito != 'retenido':
        return JsonResponse({
            'ok': False,
            'error': f'Solo se puede confirmar incumplimiento de un crédito RETENIDO. Estado actual: {credito.estado_credito}'
        }, status=400)

    vehiculo = _vehiculo_del_credito(credito)
    situacion_reparacion = _get_situacion('EN REPARACION')

    if vehiculo:
        vehiculo.id_situacion = situacion_reparacion
        vehiculo.save()
        
        # Asegurar que esté en stock (aunque esté en reparación, es parte de nuestro inventario)
        almacen = _almacen_del_credito(credito)
        # Limpieza masiva anti N+1: vaciar stock en otros almacenes
        Stock.objects.filter(id_vehiculo=vehiculo).exclude(id_almacen=almacen).update(cantidad_disponible=0)
        Stock.objects.filter(id_vehiculo=vehiculo, id_almacen=almacen).update(cantidad_disponible=1, estado=1)

    credito.estado_credito = 'cancelado'
    credito.save()

    return JsonResponse({
        'ok': True,
        'message': 'Crédito cancelado. El vehículo pasa a EN REPARACIÓN.'
    })


# ── 4. REGISTRAR REPARACIÓN ──────────────────────────────────────────────────

@transaction.atomic
def registrar_reparacion(request, idcredito):
    """
    Registra el costo de reparación y cambia vehículo → REPARADO.
    El crédito queda con estado_credito = 'reparado'.
    """
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)

    idusuario = request.session.get('idusuario')
    if not idusuario:
        return JsonResponse({'ok': False, 'error': 'Sesión caducada o no válida.'}, status=401)

    apertura_actual = AperturaCierreCaja.objects.filter(
        idusuario_id=idusuario,
        estado__in=['abierta', 'reabierta']
    ).first()

    if not apertura_actual:
        return JsonResponse({
            'ok': False,
            'error': 'No tiene una caja abierta. Debe aperturar una caja antes de registrar gastos de reparación.'
        }, status=400)

    credito = get_object_or_404(Credito, idcredito=idcredito)

    if credito.estado_credito != 'cancelado':
        return JsonResponse({
            'ok': False,
            'error': f'Solo se puede registrar reparación de un crédito CANCELADO. Estado actual: {credito.estado_credito}'
        }, status=400)

    costo_str = request.POST.get('costo_reparacion', '0')
    observaciones = request.POST.get('observaciones', '').strip()
    try:
        costo = Decimal(costo_str)
        if costo < 0:
            raise ValueError
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Costo de reparación inválido.'}, status=400)
        
    if costo > 0:
        from django.db.models import Sum
        ingresos = MovimientoCaja.objects.filter(
            id_movimiento=apertura_actual,
            tipo_movimiento='ingreso',
            estado=1
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
        
        egresos = MovimientoCaja.objects.filter(
            id_movimiento=apertura_actual,
            tipo_movimiento='egreso',
            estado=1
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
        
        saldo_inicial = apertura_actual.saldo_inicial or Decimal('0.00')
        saldo_actual = saldo_inicial + ingresos - egresos
        
        if saldo_actual < costo:
            return JsonResponse({
                'ok': False,
                'error': f'Fondos insuficientes en la caja para registrar la reparación. Saldo actual: S/ {saldo_actual:.2f}, Costo: S/ {costo:.2f}.'
            }, status=400)

    vehiculo = _vehiculo_del_credito(credito)
    situacion_reparado = _get_situacion('REPARADO')

    if vehiculo:
        vehiculo.id_situacion = situacion_reparado
        if observaciones:
            vehiculo.imperfecciones = (vehiculo.imperfecciones or '') + f'\n[REPARACIÓN] {observaciones}'
        vehiculo.save()
        
        # Mantener en stock
        almacen = _almacen_del_credito(credito)
        # Limpieza masiva anti N+1: vaciar stock en otros almacenes
        Stock.objects.filter(id_vehiculo=vehiculo).exclude(id_almacen=almacen).update(cantidad_disponible=0)
        Stock.objects.filter(id_vehiculo=vehiculo, id_almacen=almacen).update(cantidad_disponible=1, estado=1)

    credito.costo_reparacion = costo
    credito.estado_credito = 'reparado'
    credito.save()

    if costo > 0:
        MovimientoCaja.objects.create(
            id_caja=apertura_actual.id_caja,
            id_movimiento=apertura_actual,
            idusuario_id=idusuario,
            tipo_movimiento='egreso',
            monto=costo,
            descripcion=f"Pago por reparación de vehículo - Crédito {credito.codigo_credito}",
            idventa=None,
            idcompra=None,
            estado=1
        )

    return JsonResponse({
        'ok': True,
        'message': f'Reparación registrada. Costo: S/ {costo:.2f}. Vehículo listo para reingreso a stock.',
        'costo_reparacion': float(costo),
        'saldo_pendiente': float(credito.saldo_pendiente),
        'precio_compra_sugerido': float(credito.saldo_pendiente),
        'precio_venta_base': float(credito.saldo_pendiente + costo),
    })


# ── 5. REINGRESAR A STOCK (Segunda Mano) ─────────────────────────────────────

@transaction.atomic
def reingresar_stock_recuperado(request, idcredito):
    """
    Calcula precios y crea un nuevo registro de Stock marcando el vehículo como SEMI-NUEVA.
      precio_compra = saldo_pendiente del crédito
      precio_venta  = saldo_pendiente + costo_reparacion + margen
    """
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)

    credito = get_object_or_404(Credito, idcredito=idcredito)

    if credito.estado_credito != 'reparado':
        return JsonResponse({
            'ok': False,
            'error': f'Solo se puede reingresar un crédito en estado REPARADO. Estado actual: {credito.estado_credito}'
        }, status=400)

    margen_mayor_str = request.POST.get('margen_mayor', '0')
    margen_min_str = request.POST.get('margen_min', '0')
    margen_max_str = request.POST.get('margen_max', '0')
    id_almacen = request.POST.get('id_almacen')
    try:
        margen_mayor = Decimal(margen_mayor_str)
        margen_min = Decimal(margen_min_str)
        margen_max = Decimal(margen_max_str)
        if margen_mayor < 0 or margen_min < 0 or margen_max < 0:
            raise ValueError
        if margen_min < margen_mayor:
            return JsonResponse({'ok': False, 'error': 'El Margen P. CASH no puede ser menor al Margen P. X MAYOR.'}, status=400)
        if margen_max < margen_min:
            return JsonResponse({'ok': False, 'error': 'El Margen P. LISTA no puede ser menor al Margen P. CASH.'}, status=400)
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Márgenes de ganancia inválidos.'}, status=400)

    if not id_almacen:
        # Fallback: almacén del crédito directo
        if credito.id_almacen_id:
            id_almacen = credito.id_almacen_id
        else:
            return JsonResponse({'ok': False, 'error': 'Debe especificar un almacén de destino.'}, status=400)

    almacen = get_object_or_404(Almacenes, pk=id_almacen)

    vehiculo = _vehiculo_del_credito(credito)
    if not vehiculo:
        return JsonResponse({'ok': False, 'error': 'No se encontró el vehículo asociado al crédito.'}, status=400)

    estado_segunda = _ensure_estado_producto('Semi-nueva')

    # Cálculo de precios
    precio_compra = credito.saldo_pendiente + credito.costo_reparacion
    precio_mayor = precio_compra + margen_mayor
    precio_minimo = precio_compra + margen_min
    precio_maximo = precio_compra + margen_max
    
    credito.margen_minimo_recuperacion = margen_min
    credito.margen_maximo_recuperacion = margen_max
    credito.margen_recuperacion = margen_max # Por compatibilidad

    # ── Crear la infraestructura de stock ────────────────────────────────────
    tipo_entidad, _ = TipoEntidad.objects.get_or_create(
        tipo_entidad='INTERNO',
        defaults={'codigo': 'INT', 'descripcion': 'INTERNO', 'abreviatura': 'INT', 'estado': 1}
    )
    proveedor_interno, _ = Proveedor.objects.get_or_create(
        numdoc='00000000',
        defaults={
            'razonsocial': 'INGRESO STOCK DIRECTO',
            'nombre_comercial': 'INTERNO',
            'direccion': 'INTERNO',
            'telefono': '000000000',
            'email': 'interno@stock.com',
            'departamento': 'N/A',
            'provincia': 'N/A',
            'distrito': 'N/A',
            'estado': 1,
            'id_tipo_entidad': tipo_entidad
        }
    )
    id_sucursal = almacen.id_sucursal_id
    compra_stock, _ = Compras.objects.get_or_create(
        numcorrelativo='STOCKDIR',
        defaults={
            'idproveedor': proveedor_interno,
            'id_sucursal_id': id_sucursal,
            'estado': 1,
            'total_compra': 0.00
        }
    )
    compra_detalle = CompraDetalle.objects.create(
        idcompra=compra_stock,
        id_vehiculo=vehiculo,
        id_repuesto_comprado=None,
        cantidad=1,
        precio_compra=precio_compra,
        precio_por_mayor=precio_mayor,
        precio_minimo=precio_minimo,
        precio_maximo=precio_maximo,
        margen_por_mayor=0,
        margen_minimo=0, # Podríamos calcular el %, pero el sistema usa montos fijos aquí
        margen_maximo=0,
        subtotal=float(precio_maximo)
    )

    # 3. Actualizar situación del vehículo
    situacion_disponible = _get_situacion('DISPONIBLE')
    if vehiculo:
        vehiculo.id_situacion = situacion_disponible
        vehiculo.save()

    # 4. Crear o actualizar stock
    # Limpieza masiva anti N+1: vaciar stock en otros almacenes antes de asignarlo al nuevo
    Stock.objects.filter(id_vehiculo=vehiculo).exclude(id_almacen=almacen).update(cantidad_disponible=0)

    stock_obj, created = Stock.objects.get_or_create(
        id_almacen=almacen,
        id_vehiculo=vehiculo,
        defaults={
            'idcompradetalle': compra_detalle,
            'cantidad_disponible': 1,
            'estado': 1
        }
    )

    if not created:
        stock_obj.idcompradetalle = compra_detalle
        stock_obj.cantidad_disponible = 1
        stock_obj.estado = 1
        stock_obj.save()

    # ── Actualizar estados finales ────────────────────────────────────────────
    # La condición ahora es SEGUNDA y la situación es DISPONIBLE (ya no está retenido ni en reparación)
    vehiculo.idestadoproducto = estado_segunda
    vehiculo.id_situacion = _get_situacion('DISPONIBLE')
    vehiculo.save()

    # El crédito queda CANCELADO y desaparece del listado principal (estado=0)
    credito.estado_credito = 'cancelado'
    credito.estado = 0
    credito.save()

    return JsonResponse({
        'ok': True,
        'message': f'Vehículo reingresado a stock como SEMI-NUEVA. P. LISTA: S/ {precio_maximo:.2f}',
        'precio_compra': float(precio_compra),
        'costo_reparacion': float(credito.costo_reparacion),
        'margen_mayor': float(margen_mayor),
        'margen_min': float(margen_min),
        'margen_max': float(margen_max),
        'precio_mayor': float(precio_mayor),
        'precio_minimo': float(precio_minimo),
        'precio_maximo': float(precio_maximo),
        'almacen': almacen.nombre_almacen,
    })
