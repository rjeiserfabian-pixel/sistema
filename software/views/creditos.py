from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse, FileResponse
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta
from decimal import Decimal
from io import BytesIO
import json

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY

from software.models.CreditoModel import Credito
from software.models.VentasModel import Ventas
from software.models.CuotasVentaModel import CuotasVenta
from software.models.PagoCuotaModel import PagoCuota
from software.models.AuditoriaVentasModel import AuditoriaVentas
from software.models.VentaDetalleModel import VentaDetalle

from software.models.ClienteModel import Cliente
from software.models.UsuarioModel import Usuario
from software.models.TipoPagoModel import TipoPago
from software.models.CanalPagoModel import CanalPago
from software.decorators import requiere_caja_aperturada
from software.models.movimientoCajaModel import MovimientoCaja
from software.models.AperturaCierreCajaModel import AperturaCierreCaja
from software.models.VehiculosModel import Vehiculo
from software.models.RespuestoCompModel import RepuestoComp
from software.models.stockModel import Stock
from software.models.sucursalesModel import Sucursales
from software.models.almacenesModel import Almacenes
from software.utils.logo_utils import get_logo_image_for_pdf
from software.utils.credito_cuotas import (
    obtener_estados_bloqueo,
    validar_pago_secuencial,
    validar_seleccion_multiple,
)
from software.models.SeriecomprobanteModel import Seriecomprobante
from software.models.TipocomprobanteModel import Tipocomprobante
from software.models.RegionModel import Region
from software.models.ProvinciaModel import Provincia
from software.models.DistritoModel import Distrito


def creditos(request):
    """
    Vista principal del módulo de créditos
    Muestra el listado de todos los créditos con filtros
    """
    # Validación de sesión
    id_tipo_usuario = request.session.get('idtipousuario')
    if not id_tipo_usuario:
        return redirect('login')
    
    # Obtener parámetros de filtro
    estado_filtro = request.GET.get('estado', 'todos')
    busqueda = request.GET.get('busqueda', '').strip()
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')
    producto = request.GET.get('producto', '').strip()
    
    # Fechas por defecto (Primer día del mes y Hoy)
    if not fecha_desde or not fecha_hasta:
        hoy = timezone.now().date()
        fecha_desde = hoy.replace(day=1).strftime('%Y-%m-%d')
        fecha_hasta = hoy.strftime('%Y-%m-%d')
    
    # La lógica pesada de actualización de mora, consultas, filtrado, 
    # y estadísticas ha sido movida a api_listar_creditos (Server-Side Processing)
    
    creditos_list = []
    total_creditos = 0
    total_activos = 0
    total_mora = 0
    total_pagados = 0
    monto_total_creditos = 0
    saldo_total_pendiente = 0
    
    # Obtener almacenes y clientes para el modal de crédito directo
    almacenes = Almacenes.objects.filter(estado=1)
    clientes = Cliente.objects.filter(estado=1).order_by('razonsocial')
    id_almacen_session = request.session.get('id_almacen')
    regiones = Region.objects.filter(estado=1)
    
    # Contexto
    data = {
        'creditos': creditos_list,
        'almacenes': almacenes,
        'clientes': clientes,
        'id_almacen_session': id_almacen_session,
        'total_creditos': total_creditos,
        'total_activos': total_activos,
        'total_mora': total_mora,
        'total_pagados': total_pagados,
        'monto_total_creditos': monto_total_creditos,
        'saldo_total_pendiente': saldo_total_pendiente,
        'estado_filtro': estado_filtro,
        'busqueda': busqueda,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'producto': producto,
        'regiones': regiones,
    }
    
    return render(request, 'creditos/creditos.html', data)


def historial_creditos_anulados(request):
    """
    Muestra el historial de créditos anulados (ventas eliminadas)
    y créditos cancelados por el flujo de retención de vehículos.
    """
    id_tipo_usuario = request.session.get('idtipousuario')
    if not id_tipo_usuario:
        return redirect('login')

    creditos_anulados = Credito.objects.filter(
        estado=0
    ).filter(
        Q(estado_credito='anulado') | Q(estado_credito='cancelado')
    ).select_related(
        'idventa__idcliente',
        'idventa__idusuario',
        'idcliente',
        'idusuario',
    ).order_by('-fecha_credito')

    # Precargar auditorías para los créditos que no están cancelados (que están anulados por eliminación de venta)
    idventas = [c.idventa_id for c in creditos_anulados if c.idventa_id and c.estado_credito != 'cancelado']
    auditorias_dict = {}
    if idventas:
        auditorias = AuditoriaVentas.objects.filter(
            idventa__in=idventas, accion='ELIMINACION'
        ).only('idventa', 'motivo', 'fecha_auditoria').order_by('idventa', '-idauditoria_venta')
        # Guardar solo la más reciente por idventa
        for aud in auditorias:
            if aud.idventa not in auditorias_dict:
                auditorias_dict[aud.idventa] = aud

    for credito in creditos_anulados:
        if credito.estado_credito == 'cancelado':
            # Crédito cancelado por retención de vehículo
            credito.motivo_anulacion = 'Crédito cancelado por proceso de retención y recuperación del vehículo.'
            credito.fecha_anulacion = credito.fecha_retencion  # Fecha de retención como referencia
            credito.tipo_baja = 'cancelado'
        else:
            # Crédito anulado por eliminación de venta
            auditoria = auditorias_dict.get(credito.idventa_id)
            credito.motivo_anulacion = auditoria.motivo if auditoria else 'No especificado'
            credito.fecha_anulacion = auditoria.fecha_auditoria if auditoria else None
            credito.tipo_baja = 'anulado'

    data = {
        'creditos': creditos_anulados,
        'titulo': 'Historial de Créditos Anulados / Cancelados'
    }

    return render(request, 'creditos/historial_anulados.html', data)


def obtener_stock_almacen_credito(request):
    """
    Retorna el stock disponible de vehículos y repuestos en un almacén específico.
    Optimizado: sin N+1 queries en el fallback de compradetalle.
    """
    id_almacen = request.GET.get('id_almacen')
    if not id_almacen:
        return JsonResponse({'ok': False, 'error': 'Almacén no especificado'}, status=400)

    almacen = get_object_or_404(Almacenes, pk=id_almacen)
    from software.models.compradetalleModel import CompraDetalle

    # ── 1. VEHÍCULOS — una sola query con select_related profundo ──
    from django.db.models import Q
    productos_stock = {}
    stocks_v = Stock.objects.filter(
        Q(id_vehiculo__id_situacion__nombre_situacion='DISPONIBLE') | Q(id_vehiculo__id_situacion__isnull=True),
        id_almacen=almacen,
        id_vehiculo__isnull=False,
        id_vehiculo__estado=1,
        id_vehiculo__idproducto__estado=1,
        cantidad_disponible__gt=0,
        estado=1,
    ).select_related('id_vehiculo__idproducto', 'idcompradetalle')

    # Recopilar vehículos SIN compradetalle directo para el fallback
    ids_v_sin_detalle = [
        s.id_vehiculo_id for s in stocks_v if not s.idcompradetalle_id
    ]

    # FALLBACK vehiculos: una sola query agrupada
    fallback_v = {}
    if ids_v_sin_detalle:
        for cd in (
            CompraDetalle.objects.filter(id_vehiculo_id__in=ids_v_sin_detalle)
            .order_by('id_vehiculo_id', '-idcompradetalle')
        ):
            if cd.id_vehiculo_id not in fallback_v:
                fallback_v[cd.id_vehiculo_id] = cd

    for s in stocks_v:
        nom = s.id_vehiculo.idproducto.nomproducto
        if nom not in productos_stock:
            productos_stock[nom] = []

        # Resolver precio: directo o fallback
        detalle_compra = s.idcompradetalle or fallback_v.get(s.id_vehiculo_id)

        p_venta_max = float(detalle_compra.precio_maximo) if detalle_compra else 0
        p_venta_min = float(detalle_compra.precio_minimo) if detalle_compra else 0
        p_compra    = float(detalle_compra.precio_compra)  if detalle_compra else 0

        productos_stock[nom].append({
            'id_vehiculo':     s.id_vehiculo.id_vehiculo,
            'serie_motor':     s.id_vehiculo.serie_motor,
            'serie_chasis':    s.id_vehiculo.serie_chasis,
            'precio_venta':    p_venta_max,  # Usamos el máximo como referencia de venta
            'precio_maximo':   p_venta_max,
            'precio_minimo':   p_venta_min,
            'precio_compra':   p_compra,
            'stock_disponible': s.cantidad_disponible,
        })

    # ── 2. REPUESTOS — una sola query con select_related profundo ──
    repuestos_stock = {}
    stocks_r = Stock.objects.filter(
        id_almacen=almacen,
        id_repuesto_comprado__isnull=False,
        id_repuesto_comprado__estado=1,
        id_repuesto_comprado__id_repuesto__estado=1,
        cantidad_disponible__gt=0,
        estado=1,
    ).select_related('id_repuesto_comprado__id_repuesto', 'idcompradetalle')

    # Recopilar repuestos SIN compradetalle directo para el fallback
    ids_r_sin_detalle = [
        s.id_repuesto_comprado_id for s in stocks_r if not s.idcompradetalle_id
    ]

    # FALLBACK repuestos: una sola query agrupada
    fallback_r = {}
    if ids_r_sin_detalle:
        for cd in (
            CompraDetalle.objects.filter(id_repuesto_comprado_id__in=ids_r_sin_detalle)
            .order_by('id_repuesto_comprado_id', '-idcompradetalle')
        ):
            if cd.id_repuesto_comprado_id not in fallback_r:
                fallback_r[cd.id_repuesto_comprado_id] = cd

    for s in stocks_r:
        nom = s.id_repuesto_comprado.id_repuesto.nombre
        if nom not in repuestos_stock:
            repuestos_stock[nom] = []

        # Resolver precio: directo o fallback
        detalle_compra = s.idcompradetalle or fallback_r.get(s.id_repuesto_comprado_id)

        p_venta_max = float(detalle_compra.precio_maximo) if detalle_compra else 0
        p_venta_min = float(detalle_compra.precio_minimo) if detalle_compra else 0
        p_compra    = float(detalle_compra.precio_compra)  if detalle_compra else 0

        repuestos_stock[nom].append({
            'id_repuesto_comprado': s.id_repuesto_comprado.id_repuesto_comprado,
            'codigo_barras':        s.id_repuesto_comprado.id_repuesto.codigo_barras or 'N/A',
            'modelo':               s.id_repuesto_comprado.id_repuesto.modelo_referencia or 'N/A',
            'precio_venta':         p_venta_max,
            'precio_maximo':        p_venta_max,
            'precio_minimo':        p_venta_min,
            'precio_compra':        p_compra,
            'stock_disponible':     s.cantidad_disponible,
        })

    return JsonResponse({
        'ok': True,
        'productos_stock': productos_stock,
        'repuestos_stock': repuestos_stock,
    })


@requiere_caja_aperturada
@transaction.atomic
def registrar_credito_directo(request):
    """
    Registra un crédito directo sin generar una venta
    Descuenta stock manualmente y crea el cronograma de cuotas
    """
    if request.method == 'POST':
        try:
            idcliente = request.POST.get('idcliente_directo')
            tipo_item = request.POST.get('tipo_item_directo')
            id_item = request.POST.get('id_item_directo')
            monto_total = Decimal(request.POST.get('monto_total_directo', 0))
            monto_adelanto = Decimal(request.POST.get('monto_adelanto_directo', 0))
            cantidad_cuotas = int(request.POST.get('cantidad_cuotas_directo', 1))
            id_almacen = request.POST.get('id_almacen_directo')
            
            fecha_credito_str = request.POST.get('fecha_credito_directo', '').strip()
            fecha_credito = timezone.now()
            if fecha_credito_str:
                from datetime import datetime
                try:
                    parsed_date = datetime.strptime(fecha_credito_str, '%Y-%m-%d').date()
                    fecha_credito = timezone.make_aware(datetime.combine(parsed_date, timezone.now().time()))
                except ValueError:
                    pass
            
            # Datos de las cuotas (JSON strings)
            cuotas_json = request.POST.getlist('cuotas_data[]')
            # O si viene como campo oculto único
            if not cuotas_json:
                import json
                cuotas_json = json.loads(request.POST.get('cuotas_json', '[]'))
            
            idusuario = request.session.get('idusuario')
            if not idusuario:
                 return JsonResponse({'ok': False, 'error': 'Sesión expirada'}, status=403)
            
            # Validaciones básicas
            if not idcliente or not id_item or not id_almacen:
                return JsonResponse({'ok': False, 'error': 'Faltan datos obligatorios'}, status=400)
            
            # Obtener objetos
            cliente = get_object_or_404(Cliente, pk=idcliente)
            almacen = get_object_or_404(Almacenes, pk=id_almacen)
            sucursal = almacen.id_sucursal
            
            # Generar código de crédito directo (formato CRD-YYYYMMDD-NNN)
            # Cuenta solo créditos directos del día para evitar colisiones con los de venta
            hoy = fecha_credito
            _intento_d = 0
            while True:
                count_hoy = Credito.objects.filter(
                    fecha_credito__date=hoy.date(),
                    es_directo=True
                ).count() + 1 + _intento_d
                codigo_credito = f"CRD-{hoy.strftime('%Y%m%d')}-{count_hoy:03d}"
                if not Credito.objects.filter(codigo_credito=codigo_credito).exists():
                    break
                _intento_d += 1
            
            # 1. Crear el Crédito
            credito = Credito.objects.create(
                codigo_credito=codigo_credito,
                idcliente=cliente,
                es_directo=True,
                tipo_item=tipo_item,
                monto_total=monto_total,
                monto_adelanto=monto_adelanto,
                saldo_pendiente=monto_total,  # Cuota 0 también queda pendiente
                cantidad_cuotas=cantidad_cuotas,
                id_sucursal=sucursal,
                id_almacen=almacen,
                idusuario_id=idusuario,
                fecha_credito=fecha_credito,
                estado_credito='activo'
            )
            
            if tipo_item == 'vehiculo':
                vehiculo = get_object_or_404(Vehiculo, pk=id_item)
                credito.id_vehiculo = vehiculo
            else:
                repuesto = get_object_or_404(RepuestoComp, pk=id_item)
                credito.id_repuesto_comprado = repuesto
            credito.save()

            # 2. Descontar Stock
            if tipo_item == 'vehiculo':
                stock = Stock.objects.filter(id_almacen=almacen, id_vehiculo_id=id_item, estado=1).first()
            else:
                stock = Stock.objects.filter(id_almacen=almacen, id_repuesto_comprado_id=id_item, estado=1).first()
            
            if not stock or stock.cantidad_disponible < 1:
                return JsonResponse({'ok': False, 'error': 'No hay stock disponible en el almacén seleccionado'}, status=400)
            
            if not stock.descontar_stock(1):
                return JsonResponse({'ok': False, 'error': 'Error al descontar stock'}, status=500)
            
            # 3. Crear Cuotas desde el JSON del frontend
            if cuotas_json:
                total_cuotas_validas = 0
                for c in cuotas_json:
                    num = int(c.get('numero', 1))
                    monto_c = Decimal(str(c.get('monto', 0)))
                    interes_c = Decimal(str(c.get('interes', 0)))
                    total_c = Decimal(str(c.get('total', 0))) or (monto_c + interes_c)
                    fecha_venc = c.get('fecha_vencimiento')
                    
                    if num == 0:
                        # Cuota 0 (Adelanto/Inicial) -> Ahora queda PENDIENTE
                        CuotasVenta.objects.create(
                            idcredito=credito,
                            numero_cuota=0,
                            monto=monto_c,
                            interes=0,
                            total=monto_c,
                            fecha_vencimiento=fecha_venc or hoy.date(),
                            monto_adelanto=monto_c,
                            monto_pagado=0,            # Empieza en 0
                            saldo_cuota=monto_c,       # Todo pendiente
                            estado_pago='Pendiente',   # Estado Pendiente
                            fecha_pago=None,
                            estado=1
                        )
                    else:
                        CuotasVenta.objects.create(
                            idcredito=credito,
                            numero_cuota=num,
                            monto=monto_c,
                            interes=interes_c,
                            total=total_c,
                            fecha_vencimiento=fecha_venc,
                            monto_adelanto=0,
                            monto_pagado=0,
                            saldo_cuota=total_c,
                            estado_pago='Pendiente',
                            estado=1
                        )
                        total_cuotas_validas += 1
                
                # Actualizar cantidad_cuotas del crédito con las cuotas reales excluyendo la 0
                if total_cuotas_validas > 0:
                    credito.cantidad_cuotas = total_cuotas_validas
                    credito.save()
            else:
                 return JsonResponse({'ok': False, 'error': 'El cronograma de cuotas no fue generado correctamente.'}, status=400)
            
            # 4. No registramos movimiento de caja aquí, 
            # ya que el pago inicial se realizará desde el módulo de créditos
            
            return JsonResponse({'ok': True, 'message': 'Crédito registrado correctamente', 'idcredito': credito.idcredito})

        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)}, status=500)

    return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)


def detalle_credito(request, idcredito):
    """
    Vista de detalle de un crédito específico
    Muestra todas las cuotas y el historial de pagos
    """
    id_tipo_usuario = request.session.get('idtipousuario')
    if not id_tipo_usuario:
        return redirect('login')
        
    # Verificar permiso
    from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos
    from django.db.models import Q
    tiene_permiso = Detalletipousuarioxmodulos.objects.filter(
        idtipousuario=id_tipo_usuario
    ).filter(
        Q(idmodulo__nombremodulo__iexact='creditos') | 
        Q(idmodulo__nombremodulo__iexact='créditos')
    ).exists()
    
    if not tiene_permiso:
        return redirect('cpanel')

    credito = get_object_or_404(Credito, idcredito=idcredito)
    # Asegurar que el estado del crédito esté actualizado (por si hay cuotas vencidas)
    credito.actualizar_estado()
    
    from django.db.models import Prefetch
    
    # Obtener cuotas del crédito y pre-cargar sus pagos para evitar N+1 queries
    pagos_prefetch = Prefetch(
        'pagos',
        queryset=PagoCuota.objects.filter(estado=1).select_related('idusuario', 'id_tipo_pago', 'id_movimiento_caja').order_by('-fecha_pago'),
        to_attr='pagos_prefetched'
    )
    
    if credito.idventa:
        cuotas = CuotasVenta.objects.filter(idventa=credito.idventa, estado=1).order_by('numero_cuota').prefetch_related(pagos_prefetch)
    else:
        cuotas = CuotasVenta.objects.filter(idcredito=credito, estado=1).order_by('numero_cuota').prefetch_related(pagos_prefetch)
    
    # Para cada cuota, obtener su historial de pagos
    import re as _re
    cuotas_con_pagos = []
    total_interes_mora_actual = Decimal(0)
    total_monto_base = Decimal(0)
    total_interes_contrato = Decimal(0)
    total_cuota_contrato = Decimal(0)
    total_pagado_real_acumulado = Decimal(0)

    for cuota in cuotas:
        # Calcular interés por mora dinámico
        interes_mora_calculado, tasa, dias = calcular_interes_mora(cuota)
        cuota.interes_mora_dinamico = interes_mora_calculado
        cuota.tasa_mora_dinamica = tasa
        cuota.dias_retraso = dias
        
        # Monto total cobrado en esta cuota (Capital + Mora pagada)
        cuota.pagado_total = cuota.monto_pagado + cuota.interes_mora
        
        # Saldo total pendiente (Capital pendiente + Mora dinámica)
        if cuota.estado_pago == 'Pagado':
            cuota.saldo_total = Decimal('0')
        else:
            cuota.saldo_total = cuota.saldo_cuota + interes_mora_calculado
            
        total_interes_mora_actual += interes_mora_calculado
        total_monto_base += cuota.monto
        total_interes_contrato += cuota.interes
        total_cuota_contrato += cuota.total
        # Acumular el pagado total real (incluyendo descuentos para que el saldo cierre en 0)
        total_pagado_real_acumulado += cuota.pagado_total + cuota.descuento

        pagos_qs = cuota.pagos_prefetched

        # Detectar pagos que pertenecen a un pago múltiple para habilitar
        # la re-impresión del ticket grupal desde el historial de cuotas
        pagos_procesados = []
        for pago in pagos_qs:
            pago.multipago_ids = None
            pago.es_pago_total = False
            pago.observaciones_limpias = pago.observaciones

            if pago.id_movimiento_caja and pago.id_movimiento_caja.descripcion and pago.id_movimiento_caja.descripcion.startswith('PAGO TOTAL CRÉDITO'):
                pago.es_pago_total = True

            if pago.observaciones and '[MULTIPAGO:' in pago.observaciones:
                m = _re.search(r'\[MULTIPAGO:([^\]]+)\]', pago.observaciones)
                if m:
                    pago.multipago_ids = m.group(1)
                    pago.observaciones_limpias = _re.sub(r'\s*\[MULTIPAGO:[^\]]+\]', '', pago.observaciones).strip()
            pagos_procesados.append(pago)

        cuotas_con_pagos.append({
            'cuota': cuota,
            'pagos': pagos_procesados
        })

    # ── BLOQUEO SECUENCIAL ────────────────────────────────────────────────────
    # Una sola query adicional para calcular todos los estados de bloqueo.
    # No importa cuántas cuotas tenga el crédito — siempre es 1 query.
    estados_bloqueo = obtener_estados_bloqueo(credito)
    for item in cuotas_con_pagos:
        cuota = item['cuota']
        info = estados_bloqueo.get(cuota.idcuotaventa, {})
        cuota.puede_pagar       = info.get('puede_pagar', True)
        cuota.bloqueante_numero = info.get('bloqueante_numero')
    # ── FIN BLOQUEO SECUENCIAL ────────────────────────────────────────────────


    total_pagado_capital = Decimal('0')
    total_pagado_interes = Decimal('0')
    
    for cuota in cuotas:
        # El "pagado" efectivo de esta cuota incluye el dinero real más el descuento otorgado
        recibido_total = cuota.monto_pagado + cuota.descuento
        
        # En cada cuota, el total recibido se aplica primero al interés de esa cuota
        pago_interes = min(cuota.interes, recibido_total)
        pago_capital = recibido_total - pago_interes
        
        total_pagado_interes += pago_interes
        total_pagado_capital += pago_capital
    
    # Los saldos globales son simplemente la resta de los totales originales menos lo pagado
    total_capital_pendiente = max(Decimal('0'), total_monto_base - total_pagado_capital)
    total_interes_pendiente = max(Decimal('0'), total_interes_contrato - total_pagado_interes)
    
    total_total_pendiente = total_capital_pendiente + total_interes_pendiente
    
    # Verificar cuotas vencidas
    hoy = timezone.now().date()
    cuotas_vencidas = cuotas.filter(
        estado_pago__in=['Pendiente', 'Parcial'],
        fecha_vencimiento__lt=hoy
    ).count()
    
    # Obtener detalles de productos válidos
    if credito.idventa:
        detalles = VentaDetalle.objects.filter(
            idventa=credito.idventa, 
            estado=1
        ).filter(
            Q(id_vehiculo__idproducto__isnull=False) | Q(id_repuesto_comprado__id_repuesto__isnull=False)
        ).select_related(
            'id_vehiculo__idproducto',
            'id_repuesto_comprado__id_repuesto'
        )
    else:
        # Simular objeto detalle para el template para créditos directos
        detalle_directo = {
            'tipo_item': credito.tipo_item,
            'cantidad': credito.cantidad,
            'precio_venta_credito': credito.monto_total,
            'precio_venta_contado': credito.monto_total,
            'subtotal': credito.monto_total,
        }
        if credito.id_vehiculo:
            detalle_directo['id_vehiculo'] = credito.id_vehiculo
        else:
            detalle_directo['id_repuesto_comprado'] = credito.id_repuesto_comprado
        detalles = [detalle_directo]
    
    data = {
        'credito': credito,
        'cuotas_con_pagos': cuotas_con_pagos,
        'total_pagado': total_pagado_real_acumulado,
        'total_pendiente': total_total_pendiente + total_interes_mora_actual,
        'total_interes_mora': total_interes_mora_actual,
        'total_monto_base': total_monto_base,
        'total_interes_contrato': total_interes_contrato,
        'total_cuota_contrato': total_cuota_contrato,
        'saldo_capital': total_capital_pendiente,
        'saldo_interes': total_interes_pendiente,
        'total_interes_pendiente': total_interes_pendiente + total_interes_mora_actual, # Descuento máximo permitido
        'cuotas_vencidas': cuotas_vencidas,
        'detalles': detalles,
        'tipos_pago_global': TipoPago.objects.filter(estado=1),
        'almacenes_retencion': Almacenes.objects.filter(estado=1),
        'regiones': Region.objects.filter(estado=1),
    }
    
    return render(request, 'creditos/detalle_credito.html', data)


@requiere_caja_aperturada
def pagar_cuota(request, idcuotaventa):
    cuota = get_object_or_404(CuotasVenta, idcuotaventa=idcuotaventa)
    # Datos del crédito y cliente
    if cuota.idventa:
        credito = get_object_or_404(Credito, idventa=cuota.idventa)
    else:
        credito = get_object_or_404(Credito, idcredito=cuota.idcredito_id)

    # ── VALIDACIÓN SECUENCIAL ─────────────────────────────────────────────────
    # La cuota inicial (numero_cuota=0) siempre puede pagarse.
    # Desde cuota 1 en adelante, todas las anteriores deben estar 'Pagado'.
    error_secuencia = validar_pago_secuencial(cuota, credito)
    if error_secuencia:
        if request.method == 'POST':
            return JsonResponse({'ok': False, 'error': error_secuencia}, status=400)
        from django.contrib import messages
        messages.error(request, error_secuencia)
        return redirect('detalle_credito', credito.idcredito)
    # ── FIN VALIDACIÓN SECUENCIAL ─────────────────────────────────────────────

    if request.method == 'POST':

        try:
            with transaction.atomic():
                # Fecha manual o actual
                fecha_pago_str = request.POST.get('fecha_pago')
                if fecha_pago_str:
                    try:
                        fecha_pago_date = datetime.strptime(fecha_pago_str, '%Y-%m-%d').date()
                        fecha_pago_final = timezone.make_aware(datetime.combine(fecha_pago_date, timezone.now().time()))
                    except ValueError:
                        fecha_pago_final = timezone.now()
                else:
                    fecha_pago_final = timezone.now()

                # Obtener montos y tipos de pago (pueden ser varios)
                tipos_pago_ids = request.POST.getlist('tipo_pago_id[]')
                montos_item = request.POST.getlist('monto_pago_item[]')
                nros_operacion = request.POST.getlist('nro_operacion[]')
                
                observaciones_base = request.POST.get('observaciones', '').strip()
                idusuario = request.session.get('idusuario')

                if not tipos_pago_ids or not montos_item:
                    # Fallback para compatibilidad con parámetros simples
                    monto_pago_total = Decimal(request.POST.get('monto_pago', 0))
                    tipos_pago_ids = [request.POST.get('id_tipo_pago')]
                    montos_item = [monto_pago_total]
                    nros_operacion = [request.POST.get('numero_operacion', '')]
                
                # Calcular total y preparar desglose
                monto_pago_total = Decimal('0')
                desglose_pagos = []
                
                for i in range(len(tipos_pago_ids)):
                    if not tipos_pago_ids[i] or not montos_item[i]: continue
                    
                    t_id = int(tipos_pago_ids[i])
                    m_val = Decimal(montos_item[i])
                    n_op = nros_operacion[i].strip() if i < len(nros_operacion) else ''
                    
                    if m_val <= 0: continue
                    
                    monto_pago_total += m_val
                    tp_obj = get_object_or_404(TipoPago, id_tipo_pago=t_id)
                    desglose_pagos.append({
                        'nombre': tp_obj.nombre,
                        'monto': m_val,
                        'op': n_op,
                        'id': t_id
                    })

                if monto_pago_total <= 0:
                    return JsonResponse({'ok': False, 'error': 'El monto total debe ser mayor a 0.'}, status=400)

                # Validar contra el saldo
                interes_mora_vld, _, _ = calcular_interes_mora(cuota)
                saldo_total_vld = cuota.saldo_cuota + interes_mora_vld

                if monto_pago_total > saldo_total_vld + Decimal('0.01'):
                    return JsonResponse({
                        'ok': False,
                        'error': f'El monto total (S/ {monto_pago_total}) excede el saldo de la cuota (S/ {saldo_total_vld})'
                    }, status=400)
                
                # Verificar caja abierta
                apertura_actual = AperturaCierreCaja.objects.filter(
                    idusuario_id=idusuario,
                    estado__in=['abierta', 'reabierta']
                ).first()

                if not apertura_actual:
                    return JsonResponse({
                        'ok': False,
                        'error': 'No tiene una caja abierta. Debe aperturar una caja primero.'
                    }, status=400)

                # Determinar el tipo de pago principal y formatear observaciones
                if len(desglose_pagos) > 1:
                    # Múltiples métodos -> Usar tipo 'Múltiple' (ID 6)
                    tp_multiple = TipoPago.objects.filter(nombre__iexact='Múltiple').first()
                    id_tipo_pago_final = tp_multiple.id_tipo_pago if tp_multiple else desglose_pagos[0]['id']
                    
                    detalle_obs = " | ".join([f"{d['nombre']}: S/ {d['monto']}" + (f" (Op:{d['op']})" if d['op'] else "") for d in desglose_pagos])
                    observaciones_final = f"[FRACCIONADO: {detalle_obs}]"
                    if observaciones_base:
                        observaciones_final = f"{observaciones_base} {observaciones_final}"
                    
                    numero_operacion_final = "Múltiple"
                else:
                    # Un solo método
                    id_tipo_pago_final = desglose_pagos[0]['id']
                    numero_operacion_final = desglose_pagos[0]['op']
                    observaciones_final = observaciones_base

                # 1. Registrar movimiento de caja
                if credito.es_directo:
                    descripcion_movimiento = f"Pago Crédito Directo {credito.codigo_credito} - Cuota #{cuota.numero_cuota} - Cliente: {credito.idcliente.razonsocial}"
                else:
                    descripcion_movimiento = f"Pago cuota #{cuota.numero_cuota} - Crédito {credito.codigo_credito} - Cliente: {credito.idventa.idcliente.razonsocial if credito.idventa else credito.idcliente.razonsocial}"
                
                if len(desglose_pagos) > 1:
                    descripcion_movimiento += " (Múltiples métodos)"

                movimiento_caja = MovimientoCaja.objects.create(
                    id_caja=apertura_actual.id_caja,
                    id_movimiento=apertura_actual,
                    idusuario_id=idusuario,
                    tipo_movimiento='ingreso',
                    monto=monto_pago_total,
                    descripcion=descripcion_movimiento,
                    idventa=None,
                    estado=1
                )

                # 2. Registrar el pago vinculado al movimiento
                pago = PagoCuota.objects.create(
                    idcuotaventa=cuota,
                    idusuario_id=idusuario,
                    id_tipo_pago_id=id_tipo_pago_final,
                    monto_pago=monto_pago_total,
                    id_movimiento_caja=movimiento_caja,
                    numero_operacion=numero_operacion_final,
                    observaciones=observaciones_final,
                    estado=1,
                    fecha_pago=fecha_pago_final
                )

                # 3. Actualizar la cuota (Primero interés mora, luego capital)
                interes_mora_cobrado = min(monto_pago_total, interes_mora_vld)
                monto_restante = monto_pago_total - interes_mora_cobrado
                
                cuota.interes_mora += interes_mora_cobrado
                cuota.monto_pagado += monto_restante
                cuota.saldo_cuota -= monto_restante
                
                if cuota.saldo_cuota <= 0:
                    cuota.estado_pago = 'Pagado'
                    cuota.fecha_pago = fecha_pago_final
                elif cuota.monto_pagado > 0:
                    cuota.estado_pago = 'Parcial'
                
                cuota.save()
                
                # Actualizar el crédito
                credito.actualizar_estado()

                return JsonResponse({
                    'ok': True,
                    'message': 'Pago registrado correctamente',
                    'nuevo_saldo': float(cuota.saldo_cuota),
                    'estado_cuota': cuota.estado_pago,
                    'idpago': pago.idpagocuota
                })
            
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'ok': False,
                'error': f'Error al procesar el pago: {str(e)}'
            }, status=500)
    
    # GET: Mostrar formulario
    tipos_pago = TipoPago.objects.filter(estado=1)
    
    if credito.idventa:
        cuotas_activas = CuotasVenta.objects.filter(idventa=credito.idventa, estado=1)
    else:
        cuotas_activas = CuotasVenta.objects.filter(idcredito=credito, estado=1)
    
    total_pendiente_real = cuotas_activas.aggregate(total=Sum('saldo_cuota'))['total'] or Decimal('0')
    
    # Calcular interés mora
    interes_mora, tasa_mora, dias_mora = calcular_interes_mora(cuota)
    total_pendiente_cuota = cuota.saldo_cuota + interes_mora

    data = {
        'cuota': cuota,
        'credito': credito,
        'tipos_pago': tipos_pago,
        'total_pendiente': total_pendiente_real + interes_mora,
        'total_pendiente_cuota': total_pendiente_cuota,
        'interes_mora': interes_mora,
        'tasa_mora': tasa_mora,
        'dias_mora': dias_mora,
    }

    
    return render(request, 'creditos/pagar_cuota.html', data)

def anular_pago(request, idpagocuota):
    """
    Anular un pago de cuota (cambia estado a 0)
    """
    if request.method == 'POST':
        try:
            with transaction.atomic():
                pago = get_object_or_404(PagoCuota, idpagocuota=idpagocuota)
                cuota = pago.idcuotaventa
                if cuota.idventa:
                    credito = Credito.objects.get(idventa=cuota.idventa)
                else:
                    credito = cuota.idcredito
                
                # Revertir el monto en la cuota
                cuota.monto_pagado -= pago.monto_pago
                cuota.saldo_cuota += pago.monto_pago
                
                if cuota.monto_pagado == 0:
                    cuota.estado_pago = 'Pendiente'
                    cuota.fecha_pago = None
                elif cuota.saldo_cuota > 0:
                    cuota.estado_pago = 'Parcial'
                
                cuota.save()
                
                # ⭐ MEJORADO: Usar el vínculo directo si existe, sino buscar
                movimiento = None
                if pago.id_movimiento_caja:
                    movimiento = pago.id_movimiento_caja
                else:
                    movimiento = MovimientoCaja.objects.filter(
                        idusuario=pago.idusuario,
                        tipo_movimiento='ingreso',
                        monto=pago.monto_pago,
                        fecha_movimiento__date=pago.fecha_pago.date(),
                        descripcion__icontains=credito.codigo_credito,
                        estado=1
                    ).first()
                
                if movimiento:
                    # Si es un multipago, solo anulamos si es el último pago asociado 
                    # o si queremos anular todo el grupo. Por ahora, anulamos el movimiento
                    # pero ojo: un movimiento multipago tiene el total de varias cuotas.
                    # Si anulamos una sola cuota de un multipago, el movimiento queda descuadrado.
                    # Por simplicidad profesional: se anula el rastro de caja.
                    movimiento.estado = 0
                    movimiento.save()
                
                # Anular el pago
                pago.estado = 0
                pago.save()
                
                # Actualizar el crédito
                credito.actualizar_estado()
                
                return JsonResponse({
                    'ok': True,
                    'message': 'Pago anulado correctamente'
                })
            
        except Exception as e:
            return JsonResponse({
                'ok': False,
                'error': f'Error al anular el pago: {str(e)}'
            }, status=500)
    
    return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=400)

@requiere_caja_aperturada
@transaction.atomic
def editar_pago(request, idpagocuota):
    """
    Permite corregir un pago registrado sin eliminarlo.
    Actualiza montos en cuota, crédito y caja.
    """
    pago = get_object_or_404(PagoCuota, idpagocuota=idpagocuota)
    cuota = pago.idcuotaventa
    
    if cuota.idventa:
        credito = Credito.objects.get(idventa=cuota.idventa)
    else:
        credito = cuota.idcredito
        
    if request.method == 'GET':
        return JsonResponse({
            'ok': True,
            'data': {
                'idpagocuota': pago.idpagocuota,
                'monto_pago': float(pago.monto_pago),
                'id_tipo_pago': pago.id_tipo_pago_id,
                'numero_operacion': pago.numero_operacion,
                'observaciones': pago.observaciones,
                'saldo_cuota_actual': float(cuota.saldo_cuota)
            }
        })
        
    if request.method == 'POST':
        try:
            monto_anterior = pago.monto_pago
            nuevo_monto = Decimal(request.POST.get('monto_pago', 0))
            nuevo_id_tipo_pago = int(request.POST.get('id_tipo_pago'))
            nuevo_num_op = request.POST.get('numero_operacion', '').strip()
            nuevas_obs = request.POST.get('observaciones', '').strip()
            
            if nuevo_monto <= 0:
                return JsonResponse({'ok': False, 'error': 'El monto debe ser mayor a 0'}, status=400)
            
            # Validar que el nuevo monto no exceda lo que falta pagar + lo que ya se pagó en este registro
            monto_maximo = cuota.saldo_cuota + pago.monto_pago
            if nuevo_monto > monto_maximo:
                return JsonResponse({
                    'ok': False, 
                    'error': f'El monto no puede superar el saldo total de la cuota (Máx: S/ {monto_maximo})'
                }, status=400)
                
            # 1. Revertir impacto del pago original en la cuota
            cuota.monto_pagado -= pago.monto_pago
            cuota.saldo_cuota += pago.monto_pago
            
            # 2. Aplicar el nuevo impacto
            cuota.monto_pagado += nuevo_monto
            cuota.saldo_cuota -= nuevo_monto
            
            # Actualizar estados de la cuota
            if cuota.saldo_cuota == 0:
                cuota.estado_pago = 'Pagado'
                if not cuota.fecha_pago: cuota.fecha_pago = timezone.now()
            elif cuota.monto_pagado > 0:
                cuota.estado_pago = 'Parcial'
                cuota.fecha_pago = None
            else:
                cuota.estado_pago = 'Pendiente'
                cuota.fecha_pago = None
            
            cuota.save()
            
            # 3. Actualizar movimiento de caja si existe
            if pago.id_movimiento_caja:
                mov = pago.id_movimiento_caja
                diferencia = nuevo_monto - monto_anterior
                if diferencia != 0:
                    mov.monto += diferencia
                    mov.save()
            
            # 4. Actualizar el pago
            pago.monto_pago = nuevo_monto
            pago.id_tipo_pago_id = nuevo_id_tipo_pago
            pago.numero_operacion = nuevo_num_op
            
            # Lógica de observaciones solicitada por el usuario
            if not nuevas_obs:
                # Si el campo está vacío en el modal
                if monto_anterior != nuevo_monto:
                    pago.observaciones = f"[Editado: S/ {monto_anterior} -> S/ {nuevo_monto}]"
                else:
                    pago.observaciones = ""
            else:
                # Si el usuario escribió algo (o dejó el texto previo), se guarda tal cual
                pago.observaciones = nuevas_obs
                
            pago.save()
            
            # 5. Actualizar estado del crédito
            credito.actualizar_estado()
            
            return JsonResponse({
                'ok': True,
                'message': 'Pago actualizado correctamente'
            })
            
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)}, status=500)
            
    return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)


def ajax_editar_mora(request, idcuotaventa):
    """
    Actualiza el interés por mora manual de una cuota.
    Si el monto enviado está vacío, se limpia el interés manual (vuelve a dinámico).
    """
    if request.method == 'POST':
        try:
            cuota = get_object_or_404(CuotasVenta, idcuotaventa=idcuotaventa)
            monto_str = request.POST.get('interes_mora_manual', '').strip()
            
            if monto_str == "":
                cuota.interes_mora_manual = None
            else:
                cuota.interes_mora_manual = Decimal(monto_str)
            
            cuota.save()
            
            # Recalcular saldo de la cuota para la respuesta
            interes_mora, tasa, dias = calcular_interes_mora(cuota)
            saldo_total = cuota.saldo_cuota + interes_mora
            
            return JsonResponse({
                'ok': True,
                'message': 'Interés actualizado correctamente',
                'interes_mora': float(interes_mora),
                'saldo_total': float(saldo_total)
            })
            
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)}, status=500)
            
    return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)


@transaction.atomic
def fraccionar_pago(request, idpagocuota):
    """
    Permite dividir un pago ya registrado en múltiples métodos de pago
    manteniendo un solo registro de pago y un solo movimiento de caja.
    """
    pago = get_object_or_404(PagoCuota, idpagocuota=idpagocuota)
    if request.method == 'GET':
        # Respuesta simplificada para depuración
        data = {
            'idpagocuota': pago.idpagocuota,
            'monto_total': float(pago.monto_pago),
            'id_tipo_pago': pago.id_tipo_pago_id,
            'numero_operacion': pago.numero_operacion or '',
            'observaciones': pago.observaciones or '',
        }
        return JsonResponse({'ok': True, 'data': data})

    if request.method == 'POST':
        try:
            fracciones_json = request.POST.get('fracciones', '[]')
            fracciones = json.loads(fracciones_json)
            
            if not fracciones:
                return JsonResponse({'ok': False, 'error': 'Debe especificar al menos una fracción'}, status=400)
            
            total_fracciones = sum(Decimal(str(f['monto'])) for f in fracciones)
            
            # Validar que la suma coincida
            if abs(total_fracciones - pago.monto_pago) > Decimal('0.001'):
                return JsonResponse({
                    'ok': False, 
                    'error': f'La suma de las fracciones (S/ {total_fracciones}) debe ser igual al monto original (S/ {pago.monto_pago})'
                }, status=400)
            
            # Construir el detalle estructurado para observaciones
            detalles = []
            for f in fracciones:
                tipo_nombre = f.get('tipo_nombre', 'N/A')
                monto_f = f.get('monto')
                op_f = f.get('numero_operacion', '').strip()
                
                detalle_str = f"{tipo_nombre}: S/ {monto_f}"
                if op_f:
                    detalle_str += f" (Op:{op_f})"
                detalles.append(detalle_str)
            
            breakdown_str = " | ".join(detalles)
            nueva_observacion = f"[FRACCIONADO: {breakdown_str}]"
            
            # Si ya tenía observaciones, las mantenemos y agregamos el fraccionamiento
            if pago.observaciones:
                if "[FRACCIONADO:" in pago.observaciones:
                    # Si ya estaba fraccionado, reemplazamos el bloque de fraccionamiento anterior
                    import re
                    pago.observaciones = re.sub(r'\[FRACCIONADO:.*?\]', nueva_observacion, pago.observaciones)
                else:
                    pago.observaciones = f"{pago.observaciones}\n{nueva_observacion}"
            else:
                pago.observaciones = nueva_observacion
            
            # Obtener ID de tipo de pago "Múltiple"
            tipo_multiple = TipoPago.objects.filter(nombre='Múltiple').first()
            if not tipo_multiple:
                tipo_multiple = TipoPago.objects.create(nombre='Múltiple', estado=1)
            
            # 1. Actualizar el pago
            pago.id_tipo_pago = tipo_multiple
            # Consolidamos los números de operación si hay varios
            ops = [f.get('numero_operacion', '').strip() for f in fracciones if f.get('numero_operacion', '').strip()]
            if ops:
                pago.numero_operacion = ", ".join(ops)
            pago.save()
            
            # 2. Actualizar el movimiento de caja
            if pago.id_movimiento_caja:
                mov = pago.id_movimiento_caja
                # Limpiar descripción anterior si ya estaba fraccionado
                import re
                mov.descripcion = re.sub(r'\s*\[Fraccionado:.*?\]', '', mov.descripcion or '')
                mov.descripcion = f"{mov.descripcion} [Fraccionado: {breakdown_str}]"
                mov.save()
            
            return JsonResponse({
                'ok': True,
                'message': 'Pago fraccionado correctamente'
            })
            
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)}, status=500)

    return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)


def reportes_creditos(request):
    """
    Vista de reportes y estadísticas de créditos
    """
    # Obtener fechas del filtro o usar mes actual
    hoy = timezone.now()
    fecha_desde = request.GET.get('fecha_desde', hoy.replace(day=1).strftime('%Y-%m-%d'))
    fecha_hasta = request.GET.get('fecha_hasta', hoy.strftime('%Y-%m-%d'))
    
    # Convertir a datetime
    fecha_desde_dt = datetime.strptime(fecha_desde, '%Y-%m-%d')
    fecha_hasta_dt = datetime.strptime(fecha_hasta, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
    
    # Créditos en el periodo
    creditos_periodo = Credito.objects.filter(
        estado=1,
        fecha_credito__range=[fecha_desde_dt, fecha_hasta_dt]
    )
    
    # Estadísticas generales
    total_creditos_periodo = creditos_periodo.count()
    monto_total_financiado = creditos_periodo.aggregate(Sum('monto_total'))['monto_total__sum'] or 0
    
    # Créditos por estado
    creditos_activos = creditos_periodo.filter(estado_credito='activo').count()
    creditos_mora = creditos_periodo.filter(estado_credito='mora').count()
    creditos_pagados = creditos_periodo.filter(estado_credito='pagado').count()
    
    # Cuotas vencidas en el sistema (todas, no solo del periodo)
    cuotas_vencidas = CuotasVenta.objects.filter(
        estado=1,
        estado_pago__in=['Pendiente', 'Parcial'],
        fecha_vencimiento__lt=hoy.date()
    ).select_related('idventa__idcliente')
    
    monto_vencido = sum(cuota.saldo_cuota for cuota in cuotas_vencidas)
    
    # Cuotas por vencer en los próximos 30 días
    fecha_limite = hoy.date() + timedelta(days=30)
    cuotas_por_vencer = CuotasVenta.objects.filter(
        estado=1,
        estado_pago__in=['Pendiente', 'Parcial'],
        fecha_vencimiento__range=[hoy.date(), fecha_limite]
    ).select_related('idventa__idcliente').order_by('fecha_vencimiento')
    
    monto_por_vencer = sum(cuota.saldo_cuota for cuota in cuotas_por_vencer)
    
    # Top 10 clientes con mayor deuda
    clientes_deuda = {}
    creditos_activos_todos = Credito.objects.filter(
        estado=1,
        estado_credito__in=['activo', 'mora']
    )
    
    for credito in creditos_activos_todos:
        cliente = credito.idventa.idcliente if credito.idventa else credito.idcliente
        if not cliente: continue
        if cliente.idcliente not in clientes_deuda:
            clientes_deuda[cliente.idcliente] = {
                'cliente': cliente,
                'total_deuda': Decimal('0'),
                'creditos': 0
            }
        clientes_deuda[cliente.idcliente]['total_deuda'] += credito.saldo_pendiente
        clientes_deuda[cliente.idcliente]['creditos'] += 1
    
    top_clientes = sorted(
        clientes_deuda.values(),
        key=lambda x: x['total_deuda'],
        reverse=True
    )[:10]
    
    # Pagos recibidos en el periodo
    pagos_periodo = PagoCuota.objects.filter(
        estado=1,
        fecha_pago__range=[fecha_desde_dt, fecha_hasta_dt]
    )
    
    total_pagos_recibidos = pagos_periodo.aggregate(Sum('monto_pago'))['monto_pago__sum'] or 0
    cantidad_pagos = pagos_periodo.count()
    
    # Datos para gráficos - Créditos por mes (últimos 12 meses)
    hace_12_meses = hoy - timedelta(days=365)
    creditos_por_mes = []
    
    for i in range(12):
        mes_inicio = (hoy - timedelta(days=30*i)).replace(day=1)
        if i == 0:
            mes_fin = hoy
        else:
            mes_fin = mes_inicio.replace(day=28) + timedelta(days=4)
            mes_fin = mes_fin.replace(day=1) - timedelta(days=1)
        
        count = Credito.objects.filter(
            estado=1,
            fecha_credito__range=[mes_inicio, mes_fin]
        ).count()
        
        creditos_por_mes.insert(0, {
            'mes': mes_inicio.strftime('%b %Y'),
            'cantidad': count
        })
    
    data = {
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'total_creditos_periodo': total_creditos_periodo,
        'monto_total_financiado': monto_total_financiado,
        'creditos_activos': creditos_activos,
        'creditos_mora': creditos_mora,
        'creditos_pagados': creditos_pagados,
        'cuotas_vencidas': cuotas_vencidas,
        'monto_vencido': monto_vencido,
        'cuotas_por_vencer': cuotas_por_vencer,
        'monto_por_vencer': monto_por_vencer,
        'top_clientes': top_clientes,
        'total_pagos_recibidos': total_pagos_recibidos,
        'cantidad_pagos': cantidad_pagos,
        'creditos_por_mes': creditos_por_mes,
    }
    
    return render(request, 'creditos/reportes.html', data)



def calcular_interes_mora(cuota, fecha_referencia=None):
    """
    Calcula el interés moratorio para una cuota según la lógica:
    - 3 días de gracia: 0%
    - Día 4: Interés Base % (ej. 5%)
    - Día 5+: Base + (Días - 4)%
    Retorna (monto_interes, tasa_aplicada, dias_retraso)
    """
    # Si tiene interés manual, devolvemos ese valor
    if cuota.interes_mora_manual is not None:
        return cuota.interes_mora_manual, "Manual", (timezone.now().date() - cuota.fecha_vencimiento).days if cuota.fecha_vencimiento else 0

    if cuota.estado_pago == 'Pagado' or not cuota.fecha_vencimiento:
        return Decimal('0'), 0, 0
    
    if not fecha_referencia:
        fecha_referencia = timezone.now().date()
    elif isinstance(fecha_referencia, datetime):
        fecha_referencia = fecha_referencia.date()
        
    if fecha_referencia <= cuota.fecha_vencimiento:
        return Decimal('0'), 0, 0
    
    dias_retraso = (fecha_referencia - cuota.fecha_vencimiento).days
    
    # Obtener configuración de la empresa
    from software.models.empresaModel import Empresa
    empresa = Empresa.objects.all().first()
    
    dias_inicio = empresa.dias_mora_inicio if empresa and empresa.dias_mora_inicio else 4
    tasa_base = empresa.interes_mora_base if empresa else Decimal('5.00')

    if dias_retraso < dias_inicio:
        return Decimal('0'), 0, dias_retraso
    
    # tasa = base + (dias - dias_inicio)
    tasa_adicional = dias_retraso - dias_inicio
    tasa_final = tasa_base + tasa_adicional
    
    monto_interes = (cuota.saldo_cuota * tasa_final / 100).quantize(Decimal('0.01'))
    
    return monto_interes, tasa_final, dias_retraso

def _generar_pdf_cronograma(request, credito):
    """
    Genera el cronograma de pagos premium utilizando ReportLab (Directo a PDF).
    Diseño corporativo premium sin dependencia de HTML/CSS.
    """
    try:
        from io import BytesIO
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import cm, mm
        from reportlab.platypus import (
            SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
        from software.models.VentaDetalleModel import VentaDetalle
        from software.models.empresaModel import Empresa
        from software.models.CanalPagoModel import CanalPago
        from django.utils import timezone
        from decimal import Decimal
        from django.http import HttpResponse

        # ── DATOS BASE ───────────────────────────────────────────────────
        # idventa.idempresa es IntegerField en Ventas (no FK): usar el int como pk, no .pk
        if credito.idventa and credito.idventa.idempresa is not None:
            empresa = Empresa.objects.get(pk=credito.idventa.idempresa, activo=True)
        else:
            if credito.id_sucursal and getattr(credito.id_sucursal, 'idempresa', None):
                 empresa = Empresa.objects.get(pk=credito.id_sucursal.idempresa.pk, activo=True)
            else:
                 empresa = Empresa.objects.filter(activo=True).first()
        
        if not empresa:
            return HttpResponse("No se encontró información de la empresa.", status=400)

        # Determinar cliente y sucursal
        cliente = credito.idventa.idcliente if credito.idventa else credito.idcliente
        sucursal = credito.id_sucursal
        if not sucursal and credito.idventa and credito.idventa.id_almacen:
            sucursal = credito.idventa.id_almacen.id_sucursal
            
        # Cuotas y Totales
        if credito.idventa:
            cuotas_qs = CuotasVenta.objects.filter(idventa=credito.idventa, estado=1).order_by('numero_cuota')
            detalles_qs = VentaDetalle.objects.filter(idventa=credito.idventa, estado=1).select_related(
                'id_vehiculo__idproducto', 'id_repuesto_comprado__id_repuesto'
            )
        else:
            cuotas_qs = CuotasVenta.objects.filter(idcredito=credito, estado=1).order_by('numero_cuota')
            detalles_qs = [{
                'tipo_item': credito.tipo_item,
                'id_vehiculo': credito.id_vehiculo,
                'id_repuesto_comprado': credito.id_repuesto_comprado,
                'cantidad': credito.cantidad,
                'precio_unitario': credito.monto_total / (credito.cantidad or 1),
                'subtotal': credito.monto_total
            }]

        # Determinar frecuencia del crédito (Inteligente)
        def detectar_frecuencia_local(cred, cuotas_qs):
            if cuotas_qs.filter(numero_cuota__gt=0).count() < 2:
                return 'Meses'
            
            reg_cuotas = cuotas_qs.filter(numero_cuota__gt=0).order_by('numero_cuota')
            c1 = reg_cuotas[0].fecha_vencimiento
            c2 = reg_cuotas[1].fecha_vencimiento
            diff = (c2 - c1).days
            
            if diff < 7: return 'Días'
            elif diff <= 13: return 'Semanas'
            elif diff <= 20: return 'Quincenas'
            else: return 'Meses'

        frecuencia_txt = detectar_frecuencia_local(credito, cuotas_qs)

        # ── BUFFER PDF ────────────────────────────────────────────────────
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=1.2 * cm,
            leftMargin=1.2 * cm,
            topMargin=1.2 * cm,
            bottomMargin=1.2 * cm,
        )

        # ── COLORES Y ESTILOS ─────────────────────────────────────────────
        DARK_BLUE   = colors.HexColor('#0F172A')   # Slate 900
        ACCENT_BLUE = colors.HexColor('#2563EB')   # Blue 600
        BG_LIGHT    = colors.HexColor('#F8FAFC')   # Slate 50
        TEXT_DARK   = colors.HexColor('#1E293B')   # Slate 800
        TEXT_MUTED  = colors.HexColor('#64748B')   # Slate 500
        BORDER_CLR  = colors.HexColor('#E2E8F0')   # Slate 200
        WHITE       = colors.white
        GOLD        = colors.HexColor('#F59E0B')   # Amber 500

        styles = getSampleStyleSheet()
        def style(name, **kwargs):
            base = styles.get(name, styles['Normal'])
            return ParagraphStyle(name + '_premium', parent=base, **kwargs)

        s_company      = style('Heading1', fontSize=18, fontName='Helvetica-Bold', textColor=DARK_BLUE, leading=20)
        s_company_sub  = style('Normal', fontSize=8,  fontName='Helvetica',      textColor=TEXT_MUTED, leading=10)
        s_doc_title    = style('Normal', fontSize=14, fontName='Helvetica-Bold', textColor=GOLD, alignment=TA_RIGHT, leading=16)
        s_doc_meta     = style('Normal', fontSize=9,  fontName='Helvetica',      textColor=TEXT_DARK, alignment=TA_RIGHT, leading=12)
        s_card_hdr     = style('Normal', fontSize=9,  fontName='Helvetica-Bold', textColor=ACCENT_BLUE, leading=12)
        s_label        = style('Normal', fontSize=7,  fontName='Helvetica-Bold', textColor=TEXT_MUTED, leading=8, textTransform='uppercase')
        s_value        = style('Normal', fontSize=9,  fontName='Helvetica-Bold', textColor=TEXT_DARK, leading=11)
        s_th           = style('Normal', fontSize=8,  fontName='Helvetica-Bold', textColor=WHITE, alignment=TA_CENTER)
        s_cell         = style('Normal', fontSize=8,  fontName='Helvetica',      textColor=TEXT_DARK, leading=10)
        s_cell_right   = style('Normal', fontSize=8,  fontName='Helvetica',      textColor=TEXT_DARK, alignment=TA_RIGHT)
        s_cell_center  = style('Normal', fontSize=8,  fontName='Helvetica',      textColor=TEXT_DARK, alignment=TA_CENTER)
        s_total_lbl    = style('Normal', fontSize=9,  fontName='Helvetica-Bold', textColor=TEXT_DARK, alignment=TA_RIGHT)
        s_total_val    = style('Normal', fontSize=10, fontName='Helvetica-Bold', textColor=ACCENT_BLUE, alignment=TA_RIGHT)
        s_section_hdr  = style('Normal', fontSize=10, fontName='Helvetica-Bold', textColor=DARK_BLUE, spaceBefore=10, spaceAfter=5)
        s_bank_name    = style('Normal', fontSize=9,  fontName='Helvetica-Bold', textColor=TEXT_DARK, leading=10)
        s_bank_acc     = style('Normal', fontSize=8,  fontName='Courier-Bold',   textColor=TEXT_DARK, leading=9)
        s_bank_agent   = style('Normal', fontSize=7,  fontName='Helvetica',      textColor=TEXT_MUTED, leading=8)

        story = []

        # ═══════════════════════════════════════════════════════════════════
        # SECCIÓN 1: ENCABEZADO PREMIUM
        # ═══════════════════════════════════════════════════════════════════
        from software.utils.logo_utils import get_logo_image_for_pdf
        logo_rl = get_logo_image_for_pdf(empresa, width_mm=35, height_mm=20, circular=False)
        
        company_info = [
            Paragraph(empresa.razonsocial, s_company),
            Paragraph(f"{sucursal.nombre_sucursal if sucursal else 'TIENDA PRINCIPAL'} - {sucursal.id_distrito.nombre_distrito if sucursal and sucursal.id_distrito else 'TARAPOTO'}", s_company_sub),
            Paragraph(f"Cobrador: {credito.idusuario.nombrecompleto if credito.idusuario else 'SISTEMA'} • Generado: {timezone.now().strftime('%d/%m/%Y %H:%M')}", s_company_sub),
        ]
        
        doc_info = [
            Paragraph("CRONOGRAMA DE PAGOS", s_doc_title),
            Paragraph(f"Solicitud Nº: <b>{credito.idventa.numero_comprobante if credito.idventa else credito.codigo_credito}</b>", s_doc_meta),
            Paragraph(f"Código: <b>{credito.codigo_credito}</b>", s_doc_meta),
        ]
        
        header_table = Table(
            [[logo_rl if logo_rl else '', company_info, doc_info]],
            colWidths=[4*cm, 8.5*cm, 6.1*cm]
        )
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), WHITE),
            ('BOX', (0, 0), (-1, -1), 0.8, BORDER_CLR),
            ('ROUNDEDCORNERS', [6, 6, 6, 6]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
            ('RIGHTPADDING', (0, 0), (-1, -1), 15),
            ('TOPPADDING', (0, 0), (-1, -1), 15),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 15))

        # ═══════════════════════════════════════════════════════════════════
        # SECCIÓN 2: INFORMACIÓN EN 3 COLUMNAS
        # ═══════════════════════════════════════════════════════════════════
        def make_info_card(title, icon, items):
            rows = [[Paragraph(f"<b>{title}</b>", s_card_hdr)]]
            for label, value in items:
                rows.append([Paragraph(label, s_label)])
                rows.append([Paragraph(value if value else '---', s_value)])
            
            t = Table(rows, colWidths=[6.2*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, 0), BG_LIGHT),
                ('BOX', (0, 0), (-1, -1), 0.5, BORDER_CLR),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ]))
            return t

        cliente_items = [
            ('NOMBRE', cliente.razonsocial),
            ('DNI/RUC', cliente.numdoc),
            ('TELÉFONO', cliente.telefono),
            ('DIRECCIÓN', cliente.direccion),
        ]
        
        garante_items = [
            ('NOMBRE', credito.id_garante.nombre if credito.id_garante else 'Sin Garante'),
            ('DNI/RUC', credito.id_garante.numdoc if credito.id_garante else '-'),
            ('TELÉFONO', credito.id_garante.telefono if credito.id_garante else '-'),
            ('CÓNYUGE', cliente.conyuge_nombre if cliente.conyuge_nombre else '-'),
        ]
        
        vendedor_obj = credito.idusuario
        if not vendedor_obj and credito.idventa:
            vendedor_obj = credito.idventa.idusuario

        credito_items = [
            ('VENDEDOR', vendedor_obj.nombrecompleto if vendedor_obj else '-'),
            ('F. EMISIÓN', credito.fecha_credito.strftime('%d/%m/%Y')),
            ('PLAZO', f"{credito.cantidad_cuotas} {frecuencia_txt}"),
            ('C. INICIAL / TOTAL', f"S/ {credito.monto_adelanto:,.2f} / S/ {credito.monto_total:,.2f}"),
        ]

        info_grid = Table(
            [[make_info_card('DATOS DEL CLIENTE', '', cliente_items),
              make_info_card('DATOS DEL GARANTE', '', garante_items),
              make_info_card('DETALLES DEL CRÉDITO', '', credito_items)]],
            colWidths=[6.2*cm, 6.2*cm, 6.2*cm]
        )
        info_grid.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(info_grid)
        story.append(Spacer(1, 15))

        # ═══════════════════════════════════════════════════════════════════
        # SECCIÓN 3: ARTÍCULOS FINANCIADOS
        # ═══════════════════════════════════════════════════════════════════
        story.append(Paragraph("ARTÍCULOS FINANCIADOS", s_section_hdr))
        prod_data = [[Paragraph('CANT.', s_th), Paragraph('ARTÍCULO', s_th), Paragraph('MARCA / MODELO', s_th), Paragraph('SERIE / MOTOR', s_th)]]
        
        for item in detalles_qs:
            if isinstance(item, dict):
                tipo, cant, veh, rep = item['tipo_item'], item['cantidad'], item['id_vehiculo'], item['id_repuesto_comprado']
            else:
                tipo, cant, veh, rep = item.tipo_item, item.cantidad, item.id_vehiculo, item.id_repuesto_comprado

            if tipo == 'vehiculo' and veh:
                nombre = veh.idproducto.nomproducto
                marca_mod = f"{veh.idproducto.idmarca.nombremarca if veh.idproducto.idmarca else '-'} / {veh.idproducto.idmodelo.nombremodelo if veh.idproducto.idmodelo else '-'}"
                serie = f"Motor: {veh.serie_motor}\nChasis: {veh.serie_chasis}"
            elif tipo == 'repuesto' and rep:
                nombre = rep.id_repuesto.nombre
                marca_mod = f"{rep.id_repuesto.idmarca.nombremarca if rep.id_repuesto.idmarca else '-'}"
                serie = f"Código: {rep.id_repuesto.codigo_barras or 'S/N'}"
            else: continue

            prod_data.append([
                Paragraph(str(cant), s_cell_center),
                Paragraph(nombre, s_cell),
                Paragraph(marca_mod, s_cell),
                Paragraph(serie, s_cell),
            ])

        prod_table = Table(prod_data, colWidths=[1.5*cm, 6.5*cm, 5*cm, 5.6*cm])
        prod_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), DARK_BLUE),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, BG_LIGHT]),
            ('BOX', (0, 0), (-1, -1), 0.5, BORDER_CLR),
            ('INNERGRID', (0, 0), (-1, -1), 0.3, BORDER_CLR),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(prod_table)
        story.append(Spacer(1, 15))

        # ═══════════════════════════════════════════════════════════════════
        # SECCIÓN 4: PLAN DE PAGOS
        # ═══════════════════════════════════════════════════════════════════
        story.append(HRFlowable(width='100%', thickness=0.5, color=BORDER_CLR, spaceBefore=5, spaceAfter=10))
        story.append(Paragraph("PLAN DE PAGOS", s_section_hdr))
        
        # Determinar etiqueta de la columna de cuota
        col_cuota_label = f"CUOTA {frecuencia_txt[:-1].upper()}" if frecuencia_txt.endswith('s') else f"CUOTA {frecuencia_txt.upper()}"
        if col_cuota_label == "CUOTA MESE": col_cuota_label = "CUOTA MES"
        if col_cuota_label == "CUOTA QUINCENA": col_cuota_label = "CUOTA QUINCENAL" # Ajuste gramatical
        
        plan_data = [[
            Paragraph('Nº', s_th), Paragraph('VENCIMIENTO', s_th), Paragraph('DÍAS', s_th),
            Paragraph(col_cuota_label, s_th), Paragraph('MORA', s_th), Paragraph('TOTAL A PAGAR', s_th),
            Paragraph('ESTADO', s_th)
        ]]
        
        totales = {'capital': Decimal('0'), 'mora': Decimal('0'), 'total': Decimal('0')}
        hoy_date = timezone.now().date()
        
        for c in cuotas_qs:
            mora_val, _, dias = calcular_interes_mora(c)
            total_fila = c.saldo_cuota + mora_val
            
            # Formatear estado
            estado_txt = c.estado_pago
            if c.fecha_vencimiento < hoy_date and c.estado_pago != 'Pagado':
                estado_txt = "VENCIDA"
            
            plan_data.append([
                Paragraph("Ini" if c.numero_cuota == 0 else f"{c.numero_cuota:02d}", s_cell_center),
                Paragraph(c.fecha_vencimiento.strftime('%d/%m/%Y'), s_cell_center),
                Paragraph(str(dias), s_cell_center),
                Paragraph(f"S/ {c.total:,.2f}", s_cell_right),
                Paragraph(f"S/ {mora_val:,.2f}", s_cell_right),
                Paragraph(f"S/ {total_fila:,.2f}", s_cell_right),
                Paragraph(estado_txt, s_cell_center),
            ])
            totales['capital'] += c.total
            totales['mora'] += mora_val
            totales['total'] += total_fila

        plan_data.append([
            '', Paragraph('TOTALES:', s_total_lbl), '',
            Paragraph(f"S/ {totales['capital']:,.2f}", s_total_val),
            Paragraph(f"S/ {totales['mora']:,.2f}", s_total_val),
            Paragraph(f"S/ {totales['total']:,.2f}", s_total_val),
            ''
        ])

        plan_table = Table(plan_data, colWidths=[1.2*cm, 3*cm, 1.5*cm, 3.2*cm, 3.2*cm, 3.2*cm, 3.3*cm])
        plan_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), DARK_BLUE),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [WHITE, BG_LIGHT]),
            ('BACKGROUND', (0, -1), (-1, -1), BG_LIGHT),
            ('BOX', (0, 0), (-1, -1), 0.5, BORDER_CLR),
            ('INNERGRID', (0, 0), (-1, -1), 0.3, BORDER_CLR),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(plan_table)
        story.append(Spacer(1, 15))

        # ═══════════════════════════════════════════════════════════════════
        # SECCIÓN 5: CANALES DE PAGO
        # ═══════════════════════════════════════════════════════════════════
        story.append(Paragraph("CANALES DE ATENCIÓN Y MEDIOS DE PAGO", s_section_hdr))
        
        # Nota para el cliente
        s_nota_premium = ParagraphStyle(
            'NotaCanalesPremium',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=7.5,
            textColor=colors.HexColor('#475569'), # Slate 600
            spaceBefore=2,
            spaceAfter=10,
            leading=10
        )
        story.append(Paragraph("NOTA: ESTIMADO CLIENTE, A FIN DE REALIZAR EL PAGO DE SUS CUOTAS, TIENE A SU DISPOSICIÓN LOS SIGUIENTES CANALES DE ATENCIÓN:", s_nota_premium))
        
        canales = CanalPago.objects.filter(estado=True).select_related('id_tipo_cuenta').order_by('orden', 'banco')
        if canales.exists():
            bank_rows = []
            temp_row = []
            for i, canal in enumerate(canales):
                bank_info = [
                    Paragraph(f"{canal.banco} ({canal.id_tipo_cuenta.nombre})", s_bank_name),
                ]
                if canal.titular:
                    bank_info.append(Paragraph(f"Titular: <b>{canal.titular}</b>", s_cell))
                bank_info.append(Paragraph(f"Cuenta: {canal.numero_cuenta}", s_bank_acc))
                if canal.cci:
                    bank_info.append(Paragraph(f"CCI: {canal.cci}", s_bank_acc))
                if canal.codigo_agente:
                    bank_info.append(Paragraph(f"Cód. Agente: <b>{canal.codigo_agente}</b>", s_bank_agent))
                
                t_bank = Table([[bank_info]], colWidths=[9*cm])
                t_bank.setStyle(TableStyle([
                    ('BOX', (0, 0), (-1, -1), 0.5, BORDER_CLR),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 5),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ]))
                temp_row.append(t_bank)
                
                if len(temp_row) == 2 or i == len(canales) - 1:
                    while len(temp_row) < 2: temp_row.append('')
                    bank_rows.append(temp_row)
                    temp_row = []
            
            bank_grid = Table(bank_rows, colWidths=[9.3*cm, 9.3*cm])
            bank_grid.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            story.append(bank_grid)
        
        # ═══════════════════════════════════════════════════════════════════
        # SECCIÓN 5.5: AVISO DE COBRANZA (Voucher)
        # ═══════════════════════════════════════════════════════════════════
        story.append(Spacer(1, 10))
        
        # Estilos específicos para el aviso
        s_adv_main = style('Normal', fontSize=8, textColor=colors.HexColor('#1E40AF'), leading=11)
        s_adv_name = style('Normal', fontSize=8.5, fontName='Helvetica-Bold', textColor=colors.HexColor('#0F172A'))
        s_adv_phone = style('Normal', fontSize=8, textColor=colors.HexColor('#475569'), backColor=colors.HexColor('#F1F5F9'))
        s_adv_mail = style('Normal', fontSize=8, textColor=colors.HexColor('#2563EB'))
        s_disclaimer = style('Normal', fontSize=7, textColor=colors.HexColor('#64748B'), alignment=TA_CENTER, italic=True)

        # Usar la información de la empresa en lugar de los cajeros
        contacto_empresa = []
        if empresa.telefono:
            contacto_empresa.append(f"<font face='Helvetica-Bold' color='#475569' backColor='#F1F5F9'>&nbsp;Tel: {empresa.telefono}&nbsp;</font>")
        
        correos = []
        if empresa.gmail_1: correos.append(empresa.gmail_1)
        if empresa.gmail_2: correos.append(empresa.gmail_2)
        
        if correos:
            correos_str = " / ".join(correos)
            contacto_empresa.append(f"<font face='Helvetica-Bold' color='#475569'>&nbsp;Gmail: </font><font color='#2563EB'>{correos_str}&nbsp;</font>")
            
        contacto_str = " &nbsp; ".join(contacto_empresa) if contacto_empresa else "Sin datos de contacto"

        u_info = Table([
            [Paragraph("Consultar con el área de cobranza.", s_adv_name)],
            [Paragraph(contacto_str, s_adv_main)]
        ], colWidths=[17.6*cm])
        u_info.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        
        user_rows = [[u_info]]

        adv_box_content = [
            [Paragraph("<b>Importante:</b> En caso realice el depósito a una cuenta corriente, agradeceré enviar <b>fotografía del voucher</b> a los siguientes números de celular o correos electrónicos del área de cobranza para el descargo respectivo:", s_adv_main)],
            [Table(user_rows, colWidths=[17.6*cm])]
        ]
        
        adv_table = Table(adv_box_content, colWidths=[18.4*cm])
        adv_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#EFF6FF')),
            ('LINEBEFORE', (0, 0), (0, -1), 3, colors.HexColor('#2563EB')),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ]))
        story.append(adv_table)
        story.append(Spacer(1, 15))
        story.append(Paragraph("*** Si al momento de recibir la presente, su cuota se encuentra cancelada, le agradecemos aceptar nuestras disculpas, quedando sin efecto la presente comunicación ***", s_disclaimer))

        # ═══════════════════════════════════════════════════════════════════
        # SECCIÓN 6: FIRMAS
        # ═══════════════════════════════════════════════════════════════════
        story.append(Spacer(1, 25))
        # Estilo para firmas (centrado y negrita)
        s_firma_hdr = style('Normal', fontSize=9, fontName='Helvetica-Bold', textColor=ACCENT_BLUE, alignment=TA_CENTER, leading=12)

        firma_data = [
            [Paragraph('___________________________', s_cell_center), Paragraph('___________________________', s_cell_center)],
            [Paragraph('FIRMA DEL CLIENTE', s_firma_hdr), Paragraph('ASESOR DE CRÉDITOS', s_firma_hdr)],
            [Paragraph(cliente.razonsocial, s_cell_center), Paragraph(vendedor_obj.nombrecompleto if vendedor_obj else 'SISTEMA', s_cell_center)],
        ]
        firma_table = Table(firma_data, colWidths=[9.3*cm, 9.3*cm])
        firma_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(firma_table)

        # ── CONSTRUIR PDF ────────────────────────────────────────────────
        doc.build(story)
        buffer.seek(0)
        
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="Cronograma_{credito.codigo_credito}.pdf"'
        return response
        
    except Exception as e:
        print(f"ERROR al generar cronograma: {str(e)}")
        import traceback
        traceback.print_exc()
        return HttpResponse(f"Error al generar el cronograma: {str(e)}", status=500)


def buscar_cuotas_cliente(request):
    """
    AJAX: Buscar cuotas pendientes de un cliente específico
    """
    if request.method == 'GET':
        idcliente = request.GET.get('idcliente')
        
        if not idcliente:
            return JsonResponse({'error': 'Cliente no especificado'}, status=400)
        
        # Obtener créditos activos del cliente
        creditos = Credito.objects.filter(
            idventa__idcliente_id=idcliente,
            estado=1,
            estado_credito__in=['activo', 'mora']
        )
        
        resultado = []
        for credito in creditos:
            cuotas = CuotasVenta.objects.filter(
                idventa=credito.idventa,
                estado=1,
                estado_pago__in=['Pendiente', 'Parcial']
            ).order_by('numero_cuota')
            
            for cuota in cuotas:
                resultado.append({
                    'idcuotaventa': cuota.idcuotaventa,
                    'codigo_credito': credito.codigo_credito,
                    'numero_cuota': cuota.numero_cuota,
                    'fecha_vencimiento': cuota.fecha_vencimiento.strftime('%d/%m/%Y'),
                    'total': float(cuota.total),
                    'monto_pagado': float(cuota.monto_pagado),
                    'saldo_cuota': float(cuota.saldo_cuota),
                    'estado_pago': cuota.estado_pago,
                    'vencida': cuota.esta_vencida()
                })
        
        return JsonResponse(resultado, safe=False)
    
    return JsonResponse({'error': 'Método no permitido'}, status=400)


def imprimir_recibo_pago(request, idpagocuota):
    """
    Genera un PDF del recibo de pago de cuota en formato TICKET 80mm
    Estructura exacta del recibo físico de D CREDITOS E.I.R.L
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
        from io import BytesIO
        import os
        from django.conf import settings
        from software.models.empresaModel import Empresa
        from django.utils import timezone
        
        # Obtener el pago
        pago = get_object_or_404(PagoCuota, idpagocuota=idpagocuota)
        cuota = pago.idcuotaventa
        if cuota.idventa:
            credito = Credito.objects.get(idventa=cuota.idventa)
            venta = cuota.idventa
            cliente = venta.idcliente
        else:
            credito = get_object_or_404(Credito, idcredito=cuota.idcredito_id)
            venta = None
            cliente = credito.idcliente
        
        # ✅ OBTENER LA EMPRESA
        try:
            if venta and venta.idempresa:
                emp_id = getattr(venta.idempresa, 'pk', venta.idempresa)
                empresa = Empresa.objects.get(pk=emp_id, activo=True)
            else:
                empresa = Empresa.objects.filter(activo=True).first()
            
            if not empresa:
                return HttpResponse("No se encontró información de la empresa.", status=400)
        except Empresa.DoesNotExist:
            return HttpResponse(f"La empresa no existe en el sistema.", status=400)
        
        # ✅ OBTENER VEHÍCULO Y PLACA
        placa_vehiculo = "EN TRÁMITE"
        nombre_vehiculo = "Vehículo"
        
        if venta:
            from software.models.VentaDetalleModel import VentaDetalle
            detalles = VentaDetalle.objects.filter(idventa=venta, estado=1, tipo_item='vehiculo').select_related(
                'id_vehiculo__idproducto'
            )
            if detalles.exists():
                primer_vehiculo = detalles.first().id_vehiculo
                if primer_vehiculo:
                    nombre_vehiculo = primer_vehiculo.idproducto.nomproducto
                    # ✅ OBTENER PLACA
                    from software.models.ImposicionPlacaModel import ImposicionPlaca
                    imposicion = ImposicionPlaca.objects.filter(idventa=venta, estado=1).order_by('-id_imposicion').first()
                    if imposicion:
                        if imposicion.numero_placa:
                            placa_vehiculo = imposicion.numero_placa
                        else:
                            placa_vehiculo = "EN TRÁMITE"
                    else:
                        if primer_vehiculo.placas and primer_vehiculo.placas.strip():
                            placa_vehiculo = primer_vehiculo.placas.strip()
                        else:
                            placa_vehiculo = "EN TRÁMITE"
        else:
            if credito.id_vehiculo:
                nombre_vehiculo = credito.id_vehiculo.idproducto.nomproducto
                if credito.id_vehiculo.placas and credito.id_vehiculo.placas.strip():
                    placa_vehiculo = credito.id_vehiculo.placas.strip()
                else:
                    placa_vehiculo = "EN TRÁMITE"
            elif credito.id_repuesto_comprado:
                nombre_vehiculo = credito.id_repuesto_comprado.id_repuesto.nombre
                placa_vehiculo = "REPUESTO"
        
        # Generar número de recibo — usa la serie configurada en BD (Tipo: RI)
        # Fallback al correlativo clásico si no existe serie configurada
        numero_recibo = None
        try:
            with transaction.atomic():
                tipo_ri = Tipocomprobante.objects.filter(codigo='RI', estado=1).first()
                if tipo_ri:
                    serie_ri = Seriecomprobante.objects.select_for_update().filter(
                        idtipocomprobante=tipo_ri, estado=1
                    ).first()
                    if serie_ri:
                        serie_ri.numero_actual += 1
                        serie_ri.save(update_fields=['numero_actual'])
                        numero_recibo = f"{serie_ri.serie}-{str(serie_ri.numero_actual).zfill(6)}"
        except Exception:
            pass

        if not numero_recibo:
            # Fallback: correlativo por cantidad de pagos realizados
            # En lugar de contar CuotasVenta, contamos los Pagos reales hasta este momento
            # Esto garantiza un incremento real por cada pago
            correlativo = PagoCuota.objects.filter(
                estado=1,
                idpagocuota__lte=idpagocuota
            ).count()
            numero_recibo = f"RI-{str(max(1, correlativo)).zfill(6)}"
        
        # ✅ CALCULAR CUOTAS PENDIENTES Y ATRASADAS
        if venta:
            cuotas_totales = CuotasVenta.objects.filter(idventa=venta, estado=1).count()
            cuotas_pagadas = CuotasVenta.objects.filter(idventa=venta, estado=1, estado_pago='Pagado').count()
        else:
            cuotas_totales = CuotasVenta.objects.filter(idcredito=credito, estado=1).count()
            cuotas_pagadas = CuotasVenta.objects.filter(idcredito=credito, estado=1, estado_pago='Pagado').count()
        cuotas_pendientes = cuotas_totales - cuotas_pagadas
        
        # Cuotas atrasadas (vencidas y no pagadas)
        hoy = timezone.now().date()
        if venta:
            cuotas_atrasadas = CuotasVenta.objects.filter(
                idventa=venta,
                estado=1,
                estado_pago__in=['Pendiente', 'Parcial'],
                fecha_vencimiento__lt=hoy
            ).count()
        else:
            cuotas_atrasadas = CuotasVenta.objects.filter(
                idcredito=credito,
                estado=1,
                estado_pago__in=['Pendiente', 'Parcial'],
                fecha_vencimiento__lt=hoy
            ).count()
        
        # Crear el PDF en memoria
        buffer = BytesIO()
        ticket_width = 80 * mm
        

        
        ancho_util = 74 * mm
        elements = []
        styles = getSampleStyleSheet()
        
        # ==========================================
        # ESTILOS
        # ==========================================
        style_company = ParagraphStyle(
            'CompanyName',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.black,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            spaceAfter=0.5*mm,
            leading=10
        )
        
        style_normal_center = ParagraphStyle(
            'NormalCenter',
            parent=styles['Normal'],
            fontSize=7,
            alignment=TA_CENTER,
            spaceAfter=0.5*mm,
            leading=8
        )
        
        style_label = ParagraphStyle(
            'Label',
            parent=styles['Normal'],
            fontSize=7,
            alignment=TA_LEFT,
            spaceAfter=0.5*mm,
            leading=8
        )
        
        style_title = ParagraphStyle(
            'Title',
            parent=styles['Normal'],
            fontSize=9,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
            spaceAfter=1*mm,
            leading=10
        )
        
        style_importe = ParagraphStyle(
            'Importe',
            parent=styles['Normal'],
            fontSize=12,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
            spaceAfter=1*mm,
            leading=14
        )
        
        style_small = ParagraphStyle(
            'Small',
            parent=styles['Normal'],
            fontSize=6,
            alignment=TA_CENTER,
            spaceAfter=0.5*mm,
            leading=7
        )
        
        style_small_left = ParagraphStyle(
            'SmallLeft',
            parent=styles['Normal'],
            fontSize=6,
            alignment=TA_LEFT,
            spaceAfter=0.5*mm,
            leading=7
        )
        
        # LOGO DESDE CLOUDINARY
        logo_rl = get_logo_image_for_pdf(empresa, width_mm=30, height_mm=30, circular=True, use_ticket_logo=True)
        if logo_rl:
            elements.append(logo_rl)
            elements.append(Spacer(1, 3*mm))
        
        # ==========================================
        # DATOS DE LA EMPRESA
        # ==========================================
        nombre_empresa = empresa.razonsocial if empresa.razonsocial else empresa.nombrecomercial
        elements.append(Paragraph(nombre_empresa.upper(), style_company))
        
        # Dirección (ajustar formato según imagen)
        direccion_local = empresa.direccion.upper() if empresa.direccion else "TARAPOTO"
        elements.append(Paragraph(f"Local: {direccion_local}", style_small))
        
        elements.append(Paragraph(f"TELEFONOS: {empresa.telefono}", style_small))
        elements.append(Paragraph(f"<b>RUC: {empresa.ruc}</b>", style_normal_center))
        elements.append(Paragraph(f"<b>RECIBO {numero_recibo}</b>", style_title))
        
        elements.append(Spacer(1, 2*mm))
        
        # ==========================================
        # DATOS DEL CLIENTE
        # ==========================================
        elements.append(Paragraph("<b>CLIENTE</b>", style_label))
        elements.append(Paragraph(f"DNI: {cliente.numdoc or '---'}", style_label))
        elements.append(Paragraph(cliente.razonsocial.upper(), style_small_left))
        
        direccion = cliente.direccion or 'JR MPSM'
        elements.append(Paragraph(direccion.upper(), style_small_left))

        elements.append(Spacer(1, 2*mm))
        
        # ==========================================
        # DETALLE DE PRODUCTOS/VEHÍCULOS
        # ==========================================
        elements.append(Paragraph("<b>DESCRIPCIÓN</b>", style_label))
        elements.append(Spacer(1, 1*mm))
        
        # Obtener todos los detalles de la venta
        if venta:
            from software.models.VentaDetalleModel import VentaDetalle
            detalles_venta = VentaDetalle.objects.filter(idventa=venta, estado=1).select_related(
                'id_vehiculo__idproducto',
                'id_repuesto_comprado__id_repuesto'
            )
            
            # Construir lista de productos
            for detalle in detalles_venta:
                if detalle.tipo_item == 'vehiculo' and detalle.id_vehiculo:
                    vehiculo = detalle.id_vehiculo
                    nombre_producto = vehiculo.idproducto.nomproducto
                    
                    # Agregar nombre del producto
                    elements.append(Paragraph(nombre_producto.upper(), style_small_left))
                    
                    # Agregar serie motor si existe
                    if vehiculo.serie_motor:
                        elements.append(Paragraph(f"Motor: {vehiculo.serie_motor}", style_small_left))
                    
                    # Agregar serie chasis si existe
                    if vehiculo.serie_chasis:
                        elements.append(Paragraph(f"Chasis: {vehiculo.serie_chasis}", style_small_left))
                    
                    # ✅ AGREGAR PLACA DEBAJO DEL CHASIS
                    placa_asignada = "EN TRÁMITE"
                    from software.models.ImposicionPlacaModel import ImposicionPlaca
                    imposicion = ImposicionPlaca.objects.filter(idventa=venta, estado=1).order_by('-id_imposicion').first()
                    if imposicion:
                        if imposicion.numero_placa:
                            placa_asignada = imposicion.numero_placa
                        else:
                            placa_asignada = "EN TRÁMITE"
                    else:
                        if vehiculo.placas and vehiculo.placas.strip():
                            placa_asignada = vehiculo.placas.strip()
                        else:
                            placa_asignada = "EN TRÁMITE"

                    elements.append(Paragraph(f"Placa: {placa_asignada.upper()}", style_small_left))
                    
                elif detalle.tipo_item == 'repuesto' and detalle.id_repuesto_comprado:
                    repuesto = detalle.id_repuesto_comprado
                    nombre_repuesto = repuesto.id_repuesto.nombre
                    
                    # Agregar nombre del repuesto
                    elements.append(Paragraph(nombre_repuesto.upper(), style_small_left))
                    
                    # Agregar código de barras si existe
                    if repuesto.id_repuesto.codigo_barras:
                        elements.append(Paragraph(f"Código: {repuesto.id_repuesto.codigo_barras}", style_small_left))
        else:
            # Crédito directo
            if credito.tipo_item == 'vehiculo' and credito.id_vehiculo:
                vehiculo = credito.id_vehiculo
                nombre_producto = vehiculo.idproducto.nomproducto
                
                # Agregar nombre del producto
                elements.append(Paragraph(nombre_producto.upper(), style_small_left))
                
                # Agregar serie motor si existe
                if vehiculo.serie_motor:
                    elements.append(Paragraph(f"Motor: {vehiculo.serie_motor}", style_small_left))
                
                # Agregar serie chasis si existe
                if vehiculo.serie_chasis:
                    elements.append(Paragraph(f"Chasis: {vehiculo.serie_chasis}", style_small_left))
                
                # Placa
                placa_asignada = "PENDIENTE"
                if vehiculo.placas and vehiculo.placas.strip():
                    placa_asignada = vehiculo.placas.strip()
                elements.append(Paragraph(f"Placa: {placa_asignada.upper()}", style_small_left))
                
            elif credito.tipo_item == 'repuesto' and credito.id_repuesto_comprado:
                repuesto = credito.id_repuesto_comprado
                nombre_repuesto = repuesto.id_repuesto.nombre
                
                # Agregar nombre del repuesto
                elements.append(Paragraph(nombre_repuesto.upper(), style_small_left))
                
                # Agregar código de barras si existe
                if repuesto.id_repuesto.codigo_barras:
                    elements.append(Paragraph(f"Código: {repuesto.id_repuesto.codigo_barras}", style_small_left))
        
        elements.append(Spacer(1, 2*mm))
        
        # ==========================================
        # FECHA Y HORA
        # ==========================================
        fecha_str = pago.fecha_pago.strftime('%d/%m/%Y')
        hora_str = pago.fecha_pago.strftime('%H:%M')
        
        elements.append(Paragraph(f"<b>FECHA EMISION:</b> {fecha_str}", style_label))
        elements.append(Paragraph(f"<b>HORA:</b> {hora_str}", style_small_left))
        
        elements.append(Spacer(1, 1*mm))
        
        # ==========================================
        # MONEDA Y FORMA DE PAGO
        # ==========================================
        elements.append(Paragraph("<b>MONEDA: SOLES</b>", style_small_left))
        
        tipo_pago_nombre = pago.id_tipo_pago.nombre if pago.id_tipo_pago else 'EFECTIVO'
        elements.append(Paragraph(f"<b>FORMA DE PAGO: {tipo_pago_nombre.upper()}</b>", style_small_left))

        # ✅ MEJORA: SECCIÓN DE OBSERVACIONES SI ES PAGO MÚLTIPLE
        if tipo_pago_nombre.upper() == "MÚLTIPLE" and pago.observaciones:
            # Limpiar el texto si tiene el prefijo [FRACCIONADO: ...] y remover marcadores de [MULTIPAGO:...]
            import re as _re
            obs_limpia = pago.observaciones
            # Extraer solo el contenido de [FRACCIONADO: ...]
            match_frac = _re.search(r'\[FRACCIONADO: (.*?)\]', obs_limpia)
            if match_frac:
                obs_texto = match_frac.group(1)
            else:
                # Si no tiene el tag FRACCIONADO, solo limpiamos los tags de MULTIPAGO
                obs_texto = _re.sub(r'\[MULTIPAGO:.*?\]', '', obs_limpia).strip()
            
            elements.append(Paragraph(f"<b>DETALLE:</b> {obs_texto}", style_small_left))

        cajero = pago.idusuario.nombrecompleto.upper()
        elements.append(Paragraph(f"<b>CAJERO(A): {cajero}</b>", style_small_left))
        
        # Mostrar la caja del pago
        caja_nombre = pago.id_movimiento_caja.id_caja.nombre_caja if pago.id_movimiento_caja and pago.id_movimiento_caja.id_caja else 'Caja Principal'
        elements.append(Paragraph(f"<b>CAJA: {caja_nombre}</b>", style_small_left))
        
        elements.append(Paragraph("<b>CONCEPTO:</b> COBRANZA DE CUOTAS", style_small_left))
        
        elements.append(Spacer(1, 2*mm))
        
        # ==========================================
        # CUADRO DE INFORMACIÓN DEL CRÉDITO
        # ==========================================
        fecha_emision_credito = credito.fecha_credito.strftime('%Y-%m-%d')
        
        if credito.idventa:
            cuotas_activas = CuotasVenta.objects.filter(idventa=credito.idventa, estado=1)
            # Sumar pagos posteriores para obtener el saldo histórico
            from django.db.models import Sum
            pagos_posteriores = PagoCuota.objects.filter(
                idcuotaventa__idventa=credito.idventa,
                estado=1,
                idpagocuota__gt=pago.idpagocuota
            ).aggregate(total=Sum('monto_pago'))['total'] or 0
        else:
            cuotas_activas = CuotasVenta.objects.filter(idcredito=credito, estado=1)
            from django.db.models import Sum
            pagos_posteriores = PagoCuota.objects.filter(
                idcuotaventa__idcredito=credito,
                estado=1,
                idpagocuota__gt=pago.idpagocuota
            ).aggregate(total=Sum('monto_pago'))['total'] or 0
            
        total_pendiente_real = sum(c.saldo_cuota for c in cuotas_activas) + pagos_posteriores
        
        data_credito_info = [
            ['CREDITO', 'FECHA', 'IMPORTE', 'SALDO'],
            [
                credito.codigo_credito,
                fecha_emision_credito,
                f'S/ {credito.monto_total:,.2f}',
                f'S/ {total_pendiente_real:,.2f}'
            ]
        ]
        
        table_credito_info = Table(data_credito_info, colWidths=[16*mm, 22*mm, 20*mm, 16*mm])
        table_credito_info.setStyle(TableStyle([
            # Primera fila (encabezados) - en negrita
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 6),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Segunda fila (datos)
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, 1), 6),
            ('ALIGN', (0, 1), (1, 1), 'CENTER'),
            ('ALIGN', (2, 1), (2, 1), 'CENTER'),
            ('ALIGN', (3, 1), (3, 1), 'RIGHT'),
            
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            # Diseño con rayas (sin bordes verticales)
            ('LINEABOVE', (0, 0), (-1, 0), 0.5, colors.black),
            ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.black),
            ('LINEBELOW', (0, -1), (-1, -1), 0.5, colors.black),
        ]))
        elements.append(table_credito_info)
        
        elements.append(Spacer(1, 2*mm))
        
        # ==========================================
        # PAGO LETRA
        # ==========================================
        elements.append(Paragraph("<b>PAGO DE ALQUILER</b>", style_normal_center))
        
        # ✅ DETERMINAR SI ES PAGO COMPLETO O AMORTIZADO
        if cuota.saldo_cuota == 0:
            tipo_pago_letra = "CUOTA PAGADA"
            texto_inicial = "Inicial pagada"
        else:
            tipo_pago_letra = "AMORTIZADO"
            texto_inicial = "Inicial Amortizada"
        
        # ✅ LETRA PAGADA = NÚMERO DE CUOTA + TIPO DE PAGO
        if cuota.numero_cuota == 0:
            # Para la cuota inicial, usamos un texto más amigable solicitado por el usuario
            texto_cuota = f"<b>{texto_inicial}</b>"
        else:
            texto_cuota = f"<b>CUOTA PAGADA: ({cuota.numero_cuota}) {tipo_pago_letra}</b>"

        elements.append(Paragraph(texto_cuota, style_label))
        
        # Fecha de vencimiento
        fecha_venc = cuota.fecha_vencimiento.strftime('%d/%m/%Y')
        elements.append(Paragraph(f"<b>F. VENCIMIENTO:</b> {fecha_venc}", style_small_left))
        
        # ✅ PENDIENTES Y ATRASADAS
        elements.append(Paragraph(
            f"<b>PENDIENTES {cuotas_pendientes} / ATRAZADAS {cuotas_atrasadas}</b>", 
            style_small_left
        ))
        
        elements.append(Spacer(1, 3*mm))
        
        # ==========================================
        # IMPORTE TOTAL
        # ==========================================
        elements.append(Paragraph(
            f"<b>Importe Total {pago.monto_pago:.2f}</b>", 
            style_importe
        ))
        
        elements.append(Spacer(1, 2*mm))
        
        # ==========================================
        # MONTO EN LETRAS
        # ==========================================
        try:
            from software.utils.numero_a_letras import numero_a_letras
            monto_letras = numero_a_letras(pago.monto_pago)
        except:
            parte_entera = int(pago.monto_pago)
            parte_decimal = int((pago.monto_pago - parte_entera) * 100)
            monto_letras = f"CON {parte_decimal:02d}/100"
        
        elements.append(Paragraph(
            f"<b>SON: {monto_letras.upper()} SOLES</b>", 
            style_normal_center
        ))
        elements.append(Paragraph(
            "Cobro cuotas", 
            style_normal_center
        ))
        
        elements.append(Spacer(1, 3*mm))
        
        elements.append(Spacer(1, 3*mm))
        
        # ==========================================
        # LÍNEA DE CORTE
        # ==========================================
        elements.append(Paragraph(
            "- - - - - - - - - - - - - - - - - - - - - - - -", 
            style_normal_center
        ))
        
        # Calcular altura total de todos los elementos
        total_height = 0
        ancho_util = ticket_width - (6 * mm)
        for element in elements:
            if hasattr(element, 'wrap'):
                try:
                    w, h = element.wrap(ancho_util, 2000 * mm)
                    total_height += h
                except:
                    total_height += 15 * mm # Valor por defecto seguro
                    
        doc_height = total_height + (35 * mm) # Amplio margen para evitar saltos de página a otra hoja
        if doc_height < 100 * mm:  # Minimo
            doc_height = 100 * mm

        doc = SimpleDocTemplate(
            buffer, 
            pagesize=(ticket_width, doc_height),
            rightMargin=3*mm,
            leftMargin=3*mm,
            topMargin=3*mm, 
            bottomMargin=3*mm
        )
        
        # Construir el PDF
        doc.build(elements)
        
        buffer.seek(0)
        
        response = FileResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="recibo_{numero_recibo}.pdf"'
        
        return response
        
    except Exception as e:
        print(f"ERROR al generar recibo: {str(e)}")
        import traceback
        traceback.print_exc()
        return HttpResponse(f"Error al generar el recibo: {str(e)}", status=500)


@requiere_caja_aperturada
def pagar_total_credito(request):
    """
    Vista para pagar la totalidad del crédito pendiente con descuento opcional.
    Soporta múltiples métodos de pago (Yape, Plin, Efectivo, etc.)
    """
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)
    
    try:
        with transaction.atomic():
            id_credito = request.POST.get('id_credito')
            descuento_total = Decimal(request.POST.get('descuento', '0') or '0')
            observaciones_base = request.POST.get('observaciones', '').strip()
            idusuario = request.session.get('idusuario')

            # Fecha manual o actual
            fecha_pago_str = request.POST.get('fecha_pago')
            if fecha_pago_str:
                try:
                    fecha_pago_date = datetime.strptime(fecha_pago_str, '%Y-%m-%d').date()
                    fecha_pago_final = timezone.make_aware(datetime.combine(fecha_pago_date, timezone.now().time()))
                except ValueError:
                    fecha_pago_final = timezone.now()
            else:
                fecha_pago_final = timezone.now()

            # --- Métodos de pago múltiples ---
            tipos_pago_ids = request.POST.getlist('tipo_pago_id[]')
            montos_item    = request.POST.getlist('monto_pago_item[]')
            nros_operacion = request.POST.getlist('nro_operacion[]')

            if not tipos_pago_ids or not montos_item:
                return JsonResponse({'ok': False, 'error': 'Debe registrar al menos un método de pago.'}, status=400)

            # Calcular total y desglose
            monto_metodos_total = Decimal('0')
            desglose_pagos = []
            for i in range(len(tipos_pago_ids)):
                if not tipos_pago_ids[i] or not montos_item[i]: continue
                t_id  = int(tipos_pago_ids[i])
                m_val = Decimal(montos_item[i])
                n_op  = nros_operacion[i].strip() if i < len(nros_operacion) else ''
                if m_val <= 0: continue
                monto_metodos_total += m_val
                tp_obj = get_object_or_404(TipoPago, id_tipo_pago=t_id)
                desglose_pagos.append({'nombre': tp_obj.nombre, 'monto': m_val, 'op': n_op, 'id': t_id})

            if monto_metodos_total <= 0:
                return JsonResponse({'ok': False, 'error': 'El monto total debe ser mayor a 0.'}, status=400)

            credito = get_object_or_404(Credito, idcredito=id_credito)

            # Obtener cuotas pendientes
            if credito.idventa:
                cuotas = CuotasVenta.objects.filter(idventa=credito.idventa, estado=1, estado_pago__in=['Pendiente', 'Parcial']).order_by('numero_cuota')
            else:
                cuotas = CuotasVenta.objects.filter(idcredito=credito, estado=1, estado_pago__in=['Pendiente', 'Parcial']).order_by('numero_cuota')

            if not cuotas.exists():
                return JsonResponse({'ok': False, 'error': 'No hay cuotas pendientes para este crédito'}, status=400)

            # Verificar caja abierta
            apertura_actual = AperturaCierreCaja.objects.filter(
                idusuario_id=idusuario, estado__in=['abierta', 'reabierta']
            ).first()
            if not apertura_actual:
                return JsonResponse({'ok': False, 'error': 'No tiene una caja abierta.'}, status=400)

            total_principal = sum(c.saldo_cuota for c in cuotas)
            total_mora = sum(calcular_interes_mora(c)[0] for c in cuotas)
            total_a_pagar_sin_descuento = total_principal + total_mora

            # Validación de descuento
            total_interes_pendiente = sum(
                max(Decimal('0'), c.saldo_cuota - max(Decimal('0'), c.monto - c.monto_pagado))
                for c in cuotas
            )
            if descuento_total > total_interes_pendiente:
                return JsonResponse({
                    'ok': False,
                    'error': f'El descuento (S/ {descuento_total}) no puede ser mayor al interés pendiente (S/ {total_interes_pendiente:.2f})'
                }, status=400)

            monto_final_cobrado = total_a_pagar_sin_descuento - descuento_total

            # Validar que los métodos de pago coincidan con el monto final (±0.01)
            if abs(monto_metodos_total - monto_final_cobrado) > Decimal('0.01'):
                return JsonResponse({
                    'ok': False,
                    'error': f'La suma de métodos (S/ {monto_metodos_total}) no coincide con el monto final (S/ {monto_final_cobrado:.2f})'
                }, status=400)

            # Determinar tipo de pago y observaciones
            if len(desglose_pagos) > 1:
                tp_multiple = TipoPago.objects.filter(nombre__iexact='Múltiple').first()
                id_tipo_pago_final = tp_multiple.id_tipo_pago if tp_multiple else desglose_pagos[0]['id']
                detalle_obs = " | ".join([f"{d['nombre']}: S/ {d['monto']}" + (f" (Op:{d['op']})" if d['op'] else "") for d in desglose_pagos])
                observaciones_final = f"[FRACCIONADO: {detalle_obs}]"
                if observaciones_base:
                    observaciones_final = f"{observaciones_base} {observaciones_final}"
                numero_operacion_final = "Múltiple"
            else:
                id_tipo_pago_final = desglose_pagos[0]['id']
                numero_operacion_final = desglose_pagos[0]['op']
                observaciones_final = observaciones_base

            # Registrar Movimiento de Caja (uno solo)
            from software.models.movimientoCajaModel import MovimientoCaja
            nombre_cliente = (
                credito.idventa.idcliente.razonsocial if credito.idventa
                else (credito.idcliente.razonsocial if credito.idcliente else 'N/A')
            )
            movimiento = MovimientoCaja.objects.create(
                id_caja=apertura_actual.id_caja,
                id_movimiento=apertura_actual,
                idusuario_id=idusuario,
                tipo_movimiento='ingreso',
                monto=monto_final_cobrado,
                descripcion=f"PAGO TOTAL CRÉDITO {credito.codigo_credito} - {nombre_cliente}" + (f" (Desc: S/ {descuento_total})" if descuento_total > 0 else ""),
                fecha_movimiento=timezone.now(),
                estado=1
            )

            # Distribuir descuento y registrar PagoCuota por cuota
            descuento_pendiente = descuento_total
            for cuota in cuotas:
                monto_mora, _, _ = calcular_interes_mora(cuota)
                monto_total_cuota = cuota.saldo_cuota + monto_mora
                desc_esta_cuota = min(descuento_pendiente, monto_total_cuota)
                monto_pago_efectivo = monto_total_cuota - desc_esta_cuota

                obs_cuota = observaciones_final
                if desc_esta_cuota > 0:
                    obs_cuota = f"{obs_cuota} [DESC S/ {desc_esta_cuota}]".strip()

                PagoCuota.objects.create(
                    idcuotaventa=cuota,
                    idusuario_id=idusuario,
                    id_tipo_pago_id=id_tipo_pago_final,
                    monto_pago=monto_pago_efectivo,
                    id_movimiento_caja=movimiento,
                    numero_operacion=numero_operacion_final,
                    observaciones=obs_cuota,
                    estado=1,
                    fecha_pago=fecha_pago_final
                )

                cuota.monto_pagado += monto_pago_efectivo
                cuota.descuento   += desc_esta_cuota
                cuota.interes_mora += monto_mora
                cuota.saldo_cuota  = 0
                cuota.estado_pago  = 'Pagado'
                cuota.fecha_pago   = fecha_pago_final
                cuota.save()

                descuento_pendiente -= desc_esta_cuota

            credito.actualizar_estado()

            return JsonResponse({
                'ok': True,
                'message': 'Crédito pagado totalmente con éxito',
                'idmovimiento': movimiento.id_movimiento_caja
            })

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


# =============================================================================
# PAGO MÚLTIPLE DE CUOTAS
# =============================================================================

@requiere_caja_aperturada
def pagar_cuotas_multiples(request):
    """
    Vista para pagar múltiples cuotas en una sola transacción.
    GET  → muestra el formulario con las cuotas seleccionadas y el total.
    POST → registra un PagoCuota por cada cuota y un único movimiento de caja.
    """
    if request.method == 'GET':
        cuotas_ids_str = request.GET.get('cuotas', '').strip()
        if not cuotas_ids_str:
            return redirect('creditos')

        try:
            cuotas_ids = [int(x) for x in cuotas_ids_str.split(',') if x.strip()]
        except ValueError:
            return redirect('creditos')

        cuotas = CuotasVenta.objects.filter(
            idcuotaventa__in=cuotas_ids,
            estado=1,
            estado_pago__in=['Pendiente', 'Parcial']
        ).select_related('idventa').order_by('numero_cuota')

        if not cuotas.exists():
            return redirect('creditos')

        c_first = cuotas.first()
        if c_first.idventa:
            venta = c_first.idventa
            credito = get_object_or_404(Credito, idventa=venta)
            # Verificar que todas las cuotas pertenecen al mismo crédito
            if not all(c.idventa_id == venta.idventa for c in cuotas):
                return redirect('creditos')
        else:
            venta = None
            credito = c_first.idcredito
            if not all(c.idcredito_id == (credito.idcredito if credito else None) for c in cuotas):
                return redirect('creditos')

        total_a_pagar = sum(c.saldo_cuota for c in cuotas)
        tipos_pago = TipoPago.objects.filter(estado=1)

        if credito.idventa:
            cuotas_activas = CuotasVenta.objects.filter(idventa=credito.idventa, estado=1)
        else:
            cuotas_activas = CuotasVenta.objects.filter(idcredito=credito, estado=1)
            
        total_pendiente_real = sum(c.saldo_cuota for c in cuotas_activas)

        # ── VALIDACIÓN SECUENCIAL (GET) ───────────────────────────────────────
        error_secuencia = validar_seleccion_multiple(cuotas, credito)
        if error_secuencia:
            from django.contrib import messages
            messages.error(request, error_secuencia)
            return redirect('detalle_credito', credito.idcredito)
        # ── FIN VALIDACIÓN SECUENCIAL ─────────────────────────────────────────



        data = {
            'cuotas': cuotas,
            'credito': credito,
            'venta': venta,
            'total_a_pagar': total_a_pagar,
            'cuotas_ids': cuotas_ids_str,
            'tipos_pago': tipos_pago,
            'total_pendiente': total_pendiente_real,
        }
        return render(request, 'creditos/pagar_cuotas_multiples.html', data)

    elif request.method == 'POST':
        try:
            with transaction.atomic():
                cuotas_ids_str = request.POST.get('cuotas_ids', '').strip()
                idusuario        = request.session.get('idusuario')

                # Obtener montos y tipos de pago (MÉTODOS)
                tipos_pago_ids = request.POST.getlist('tipo_pago_id[]')
                montos_metodos = request.POST.getlist('monto_pago_item[]')
                nros_operacion = request.POST.getlist('nro_operacion[]')
                
                observaciones_base = request.POST.get('observaciones', '').strip()

                # Fecha manual o actual
                fecha_pago_str = request.POST.get('fecha_pago')
                if fecha_pago_str:
                    try:
                        fecha_pago_date = datetime.strptime(fecha_pago_str, '%Y-%m-%d').date()
                        fecha_pago_final = timezone.make_aware(datetime.combine(fecha_pago_date, timezone.now().time()))
                    except ValueError:
                        fecha_pago_final = timezone.now()
                else:
                    fecha_pago_final = timezone.now()

                # Calcular total pagado (suma de métodos)
                monto_total_pagado = Decimal('0')
                desglose_pagos = []
                for i in range(len(tipos_pago_ids)):
                    if not tipos_pago_ids[i] or not montos_metodos[i]: continue
                    t_id = int(tipos_pago_ids[i])
                    m_val = Decimal(montos_metodos[i])
                    n_op = nros_operacion[i].strip() if i < len(nros_operacion) else ''
                    if m_val <= 0: continue
                    monto_total_pagado += m_val
                    tp_obj = get_object_or_404(TipoPago, id_tipo_pago=t_id)
                    desglose_pagos.append({'nombre': tp_obj.nombre, 'monto': m_val, 'op': n_op, 'id': t_id})

                if monto_total_pagado <= 0:
                    return JsonResponse({'ok': False, 'error': 'El monto total pagado debe ser mayor a 0.'}, status=400)

                # Cuotas a pagar
                cuotas_ids = [int(x) for x in cuotas_ids_str.split(',') if x.strip()]
                cuotas = CuotasVenta.objects.filter(
                    idcuotaventa__in=cuotas_ids,
                    estado=1,
                    estado_pago__in=['Pendiente', 'Parcial']
                ).select_related('idventa').order_by('numero_cuota')

                if not cuotas.exists():
                    return JsonResponse({'ok': False, 'error': 'No se encontraron cuotas válidas'}, status=400)

                c_first = cuotas.first()
                credito = get_object_or_404(Credito, idventa=c_first.idventa) if c_first.idventa else c_first.idcredito

                # ── VALIDACIÓN SECUENCIAL (POST) ──────────────────────────────
                error_secuencia = validar_seleccion_multiple(cuotas, credito)
                if error_secuencia:
                    return JsonResponse({'ok': False, 'error': error_secuencia}, status=400)
                # ── FIN VALIDACIÓN SECUENCIAL ─────────────────────────────────

                # Verificar caja abierta

                apertura_actual = AperturaCierreCaja.objects.filter(
                    idusuario_id=idusuario,
                    estado__in=['abierta', 'reabierta']
                ).first()

                if not apertura_actual:
                    return JsonResponse({'ok': False, 'error': 'No tiene una caja abierta.'}, status=400)

                # Determinar el tipo de pago principal y formatear observaciones
                if len(desglose_pagos) > 1:
                    tp_multiple = TipoPago.objects.filter(nombre__iexact='Múltiple').first()
                    id_tipo_pago_final = tp_multiple.id_tipo_pago if tp_multiple else desglose_pagos[0]['id']
                    detalle_obs = " | ".join([f"{d['nombre']}: S/ {d['monto']}" + (f" (Op:{d['op']})" if d['op'] else "") for d in desglose_pagos])
                    observaciones_final = f"[FRACCIONADO: {detalle_obs}]"
                    if observaciones_base: observaciones_final = f"{observaciones_base} {observaciones_final}"
                    numero_operacion_final = "Múltiple"
                else:
                    id_tipo_pago_final = desglose_pagos[0]['id']
                    numero_operacion_final = desglose_pagos[0]['op']
                    observaciones_final = observaciones_base

                pagos_ids      = []
                total_cuotas_verif = Decimal('0')
                numeros_cuotas = []

                detalles_cuotas_json = request.POST.get('detalles_pagos')
                if not detalles_cuotas_json:
                    return JsonResponse({'ok': False, 'error': 'No se enviaron los detalles de las cuotas'}, status=400)
                
                detalles_cuotas = json.loads(detalles_cuotas_json)
                mapa_montos = {int(item['id_cuota']): Decimal(str(item['monto'])) for item in detalles_cuotas}

                # Registrar un PagoCuota por cada cuota seleccionada
                for cuota in cuotas:
                    monto_a_cuota = mapa_montos.get(cuota.idcuotaventa)
                    if monto_a_cuota is None or monto_a_cuota <= 0: continue

                    pago = PagoCuota.objects.create(
                        idcuotaventa=cuota,
                        idusuario_id=idusuario,
                        id_tipo_pago_id=id_tipo_pago_final,
                        monto_pago=monto_a_cuota,
                        numero_operacion=numero_operacion_final,
                        observaciones=observaciones_final,
                        estado=1,
                        fecha_pago=fecha_pago_final
                    )
                    pagos_ids.append(pago.idpagocuota)
                    total_cuotas_verif += monto_a_cuota
                    numeros_cuotas.append("Inicial" if cuota.numero_cuota == 0 else str(cuota.numero_cuota))

                    cuota.monto_pagado += monto_a_cuota
                    cuota.saldo_cuota  -= monto_a_cuota
                    if cuota.saldo_cuota <= 0:
                        cuota.estado_pago = 'Pagado'
                        cuota.fecha_pago  = fecha_pago_final
                    else:
                        cuota.estado_pago = 'Parcial'
                    cuota.save()

                # Validar consistencia entre total métodos y total cuotas
                if abs(monto_total_pagado - total_cuotas_verif) > Decimal('0.01'):
                    raise Exception(f"Desajuste: Métodos (S/ {monto_total_pagado}) != Cuotas (S/ {total_cuotas_verif})")

                # Marcar cada PagoCuota con el grupo MULTIPAGO
                pago_ids_grupo = ','.join(str(p) for p in pagos_ids)
                marker = f'[MULTIPAGO:{pago_ids_grupo}]'
                for p_id in pagos_ids:
                    p_obj = PagoCuota.objects.get(idpagocuota=p_id)
                    p_obj.observaciones = (f"{p_obj.observaciones} {marker}".strip() if p_obj.observaciones else marker)
                    p_obj.save()

                # Un solo movimiento de caja
                nombre_cliente = (
                    credito.idventa.idcliente.razonsocial
                    if credito.idventa
                    else (credito.idcliente.razonsocial if credito.idcliente else 'N/A')
                )
                descripcion_movimiento = (
                    f"Pago cuotas #{', '.join(numeros_cuotas)} - "
                    f"Crédito {credito.codigo_credito} - "
                    f"Cliente: {nombre_cliente}"
                )
                if len(desglose_pagos) > 1: descripcion_movimiento += " (Múltiples métodos)"

                movimiento_caja = MovimientoCaja.objects.create(
                    id_caja=apertura_actual.id_caja,
                    id_movimiento=apertura_actual,
                    idusuario_id=idusuario,
                    tipo_movimiento='ingreso',
                    monto=monto_total_pagado,
                    descripcion=descripcion_movimiento,
                    estado=1
                )

                PagoCuota.objects.filter(idpagocuota__in=pagos_ids).update(id_movimiento_caja=movimiento_caja)
                credito.actualizar_estado()

                return JsonResponse({
                    'ok': True,
                    'message': f'Pago de {len(pagos_ids)} cuotas registrado correctamente',
                    'pago_ids': pago_ids_grupo,
                    'total_pagado': float(monto_total_pagado),
                })

        except Exception as e:
            print(f"❌ ERROR pago múltiple: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'ok': False,
                'error': f'Error al procesar el pago: {str(e)}'
            }, status=500)

    return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=400)


def imprimir_recibo_pago_multiple(request, pago_ids):
    """
    Genera un PDF de recibo para el pago múltiple de cuotas en formato TICKET 80mm.
    Recibe los IDs de los PagoCuota separados por comas.
    Lista cada cuota pagada con su número, fecha de vencimiento e importe.
    """
    try:
        import os
        from django.conf import settings
        from software.models.empresaModel import Empresa
        from software.models.VentaDetalleModel import VentaDetalle

        # Parsear IDs
        try:
            ids_list = [int(x) for x in pago_ids.split(',') if x.strip()]
        except ValueError:
            return HttpResponse("IDs de pagos inválidos.", status=400)

        pagos_list = PagoCuota.objects.filter(
            idpagocuota__in=ids_list,
            estado=1
        ).select_related('idcuotaventa', 'idusuario', 'id_tipo_pago').order_by('idcuotaventa__numero_cuota')

        if not pagos_list.exists():
            return HttpResponse("No se encontraron pagos.", status=400)

        primer_pago = pagos_list.first()
        cuota_ref   = primer_pago.idcuotaventa
        venta       = cuota_ref.idventa
        
        if venta:
            credito = Credito.objects.filter(idventa=venta).first()
            cliente = venta.idcliente
        else:
            credito = cuota_ref.idcredito
            cliente = credito.idcliente if credito else None
            
        if not credito:
            return HttpResponse("No se encontró el crédito asociado.", status=400)

        # Empresa (Ventas.idempresa es IntegerField, no FK)
        try:
            if venta and getattr(venta, 'idempresa', None) is not None:
                empresa = Empresa.objects.get(pk=venta.idempresa, activo=True)
            else:
                empresa = Empresa.objects.filter(activo=True).first()
            if not empresa:
                return HttpResponse("No se encontró información de la empresa.", status=400)
        except Empresa.DoesNotExist:
            return HttpResponse("La empresa no existe en el sistema.", status=400)

        total_pagado = sum(p.monto_pago for p in pagos_list)

        # Número de recibo múltiple — usa la serie configurada en BD (Tipo: RM)
        # Fallback al correlativo clásico si no existe serie configurada
        numero_recibo = None
        try:
            with transaction.atomic():
                tipo_rm = Tipocomprobante.objects.filter(codigo='RM', estado=1).first()
                if tipo_rm:
                    serie_rm = Seriecomprobante.objects.select_for_update().filter(
                        idtipocomprobante=tipo_rm, estado=1
                    ).first()
                    if serie_rm:
                        serie_rm.numero_actual += 1
                        serie_rm.save(update_fields=['numero_actual'])
                        numero_recibo = f"{serie_rm.serie}-{str(serie_rm.numero_actual).zfill(6)}"
        except Exception:
            pass

        if not numero_recibo:
            # Fallback: correlativo por cantidad de pagos realizados
            max_pago_id = max(p.idpagocuota for p in pagos_list)
            correlativo = PagoCuota.objects.filter(
                estado=1,
                idpagocuota__lte=max_pago_id
            ).count()
            numero_recibo = f"RM-{str(max(1, correlativo)).zfill(6)}"

        # Cuotas pendientes / atrasadas tras el pago
        if venta:
            q_cuotas = CuotasVenta.objects.filter(idventa=venta, estado=1)
        else:
            q_cuotas = CuotasVenta.objects.filter(idcredito=credito, estado=1)
            
        cuotas_totales   = q_cuotas.count()
        cuotas_pagadas   = q_cuotas.filter(estado_pago='Pagado').count()
        cuotas_pendientes = cuotas_totales - cuotas_pagadas
        hoy = timezone.now().date()
        cuotas_atrasadas = q_cuotas.filter(
            estado_pago__in=['Pendiente', 'Parcial'],
            fecha_vencimiento__lt=hoy
        ).count()

        # ---- Construcción del PDF ----
        buffer       = BytesIO()
        ticket_width = 80 * mm
        ancho_util   = ticket_width - (6 * mm)
        elements     = []
        styles       = getSampleStyleSheet()

        # Estilos
        style_company       = ParagraphStyle('RMCompanyName', parent=styles['Normal'], fontSize=9, textColor=colors.black, alignment=TA_CENTER, fontName='Helvetica-Bold', spaceAfter=0.5*mm, leading=10)
        style_normal_center = ParagraphStyle('RMNormalCenter', parent=styles['Normal'], fontSize=7, alignment=TA_CENTER, spaceAfter=0.5*mm, leading=8)
        style_label         = ParagraphStyle('RMLabel', parent=styles['Normal'], fontSize=7, alignment=TA_LEFT, spaceAfter=0.5*mm, leading=8)
        style_title         = ParagraphStyle('RMTitle', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=1*mm, leading=10)
        style_importe       = ParagraphStyle('RMImporte', parent=styles['Normal'], fontSize=12, fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=1*mm, leading=14)
        style_small         = ParagraphStyle('RMSmall', parent=styles['Normal'], fontSize=6, alignment=TA_CENTER, spaceAfter=0.5*mm, leading=7)
        style_small_left    = ParagraphStyle('RMSmallLeft', parent=styles['Normal'], fontSize=6, alignment=TA_LEFT, spaceAfter=0.5*mm, leading=7)

        # Logo — usando el mismo helper que el recibo individual
        logo_rl = get_logo_image_for_pdf(empresa, width_mm=30, height_mm=30, circular=True, use_ticket_logo=True)
        if logo_rl:
            elements.append(logo_rl)
            elements.append(Spacer(1, 3*mm))


        # Cabecera empresa
        nombre_empresa = empresa.razonsocial if empresa.razonsocial else empresa.nombrecomercial
        elements.append(Paragraph(nombre_empresa.upper(), style_company))
        if empresa.direccion:
            elements.append(Paragraph(f"Local: {empresa.direccion.upper()}", style_small))
        elements.append(Paragraph(f"TELEFONOS: {empresa.telefono}", style_small))
        elements.append(Paragraph(f"<b>RUC: {empresa.ruc}</b>", style_normal_center))
        elements.append(Paragraph(f"<b>RECIBO {numero_recibo}</b>", style_title))
        elements.append(Spacer(1, 2*mm))

        # Cliente
        elements.append(Paragraph("<b>CLIENTE</b>", style_label))
        elements.append(Paragraph(f"DNI: {cliente.numdoc or '---'}", style_label))
        elements.append(Paragraph(cliente.razonsocial.upper(), style_small_left))
        if cliente.direccion:
            elements.append(Paragraph(cliente.direccion.upper(), style_small_left))
        elements.append(Spacer(1, 2*mm))

        # Descripción productos
        elements.append(Paragraph("<b>DESCRIPCIÓN</b>", style_label))
        elements.append(Spacer(1, 1*mm))
        
        if venta:
            detalles_venta = VentaDetalle.objects.filter(idventa=venta, estado=1).select_related(
                'id_vehiculo__idproducto',
                'id_repuesto_comprado__id_repuesto'
            )
            for detalle in detalles_venta:
                if detalle.tipo_item == 'vehiculo' and detalle.id_vehiculo:
                    v = detalle.id_vehiculo
                    elements.append(Paragraph(v.idproducto.nomproducto.upper(), style_small_left))
                    if v.serie_motor:  elements.append(Paragraph(f"Motor: {v.serie_motor}", style_small_left))
                    if v.serie_chasis: elements.append(Paragraph(f"Chasis: {v.serie_chasis}", style_small_left))
                    placa_asignada = "PENDIENTE"
                    from software.models.ImposicionPlacaModel import ImposicionPlaca
                    imposicion = ImposicionPlaca.objects.filter(idventa=venta, estado=1).order_by('-id_imposicion').first()
                    if imposicion and imposicion.numero_placa:
                        placa_asignada = imposicion.numero_placa
                    elif v.placas and v.placas.strip():
                        placa_asignada = v.placas.strip()
                    elements.append(Paragraph(f"Placa: {placa_asignada.upper()}", style_small_left))
                elif detalle.tipo_item == 'repuesto' and detalle.id_repuesto_comprado:
                    r = detalle.id_repuesto_comprado
                    elements.append(Paragraph(r.id_repuesto.nombre.upper(), style_small_left))
                    if r.id_repuesto.codigo_barras: elements.append(Paragraph(f"Código: {r.id_repuesto.codigo_barras}", style_small_left))
        else:
            if credito.tipo_item == 'vehiculo' and credito.id_vehiculo:
                v = credito.id_vehiculo
                elements.append(Paragraph(v.idproducto.nomproducto.upper(), style_small_left))
                if v.serie_motor: elements.append(Paragraph(f"Motor: {v.serie_motor}", style_small_left))
            elif credito.tipo_item == 'repuesto' and credito.id_repuesto_comprado:
                elements.append(Paragraph(credito.id_repuesto_comprado.id_repuesto.nombre.upper(), style_small_left))
            else:
                elements.append(Paragraph('CRÉDITO DIRECTO', style_small_left))
            
        elements.append(Spacer(1, 2*mm))

        # Fecha, hora y meta del pago
        fecha_str = primer_pago.fecha_pago.strftime('%d/%m/%Y')
        hora_str  = primer_pago.fecha_pago.strftime('%H:%M')
        elements.append(Paragraph(f"<b>FECHA EMISION:</b> {fecha_str}", style_label))
        elements.append(Paragraph(f"<b>HORA:</b> {hora_str}", style_small_left))
        elements.append(Spacer(1, 1*mm))
        elements.append(Paragraph("<b>MONEDA: SOLES</b>", style_small_left))
        tipo_pago_nombre = primer_pago.id_tipo_pago.nombre if primer_pago.id_tipo_pago else 'EFECTIVO'
        elements.append(Paragraph(f"<b>FORMA DE PAGO: {tipo_pago_nombre.upper()}</b>", style_small_left))

        # ✅ DETALLE de pago fraccionado (si es MÚLTIPLE)
        if tipo_pago_nombre.upper() == "MÚLTIPLE" and primer_pago.observaciones:
            import re as _re
            obs_limpia = primer_pago.observaciones
            match_frac = _re.search(r'\[FRACCIONADO: (.*?)\]', obs_limpia)
            if match_frac:
                obs_texto = match_frac.group(1)
            else:
                obs_texto = _re.sub(r'\[MULTIPAGO:.*?\]', '', obs_limpia).strip()
            if obs_texto:
                elements.append(Paragraph(f"<b>DETALLE:</b> {obs_texto}", style_small_left))

        cajero = primer_pago.idusuario.nombrecompleto.upper()
        elements.append(Paragraph(f"<b>CAJERO(A): {cajero}</b>", style_small_left))
        
        # Mostrar la caja del pago
        caja_nombre = primer_pago.id_movimiento_caja.id_caja.nombre_caja if primer_pago.id_movimiento_caja and primer_pago.id_movimiento_caja.id_caja else 'Caja Principal'
        elements.append(Paragraph(f"<b>CAJA: {caja_nombre}</b>", style_small_left))
        
        elements.append(Paragraph("<b>CONCEPTO:</b> COBRANZA DE CUOTAS MÚLTIPLES", style_small_left))
        elements.append(Spacer(1, 2*mm))

        # Info crédito (cabecera)
        fecha_emision_credito = credito.fecha_credito.strftime('%Y-%m-%d')
        
        if credito.idventa:
            cuotas_activas_mult = CuotasVenta.objects.filter(idventa=credito.idventa, estado=1)
            from django.db.models import Sum
            max_pago_id = max(p.idpagocuota for p in pagos_list)
            pagos_posteriores = PagoCuota.objects.filter(
                idcuotaventa__idventa=credito.idventa,
                estado=1,
                idpagocuota__gt=max_pago_id
            ).aggregate(total=Sum('monto_pago'))['total'] or 0
        else:
            cuotas_activas_mult = CuotasVenta.objects.filter(idcredito=credito, estado=1)
            from django.db.models import Sum
            max_pago_id = max(p.idpagocuota for p in pagos_list)
            pagos_posteriores = PagoCuota.objects.filter(
                idcuotaventa__idcredito=credito,
                estado=1,
                idpagocuota__gt=max_pago_id
            ).aggregate(total=Sum('monto_pago'))['total'] or 0
            
        total_pendiente_real_mult = sum(c.saldo_cuota for c in cuotas_activas_mult) + pagos_posteriores
        
        data_credito_info = [
            ['CREDITO', 'FECHA', 'IMPORTE', 'SALDO'],
            [credito.codigo_credito, fecha_emision_credito,
             f'S/ {credito.monto_total:,.2f}', f'S/ {total_pendiente_real_mult:,.2f}']
        ]
        table_credito_info = Table(data_credito_info, colWidths=[16*mm, 22*mm, 20*mm, 16*mm])
        table_credito_info.setStyle(TableStyle([
            ('FONTNAME',  (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE',  (0, 0), (-1, -1), 6),
            ('ALIGN',     (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN',     (0, 1), (1, 1), 'CENTER'),
            ('ALIGN',     (2, 1), (2, 1), 'CENTER'),
            ('ALIGN',     (3, 1), (3, 1), 'RIGHT'),
            ('VALIGN',    (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING',    (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING',   (0, 0), (-1, -1), 2),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 2),
            # Diseño con rayas (sin bordes verticales)
            ('LINEABOVE', (0, 0), (-1, 0), 0.5, colors.black),
            ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.black),
            ('LINEBELOW', (0, -1), (-1, -1), 0.5, colors.black),
        ]))
        elements.append(table_credito_info)
        elements.append(Spacer(1, 2*mm))

        # ---- Tabla detalle de cuotas pagadas (listado por número) ----
        elements.append(Paragraph("<b>DETALLE DE CUOTAS PAGADAS</b>", style_normal_center))
        elements.append(Spacer(1, 1*mm))

        data_cuotas = [['N° CUOTA', 'VENCIMIENTO', 'IMPORTE']]
        for pago in pagos_list:
            cuota = pago.idcuotaventa
            num   = "Inicial" if cuota.numero_cuota == 0 else str(cuota.numero_cuota)
            fecha_venc = cuota.fecha_vencimiento.strftime('%d/%m/%Y')
            data_cuotas.append([num, fecha_venc, f'S/ {pago.monto_pago:,.2f}'])

        table_cuotas = Table(data_cuotas, colWidths=[18*mm, 28*mm, 22*mm])
        table_cuotas.setStyle(TableStyle([
            ('FONTNAME',  (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE',  (0, 0), (-1, -1), 6),
            ('ALIGN',     (0, 0), (1, -1), 'CENTER'),
            ('ALIGN',     (2, 0), (2, -1), 'CENTER'),
            ('VALIGN',    (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING',    (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING',   (0, 0), (-1, -1), 2),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 2),
            # Diseño con rayas (sin bordes verticales)
            ('LINEABOVE', (0, 0), (-1, 0), 0.5, colors.black),
            ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.black),
            ('LINEBELOW', (0, -1), (-1, -1), 0.5, colors.black),
        ]))
        elements.append(table_cuotas)
        elements.append(Spacer(1, 2*mm))

        # Pendientes / Atrasadas
        elements.append(Paragraph(
            f"<b>PENDIENTES {cuotas_pendientes} / ATRAZADAS {cuotas_atrasadas}</b>",
            style_small_left
        ))
        elements.append(Spacer(1, 3*mm))

        # Importe total
        elements.append(Paragraph(f"<b>Importe Total {total_pagado:.2f}</b>", style_importe))
        elements.append(Spacer(1, 2*mm))

        # Monto en letras
        try:
            from software.utils.numero_a_letras import numero_a_letras
            monto_letras = numero_a_letras(total_pagado)
        except Exception:
            parte_entera  = int(total_pagado)
            parte_decimal = int((total_pagado - parte_entera) * 100)
            monto_letras  = f"CON {parte_decimal:02d}/100"

        elements.append(Paragraph(f"<b>SON: {monto_letras.upper()} SOLES</b>", style_normal_center))
        elements.append(Paragraph("Cobro cuotas múltiples", style_normal_center))
        elements.append(Spacer(1, 3*mm))
        elements.append(Paragraph(
            "- - - - - - - - - - - - - - - - - - - - - - - -",
            style_normal_center
        ))

        # Calcular altura dinámica del ticket
        total_height = 0
        for element in elements:
            if hasattr(element, 'wrap'):
                try:
                    _, h = element.wrap(ancho_util, 2000 * mm)
                    total_height += h
                except Exception:
                    total_height += 15 * mm

        doc_height = max(total_height + (35 * mm), 100 * mm)

        doc = SimpleDocTemplate(
            buffer,
            pagesize=(ticket_width, doc_height),
            rightMargin=3*mm, leftMargin=3*mm,
            topMargin=3*mm, bottomMargin=3*mm
        )
        doc.build(elements)
        buffer.seek(0)

        response = FileResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="recibo_multiple_{numero_recibo}.pdf"'
        return response

    except Exception as e:
        print(f"ERROR al generar recibo múltiple: {str(e)}")
        import traceback
        traceback.print_exc()
        return HttpResponse(f"Error al generar el recibo múltiple: {str(e)}", status=500)


def imprimir_cronograma_credito(request, idventa):
    """
    Vista de compatibilidad para imprimir cronograma desde ID de venta
    """
    credito = get_object_or_404(Credito, idventa=idventa)
    return _generar_pdf_cronograma(request, credito)


def obtener_notificaciones_vencidas(request):
    """
    API para obtener las cuotas vencidas y la preferencia de sonido del usuario
    """
    idusuario = request.session.get('idusuario')
    if not idusuario:
        return JsonResponse({'ok': False, 'error': 'No autorizado'}, status=401)
    
    try:
        from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos
        usuario = Usuario.objects.select_related('idtipousuario').get(idusuario=idusuario)
        
        from django.db.models import Q
        # Validar si el usuario tiene acceso al módulo de créditos principal
        tiene_permiso = Detalletipousuarioxmodulos.objects.filter(
            idtipousuario=usuario.idtipousuario
        ).filter(
            Q(idmodulo__nombremodulo__iexact='creditos') | 
            Q(idmodulo__nombremodulo__iexact='créditos')
        ).exists()
        
        if not tiene_permiso:
            return JsonResponse({
                'ok': True,
                'cantidad_vencidas': 0,
                'cuotas': [],
                'sonido_alerta': False
            })

        hoy = timezone.now().date()
        
        # Estados de crédito que NO deben aparecer en notificaciones
        # (créditos en proceso de retención o ya cancelados por retención)
        ESTADOS_EXCLUIDOS = ['retenido', 'cancelado', 'reparado', 'segunda']

        # Cuotas vencidas no pagadas — solo de créditos activos en estado MORA
        cuotas_vencidas = CuotasVenta.objects.filter(
            estado=1,
            estado_pago__in=['Pendiente', 'Parcial'],
            fecha_vencimiento__lt=hoy
        ).exclude(
            # Excluir cuotas de créditos directos cancelados/retenidos
            idcredito__estado_credito__in=ESTADOS_EXCLUIDOS
        ).exclude(
            # Excluir cuotas de créditos directos con estado=0 (baja lógica)
            idcredito__estado=0
        ).exclude(
            # Excluir cuotas de ventas con crédito cancelado/retenido
            idventa__credito__estado_credito__in=ESTADOS_EXCLUIDOS
        ).exclude(
            # Excluir cuotas de ventas con crédito en estado=0
            idventa__credito__estado=0
        )

        id_suc = request.session.get('id_sucursal')
        if id_suc:
            cuotas_vencidas = cuotas_vencidas.filter(
                Q(idventa__id_sucursal_id=id_suc) | 
                Q(idcredito__id_sucursal_id=id_suc)
            )

        cuotas_vencidas = cuotas_vencidas.select_related(
            'idventa__idcliente',
            'idcredito__idcliente',
            'idcredito__idventa__idcliente',
            'idventa__credito'
        ).order_by('-fecha_vencimiento')
        
        total_count = cuotas_vencidas.count()
        
        # Lista para el dropdown (últimas 30)
        lista_notificaciones = []
        for cuota in cuotas_vencidas[:30]:
            cliente = "Cliente Desconocido"
            id_credito_final = None
            
            if cuota.idcredito:
                id_credito_final = cuota.idcredito.idcredito
                if cuota.idcredito.idcliente:
                    cliente = cuota.idcredito.idcliente.razonsocial
                elif cuota.idcredito.idventa and cuota.idcredito.idventa.idcliente:
                    cliente = cuota.idcredito.idventa.idcliente.razonsocial
            elif cuota.idventa:
                if cuota.idventa.idcliente:
                    cliente = cuota.idventa.idcliente.razonsocial
                
                # Intentar obtener el ID del crédito desde la venta
                if hasattr(cuota.idventa, 'credito') and cuota.idventa.credito:
                    id_credito_final = cuota.idventa.credito.idcredito
            
            lista_notificaciones.append({
                'id': cuota.idcuotaventa,
                'cliente': cliente,
                'monto': float(cuota.saldo_cuota),
                'fecha_vencimiento': cuota.fecha_vencimiento.strftime('%d/%m/%Y'),
                'numero_cuota': cuota.numero_cuota,
                'url': f'/creditos/detalle/{id_credito_final}/' if id_credito_final else '#'
            })
            
        return JsonResponse({
            'ok': True,
            'count': total_count,
            'notificaciones': lista_notificaciones,
            'sonido_activo': usuario.notificaciones_sonido,
            'sonido_url': usuario.sonido_notificacion.url if usuario.sonido_notificacion else None
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


def subir_sonido_notificacion(request):
    """
    API para subir un archivo de sonido personalizado para las notificaciones
    """
    if request.method == 'POST' and request.FILES.get('sonido'):
        idusuario = request.session.get('idusuario')
        if not idusuario:
            return JsonResponse({'ok': False, 'error': 'No autorizado'}, status=401)
        
        try:
            archivo = request.FILES['sonido']
            # Validar que sea un archivo de audio (opcional pero recomendado)
            if not archivo.name.endswith(('.mp3', '.wav', '.ogg')):
                return JsonResponse({'ok': False, 'error': 'Formato de archivo no válido (use mp3, wav u ogg)'})

            usuario = Usuario.objects.get(idusuario=idusuario)
            
            # Borrar el sonido anterior si existe (opcional)
            if usuario.sonido_notificacion:
                import os
                if os.path.exists(usuario.sonido_notificacion.path):
                    os.remove(usuario.sonido_notificacion.path)
            
            usuario.sonido_notificacion = archivo
            usuario.save()
            
            return JsonResponse({
                'ok': True, 
                'mensaje': 'Sonido actualizado correctamente',
                'url': usuario.sonido_notificacion.url
            })
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)}, status=500)
            
    return JsonResponse({'ok': False, 'error': 'Solicitud inválida'}, status=400)


def actualizar_preferencia_sonido(request):
    """
    API para actualizar la preferencia de sonido del usuario
    """
    if request.method == 'POST':
        idusuario = request.session.get('idusuario')
        if not idusuario:
            return JsonResponse({'ok': False, 'error': 'No autorizado'}, status=401)
        
        activo = request.POST.get('activo') == 'true'
        Usuario.objects.filter(idusuario=idusuario).update(notificaciones_sonido=activo)
        return JsonResponse({'ok': True})
    
    return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)


def imprimir_cronograma_credito_directo(request, idcredito):
    """
    Vista para imprimir cronograma desde ID de crédito (Directo)
    """
    credito = get_object_or_404(Credito, idcredito=idcredito)
    return _generar_pdf_cronograma(request, credito)

from django.http import HttpResponse
from software.utils.contrato_pdf_service import generar_contrato_pdf
from software.models.empresaModel import Empresa
from software.models.GaranteModel import Garante
from software.utils.contratos_especiales_service import generar_contrato_especial_pdf
from software.utils.pagare_pdf_service import generar_pagare_pdf


def descargar_contrato_pdf(request, idcredito):
    credito = get_object_or_404(Credito, idcredito=idcredito)
    empresa = Empresa.objects.first()
    if not empresa:
        return HttpResponse('No hay una empresa configurada.', status=400)
    try:
        pdf_bytes = generar_contrato_pdf(credito, empresa)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="contrato_{credito.codigo_credito}.pdf"'
        return response
    except Exception as e:
        return HttpResponse(f'Error generando el PDF: {str(e)}', status=500)

def descargar_contrato_especial_pdf(request, idcredito):
    credito = get_object_or_404(Credito, idcredito=idcredito)
    empresa = Empresa.objects.first()
    
    asume_gastos = request.GET.get('asume_gastos') == 'true'
    
    # Si la empresa asume los gastos, usamos el contrato original (el viejo)
    if asume_gastos:
        try:
            pdf_bytes = generar_contrato_pdf(credito, empresa, asume_gastos=True)
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="contrato_{credito.codigo_credito}.pdf"'
            return response
        except Exception as e:
            return HttpResponse(f'Error generando el PDF Original: {str(e)}', status=500)
    if not empresa:
        return HttpResponse('No hay una empresa configurada.', status=400)
        
    try:
        pdf_bytes = generar_contrato_especial_pdf(credito, empresa, asume_gastos=False)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="contrato_especial_{credito.codigo_credito}.pdf"'
        return response
    except Exception as e:
        import traceback
        traceback.print_exc()
        return HttpResponse(f'Error generando el PDF Especial: {str(e)}', status=500)

def descargar_pagare_pdf(request, idcredito):
    credito = get_object_or_404(Credito, idcredito=idcredito)
    empresa = Empresa.objects.first()
    
    if not empresa:
        return HttpResponse('No hay una empresa configurada.', status=400)
        
    try:
        pdf_bytes = generar_pagare_pdf(credito, empresa)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="pagare_{credito.codigo_credito}.pdf"'
        return response
    except Exception as e:
        import traceback
        traceback.print_exc()
        return HttpResponse(f'Error generando el PDF del Pagaré: {str(e)}', status=500)

from django.views.decorators.csrf import csrf_exempt
@csrf_exempt
def guardar_garante_credito(request):
    if request.method == 'POST':
        try:
            idcredito = request.POST.get('id_credito')
            id_garante = request.POST.get('id_garante')
            nombre = request.POST.get('nombreGarante')
            numdoc = request.POST.get('dniGarante')
            direccion = request.POST.get('direccionGarante')
            telefono = request.POST.get('telefonoGarante')
            id_region_val = request.POST.get('idRegion')
            id_provincia_val = request.POST.get('idProvincia')
            id_distrito_val = request.POST.get('idDistrito')
            conyuge_nombre = request.POST.get('conyuge_nombre')
            conyuge_dni = request.POST.get('conyuge_dni')
            
            credito = get_object_or_404(Credito, idcredito=idcredito)
            
            if id_garante:
                garante = Garante.objects.get(id_garante=id_garante)
                # Si se quiere, se podrian actualizar los datos aqui
            else:
                # Si es un garante nuevo, lo asociamos al cliente del crédito
                idcliente_asociado = None
                if credito.idventa:
                    idcliente_asociado = credito.idventa.idcliente
                else:
                    idcliente_asociado = credito.idcliente
                
                region_obj = Region.objects.get(id_region=id_region_val) if id_region_val else None
                provincia_obj = Provincia.objects.get(id_provincia=id_provincia_val) if id_provincia_val else None
                distrito_obj = Distrito.objects.get(id_distrito=id_distrito_val) if id_distrito_val else None
                
                garante = Garante.objects.create(
                    idcliente=idcliente_asociado,
                    nombre=nombre, 
                    numdoc=numdoc, 
                    direccion=direccion, 
                    telefono=telefono,
                    id_region=region_obj,
                    id_provincia=provincia_obj,
                    id_distrito=distrito_obj,
                    conyuge_nombre=conyuge_nombre,
                    conyuge_dni=conyuge_dni,
                    estado=1
                )
            
            credito.id_garante = garante
            credito.save()
            return JsonResponse({'ok': True, 'success': 'Garante asignado correctamente'})
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)}, status=400)
    return JsonResponse({'ok': False, 'error': 'Metodo no permitido'}, status=405)

def buscar_garantes(request):
    term = request.GET.get('term', '')
    idcliente = request.GET.get('idcliente')
    
    garantes = Garante.objects.filter(estado=1)
    
    if idcliente:
        garantes = garantes.filter(idcliente_id=idcliente)
        
    if term:
        garantes = garantes.filter(Q(numdoc__icontains=term) | Q(nombre__icontains=term))
        
    resultados = [{
        'id': g.id_garante, 
        'text': f'{g.nombre} - DNI: {g.numdoc}', 
        'nombre': g.nombre, 
        'dni': g.numdoc, 
        'direccion': g.direccion, 
        'telefono': g.telefono,
        'id_region': g.id_region_id,
        'id_provincia': g.id_provincia_id,
        'id_distrito': g.id_distrito_id,
        'conyuge_nombre': g.conyuge_nombre,
        'conyuge_dni': g.conyuge_dni
    } for g in garantes[:15]]
    
    return JsonResponse(resultados, safe=False)

def imprimir_recibo_pago_total(request, idmovimiento):
    """
    Genera un PDF de recibo para el pago total del crédito en formato TICKET 80mm.
    Recibe el id del movimiento de caja que consolidó el pago.
    """
    try:
        import os
        from django.conf import settings
        from software.models.empresaModel import Empresa
        from software.models.VentaDetalleModel import VentaDetalle
        from software.models.movimientoCajaModel import MovimientoCaja

        movimiento = get_object_or_404(MovimientoCaja, id_movimiento_caja=idmovimiento)
        pagos_list = PagoCuota.objects.filter(id_movimiento_caja=movimiento, estado=1).select_related('idcuotaventa', 'idusuario', 'id_tipo_pago').order_by('idcuotaventa__numero_cuota')

        if not pagos_list.exists():
            return HttpResponse("No se encontraron pagos asociados a este movimiento.", status=400)

        primer_pago = pagos_list.first()
        cuota_ref   = primer_pago.idcuotaventa
        venta       = cuota_ref.idventa
        credito     = Credito.objects.get(idventa=venta) if venta else Credito.objects.get(idcredito=cuota_ref.idcredito.idcredito)
        cliente     = venta.idcliente if venta else credito.idcliente

        # Empresa (Ventas.idempresa es IntegerField, no FK)
        try:
            if venta and venta.idempresa is not None:
                empresa = Empresa.objects.get(pk=venta.idempresa, activo=True)
            else:
                empresa = Empresa.objects.filter(activo=True).first()
            if not empresa:
                return HttpResponse("No se encontró información de la empresa.", status=400)
        except Empresa.DoesNotExist:
            return HttpResponse("La empresa no existe en el sistema.", status=400)

        total_pagado = movimiento.monto

        # Número de recibo total — usa la serie configurada en BD (Tipo: RT)
        # Fallback al correlativo clásico si no existe serie configurada
        numero_recibo = None
        try:
            with transaction.atomic():
                tipo_rt = Tipocomprobante.objects.filter(codigo='RT', estado=1).first()
                if tipo_rt:
                    serie_rt = Seriecomprobante.objects.select_for_update().filter(
                        idtipocomprobante=tipo_rt, estado=1
                    ).first()
                    if serie_rt:
                        serie_rt.numero_actual += 1
                        serie_rt.save(update_fields=['numero_actual'])
                        numero_recibo = f"{serie_rt.serie}-{str(serie_rt.numero_actual).zfill(6)}"
        except Exception:
            pass

        if not numero_recibo:
            # Fallback: correlativo por movimientos de caja
            sucursal_id = venta.id_sucursal.id_sucursal if venta else 1
            correlativo = MovimientoCaja.objects.filter(
                id_caja__id_sucursal=sucursal_id,
                tipo_movimiento='ingreso',
                descripcion__icontains='Pago total',
                id_movimiento_caja__lte=movimiento.id_movimiento_caja
            ).count()
            numero_recibo = f"RT-{str(max(1, correlativo)).zfill(6)}"

        # ---- Construcción del PDF ----
        buffer       = BytesIO()
        ticket_width = 80 * mm
        ancho_util   = ticket_width - (6 * mm)
        elements     = []
        styles       = getSampleStyleSheet()

        # Estilos
        style_company       = ParagraphStyle('RMCompanyName', parent=styles['Normal'], fontSize=9, textColor=colors.black, alignment=TA_CENTER, fontName='Helvetica-Bold', spaceAfter=0.5*mm, leading=10)
        style_normal_center = ParagraphStyle('RMNormalCenter', parent=styles['Normal'], fontSize=7, alignment=TA_CENTER, spaceAfter=0.5*mm, leading=8)
        style_label         = ParagraphStyle('RMLabel', parent=styles['Normal'], fontSize=7, alignment=TA_LEFT, spaceAfter=0.5*mm, leading=8)
        style_title         = ParagraphStyle('RMTitle', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=1*mm, leading=10)
        style_importe       = ParagraphStyle('RMImporte', parent=styles['Normal'], fontSize=12, fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=1*mm, leading=14)
        style_small         = ParagraphStyle('RMSmall', parent=styles['Normal'], fontSize=6, alignment=TA_CENTER, spaceAfter=0.5*mm, leading=7)
        style_small_left    = ParagraphStyle('RMSmallLeft', parent=styles['Normal'], fontSize=6, alignment=TA_LEFT, spaceAfter=0.5*mm, leading=7)

        # Logo — usando el mismo helper que el recibo individual
        logo_rl = get_logo_image_for_pdf(empresa, width_mm=30, height_mm=30, circular=True, use_ticket_logo=True)
        if logo_rl:
            elements.append(logo_rl)
            elements.append(Spacer(1, 3*mm))

        # Cabecera empresa
        nombre_empresa = empresa.razonsocial if empresa.razonsocial else empresa.nombrecomercial
        elements.append(Paragraph(nombre_empresa.upper(), style_company))
        if empresa.direccion:
            elements.append(Paragraph(f"Local: {empresa.direccion.upper()}", style_small))
        elements.append(Paragraph(f"TELEFONOS: {empresa.telefono}", style_small))
        elements.append(Paragraph(f"<b>RUC: {empresa.ruc}</b>", style_normal_center))
        elements.append(Paragraph(f"<b>RECIBO {numero_recibo}</b>", style_title))
        elements.append(Spacer(1, 2*mm))

        # Cliente
        elements.append(Paragraph("<b>CLIENTE</b>", style_label))
        elements.append(Paragraph(f"DNI: {cliente.numdoc or '---'}", style_label))
        elements.append(Paragraph(cliente.razonsocial.upper(), style_small_left))
        if cliente.direccion:
            elements.append(Paragraph(cliente.direccion.upper(), style_small_left))
        elements.append(Spacer(1, 2*mm))

        # Descripción productos
        if venta:
            elements.append(Paragraph("<b>DESCRIPCIÓN</b>", style_label))
            elements.append(Spacer(1, 1*mm))
            detalles_venta = VentaDetalle.objects.filter(idventa=venta, estado=1).select_related(
                'id_vehiculo__idproducto',
                'id_repuesto_comprado__id_repuesto'
            )
            for detalle in detalles_venta:
                if detalle.tipo_item == 'vehiculo' and detalle.id_vehiculo:
                    v = detalle.id_vehiculo
                    elements.append(Paragraph(v.idproducto.nomproducto.upper(), style_small_left))
                    if v.serie_motor:  elements.append(Paragraph(f"Motor: {v.serie_motor}", style_small_left))
                    if v.serie_chasis: elements.append(Paragraph(f"Chasis: {v.serie_chasis}", style_small_left))
                    placa_asignada = "PENDIENTE"
                    from software.models.ImposicionPlacaModel import ImposicionPlaca
                    imposicion = ImposicionPlaca.objects.filter(idventa=venta, estado=1).order_by('-id_imposicion').first()
                    if imposicion and imposicion.numero_placa:
                        placa_asignada = imposicion.numero_placa
                    elif v.placas and v.placas.strip():
                        placa_asignada = v.placas.strip()
                    elements.append(Paragraph(f"Placa: {placa_asignada.upper()}", style_small_left))
                elif detalle.tipo_item == 'repuesto' and detalle.id_repuesto_comprado:
                    r = detalle.id_repuesto_comprado
                    elements.append(Paragraph(r.id_repuesto.nombre.upper(), style_small_left))
                    if r.id_repuesto.codigo_barras: elements.append(Paragraph(f"Código: {r.id_repuesto.codigo_barras}", style_small_left))
            elements.append(Spacer(1, 2*mm))

        # Fecha, hora y meta del pago
        fecha_str = primer_pago.fecha_pago.strftime('%d/%m/%Y')
        hora_str  = primer_pago.fecha_pago.strftime('%H:%M')
        elements.append(Paragraph(f"<b>FECHA EMISION:</b> {fecha_str}", style_label))
        elements.append(Paragraph(f"<b>HORA:</b> {hora_str}", style_small_left))
        elements.append(Spacer(1, 1*mm))
        elements.append(Paragraph("<b>MONEDA: SOLES</b>", style_small_left))
        tipo_pago_nombre = primer_pago.id_tipo_pago.nombre if primer_pago.id_tipo_pago else 'EFECTIVO'
        elements.append(Paragraph(f"<b>FORMA DE PAGO: {tipo_pago_nombre.upper()}</b>", style_small_left))

        # ✅ DETALLE de pago fraccionado (si es MÚLTIPLE)
        if tipo_pago_nombre.upper() == "MÚLTIPLE" and primer_pago.observaciones:
            import re as _re
            obs_limpia = primer_pago.observaciones
            match_frac = _re.search(r'\[FRACCIONADO: (.*?)\]', obs_limpia)
            if match_frac:
                obs_texto = match_frac.group(1)
            else:
                obs_texto = _re.sub(r'\[PAGO TOTAL CON DESCUENTO.*?\]', '', obs_limpia).strip()
            if obs_texto:
                elements.append(Paragraph(f"<b>DETALLE:</b> {obs_texto}", style_small_left))

        cajero = primer_pago.idusuario.nombrecompleto.upper()
        elements.append(Paragraph(f"<b>CAJERO(A): {cajero}</b>", style_small_left))
        
        # Mostrar la caja del pago
        caja_nombre = primer_pago.id_movimiento_caja.id_caja.nombre_caja if primer_pago.id_movimiento_caja and primer_pago.id_movimiento_caja.id_caja else 'Caja Principal'
        elements.append(Paragraph(f"<b>CAJA: {caja_nombre}</b>", style_small_left))
        
        elements.append(Paragraph("<b>CONCEPTO:</b> PAGO TOTAL DEL CRÉDITO", style_small_left))
        elements.append(Spacer(1, 2*mm))

        # Info crédito (cabecera)
        fecha_emision_credito = credito.fecha_credito.strftime('%Y-%m-%d')
        
        data_credito_info = [
            ['CREDITO', 'FECHA', 'IMPORTE', 'SALDO'],
            [credito.codigo_credito, fecha_emision_credito,
             f'S/ {credito.monto_total:,.2f}', f'S/ 0.00']
        ]
        table_credito_info = Table(data_credito_info, colWidths=[16*mm, 22*mm, 20*mm, 16*mm])
        table_credito_info.setStyle(TableStyle([
            ('FONTNAME',  (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE',  (0, 0), (-1, -1), 6),
            ('ALIGN',     (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN',     (0, 1), (1, 1), 'CENTER'),
            ('ALIGN',     (2, 1), (2, 1), 'CENTER'),
            ('ALIGN',     (3, 1), (3, 1), 'RIGHT'),
            ('VALIGN',    (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING',    (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING',   (0, 0), (-1, -1), 2),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 2),
            ('LINEABOVE', (0, 0), (-1, 0), 0.5, colors.black),
            ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.black),
            ('LINEBELOW', (0, -1), (-1, -1), 0.5, colors.black),
        ]))
        elements.append(table_credito_info)
        elements.append(Spacer(1, 2*mm))

        # ---- Tabla detalle de cuotas pagadas (listado por número) ----
        elements.append(Paragraph("<b>DETALLE DE CUOTAS PAGADAS</b>", style_normal_center))
        elements.append(Spacer(1, 1*mm))

        data_cuotas = [['N° CUOTA', 'VENCIMIENTO', 'IMPORTE']]
        for pago in pagos_list:
            cuota = pago.idcuotaventa
            num   = "Inicial" if cuota.numero_cuota == 0 else str(cuota.numero_cuota)
            fecha_venc = cuota.fecha_vencimiento.strftime('%d/%m/%Y')
            data_cuotas.append([num, fecha_venc, f'S/ {pago.monto_pago:,.2f}'])

        table_cuotas = Table(data_cuotas, colWidths=[18*mm, 28*mm, 22*mm])
        table_cuotas.setStyle(TableStyle([
            ('FONTNAME',  (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE',  (0, 0), (-1, -1), 6),
            ('ALIGN',     (0, 0), (1, -1), 'CENTER'),
            ('ALIGN',     (2, 0), (2, -1), 'CENTER'),
            ('VALIGN',    (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING',    (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING',   (0, 0), (-1, -1), 2),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 2),
            ('LINEABOVE', (0, 0), (-1, 0), 0.5, colors.black),
            ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.black),
            ('LINEBELOW', (0, -1), (-1, -1), 0.5, colors.black),
        ]))
        elements.append(table_cuotas)
        elements.append(Spacer(1, 2*mm))

        # Pendientes / Atrasadas (0 porque se pagó todo)
        elements.append(Paragraph(
            "<b>PENDIENTES 0 / ATRAZADAS 0</b>", 
            style_small_left
        ))
        elements.append(Spacer(1, 3*mm))

        # Total Pagado
        elements.append(Paragraph(f"Importe Total {total_pagado:,.2f}", style_importe))
        
        # Monto en letras
        from software.utils.numero_a_letras import numero_a_letras
        str_son = f"SON: {numero_a_letras(total_pagado)} SOLES"
        elements.append(Paragraph(f"<b>{str_son}</b>", style_small))
        elements.append(Paragraph("Pago total de crédito", style_small))
        elements.append(Spacer(1, 5*mm))
        elements.append(Paragraph("---------------------------------", style_normal_center))
        elements.append(Spacer(1, 5*mm))

        # Calcular altura dinámica del ticket
        total_height = 0
        for element in elements:
            if hasattr(element, 'wrap'):
                try:
                    _, h = element.wrap(ancho_util, 2000 * mm)
                    total_height += h
                except Exception:
                    total_height += 15 * mm

        doc_height = max(total_height + (35 * mm), 100 * mm)

        doc = SimpleDocTemplate(
            buffer,
            pagesize=(ticket_width, doc_height),
            rightMargin=3*mm, leftMargin=3*mm,
            topMargin=3*mm, bottomMargin=3*mm
        )
        doc.build(elements)

        pdf = buffer.getvalue()
        buffer.close()
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="recibo_pago_total_{credito.codigo_credito}.pdf"'
        response.write(pdf)
        return response

    except Exception as e:
        print(f"❌ Error en imprimir_recibo_pago_total: {str(e)}")
        import traceback
        traceback.print_exc()
        return HttpResponse(f"Error generando el recibo PDF: {str(e)}", status=500)

# ==================== NUEVA API: LISTAR CRÉDITOS PAGINADO ====================
def api_listar_creditos(request):
    """
    API AJAX para listar los créditos con paginación, filtros y búsqueda rápida.
    """
    if request.method != 'GET':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)

    try:
        # 1. Obtener parámetros
        page = request.GET.get('page', '1')
        estado_filtro = request.GET.get('estado', 'todos')
        busqueda = request.GET.get('busqueda', '').strip()
        fecha_desde = request.GET.get('fecha_desde', '')
        fecha_hasta = request.GET.get('fecha_hasta', '')
        producto = request.GET.get('producto', '').strip()

        # 2. Sincronizar estados de mora (SOLO para los que tienen sentido, para mayor eficiencia)
        hoy_date = timezone.now().date()
        ESTADOS_PROTEGIDOS = ['retenido', 'cancelado', 'reparado', 'segunda', 'pagado']

        cuotas_vencidas_qs = CuotasVenta.objects.filter(
            estado=1,
            estado_pago__in=['Pendiente', 'Parcial'],
            fecha_vencimiento__lt=hoy_date
        )

        Credito.objects.filter(
            estado=1,
            estado_credito='activo'
        ).filter(
            Q(idventa__cuotasventa__in=cuotas_vencidas_qs) |
            Q(cuotas__in=cuotas_vencidas_qs)
        ).distinct().update(estado_credito='mora')

        Credito.objects.filter(
            estado=1,
            estado_credito='mora'
        ).exclude(
            Q(idventa__cuotasventa__in=cuotas_vencidas_qs) |
            Q(cuotas__in=cuotas_vencidas_qs)
        ).exclude(
            estado_credito__in=ESTADOS_PROTEGIDOS
        ).update(estado_credito='activo')

        # 3. Query base
        creditos_qs = Credito.objects.filter(estado=1).select_related(
            'idventa__idcliente',
            'idcliente',
            'id_vehiculo__idproducto',
            'id_repuesto_comprado__id_repuesto'
        ).distinct()

        # 4. Filtrar por estado
        if estado_filtro != 'todos':
            creditos_qs = creditos_qs.filter(estado_credito=estado_filtro)

        # 5. Filtrar por búsqueda general
        if busqueda:
            creditos_qs = creditos_qs.filter(
                Q(codigo_credito__icontains=busqueda) |
                Q(idventa__idcliente__razonsocial__icontains=busqueda) |
                Q(idventa__idcliente__numdoc__icontains=busqueda) |
                Q(idcliente__razonsocial__icontains=busqueda) |
                Q(idcliente__numdoc__icontains=busqueda) |
                Q(idventa__numero_comprobante__icontains=busqueda)
            )

        # 6. Filtrar por búsqueda de producto AMPLIADA (nombre, chasis, motor, cod. barras)
        if producto:
            ventas_con_producto = VentaDetalle.objects.filter(
                estado=1
            ).filter(
                Q(id_vehiculo__idproducto__nomproducto__icontains=producto) |
                Q(id_vehiculo__serie_chasis__icontains=producto) |
                Q(id_vehiculo__serie_motor__icontains=producto) |
                Q(id_repuesto_comprado__id_repuesto__nombre__icontains=producto) |
                Q(id_repuesto_comprado__id_repuesto__codigo_barras__icontains=producto)
            ).values_list('idventa_id', flat=True)
            
            creditos_qs = creditos_qs.filter(
                Q(idventa__idventa__in=ventas_con_producto) |
                Q(id_vehiculo__idproducto__nomproducto__icontains=producto) |
                Q(id_vehiculo__serie_chasis__icontains=producto) |
                Q(id_vehiculo__serie_motor__icontains=producto) |
                Q(id_repuesto_comprado__id_repuesto__nombre__icontains=producto) |
                Q(id_repuesto_comprado__id_repuesto__codigo_barras__icontains=producto)
            )

        # 7. Filtrar por fechas
        if fecha_desde:
            creditos_qs = creditos_qs.filter(fecha_credito__gte=fecha_desde)
        if fecha_hasta:
            try:
                fecha_hasta_dt = datetime.strptime(fecha_hasta, '%Y-%m-%d')
                fecha_hasta_dt = fecha_hasta_dt.replace(hour=23, minute=59, second=59)
                creditos_qs = creditos_qs.filter(fecha_credito__lte=fecha_hasta_dt)
            except ValueError:
                pass

        # 8. Ordenar
        creditos_qs = creditos_qs.order_by('-fecha_credito')

        # 9. Calcular estadísticas dinámicas
        total_activos = creditos_qs.filter(estado_credito='activo').count()
        total_mora = creditos_qs.filter(estado_credito='mora').count()
        total_pagados = creditos_qs.filter(estado_credito='pagado').count()
        monto_total_creditos = float(creditos_qs.aggregate(Sum('monto_total'))['monto_total__sum'] or 0)
        saldo_total_pendiente = float(creditos_qs.aggregate(Sum('saldo_pendiente'))['saldo_pendiente__sum'] or 0)

        # 10. Paginar
        paginator = Paginator(creditos_qs, 10)
        try:
            page_obj = paginator.get_page(page)
        except Exception:
            page_obj = paginator.get_page(1)

        # 11. Serializar página
        creditos_serializados = []
        for c in page_obj:
            cliente_nombre = ''
            cliente_doc = ''
            comprobante = 'DIRECTO'
            id_imprimir = c.idcredito
            es_directo = True
            
            if c.idventa:
                if c.idventa.idcliente:
                    cliente_nombre = c.idventa.idcliente.razonsocial
                    cliente_doc = c.idventa.idcliente.numdoc
                comprobante = c.idventa.numero_comprobante or 'SIN COMPROBANTE'
                id_imprimir = c.idventa.idventa
                es_directo = False
            elif c.idcliente:
                cliente_nombre = c.idcliente.razonsocial
                cliente_doc = c.idcliente.numdoc

            # Acortar nombre del cliente (truncatewords approx)
            if cliente_nombre:
                palabras = cliente_nombre.split()
                if len(palabras) > 4:
                    cliente_nombre_truncado = " ".join(palabras[:4]) + "..."
                else:
                    cliente_nombre_truncado = cliente_nombre
            else:
                cliente_nombre_truncado = "Sin Cliente"

            creditos_serializados.append({
                'idcredito': c.idcredito,
                'id_imprimir': id_imprimir,
                'es_directo': es_directo,
                'codigo_credito': c.codigo_credito,
                'cliente_nombre': cliente_nombre_truncado,
                'cliente_doc': cliente_doc,
                'comprobante': comprobante,
                'fecha': c.fecha_credito.strftime('%d/%m/%Y') if c.fecha_credito else '',
                'monto_total': float(c.monto_total) if c.monto_total else 0,
                'monto_adelanto': float(c.monto_adelanto) if c.monto_adelanto else 0,
                'saldo_pendiente': float(c.saldo_pendiente) if c.saldo_pendiente else 0,
                'cuotas': c.cantidad_cuotas,
                'estado': (c.estado_credito or 'desconocido').upper()
            })

        return JsonResponse({
            'ok': True,
            'creditos': creditos_serializados,
            'stats': {
                'total_creditos': paginator.count,
                'total_activos': total_activos,
                'total_mora': total_mora,
                'total_pagados': total_pagados,
                'monto_total_creditos': monto_total_creditos,
                'saldo_total_pendiente': saldo_total_pendiente
            },
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous()
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)
