from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum, Q
from django.utils import timezone
from decimal import Decimal

from software.models.movimientoCajaModel import MovimientoCaja
from software.models.cajaModel import Caja
from software.models.AperturaCierreCajaModel import AperturaCierreCaja
from software.models.UsuarioModel import Usuario
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos
from software.models.comprasModel import Compras
from software.models.compradetalleModel import CompraDetalle


def movimientos_caja(request):
    """
    Listado de movimientos de caja
    """
    id_tipo_usuario = request.session.get('idtipousuario')
    idusuario = request.session.get('idusuario')
    
    if not id_tipo_usuario or not idusuario:
        return HttpResponse("<h1>No tiene acceso</h1>")
    
    permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id_tipo_usuario)
    es_admin = id_tipo_usuario == 1
    usuario = Usuario.objects.get(idusuario=idusuario)
    
    id_caja_session = request.session.get('id_caja')
    
    apertura_actual = None
    if id_caja_session:
        apertura_actual = AperturaCierreCaja.objects.filter(
            idusuario_id=idusuario,
            id_caja_id=id_caja_session,
            estado__in=['abierta', 'reabierta']
        ).first()
    
    # ⭐ FILTRO SIMPLIFICADO con id_movimiento
    if apertura_actual:
        # Mostrar solo movimientos de esta apertura
        movimientos = MovimientoCaja.objects.filter(
            id_movimiento=apertura_actual,  # ✅ USAR id_movimiento
            estado=1
        ).select_related(
            'id_caja', 'idusuario', 'idventa'
        ).order_by('-fecha_movimiento')
    else:
        movimientos = MovimientoCaja.objects.none()
    
    # Calcular totales
    total_ingresos = movimientos.filter(
        tipo_movimiento='ingreso'
    ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
    
    total_egresos = movimientos.filter(
        tipo_movimiento='egreso'
    ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
    
    saldo_actual = total_ingresos - total_egresos
    
    if apertura_actual:
        saldo_actual += apertura_actual.saldo_inicial
    
    data = {
        'movimientos': [],
        'total_ingresos': total_ingresos,
        'total_egresos': total_egresos,
        'saldo_actual': saldo_actual,
        'apertura_actual': apertura_actual,
        'tiene_caja_abierta': bool(apertura_actual),
        'es_admin': es_admin,
        'permisos': permisos,
    }
    
    return render(request, 'movimientos_caja/movimientos.html', data)


def api_listar_movimientos(request):
    """
    API Server-Side para listar los movimientos de caja usando AJAX manual
    """
    id_tipo_usuario = request.session.get('idtipousuario')
    idusuario = request.session.get('idusuario')
    id_caja_session = request.session.get('id_caja')
    
    if not id_tipo_usuario or not idusuario or not id_caja_session:
        return JsonResponse({'error': 'No tiene acceso o no hay caja abierta'}, status=403)
        
    apertura_actual = AperturaCierreCaja.objects.filter(
        idusuario_id=idusuario,
        id_caja_id=id_caja_session,
        estado__in=['abierta', 'reabierta']
    ).first()
    
    if not apertura_actual:
        return JsonResponse({'data': [], 'total_pages': 0, 'current_page': 1})
        
    movimientos = MovimientoCaja.objects.filter(
        id_movimiento=apertura_actual,
        estado=1
    ).select_related('id_caja', 'idusuario', 'idventa').order_by('-fecha_movimiento')
    
    # Búsqueda
    search = request.GET.get('search', '').strip()
    if search:
        movimientos = movimientos.filter(
            Q(descripcion__icontains=search) | 
            Q(idusuario__nombrecompleto__icontains=search)
        )
        
    # Filtro Tipo (Ingreso / Egreso / Todos)
    tipo = request.GET.get('tipo', 'todos')
    if tipo in ['ingreso', 'egreso']:
        movimientos = movimientos.filter(tipo_movimiento=tipo)
        
    # Paginación
    try:
        page = int(request.GET.get('page', 1))
    except ValueError:
        page = 1
        
    per_page = 10
    total_records = movimientos.count()
    total_pages = (total_records + per_page - 1) // per_page
    
    start = (page - 1) * per_page
    end = start + per_page
    mov_page = movimientos[start:end]
    
    data = []
    for mov in mov_page:
        comprobante_url = f"/ventas/imprimir/{mov.idventa.idventa}/" if mov.idventa else None
        comprobante_numero = mov.idventa.numero_comprobante if mov.idventa else None
        
        # Obtener fecha formateada
        if timezone.is_aware(mov.fecha_movimiento):
            fecha_format = timezone.localtime(mov.fecha_movimiento).strftime("%d/%m/%Y %H:%M")
        else:
            fecha_format = mov.fecha_movimiento.strftime("%d/%m/%Y %H:%M")
            
        data.append({
            'id': mov.id_movimiento_caja,
            'fecha_movimiento': fecha_format,
            'tipo_movimiento': mov.tipo_movimiento,
            'descripcion': mov.descripcion,
            'usuario': mov.idusuario.nombrecompleto if mov.idusuario else '',
            'monto': float(mov.monto),
            'comprobante_url': comprobante_url,
            'comprobante_numero': comprobante_numero
        })
        
    return JsonResponse({
        'data': data,
        'total_pages': total_pages,
        'current_page': page
    })



def buscar_compra_por_numero(request):
    """
    Busca una compra por su número de comprobante y retorna sus detalles en JSON.
    """
    numero = request.GET.get('numero', '').strip()
    if not numero:
        return JsonResponse({'ok': False, 'error': 'Debe ingresar un número de comprobante.'}, status=400)

    try:
        compra = Compras.objects.select_related('idproveedor').get(numcorrelativo=numero)
    except Compras.DoesNotExist:
        return JsonResponse({'ok': False, 'error': f'No se encontró ninguna compra con el comprobante "{numero}".'}, status=404)
    except Compras.MultipleObjectsReturned:
        return JsonResponse({'ok': False, 'error': f'Existe más de una compra con el comprobante "{numero}". Contacte al administrador.'}, status=400)

    # Obtener detalles de la compra con relaciones pre-cargadas
    detalles_qs = CompraDetalle.objects.filter(idcompra=compra).select_related(
        'id_repuesto_comprado__id_repuesto', 
        'id_vehiculo__idproducto'
    )

    items = []
    for det in detalles_qs:
        descripcion = 'Sin descripción'
        if det.id_repuesto_comprado:
            repuesto_comprado = det.id_repuesto_comprado
            # Intentar obtener el nombre del catálogo de repuestos
            if hasattr(repuesto_comprado, 'id_repuesto') and repuesto_comprado.id_repuesto:
                descripcion = repuesto_comprado.id_repuesto.nombre
            # Si no, usar su propio campo descripción
            elif hasattr(repuesto_comprado, 'descripcion') and repuesto_comprado.descripcion:
                descripcion = repuesto_comprado.descripcion
            else:
                descripcion = str(repuesto_comprado)
        elif det.id_vehiculo:
            vehiculo = det.id_vehiculo
            # Obtener el nombre del producto asociado al vehículo
            if hasattr(vehiculo, 'idproducto') and vehiculo.idproducto:
                descripcion = vehiculo.idproducto.nomproducto
            else:
                descripcion = str(vehiculo)

        items.append({
            'descripcion': descripcion,
            'cantidad': det.cantidad,
            'precio_compra': float(det.precio_compra),
            'precio_venta': float(det.precio_maximo),
            'subtotal': float(det.subtotal),
        })

    proveedor_nombre = str(compra.idproveedor) if compra.idproveedor else 'Sin proveedor'

    return JsonResponse({
        'ok': True,
        'idcompra': compra.idcompra,
        'numcorrelativo': compra.numcorrelativo,
        'proveedor': proveedor_nombre,
        'fecha_compra': compra.fechacompra.strftime('%d/%m/%Y') if compra.fechacompra else '---',
        'total': float(compra.total_compra),
        'items': items,
    })


def registrar_egreso(request):
    if request.method != 'POST':
        return redirect('movimientos_caja')
    
    try:
        idusuario = request.session.get('idusuario')
        
        # Verificar caja abierta
        apertura_actual = AperturaCierreCaja.objects.filter(
            idusuario_id=idusuario,
            estado__in=['abierta', 'reabierta']
        ).first()
        
        if not apertura_actual:
            return JsonResponse({
                'ok': False,
                'error': 'No tiene una caja abierta. Debe aperturar una caja primero.',
                'necesita_aperturar': True
            }, status=400)
        
        # Obtener datos del formulario
        monto_str = (request.POST.get('monto') or '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        idcompra_str = (request.POST.get('idcompra') or '').strip()

        # Parseo seguro del monto
        if not monto_str:
            return JsonResponse({
                'ok': False,
                'error': 'El monto es obligatorio'
            }, status=400)
        try:
            monto = Decimal(monto_str)
        except Exception:
            return JsonResponse({
                'ok': False,
                'error': 'El monto debe ser un número válido'
            }, status=400)
        
        # Validaciones
        if monto <= 0:
            return JsonResponse({
                'ok': False,
                'error': 'El monto debe ser mayor a cero'
            }, status=400)
        
        if not descripcion:
            return JsonResponse({
                'ok': False,
                'error': 'Debe ingresar una descripción del egreso'
            }, status=400)

        # Validación server-side: saldo disponible real
        movimientos_apertura = MovimientoCaja.objects.filter(
            id_movimiento=apertura_actual,
            estado=1
        )

        total_ingresos = movimientos_apertura.filter(
            tipo_movimiento='ingreso'
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

        total_egresos = movimientos_apertura.filter(
            tipo_movimiento='egreso'
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

        saldo_disponible = (apertura_actual.saldo_inicial or Decimal('0.00')) + total_ingresos - total_egresos

        if monto > saldo_disponible:
            return JsonResponse({
                'ok': False,
                'error': f'El monto del egreso no puede ser mayor al saldo disponible (S/ {saldo_disponible:.2f})',
                'saldo_disponible': str(saldo_disponible)
            }, status=400)
        
        # Validar y asociar compra si se proporcionó
        compra_obj = None
        if idcompra_str:
            try:
                compra_obj = Compras.objects.get(idcompra=int(idcompra_str))
                total_compra = Decimal(str(compra_obj.total_compra))
                if monto != total_compra:
                    return JsonResponse({
                        'ok': False,
                        'error': f'El monto del egreso (S/ {monto:.2f}) debe ser igual al total de la compra (S/ {total_compra:.2f}).'
                    }, status=400)
            except (Compras.DoesNotExist, ValueError):
                return JsonResponse({
                    'ok': False,
                    'error': 'La compra seleccionada no existe. Busque nuevamente el comprobante.'
                }, status=400)

        # ✅ Crear movimiento de egreso CON id_apertura
        movimiento = MovimientoCaja.objects.create(
            id_caja=apertura_actual.id_caja,
            id_movimiento=apertura_actual,
            idusuario_id=idusuario,
            tipo_movimiento='egreso',
            monto=monto,
            descripcion=descripcion,
            idcompra=compra_obj,
            estado=1
        )
        
        print(f"✅ Egreso registrado: S/ {monto} - {descripcion}")
        print(f"   Asociado a apertura: {apertura_actual.id_movimiento}")
        
        return JsonResponse({
            'ok': True,
            'message': 'Egreso registrado correctamente',
            'id_movimiento': movimiento.id_movimiento_caja
        })
    
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'ok': False,
            'error': f'Error al registrar egreso: {str(e)}'
        }, status=500)


def reporte_caja(request):
    """
    Generar reporte de caja (filtrado por fechas)
    """
    id_tipo_usuario = request.session.get('idtipousuario')
    idusuario = request.session.get('idusuario')
    
    if not id_tipo_usuario or not idusuario:
        return HttpResponse("<h1>No tiene acceso</h1>")
    
    # Obtener filtros
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    # Base query
    movimientos = MovimientoCaja.objects.all().select_related(
        'id_caja', 'idusuario', 'idventa'
    )
    
    # Aplicar filtros
    if fecha_inicio:
        movimientos = movimientos.filter(fecha_movimiento__gte=fecha_inicio)
    
    if fecha_fin:
        movimientos = movimientos.filter(fecha_movimiento__lte=fecha_fin)
    
    # Si no es admin, solo sus movimientos
    es_admin = id_tipo_usuario == 1
    if not es_admin:
        movimientos = movimientos.filter(idusuario_id=idusuario)
    
    # Calcular totales
    total_ingresos = movimientos.filter(
        tipo_movimiento='ingreso'
    ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
    
    total_egresos = movimientos.filter(
        tipo_movimiento='egreso'
    ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
    
    saldo = total_ingresos - total_egresos
    
    data = {
        'movimientos': movimientos.order_by('-fecha_movimiento'),
        'total_ingresos': total_ingresos,
        'total_egresos': total_egresos,
        'saldo': saldo,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
    }
    
    return render(request, 'movimientos_caja/reporte.html', data)