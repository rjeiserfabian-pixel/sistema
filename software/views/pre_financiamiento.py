import json
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db import transaction
from django.utils import timezone
from django.db.models import Q
from django.core.paginator import Paginator

from software.models.PreCreditoModel import PreCredito
from software.models.DetallePagoInicialModel import DetallePagoInicial
from software.models.ClienteModel import Cliente
from software.models.VehiculosModel import Vehiculo
from software.models.TipoPagoModel import TipoPago
from software.models.UsuarioModel import Usuario
from software.models.stockModel import Stock
from software.models.compradetalleModel import CompraDetalle
from software.models.ProductoModel import Producto
from software.models.almacenesModel import Almacenes
from software.models.movimientoCajaModel import MovimientoCaja
from software.models.AperturaCierreCajaModel import AperturaCierreCaja


# ─────────────────────────────────────────────────────────────────────────────
# 1. ÍNDICE / LISTADO
# ─────────────────────────────────────────────────────────────────────────────

def index_pre_financiamiento(request):
    """
    Vista principal del módulo de Pre-Financiamiento.
    Muestra todas las solicitudes con filtros por estado y búsqueda.
    """
    id_tipo_usuario = request.session.get('idtipousuario')
    if not id_tipo_usuario:
        return redirect('login')

    import datetime
    today = datetime.date.today()
    first_day = today.replace(day=1)

    fecha_desde = request.GET.get('fecha_desde', first_day.strftime('%Y-%m-%d'))
    fecha_hasta = request.GET.get('fecha_hasta', today.strftime('%Y-%m-%d'))
    estado_filtro = request.GET.get('estado', 'todos')
    busqueda = request.GET.get('busqueda', '').strip()

    data = {
        'idtipousuario': id_tipo_usuario,
        'solicitudes': [],  # Se cargará vía AJAX
        'estado_filtro': estado_filtro,
        'busqueda': busqueda,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'total_pendientes': 0,
        'total_aprobados': 0,
        'total_rechazados': 0,
    }
    return render(request, 'pre_financiamiento/index.html', data)


# ─────────────────────────────────────────────────────────────────────────────
# API LISTAR (SERVER-SIDE)
# ─────────────────────────────────────────────────────────────────────────────

def api_listar_pre_financiamiento(request):
    """
    API JSON para listado de Pre-Financiamientos paginado.
    """
    id_tipo_usuario = request.session.get('idtipousuario')
    if not id_tipo_usuario:
        return JsonResponse({'ok': False, 'error': 'No autorizado'}, status=401)

    page_number = request.GET.get('page', 1)
    busqueda = request.GET.get('busqueda', '').strip()
    estado_filtro = request.GET.get('estado', 'todos')
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')

    qs = PreCredito.objects.select_related(
        'idcliente', 'id_vehiculo__idproducto', 'idusuario', 'id_sucursal'
    ).order_by('-fecha_registro')

    id_almacen_session = request.session.get('id_almacen')
    if id_almacen_session:
        from software.models.stockModel import Stock
        # Obtener los IDs de los vehículos que tienen stock en el almacén actual
        vehiculos_en_almacen = Stock.objects.filter(
            id_almacen_id=id_almacen_session,
            estado=1
        ).values_list('id_vehiculo_id', flat=True)
        qs = qs.filter(id_vehiculo_id__in=vehiculos_en_almacen)

    if estado_filtro != 'todos':
        qs = qs.filter(estado=estado_filtro)

    if fecha_desde:
        qs = qs.filter(fecha_registro__date__gte=fecha_desde)
    
    if fecha_hasta:
        qs = qs.filter(fecha_registro__date__lte=fecha_hasta)

    if busqueda:
        qs = qs.filter(
            Q(idcliente__razonsocial__icontains=busqueda) |
            Q(idcliente__numdoc__icontains=busqueda) |
            Q(id_vehiculo__idproducto__nomproducto__icontains=busqueda) |
            Q(id_vehiculo__serie_motor__icontains=busqueda) |
            Q(id_vehiculo__serie_chasis__icontains=busqueda)
        )

    qs_stats = PreCredito.objects.all()
    if id_almacen_session:
        qs_stats = qs_stats.filter(id_vehiculo_id__in=vehiculos_en_almacen)
    if fecha_desde: qs_stats = qs_stats.filter(fecha_registro__date__gte=fecha_desde)
    if fecha_hasta: qs_stats = qs_stats.filter(fecha_registro__date__lte=fecha_hasta)

    total_pendientes = qs_stats.filter(estado='pendiente').count()
    total_aprobados  = qs_stats.filter(estado='aprobado').count()
    total_rechazados = qs_stats.filter(estado='rechazado').count()

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(page_number)

    data = []
    for s in page_obj:
        detalles_pago = s.detalles_pago.all()
        pagos_list = []
        for d in detalles_pago:
            pagos_list.append({
                'tipo': d.id_tipo_pago.nombre if d.id_tipo_pago else 'Desconocido',
                'monto': str(d.monto)
            })

        data.append({
            'id_pre_credito': s.id_pre_credito,
            'cliente_razonsocial': s.idcliente.razonsocial if getattr(s, 'idcliente', None) else '',
            'cliente_numdoc': s.idcliente.numdoc if getattr(s, 'idcliente', None) else '',
            'vehiculo_nombre': s.nombre_vehiculo,
            'vehiculo_chasis': s.id_vehiculo.serie_chasis if getattr(s, 'id_vehiculo', None) else '',
            'vehiculo_motor': s.id_vehiculo.serie_motor if getattr(s, 'id_vehiculo', None) else '',
            'monto_inicial': str(s.monto_inicial),
            'estado': s.estado,
            'cobrado': s.cobrado,
            'fecha_registro': s.fecha_registro.strftime("%d/%m/%Y %H:%M") if s.fecha_registro else '',
            'usuario_nombre': s.idusuario.nombrecompleto if getattr(s, 'idusuario', None) else '—',
            'observaciones': s.observaciones or '',
            'observacion_evaluacion': s.observacion_evaluacion or '',
            'pagos': pagos_list
        })

    # Construir paginacion visible: mostramos hasta 7 paginas alrededor de la actual
    page_range = []
    for i in paginator.page_range:
        if i >= page_obj.number - 3 and i <= page_obj.number + 3:
            page_range.append(i)

    return JsonResponse({
        'ok': True,
        'solicitudes': data,
        'stats': {
            'pendientes': total_pendientes,
            'aprobados': total_aprobados,
            'rechazados': total_rechazados,
        },
        'pagination': {
            'has_previous': page_obj.has_previous(),
            'has_next': page_obj.has_next(),
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'previous_page_number': page_obj.previous_page_number() if page_obj.has_previous() else None,
            'next_page_number': page_obj.next_page_number() if page_obj.has_next() else None,
            'page_range': page_range,
        }
    })

# ─────────────────────────────────────────────────────────────────────────────
# 2. REGISTRAR NUEVA SOLICITUD
# ─────────────────────────────────────────────────────────────────────────────

def registrar_pre_financiamiento(request):
    """
    Formulario para registrar una nueva solicitud de pre-financiamiento.
    Incluye selección de cliente, vehículo y registro del pago inicial (mixto).
    """
    id_tipo_usuario = request.session.get('idtipousuario')
    if not id_tipo_usuario:
        return redirect('login')

    if request.method == 'POST':
        return _guardar_pre_financiamiento(request)

    # GET: Obtener datos para el formulario
    clientes = Cliente.objects.filter(estado=1).order_by('razonsocial')
    tipos_pago = TipoPago.objects.filter(estado=1)

    # Obtener vehículos con stock en el almacén de sesión
    id_almacen_session = request.session.get('id_almacen')
    vehiculos_disponibles = _get_vehiculos_disponibles(id_almacen_session)

    data = {
        'clientes': clientes,
        'tipos_pago': tipos_pago,
        'vehiculos_disponibles_json': json.dumps(vehiculos_disponibles),
        'id_almacen_session': id_almacen_session,
    }
    return render(request, 'pre_financiamiento/registrar.html', data)


@transaction.atomic
def _guardar_pre_financiamiento(request):
    """Lógica de guardado de la nueva solicitud de pre-financiamiento."""
    try:
        idcliente    = request.POST.get('idcliente', '').strip()
        id_vehiculo  = request.POST.get('id_vehiculo', '').strip()
        observaciones = request.POST.get('observaciones', '').strip()
        idusuario    = request.session.get('idusuario')
        id_sucursal  = request.session.get('id_sucursal')

        # Validaciones básicas
        if not idcliente:
            return JsonResponse({'ok': False, 'error': 'Debe seleccionar un cliente.'}, status=400)
        if not id_vehiculo:
            return JsonResponse({'ok': False, 'error': 'Debe seleccionar un vehículo.'}, status=400)

        # Obtener montos de pago (puede ser mixto: varios métodos)
        tipos_pago_ids   = request.POST.getlist('tipo_pago_id[]')
        montos_pago      = request.POST.getlist('monto_pago[]')
        nros_operacion   = request.POST.getlist('nro_operacion[]')

        if not tipos_pago_ids or not montos_pago:
            return JsonResponse({'ok': False, 'error': 'Debe registrar al menos un pago inicial.'}, status=400)

        # Calcular monto total inicial
        monto_total_inicial = Decimal('0')
        detalles_pago = []
        # Usar zip_longest o similar si el tamaño varía, pero aquí asumimos que coinciden
        for i in range(len(tipos_pago_ids)):
            tipo_id = tipos_pago_ids[i]
            monto_str = montos_pago[i]
            nro_op = nros_operacion[i] if i < len(nros_operacion) else ''

            try:
                monto = Decimal(monto_str)
                if monto <= 0:
                    raise ValueError
            except Exception:
                return JsonResponse({'ok': False, 'error': f'Monto inválido: {monto_str}'}, status=400)
            
            monto_total_inicial += monto
            detalles_pago.append({
                'tipo_id': tipo_id, 
                'monto': monto,
                'nro_op': nro_op
            })

        if monto_total_inicial <= 0:
            return JsonResponse({'ok': False, 'error': 'El monto inicial total debe ser mayor a cero.'}, status=400)

        cliente  = get_object_or_404(Cliente, pk=idcliente)
        vehiculo = get_object_or_404(Vehiculo, pk=id_vehiculo)

        # Crear el PreCredito
        pre_credito = PreCredito.objects.create(
            idcliente=cliente,
            id_vehiculo=vehiculo,
            monto_inicial=monto_total_inicial,
            estado='pendiente',
            idusuario_id=idusuario,
            id_sucursal_id=id_sucursal,
            observaciones=observaciones,
        )

        # ✅ ACTUALIZAR SITUACIÓN DEL VEHÍCULO A RESERVADO
        from software.models.SituacionVehiculoModel import SituacionVehiculo
        situacion_reservado, _ = SituacionVehiculo.objects.get_or_create(
            nombre_situacion='RESERVADO (PRE-FINANC.)', 
            defaults={'estado': 1}
        )
        vehiculo.id_situacion = situacion_reservado
        vehiculo.save()

        # Crear el detalle de pago (mixto)
        for detalle in detalles_pago:
            DetallePagoInicial.objects.create(
                id_pre_credito=pre_credito,
                id_tipo_pago_id=detalle['tipo_id'],
                monto=detalle['monto'],
                numero_operacion=detalle['nro_op']
            )

        return JsonResponse({
            'ok': True,
            'message': f'Solicitud registrada correctamente con monto inicial de S/ {monto_total_inicial}.',
            'id_pre_credito': pre_credito.id_pre_credito,
        })

    except Exception as e:
        return JsonResponse({'ok': False, 'error': f'Error al registrar: {str(e)}'}, status=500)


# ─────────────────────────────────────────────────────────────────────────────
# 3. EVALUAR (APROBAR / RECHAZAR)
# ─────────────────────────────────────────────────────────────────────────────

@transaction.atomic
def evaluar_pre_financiamiento(request, id_pre_credito):
    """
    Cambia el estado de una solicitud de pre-financiamiento:
    - accion='aprobar'  → estado = 'aprobado'
    - accion='rechazar' → estado = 'rechazado'
    Solo admite POST.
    """
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido.'}, status=405)

    id_tipo_usuario = request.session.get('idtipousuario')
    if not id_tipo_usuario:
        return JsonResponse({'ok': False, 'error': 'Sesión expirada.'}, status=403)
    
    if id_tipo_usuario == 2:
        return JsonResponse({'ok': False, 'error': 'No tiene permisos para evaluar solicitudes.'}, status=403)

    pre_credito = get_object_or_404(PreCredito, pk=id_pre_credito)

    if pre_credito.estado != 'pendiente':
        return JsonResponse({
            'ok': False,
            'error': f'Esta solicitud ya fue evaluada (estado: {pre_credito.get_estado_display()}).'
        }, status=400)

    accion = request.POST.get('accion', '').strip().lower()
    observacion_eval = request.POST.get('observacion_evaluacion', '').strip()
    
    if observacion_eval:
        pre_credito.observacion_evaluacion = observacion_eval

    if accion == 'aprobar':
        pre_credito.estado = 'aprobado'
        pre_credito.save()
        return JsonResponse({
            'ok': True,
            'message': '✅ Solicitud aprobada. Puede proceder a registrar la venta a crédito.',
            'nuevo_estado': 'aprobado',
            'redirect_url': f'/ventas/?pre_credito_id={pre_credito.id_pre_credito}',
        })

    elif accion == 'rechazar':
        if pre_credito.cobrado:
            # 1. Verificar caja abierta para devolución
            idusuario = request.session.get('idusuario')
            apertura = AperturaCierreCaja.objects.filter(
                idusuario_id=idusuario,
                estado__in=['abierta', 'reabierta']
            ).first()

            if not apertura:
                return JsonResponse({
                    'ok': False, 
                    'error': 'Debe tener una caja abierta para procesar el rechazo (devolución de inicial cobrado).'
                }, status=400)

        pre_credito.estado = 'rechazado'
        pre_credito.save()

        # ✅ VOLVER VEHÍCULO A DISPONIBLE
        from software.models.SituacionVehiculoModel import SituacionVehiculo
        situacion_disponible, _ = SituacionVehiculo.objects.get_or_create(
            nombre_situacion='DISPONIBLE', 
            defaults={'estado': 1}
        )
        if pre_credito.id_vehiculo:
            pre_credito.id_vehiculo.id_situacion = situacion_disponible
            pre_credito.id_vehiculo.save()

        # 2. Registrar egreso en caja si fue cobrado
        if pre_credito.cobrado:
            MovimientoCaja.objects.create(
                id_caja=apertura.id_caja,
                id_movimiento=apertura,
                idusuario_id=idusuario,
                tipo_movimiento='egreso',
                monto=pre_credito.monto_inicial,
                descripcion=f"Devolución Inicial Pre-Crédito #{pre_credito.id_pre_credito} (Rechazado) - Cliente: {pre_credito.idcliente.razonsocial}",
                estado=1
            )

        return JsonResponse({
            'ok': True,
            'message': '❌ Solicitud rechazada' + (' y monto inicial devuelto desde caja.' if pre_credito.cobrado else '.'),
            'nuevo_estado': 'rechazado',
        })

    else:
        return JsonResponse({'ok': False, 'error': 'Acción no válida. Use "aprobar" o "rechazar".'}, status=400)


# ─────────────────────────────────────────────────────────────────────────────
# COBRAR E IMPRIMIR RECIBO
# ─────────────────────────────────────────────────────────────────────────────

@transaction.atomic
def cobrar_pre_financiamiento(request, id_pre_credito):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido.'}, status=405)

    id_tipo_usuario = request.session.get('idtipousuario')
    if not id_tipo_usuario:
        return JsonResponse({'ok': False, 'error': 'Sesión expirada.'}, status=403)
    if id_tipo_usuario == 2:
        return JsonResponse({'ok': False, 'error': 'No tiene permisos para cobrar solicitudes.'}, status=403)

    pre_credito = get_object_or_404(PreCredito, pk=id_pre_credito)

    if pre_credito.cobrado:
        return JsonResponse({'ok': False, 'error': 'Esta solicitud ya ha sido cobrada.'}, status=400)

    idusuario = request.session.get('idusuario')
    apertura = AperturaCierreCaja.objects.filter(
        idusuario_id=idusuario,
        estado__in=['abierta', 'reabierta']
    ).first()

    if not apertura:
        return JsonResponse({
            'ok': False, 
            'error': 'Debe tener una caja abierta para registrar el cobro.'
        }, status=400)

    # 1. Registrar movimiento en caja
    MovimientoCaja.objects.create(
        id_caja=apertura.id_caja,
        id_movimiento=apertura,
        idusuario_id=idusuario,
        tipo_movimiento='ingreso',
        monto=pre_credito.monto_inicial,
        descripcion=f"Cobro Inicial Pre-Crédito #{pre_credito.id_pre_credito} - Cliente: {pre_credito.idcliente.razonsocial}",
        estado=1
    )

    pre_credito.cobrado = True
    pre_credito.save()

    return JsonResponse({
        'ok': True,
        'message': 'Cobro registrado correctamente en caja.',
        'url_recibo': f'/pre-financiamiento/recibo/{pre_credito.id_pre_credito}/'
    })


def imprimir_recibo_pre_financiamiento(request, id_pre_credito):
    """Genera el ticket térmico para el cliente en formato PDF."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from io import BytesIO
        from django.http import HttpResponse
        
        from software.models.empresaModel import Empresa
        from software.utils.logo_utils import get_logo_image_for_pdf
        from software.models.movimientoCajaModel import MovimientoCaja
        
        pre_credito = get_object_or_404(PreCredito, pk=id_pre_credito)
        
        # Buscar empresa (la primera activa)
        empresa = Empresa.objects.filter(activo=True).first()
        if not empresa:
            return HttpResponse("No se encontró información de la empresa.", status=400)
            
        buffer = BytesIO()
        ticket_width = 80 * mm
        elements = []
        styles = getSampleStyleSheet()
        
        style_company = ParagraphStyle('CompanyName', parent=styles['Normal'], fontSize=10, textColor=colors.black, alignment=TA_CENTER, fontName='Helvetica-Bold', spaceAfter=1, leading=11)
        style_header = ParagraphStyle('TicketHeader', parent=styles['Normal'], fontSize=9, textColor=colors.black, alignment=TA_CENTER, fontName='Helvetica-Bold', spaceAfter=2, leading=10)
        style_normal_center = ParagraphStyle('NormalCenter', parent=styles['Normal'], fontSize=7, alignment=TA_CENTER, spaceAfter=1, leading=8)
        style_bold = ParagraphStyle('TicketBold', parent=styles['Normal'], fontSize=7, fontName='Helvetica-Bold', spaceAfter=1, alignment=TA_CENTER, leading=8)
        style_small = ParagraphStyle('SmallText', parent=styles['Normal'], fontSize=6, alignment=TA_CENTER, spaceAfter=0.5, leading=7)
        
        # LOGO
        logo_rl = get_logo_image_for_pdf(empresa, width_mm=30, height_mm=30, circular=True, use_ticket_logo=True)
        if logo_rl:
            elements.append(logo_rl)
            elements.append(Spacer(1, 3*mm))
            
        # ENCABEZADO
        nombre_empresa = empresa.razonsocial if empresa.razonsocial else empresa.nombrecomercial
        elements.append(Paragraph(nombre_empresa.upper(), style_company))
        elements.append(Paragraph(f"RUC: {empresa.ruc}", style_normal_center))
        elements.append(Paragraph(empresa.direccion.upper(), style_normal_center))
        if empresa.ubigueo:
            elements.append(Paragraph(f"UBIGEO: {empresa.ubigueo}", style_normal_center))
        elements.append(Paragraph(f"Telf: {empresa.telefono}", style_normal_center))
        if empresa.pagina:
            elements.append(Paragraph(f"Pagina: {empresa.pagina}", style_small))
        
        elements.append(Spacer(1, 2*mm))
        elements.append(Paragraph("=" * 48, style_normal_center))
        elements.append(Spacer(1, 2*mm))
        
        # TITULO
        elements.append(Paragraph("<b>RECIBO DE ADELANTO</b>", style_header))
        elements.append(Paragraph(f"<b>PRE-FINANCIAMIENTO #{pre_credito.id_pre_credito}</b>", style_header))
        elements.append(Spacer(1, 2*mm))
        
        # CLIENTE
        cliente_nombre = pre_credito.idcliente.razonsocial
        if len(cliente_nombre) > 35:
            cliente_nombre = cliente_nombre[:32] + '...'
            
        elements.append(Paragraph("<b>CLIENTE:</b>", style_bold))
        elements.append(Paragraph(f"{cliente_nombre}", style_normal_center))
        elements.append(Paragraph(f"<b>RUC/DNI:</b> {pre_credito.idcliente.numdoc or '---'}", style_normal_center))
        if pre_credito.idcliente.direccion:
            elements.append(Paragraph(f"<b>DIR:</b> {pre_credito.idcliente.direccion[:40]}", style_small))
        
        if pre_credito.idcliente.telefono:
            elements.append(Paragraph(f"<b>Tel:</b> {pre_credito.idcliente.telefono}", style_small))
            
        elements.append(Spacer(1, 2*mm))
        elements.append(Paragraph("-" * 50, style_normal_center))
        
        # VEHICULO
        elements.append(Paragraph("<b>VEHÍCULO RESERVADO:</b>", style_bold))
        vehiculo_nombre = pre_credito.nombre_vehiculo
        elements.append(Paragraph(f"{vehiculo_nombre}", style_normal_center))
        
        if pre_credito.id_vehiculo:
            if pre_credito.id_vehiculo.serie_chasis:
                elements.append(Paragraph(f"<b>CHASIS:</b> {pre_credito.id_vehiculo.serie_chasis}", style_normal_center))
            if pre_credito.id_vehiculo.serie_motor:
                elements.append(Paragraph(f"<b>MOTOR:</b> {pre_credito.id_vehiculo.serie_motor}", style_normal_center))
                
        elements.append(Spacer(1, 2*mm))
        
        # MONTO Y ESTADO
        elements.append(Paragraph(f"<b>MONTO ADELANTO:</b> S/ {pre_credito.monto_inicial}", style_bold))
        estado_txt = "PAGADO" if pre_credito.cobrado else "PENDIENTE"
        elements.append(Paragraph(f"<b>ESTADO:</b> {estado_txt}", style_normal_center))
        
        elements.append(Spacer(1, 2*mm))
        elements.append(Paragraph("-" * 50, style_normal_center))
        
        # DATOS ADICIONALES
        fecha_str = pre_credito.fecha_registro.strftime('%d/%m/%Y')
        hora_str = pre_credito.fecha_registro.strftime('%I:%M %p')
        elements.append(Paragraph(f"<b>FECHA:</b> {fecha_str} <b>HORA:</b> {hora_str}", style_normal_center))
        
        cajero_nombre = pre_credito.idusuario.nombrecompleto if pre_credito.idusuario else "Admin"
        elements.append(Paragraph(f"<b>VENDEDOR/CAJERO:</b> {cajero_nombre}", style_normal_center))
        
        # CAJA QUE COBRÓ
        caja_nombre = "---"
        if pre_credito.cobrado:
            mov = MovimientoCaja.objects.filter(
                descripcion__contains=f"Cobro Inicial Pre-Crédito #{pre_credito.id_pre_credito}"
            ).first()
            if mov and mov.id_caja:
                caja_nombre = mov.id_caja.nombre_caja
        elements.append(Paragraph(f"<b>CAJA:</b> {caja_nombre}", style_normal_center))
        
        elements.append(Spacer(1, 4*mm))
        
        # PIE DE PÁGINA
        elements.append(Paragraph("Conserve este recibo para cualquier reclamo o devolución en caso de rechazo del crédito.", style_small))
        elements.append(Paragraph("¡Gracias por su preferencia!", style_bold))
        
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
            rightMargin=3 * mm,
            leftMargin=3 * mm,
            topMargin=5 * mm,
            bottomMargin=5 * mm
        )
        
        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="recibo_pre_credito_{pre_credito.id_pre_credito}.pdf"'
        response.write(pdf)
        
        return response
        
    except Exception as e:
        import traceback
        print(f"Error generando recibo pre-credito: {e}")
        traceback.print_exc()
        return HttpResponse(f"Error al generar el recibo PDF: {e}", status=500)


# ─────────────────────────────────────────────────────────────────────────────
# 4. API — OBTENER DATOS DE UN PRE-CRÉDITO (para el módulo de ventas)
# ─────────────────────────────────────────────────────────────────────────────

def get_pre_credito_data(request, id_pre_credito):
    """
    Endpoint JSON que retorna los datos del pre-crédito para
    que el módulo de ventas pueda pre-cargar el formulario automáticamente.
    """
    id_tipo_usuario = request.session.get('idtipousuario')
    if not id_tipo_usuario:
        return JsonResponse({'ok': False, 'error': 'No autenticado.'}, status=403)

    pre_credito = get_object_or_404(PreCredito, pk=id_pre_credito)

    if pre_credito.estado != 'aprobado':
        return JsonResponse({
            'ok': False,
            'error': f'El pre-crédito no está aprobado (estado: {pre_credito.get_estado_display()}).'
        }, status=400)

    # Datos del cliente
    cliente = pre_credito.idcliente
    cliente_data = {
        'idcliente': cliente.idcliente,
        'razonsocial': cliente.razonsocial,
        'numdoc': cliente.numdoc,
    }

    # Datos del vehículo
    vehiculo_data = None
    if pre_credito.id_vehiculo:
        vehiculo = pre_credito.id_vehiculo
        # Buscar precio desde stock o compradetalle
        id_almacen = request.session.get('id_almacen')
        precio_venta = 0
        precio_compra = 0
        
        # 1. Intentar obtener desde el stock del almacén actual
        stock = None
        if id_almacen:
            stock = Stock.objects.filter(
                id_almacen_id=id_almacen,
                id_vehiculo=vehiculo,
                estado=1
            ).select_related('idcompradetalle').first()
        
        # 2. Fallback: Buscar en CompraDetalle si no hay stock o no tiene detalle
        detalle_compra = None
        if stock and stock.idcompradetalle:
            detalle_compra = stock.idcompradetalle
        else:
            detalle_compra = CompraDetalle.objects.filter(
                id_vehiculo=vehiculo
            ).order_by('-idcompradetalle').first()

        if detalle_compra:
            precio_venta  = float(detalle_compra.precio_maximo)
            precio_compra = float(detalle_compra.precio_compra)

        vehiculo_data = {
            'id_vehiculo': vehiculo.id_vehiculo,
            'nombre': vehiculo.idproducto.nomproducto if vehiculo.idproducto else 'N/A',
            'serie_motor': vehiculo.serie_motor,
            'serie_chasis': vehiculo.serie_chasis,
            'precio_venta': precio_venta,
            'precio_compra': precio_compra,
        }

    # Detalles del pago inicial (para mostrar en la UI)
    detalles = []
    for d in pre_credito.detalles_pago.select_related('id_tipo_pago').all():
        detalles.append({
            'metodo': d.id_tipo_pago.nombre if d.id_tipo_pago else 'N/A',
            'monto': float(d.monto),
        })

    return JsonResponse({
        'ok': True,
        'pre_credito': {
            'id_pre_credito': pre_credito.id_pre_credito,
            'monto_inicial': float(pre_credito.monto_inicial),
            'observaciones': pre_credito.observaciones or '',
        },
        'cliente': cliente_data,
        'vehiculo': vehiculo_data,
        'detalles_pago': detalles,
    })


# ─────────────────────────────────────────────────────────────────────────────
# HELPER — Obtener vehículos con stock disponible
# ─────────────────────────────────────────────────────────────────────────────

def _get_vehiculos_disponibles(id_almacen):
    """
    Retorna lista de vehículos con stock en el almacén indicado,
    incluyendo nombre del producto y precio de venta.
    """
    if not id_almacen:
        return []

    # Obtener IDs de vehículos que ya tienen una solicitud activa (pendiente o aprobada)
    vehiculos_en_proceso = PreCredito.objects.filter(
        estado__in=['pendiente', 'aprobado']
    ).values_list('id_vehiculo_id', flat=True)

    vehiculos = []
    stocks = Stock.objects.filter(
        id_almacen_id=id_almacen,
        id_vehiculo__isnull=False,
        id_vehiculo__id_situacion__nombre_situacion='DISPONIBLE',
        cantidad_disponible__gt=0,
        estado=1
    ).exclude(
        id_vehiculo_id__in=vehiculos_en_proceso
    ).select_related(
        'id_vehiculo__idproducto',
        'idcompradetalle'
    )

    for s in stocks:
        v = s.id_vehiculo
        
        # Obtener detalle de compra (directo o por fallback para datos antiguos)
        if s.idcompradetalle:
            detalle_compra = s.idcompradetalle
        else:
            from software.models.compradetalleModel import CompraDetalle
            detalle_compra = CompraDetalle.objects.filter(
                id_vehiculo=v
            ).order_by('-idcompradetalle').first()
            
        precio_venta  = float(detalle_compra.precio_maximo)  if detalle_compra else 0
        precio_compra = float(detalle_compra.precio_compra) if detalle_compra else 0
        vehiculos.append({
            'id_vehiculo':   v.id_vehiculo,
            'nombre':        v.idproducto.nomproducto if v.idproducto else 'N/A',
            'serie_motor':   v.serie_motor,
            'serie_chasis':  v.serie_chasis,
            'precio_venta':  precio_venta,
            'precio_compra': precio_compra,
            'stock':         s.cantidad_disponible,
        })

    return vehiculos
