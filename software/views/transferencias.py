import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from software.models.transferenciaModel import Transferencia
from software.models.detalleTransferenciaModel import DetalleTransferencia
from software.models.stockModel import Stock
from software.models.almacenesModel import Almacenes
from software.models.VehiculosModel import Vehiculo
from software.models.RespuestoCompModel import RepuestoComp
from software.models.transporteVehiculoModel import TransporteVehiculo
from software.models.transporteConductorModel import TransporteConductor
from software.models.logisticaTransferenciaModel import LogisticaTransferencia
from software.models.empresaModel import Empresa
from software.utils.guia_remision_service import generar_guia_pdf
from django.http import FileResponse, HttpResponse
from io import BytesIO

def transferencias(request):
    """
    Vista principal de transferencias.
    Ahora carga vacía para Server-Side Processing.
    """
    almacenes = Almacenes.objects.filter(estado=1)
    almacenes_principal = Almacenes.objects.filter(estado=1, id_sucursal__es_principal=True)

    # Datos para logística
    vehiculos_transporte = TransporteVehiculo.objects.filter(estado='disponible')
    conductores = TransporteConductor.objects.filter(estado='disponible')

    context = {
        'transferencias': [], # Ya no pasamos todo para evitar colapsar la página
        'almacenes': almacenes,
        'almacenes_principal': almacenes_principal,
        'vehiculos_transporte': vehiculos_transporte,
        'conductores': conductores,
        'es_admin': request.session.get('idtipousuario') == 1,
        'puede_gestionar_transferencias': request.session.get('idtipousuario') in [1, 5],
        'stats': {
            'pendientes': Transferencia.objects.filter(estado='pendiente').count(),
            'en_transito': Transferencia.objects.filter(estado='en_transito').count(),
            'recibidas': Transferencia.objects.filter(estado__in=['recibido', 'en_retorno', 'completada']).count(),
        }
    }
    return render(request, 'transferencias/transferencias.html', context)

from django.core.paginator import Paginator

def api_listar_transferencias(request):
    try:
        page = int(request.GET.get('page', 1))
        fecha_desde = request.GET.get('fecha_desde', '')
        fecha_hasta = request.GET.get('fecha_hasta', '')
        estado = request.GET.get('estado', '')
        almacen = request.GET.get('almacen', '')
        solicitante = request.GET.get('solicitante', '')
        search_value = request.GET.get('search_value', '').strip()

        queryset = Transferencia.objects.select_related(
            'id_almacen_origen__id_sucursal',
            'id_almacen_destino__id_sucursal',
            'idusuario_solicita'
        )

        if fecha_desde:
            queryset = queryset.filter(fecha_transferencia__gte=fecha_desde)
        if fecha_hasta:
            queryset = queryset.filter(fecha_transferencia__lte=fecha_hasta)
        # Create a base queryset without 'estado' filter for the stats cards
        base_qs = Transferencia.objects.all()
        if fecha_desde: base_qs = base_qs.filter(fecha_transferencia__gte=fecha_desde)
        if fecha_hasta: base_qs = base_qs.filter(fecha_transferencia__lte=fecha_hasta)
        if almacen: base_qs = base_qs.filter(Q(id_almacen_origen_id=almacen) | Q(id_almacen_destino_id=almacen))
        if solicitante: base_qs = base_qs.filter(idusuario_solicita__nombrecompleto__icontains=solicitante)
        if search_value:
            base_qs = base_qs.filter(
                Q(numero_guia__icontains=search_value) |
                Q(id_almacen_origen__nombre_almacen__icontains=search_value) |
                Q(id_almacen_destino__nombre_almacen__icontains=search_value) |
                Q(lugar_destino__icontains=search_value)
            )

        if estado:
            queryset = queryset.filter(estado=estado)
        if almacen:
            queryset = queryset.filter(Q(id_almacen_origen_id=almacen) | Q(id_almacen_destino_id=almacen))
        if solicitante:
            queryset = queryset.filter(idusuario_solicita__nombrecompleto__icontains=solicitante)
        if search_value:
            queryset = queryset.filter(
                Q(numero_guia__icontains=search_value) |
                Q(id_almacen_origen__nombre_almacen__icontains=search_value) |
                Q(id_almacen_destino__nombre_almacen__icontains=search_value) |
                Q(lugar_destino__icontains=search_value)
            )

        queryset = queryset.order_by('-id_transferencia')

        paginator = Paginator(queryset, 10)
        page_obj = paginator.get_page(page)

        data = []
        es_admin = request.session.get('idtipousuario') == 1
        puede_gestionar_transferencias = request.session.get('idtipousuario') in [1, 5]
        id_almacen_session = request.session.get('id_almacen')
        
        # Calculate continuous index across pages
        start_index = (page_obj.number - 1) * paginator.per_page + 1

        for idx, trans in enumerate(page_obj.object_list):
            almacen_origen_nom = trans.id_almacen_origen.nombre_almacen if trans.id_almacen_origen else '---'
            almacen_destino_nom = trans.id_almacen_destino.nombre_almacen if trans.id_almacen_destino else '---'
            
            es_almacen_destino = str(trans.id_almacen_destino_id) == str(id_almacen_session) if id_almacen_session else False
            es_almacen_origen = str(trans.id_almacen_origen_id) == str(id_almacen_session) if id_almacen_session else False

            data.append({
                'index': start_index + idx,
                'id_transferencia': trans.id_transferencia,
                'fecha': trans.fecha_transferencia.strftime('%d/%m/%Y') if trans.fecha_transferencia else '',
                'tipo_transferencia': trans.tipo_transferencia,
                'origen': almacen_origen_nom,
                'destino': almacen_destino_nom,
                'solicitante': trans.idusuario_solicita.nombrecompleto if trans.idusuario_solicita else '',
                'numero_guia': trans.numero_guia or '---',
                'estado': trans.estado,
                'es_admin': es_admin,
                'puede_gestionar_transferencias': puede_gestionar_transferencias,
                'es_almacen_destino': es_almacen_destino,
                'es_almacen_origen': es_almacen_origen
            })

        stats = {
            'pendientes': base_qs.filter(estado='pendiente').count(),
            'en_transito': base_qs.filter(estado='en_transito').count(),
            'recibidas': base_qs.filter(estado__in=['recibido', 'en_retorno', 'completada']).count(),
            'total_registros': paginator.count
        }

        return JsonResponse({
            'ok': True,
            'transferencias': data,
            'stats': stats,
            'pagination': {
                'current_page': page_obj.number,
                'num_pages': paginator.num_pages,
                'has_previous': page_obj.has_previous(),
                'has_next': page_obj.has_next(),
                'previous_page_number': page_obj.previous_page_number() if page_obj.has_previous() else None,
                'next_page_number': page_obj.next_page_number() if page_obj.has_next() else None,
                'start_index': page_obj.start_index() if paginator.count > 0 else 0,
                'end_index': page_obj.end_index() if paginator.count > 0 else 0,
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'ok': False, 'error': str(e)})

def render_modal_detalle_transferencia(request, id):
    trans = get_object_or_404(
        Transferencia.objects.prefetch_related(
            'detalles__id_vehiculo__idproducto', 
            'detalles__id_repuesto_comprado__id_repuesto',
            'logisticas__id_transporte_vehiculo',
            'logisticas__id_transporte_conductor'
        ).select_related(
            'id_almacen_origen__id_sucursal', 
            'id_almacen_destino__id_sucursal'
        ),
        id_transferencia=id
    )
    # Pasar al template un contexto con 'trans'
    return render(request, 'transferencias/modal_detalle_content.html', {'trans': trans})

def obtener_stock_almacen(request):
    """
    API para obtener stock disponible de un almacén
    """
    id_almacen = request.GET.get('id_almacen')
    if not id_almacen:
        return JsonResponse({'error': 'ID de almacén requerido'}, status=400)
    
    try:
        stocks = Stock.objects.filter(
            id_almacen_id=id_almacen, estado=1, cantidad_disponible__gt=0
        ).filter(
            Q(id_vehiculo__isnull=False, id_vehiculo__estado=1, id_vehiculo__idproducto__estado=1) |
            Q(id_repuesto_comprado__isnull=False, id_repuesto_comprado__estado=1, id_repuesto_comprado__id_repuesto__estado=1)
        ).select_related(
            'id_vehiculo', 
            'id_vehiculo__idproducto', 
            'id_repuesto_comprado', 
            'id_repuesto_comprado__id_repuesto'
        )
        vehiculos_stock = []
        repuestos_stock = []
        
        for stock in stocks:
            if stock.id_vehiculo:
                vehiculos_stock.append({
                    'id_vehiculo': stock.id_vehiculo.id_vehiculo,
                    'nombre': stock.id_vehiculo.idproducto.nomproducto,
                    'serie_motor': stock.id_vehiculo.serie_motor,
                    'serie_chasis': stock.id_vehiculo.serie_chasis,
                    'cantidad_disponible': stock.cantidad_disponible,
                })
            elif stock.id_repuesto_comprado:
                repuestos_stock.append({
                    'id_repuesto_comprado': stock.id_repuesto_comprado.id_repuesto_comprado,
                    'nombre': stock.id_repuesto_comprado.id_repuesto.nombre,
                    'codigo_barras': stock.id_repuesto_comprado.id_repuesto.codigo_barras or 'S/N',
                    'cantidad_disponible': stock.cantidad_disponible,
                })
        
        return JsonResponse({
            'vehiculos': vehiculos_stock,
            'repuestos': repuestos_stock,
        })
        
    except Almacenes.DoesNotExist:
        return JsonResponse({'error': 'Almacén no encontrado'}, status=404)
    except Exception as e:
        print(f"Error: {str(e)}")
        return JsonResponse({'error': 'Error al obtener stock'}, status=500)


def obtener_detalle_transferencia(request, id):
    """
    API para obtener los productos de una transferencia específica.
    select_related evita lazy loads dentro del bucle → pasa de N*2 queries a 1.
    """
    try:
        transferencia = get_object_or_404(
            Transferencia.objects.select_related('id_almacen_origen'),
            id_transferencia=id,
        )
        # Una sola query con todos los relacionados necesarios en el bucle
        detalles = (
            transferencia.detalles
            .filter(estado=1)
            .select_related(
                'id_vehiculo__idproducto',
                'id_repuesto_comprado__id_repuesto',
            )
        )
        items = []

        for d in detalles:
            item = {
                'tipo': 'vehiculo' if d.id_vehiculo else 'repuesto',
                'id': d.id_vehiculo.id_vehiculo if d.id_vehiculo else d.id_repuesto_comprado.id_repuesto_comprado,
                'nombre': d.id_vehiculo.idproducto.nomproducto if d.id_vehiculo else d.id_repuesto_comprado.id_repuesto.nombre,
                'detalle': f"Motor: {d.id_vehiculo.serie_motor}" if d.id_vehiculo else f"Código: {d.id_repuesto_comprado.id_repuesto.codigo_barras}",
                'cantidad': d.cantidad
            }
            items.append(item)

        return JsonResponse({
            'ok': True,
            'id_almacen_origen': transferencia.id_almacen_origen.id_almacen if transferencia.id_almacen_origen else None,
            'lugar_exhibicion': transferencia.lugar_destino,
            'direccion_exhibicion': transferencia.direccion_destino,
            'items': items
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


def nueva_transferencia(request):
    """
    Crear nueva transferencia
    """
    if request.method != 'POST':
        return redirect('transferencias')
    
    try:
        with transaction.atomic():
            # Obtener datos del formulario
            id_origen_raw = request.POST.get('id_almacen_origen')
            id_destino_raw = request.POST.get('id_almacen_destino')
            tipo_transf = request.POST.get('tipo_transferencia')
            
            # El origen solo es obligatorio si NO es retorno de exhibición
            if not id_origen_raw and tipo_transf != 'exhibicion_a_sucursal':
                return JsonResponse({'ok': False, 'error': 'Debe seleccionar el almacén de origen.'}, status=400)
            
            # El destino solo es obligatorio si NO es salida a exhibición
            if not id_destino_raw and tipo_transf != 'sucursal_a_exhibicion':
                return JsonResponse({'ok': False, 'error': 'Debe seleccionar un almacén de destino.'}, status=400)

            id_almacen_origen = int(id_origen_raw) if id_origen_raw else None
            id_almacen_destino = int(id_destino_raw) if id_destino_raw else None
            fecha_transferencia = request.POST.get('fecha_transferencia')
            numero_guia = request.POST.get('numero_guia', '').strip()
            observaciones = request.POST.get('observaciones', '').strip()
            lugar_destino = request.POST.get('lugar_destino', '').strip()
            direccion_destino = request.POST.get('direccion_destino', '').strip()
            lugar_origen = request.POST.get('lugar_origen', '').strip()
            direccion_origen = request.POST.get('direccion_origen', '').strip()
            idusuario = request.session.get('idusuario')
            
            # Validaciones
            if id_almacen_destino and id_almacen_origen == id_almacen_destino:
                return JsonResponse({
                    'ok': False,
                    'error': 'El almacén origen y destino no pueden ser iguales'
                }, status=400)
            
            # Crear transferencia
            transferencia = Transferencia.objects.create(
                id_almacen_origen_id=id_almacen_origen,
                id_almacen_destino_id=id_almacen_destino,
                idusuario_solicita_id=idusuario,
                fecha_transferencia=fecha_transferencia,
                numero_guia=numero_guia,
                observaciones=observaciones,
                tipo_transferencia=tipo_transf,
                lugar_destino=lugar_destino,
                direccion_destino=direccion_destino,
                lugar_origen=lugar_origen,
                direccion_origen=direccion_origen,
                estado='pendiente'
            )
            
            # Procesar items
            items_count = int(request.POST.get('items_count', 0))
            if items_count == 0:
                raise ValueError("Debe agregar al menos un producto a la transferencia")
            
            # Construir los objetos en memoria y hacer un solo bulk_create
            # en lugar de N INSERT individuales (1 query en lugar de N)
            nuevos_detalles = []
            for i in range(1, items_count + 1):
                tipo_item = request.POST.get(f'tipo_item_{i}')
                if not tipo_item:
                    continue
                cantidad = int(request.POST.get(f'cantidad_{i}', 1))
                if tipo_item == 'vehiculo':
                    # Un vehículo es una unidad única (serie motor/chasis).
                    # Forzamos cantidad=1 también en backend para evitar
                    # que se salte la restricción del frontend.
                    nuevos_detalles.append(DetalleTransferencia(
                        id_transferencia=transferencia,
                        id_vehiculo_id=request.POST.get(f'id_vehiculo_{i}'),
                        cantidad=1,
                        estado=1,
                    ))
                elif tipo_item == 'repuesto':
                    nuevos_detalles.append(DetalleTransferencia(
                        id_transferencia=transferencia,
                        id_repuesto_comprado_id=request.POST.get(f'id_repuesto_{i}'),
                        cantidad=cantidad,
                        estado=1,
                    ))

            # 1 INSERT en lugar de N INSERT individuales
            DetalleTransferencia.objects.bulk_create(nuevos_detalles)

            return JsonResponse({'ok': True, 'message': 'Transferencia registrada exitosamente'})
            
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


def _construir_stock_map(detalles, almacen_origen):
    """
    Pre-carga todos los registros de Stock relevantes en UNA sola query
    y los devuelve como dict keyed por (id_vehiculo_id, id_repuesto_comprado_id).

    Elimina el patrón N+1: en vez de 1 query por ítem dentro del bucle,
    se lanza 1 única query con OR para todos los ítems a la vez.
    """
    if not detalles:
        return {}

    filtro_combinado = Q()
    for detalle in detalles:
        if detalle.id_vehiculo_id:
            filtro_combinado |= Q(id_almacen=almacen_origen, id_vehiculo_id=detalle.id_vehiculo_id)
        else:
            filtro_combinado |= Q(id_almacen=almacen_origen, id_repuesto_comprado_id=detalle.id_repuesto_comprado_id)

    # Una única query a la base de datos
    stocks = Stock.objects.filter(filtro_combinado).order_by('id_stock')

    # order_by('id_stock') garantiza que ante duplicados heredados se use el más antiguo
    stock_map = {}
    for s in stocks:
        key = (s.id_vehiculo_id, s.id_repuesto_comprado_id)
        if key not in stock_map:
            stock_map[key] = s

    return stock_map


def registrar_salida_transferencia(request, id):
    """
    Registra la salida física de la mercancía (Descuenta stock origen).

    Optimizaciones N+1 aplicadas:
    - select_related en la transferencia y en los detalles.
    - _construir_stock_map() trae todos los stocks en 1 query (no N).
    - bulk_update() actualiza todos los stocks en 1 query (no N saves).
    """
    if request.method != 'POST':
        return redirect('transferencias')

    transferencia = get_object_or_404(
        Transferencia.objects.select_related('id_almacen_origen', 'id_almacen_destino'),
        id_transferencia=id,
    )
    id_vehiculo_trans = request.POST.get('id_transporte_vehiculo')
    id_conductor = request.POST.get('id_transporte_conductor')

    # ── Validaciones previas (fuera de la transacción para devolver 400 limpio) ──
    if not id_vehiculo_trans or not id_conductor:
        return JsonResponse(
            {'ok': False, 'error': 'Debe seleccionar un vehículo de transporte y un conductor.'},
            status=400,
        )

    if transferencia.estado != 'pendiente':
        return JsonResponse(
            {'ok': False, 'error': f'La transferencia ya está en estado "{transferencia.estado}" y no puede procesarse.'},
            status=400,
        )

    # Una sola query con select_related para evitar lazy loads en el bucle
    detalles = list(
        transferencia.detalles
        .filter(estado=1)
        .select_related('id_vehiculo__idproducto', 'id_repuesto_comprado__id_repuesto')
    )
    if not detalles:
        return JsonResponse(
            {'ok': False, 'error': 'La transferencia no tiene productos activos.'},
            status=400,
        )

    # Pre-cargar todos los stocks de una vez (1 query, no N)
    stock_map = _construir_stock_map(detalles, transferencia.id_almacen_origen)

    # ── Validación de stock (0 queries extra — todo en memoria) ──
    errores_stock = []
    for detalle in detalles:
        key = (detalle.id_vehiculo_id, detalle.id_repuesto_comprado_id)
        nombre_item = str(detalle.id_vehiculo or detalle.id_repuesto_comprado)
        stock_orig = stock_map.get(key)

        if stock_orig is None:
            errores_stock.append(f"{nombre_item}: no tiene registro de stock en el almacén de origen.")
        elif stock_orig.cantidad_disponible < detalle.cantidad:
            errores_stock.append(
                f"{nombre_item}: stock disponible ({stock_orig.cantidad_disponible}) "
                f"es menor que la cantidad requerida ({detalle.cantidad}). "
                f"Es posible que este ítem ya haya sido vendido."
            )

    if errores_stock:
        return JsonResponse(
            {'ok': False, 'error': 'No se puede registrar la salida:\n' + '\n'.join(errores_stock)},
            status=400,
        )

    try:
        with transaction.atomic():
            # 1. Validar disponibilidad de vehículo y conductor
            trans_vehiculo = get_object_or_404(TransporteVehiculo, id_transporte_vehiculo=id_vehiculo_trans)
            conductor = get_object_or_404(TransporteConductor, id_transporte_conductor=id_conductor)

            if trans_vehiculo.estado != 'disponible' or conductor.estado != 'disponible':
                return JsonResponse(
                    {'ok': False, 'error': 'El vehículo de transporte o el conductor ya no están disponibles.'},
                    status=400,
                )

            # 2. Descontar Stock del ORIGEN
            # Modificar los objetos ya cargados en memoria (0 queries extra)
            stocks_a_actualizar = []
            for detalle in detalles:
                key = (detalle.id_vehiculo_id, detalle.id_repuesto_comprado_id)
                stock_orig = stock_map[key]
                stock_orig.cantidad_disponible -= detalle.cantidad
                stocks_a_actualizar.append(stock_orig)

            # Un solo UPDATE para todos los stocks (1 query en lugar de N saves)
            Stock.objects.bulk_update(stocks_a_actualizar, ['cantidad_disponible'])

            # 3. Asignar Logística
            LogisticaTransferencia.objects.create(
                id_transferencia=transferencia,
                id_transporte_vehiculo=trans_vehiculo,
                id_transporte_conductor=conductor,
                fecha_salida=timezone.now(),
                estado_logistica='activo',
            )

            # 4. Actualizar Estados y Asignar Número de Guía si no tiene
            if not transferencia.numero_guia:
                ultima_transferencia = (
                    Transferencia.objects
                    .filter(numero_guia__startswith='G001-')
                    .order_by('-numero_guia')
                    .first()
                )
                if ultima_transferencia:
                    try:
                        ultimo_numero = int(ultima_transferencia.numero_guia.split('-')[1])
                        nuevo_numero = ultimo_numero + 1
                    except (ValueError, IndexError):
                        nuevo_numero = 1
                else:
                    nuevo_numero = 1
                transferencia.numero_guia = f"G001-{str(nuevo_numero).zfill(9)}"

            trans_vehiculo.estado = 'en_uso'
            trans_vehiculo.save()
            conductor.estado = 'en_viaje'
            conductor.save()

            transferencia.estado = 'en_transito'
            transferencia.save()

            return JsonResponse({'ok': True, 'message': 'Salida registrada. Mercancía en tránsito.'})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'ok': False, 'error': f'Error interno al registrar la salida: {str(e)}'}, status=500)


def confirmar_recepcion_transferencia(request, id):
    """
    Confirma que la mercancía llegó al destino (Suma stock destino)
    """
    if request.method != 'POST':
        return redirect('transferencias')
    
    try:
        transferencia = get_object_or_404(
            Transferencia.objects.select_related('id_almacen_origen', 'id_almacen_destino'),
            id_transferencia=id,
        )
        # select_related evita lazy loads al acceder a id_vehiculo / id_repuesto_comprado
        detalles = list(
            transferencia.detalles
            .filter(estado=1)
            .select_related('id_vehiculo', 'id_repuesto_comprado')
        )

        with transaction.atomic():
            # 1. Determinar el almacén de reingreso y el nuevo estado
            almacen_reingreso = None
            nuevo_estado = 'recibido'

            if transferencia.estado == 'en_retorno':
                almacen_reingreso = transferencia.id_almacen_origen
                nuevo_estado = 'completada'
            else:
                almacen_reingreso = transferencia.id_almacen_destino
                if transferencia.tipo_transferencia == 'sucursal_a_sucursal':
                    nuevo_estado = 'completada'

            # 2. Sumar stock al almacén correspondiente
            # get_or_create es necesario por ítem (puede crear registros nuevos),
            # pero se usa bulk_update para los saves finales (1 query en lugar de N).
            if almacen_reingreso and detalles:
                stocks_a_actualizar = []
                for detalle in detalles:
                    if detalle.id_vehiculo_id:
                        filtro_gc = dict(
                            id_almacen=almacen_reingreso,
                            id_vehiculo_id=detalle.id_vehiculo_id,
                            id_repuesto_comprado=None,
                        )
                    else:
                        filtro_gc = dict(
                            id_almacen=almacen_reingreso,
                            id_vehiculo=None,
                            id_repuesto_comprado_id=detalle.id_repuesto_comprado_id,
                        )
                    stock_dest, _ = Stock.objects.get_or_create(
                        **filtro_gc,
                        defaults={'cantidad_disponible': 0, 'estado': 1},
                    )
                    stock_dest.cantidad_disponible += detalle.cantidad
                    stocks_a_actualizar.append(stock_dest)

                # Un solo UPDATE para todos los stocks destino (1 query en lugar de N saves)
                Stock.objects.bulk_update(stocks_a_actualizar, ['cantidad_disponible'])

            # 3. Liberar Vehículo y Conductor
            # select_related elimina los lazy loads al acceder a vehiculo/conductor
            logistica = (
                transferencia.logisticas
                .select_related('id_transporte_vehiculo', 'id_transporte_conductor')
                .filter(estado_logistica='activo')
                .first()
            )
            if logistica:
                vehiculo = logistica.id_transporte_vehiculo
                vehiculo.estado = 'disponible'
                vehiculo.save()

                conductor = logistica.id_transporte_conductor
                conductor.estado = 'disponible'
                conductor.save()

                logistica.estado_logistica = 'completado'
                logistica.save()

            # 4. Finalizar transferencia
            idusuario = request.session.get('idusuario')
            transferencia.estado = nuevo_estado
            transferencia.idusuario_confirma_id = idusuario
            transferencia.fecha_confirmacion = timezone.now()
            transferencia.save()

            msg = 'Recepción confirmada.' if nuevo_estado == 'recibido' else 'Retorno finalizado. Stock reingresado al almacén de origen.'
            return JsonResponse({'ok': True, 'message': msg})

    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


def rechazar_transferencia(request, id):
    """
    Rechazar una transferencia
    """
    if request.method != 'POST':
        return redirect('transferencias')
    
    try:
        transferencia = get_object_or_404(Transferencia, id_transferencia=id)
        if transferencia.estado != 'pendiente':
            return JsonResponse({'ok': False, 'error': 'Solo se pueden rechazar transferencias pendientes'}, status=400)
        
        transferencia.estado = 'rechazada'
        transferencia.save()
        return JsonResponse({'ok': True, 'message': 'Transferencia rechazada'})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

@csrf_exempt
def iniciar_retorno_transferencia(request, id):
    """
    Cambia el estado de una transferencia de exhibición a 'en_retorno'
    para indicar que el vehículo viene de regreso al almacén.
    """
    if request.method == 'POST':
        try:
            transferencia = get_object_or_404(Transferencia, id_transferencia=id)
            
            if transferencia.tipo_transferencia != 'sucursal_a_exhibicion':
                return JsonResponse({'ok': False, 'error': 'Solo se pueden retornar transferencias de exhibición.'}, status=400)
            
            if transferencia.estado != 'recibido':
                return JsonResponse({'ok': False, 'error': 'La transferencia debe estar en estado Recibido en Feria para retornar.'}, status=400)
            
            # Cambiar estado de la transferencia
            transferencia.estado = 'en_retorno'
            transferencia.save()
            
            # Re-activar Logística (Vehículo y Conductor originales)
            with transaction.atomic():
                # select_related elimina los lazy loads de vehiculo y conductor
                logistica = (
                    transferencia.logisticas
                    .select_related('id_transporte_vehiculo', 'id_transporte_conductor')
                    .filter(estado_logistica='completado')
                    .first()
                )
                if logistica:
                    vehiculo = logistica.id_transporte_vehiculo
                    vehiculo.estado = 'en_uso'
                    vehiculo.save()

                    conductor = logistica.id_transporte_conductor
                    conductor.estado = 'en_viaje'
                    conductor.save()

                    logistica.estado_logistica = 'activo'
                    logistica.save()
            
            return JsonResponse({
                'ok': True,
                'message': 'Iniciando retorno. El conductor y vehículo originales han sido re-asignados automáticamente.'
            })
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)}, status=500)
    return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)


def descargar_guia_pdf(request, id):
    """
    Genera y descarga el PDF de la Guía de Remisión
    """
    try:
        transferencia = get_object_or_404(
            Transferencia.objects.select_related('id_almacen_origen', 'id_almacen_destino'),
            id_transferencia=id,
        )
        # select_related en logística y detalles para evitar lazy loads en generar_guia_pdf
        logistica = (
            transferencia.logisticas
            .select_related('id_transporte_vehiculo', 'id_transporte_conductor')
            .order_by('-fecha_asignacion')
            .first()
        )
        detalles = (
            transferencia.detalles
            .filter(estado=1)
            .select_related('id_vehiculo__idproducto', 'id_repuesto_comprado__id_repuesto')
        )

        empresa = Empresa.objects.filter(activo=True).first()
        if not empresa:
            return HttpResponse("Error: No se encontró información de la empresa configurada.", status=404)

        pdf_content = generar_guia_pdf(transferencia, logistica, detalles, empresa)
        
        filename = f"Guia_Remision_{transferencia.numero_guia or transferencia.id_transferencia}.pdf"
        
        response = FileResponse(
            BytesIO(pdf_content),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response
    except Exception as e:
        return HttpResponse(f"Error al generar PDF: {str(e)}", status=500)


def buscar_vehiculos_transporte(request):
    """
    API para búsqueda de vehículos de transporte para autocomplete
    """
    term = request.GET.get('term', '')
    vehiculos = TransporteVehiculo.objects.filter(
        Q(placa__icontains=term) | Q(marca__icontains=term) | Q(modelo__icontains=term),
        estado='disponible'
    )[:10]
    
    results = []
    for v in vehiculos:
        results.append({
            'id': v.id_transporte_vehiculo,
            'text': f"{v.placa} - {v.marca} {v.modelo} ({v.get_tipo_display()})"
        })
    return JsonResponse(results, safe=False)


def buscar_conductores_transporte(request):
    """
    API para búsqueda de conductores para autocomplete
    """
    term = request.GET.get('term', '')
    conductores = TransporteConductor.objects.filter(
        Q(nombre_completo__icontains=term) | Q(dni__icontains=term),
        estado='disponible'
    )[:10]
    
    results = []
    for c in conductores:
        results.append({
            'id': c.id_transporte_conductor,
            'text': f"{c.nombre_completo} (DNI: {c.dni})"
        })
    return JsonResponse(results, safe=False)