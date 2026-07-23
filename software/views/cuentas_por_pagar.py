from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.utils import timezone
from io import BytesIO

from reportlab.lib.pagesizes import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, Image, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from software.models.comprasModel import Compras
from software.models.cuotaModel import Cuota
from software.models.PagoCuotaCompraModel import PagoCuotaCompra
from software.models.TipoPagoModel import TipoPago
from software.models.AperturaCierreCajaModel import AperturaCierreCaja
from software.models.movimientoCajaModel import MovimientoCaja
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos

def cuentas_por_pagar(request):
    id2 = request.session.get('idtipousuario')
    if not id2:
        return HttpResponse("<h1>No tiene acceso señor</h1>")
    
    permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
    id_sucursal = request.session.get('id_sucursal')
    es_admin = (id2 == 1)
    
    # Filtrar solo compras al crédito (id_forma_pago=2) para stats base vacias
    import datetime
    today = datetime.date.today()
    first_day = today.replace(day=1)

    fecha_desde = request.GET.get('fecha_desde', first_day.strftime('%Y-%m-%d'))
    fecha_hasta = request.GET.get('fecha_hasta', today.strftime('%Y-%m-%d'))

    data = {
        'compras_credito': [], # Se cargará por AJAX
        'total_compras': 0,
        'total_activos': 0,
        'total_canceladas': 0,
        'saldo_total_pendiente': 0.0,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'permisos': permisos,
        'es_admin': es_admin,
    }
    return render(request, 'cuentas_por_pagar/lista.html', data)

def api_listar_cuentas_por_pagar(request):
    from django.core.paginator import Paginator
    from django.db.models import Q

    id2 = request.session.get('idtipousuario')
    if not id2:
        return JsonResponse({'ok': False, 'error': 'No autorizado'}, status=401)
        
    id_sucursal = request.session.get('id_sucursal')
    es_admin = (id2 == 1)

    page_number = request.GET.get('page', 1)
    busqueda = request.GET.get('busqueda', '').strip()
    estado_filtro = request.GET.get('estado', 'todos')
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')

    base_queryset = Compras.objects.filter(estado=1, id_forma_pago_id=2).select_related(
        'idproveedor'
    ).prefetch_related('cuota')

    if not es_admin and id_sucursal:
        base_queryset = base_queryset.filter(id_sucursal_id=id_sucursal)
    elif es_admin and id_sucursal:
        base_queryset = base_queryset.filter(id_sucursal_id=id_sucursal)

    if fecha_desde:
        base_queryset = base_queryset.filter(fechacompra__gte=fecha_desde)
    if fecha_hasta:
        base_queryset = base_queryset.filter(fechacompra__lte=fecha_hasta)

    if busqueda:
        base_queryset = base_queryset.filter(
            Q(idproveedor__razonsocial__icontains=busqueda) |
            Q(idproveedor__numdoc__icontains=busqueda) |
            Q(numcorrelativo__icontains=busqueda)
        )

    compras_list = []
    total_compras = 0
    total_activos = 0
    total_canceladas = 0
    saldo_total_pendiente = 0.0

    all_filtered = base_queryset.order_by('-idcompra')
    
    for compra in all_filtered:
        cuotas = compra.cuota.all()
        compra.saldo_pendiente_calculado = sum((c.total - c.monto_pagado) for c in cuotas if c.estado == 1)
        
        if compra.saldo_pendiente_calculado <= 0:
            compra.estado_credito = 'pagado'
        else:
            compra.estado_credito = 'activo'
            
        if estado_filtro != 'todos' and compra.estado_credito != estado_filtro:
            continue
            
        compras_list.append(compra)
        total_compras += 1
        
        if compra.estado_credito == 'pagado':
            total_canceladas += 1
        else:
            total_activos += 1
            saldo_total_pendiente += float(compra.saldo_pendiente_calculado)

    paginator = Paginator(compras_list, 10)
    page_obj = paginator.get_page(page_number)

    data = []
    for c in page_obj:
        data.append({
            'idcompra': c.idcompra,
            'numcorrelativo': c.numcorrelativo,
            'proveedor_razonsocial': c.idproveedor.razonsocial if c.idproveedor else '',
            'proveedor_numdoc': c.idproveedor.numdoc if c.idproveedor else '',
            'fechacompra': c.fechacompra.strftime("%d/%m/%Y") if c.fechacompra else '',
            'total_compra': str(c.total_compra),
            'saldo_pendiente': str(c.saldo_pendiente_calculado),
            'estado_credito': c.estado_credito
        })
        
    page_range = []
    for i in paginator.page_range:
        if i >= page_obj.number - 3 and i <= page_obj.number + 3:
            page_range.append(i)

    return JsonResponse({
        'ok': True,
        'solicitudes': data,
        'stats': {
            'total_compras': total_compras,
            'total_activos': total_activos,
            'total_canceladas': total_canceladas,
            'saldo_total_pendiente': saldo_total_pendiente
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

def detalle_cuenta_pagar(request, idcompra):
    id2 = request.session.get('idtipousuario')
    if not id2:
        return HttpResponse("<h1>No tiene acceso señor</h1>")
        
    compra = get_object_or_404(Compras, idcompra=idcompra, estado=1)
    cuotas = Cuota.objects.filter(idcompra=compra, estado=1).prefetch_related('pagos__id_tipo_pago', 'pagos__idusuario').order_by('numero_cuota')
    tipos_pago = TipoPago.objects.filter(estado=1)
    
    saldo_total = sum((c.total - c.monto_pagado) for c in cuotas)
    total_pagado = sum(c.monto_pagado for c in cuotas)
    
    for c in cuotas:
        for pago in c.pagos.all():
            pago.nombres_metodos_display = pago.id_tipo_pago.nombre
            if pago.observaciones and " (S/" in pago.observaciones:
                try:
                    parts = pago.observaciones.split(" - ")[0].split(" | ")
                    names = [p.split(" (S/")[0].strip() for p in parts if " (S/" in p]
                    if names:
                        pago.nombres_metodos_display = ", ".join(names)
                except Exception:
                    pass
    
    data = {
        'compra': compra,
        'cuotas': cuotas,
        'saldo_total': saldo_total,
        'total_pagado': total_pagado,
        'tipos_pago': tipos_pago,
    }
    return render(request, 'cuentas_por_pagar/detalle.html', data)

@transaction.atomic
def registrar_pago_cuota(request):
    if request.method == "POST":
        idusuario_session = request.session.get('idusuario')
        id_caja_session = request.session.get('id_caja')
        id_sucursal_session = request.session.get('id_sucursal')
        # Verificar si afecta a caja
        afecta_caja = request.POST.get('afecta_caja') == '1'
        
        apertura = None
        if afecta_caja:
            if not id_caja_session:
                return JsonResponse({'ok': False, 'error': 'Debe seleccionar una caja'}, status=400)
                
            apertura = AperturaCierreCaja.objects.filter(
                idusuario_id=idusuario_session,
                id_caja_id=id_caja_session,
                estado__in=['abierta', 'reabierta']
            ).first()
            
            if not apertura:
                return JsonResponse({'ok': False, 'error': 'La caja no está aperturada'}, status=400)
            
        idcuota = request.POST.get('idcuota')
        
        montos_list = request.POST.getlist('monto[]')
        tipos_pago_list = request.POST.getlist('tipo_pago_id[]')
        nros_operacion_list = request.POST.getlist('nro_operacion[]')
        observaciones_gen = request.POST.get('observaciones', '')
        
        if not montos_list or not tipos_pago_list:
            return JsonResponse({'ok': False, 'error': 'Debe especificar al menos un método de pago'}, status=400)
            
        monto_total_pago = sum(float(m) for m in montos_list if m)
        
        # Prevención de N+1
        tipos_pago_obj = {str(t.id_tipo_pago): t for t in TipoPago.objects.filter(id_tipo_pago__in=tipos_pago_list)}
        
        cuota = get_object_or_404(Cuota, id_cuota=idcuota, estado=1)
        saldo_actual_cuota = float(cuota.total) - float(cuota.monto_pagado)
        
        if monto_total_pago <= 0 or monto_total_pago > saldo_actual_cuota + 0.01:
            return JsonResponse({'ok': False, 'error': 'Monto de pago inválido o excede el saldo'}, status=400)
            
            
        # Validar fondos en caja si afecta a caja
        if afecta_caja:
            from django.db.models import Sum
            from decimal import Decimal
            
            ingresos = MovimientoCaja.objects.filter(
                id_movimiento=apertura,
                tipo_movimiento='ingreso',
                estado=1
            ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
            
            egresos = MovimientoCaja.objects.filter(
                id_movimiento=apertura,
                tipo_movimiento='egreso',
                estado=1
            ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
            
            saldo_inicial = apertura.saldo_inicial or Decimal('0.00')
            saldo_actual_caja = saldo_inicial + ingresos - egresos
            
            if saldo_actual_caja < Decimal(str(monto_total_pago)):
                return JsonResponse({
                    'ok': False, 
                    'error': f'Fondos insuficientes en la caja para registrar el pago. Saldo actual: S/ {saldo_actual_caja:.2f}, Monto requerido: S/ {monto_total_pago:.2f}.'
                }, status=400)
            
        # Actualizar cuota
        cuota.monto_pagado = float(cuota.monto_pagado) + monto_total_pago
        cuota.saldo_cuota = float(cuota.total) - cuota.monto_pagado
        cuota.fecha_pago = timezone.now()
        
        if abs(cuota.saldo_cuota) <= 0.01:
            cuota.estado_pago = 'Cancelado'
            cuota.saldo_cuota = 0
            
        cuota.save()
        
        primer_pago_id = None
        detalles_observacion = []
        
        # Registrar egresos múltiples e ir armando la observación consolidada
        for i in range(len(montos_list)):
            m_parcial = float(montos_list[i])
            if m_parcial <= 0: continue
            
            t_pago_id = tipos_pago_list[i]
            n_op = nros_operacion_list[i] if i < len(nros_operacion_list) else ''
            
            tipo_pago = tipos_pago_obj.get(str(t_pago_id))
            nombre_metodo = tipo_pago.nombre if tipo_pago else 'Desconocido'
            
            detalle = f"{nombre_metodo} (S/{m_parcial})"
            if n_op.strip():
                detalle += f" [Op: {n_op.strip()}]"
            detalles_observacion.append(detalle)
                
            if afecta_caja:
                MovimientoCaja.objects.create(
                    id_caja_id=id_caja_session,
                    idusuario_id=idusuario_session,
                    id_movimiento=apertura,
                    idcompra=cuota.idcompra,
                    tipo_movimiento='egreso',
                    monto=m_parcial,
                    descripcion=f"Pago cuota {cuota.numero_cuota} compra {cuota.idcompra.numcorrelativo} - {nombre_metodo}",
                    estado=1
                )

        obs_consolidada = observaciones_gen
        if detalles_observacion:
            obs_consolidada = " | ".join(detalles_observacion) + (" - " + observaciones_gen if observaciones_gen else "")

        # Crear UN SOLO registro de pago para el historial y ticket
        pago = PagoCuotaCompra.objects.create(
            idcuota=cuota,
            idusuario_id=idusuario_session,
            id_tipo_pago_id=tipos_pago_list[0] if tipos_pago_list else None,
            monto_pago=monto_total_pago,
            observaciones=obs_consolidada
        )
        
        primer_pago_id = pago.idpagocuotacompra
        
        return JsonResponse({
            'ok': True, 
            'message': 'Abono registrado correctamente',
            'idpagocuotacompra': primer_pago_id
        })
        
    return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)

def imprimir_ticket_pago(request, idpago):
    pago = get_object_or_404(PagoCuotaCompra, idpagocuotacompra=idpago, estado=1)
    
    # Valores por defecto para el ancho (80mm) y largo
    TAMANO_TICKET = (80 * mm, 200 * mm)
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=TAMANO_TICKET,
        rightMargin=5*mm, leftMargin=5*mm, topMargin=5*mm, bottomMargin=5*mm
    )
    
    # Estilos
    estilos = {
        'titulo': ParagraphStyle(name='Titulo', fontSize=10, leading=12, alignment=TA_CENTER, fontName='Helvetica-Bold'),
        'subtitulo': ParagraphStyle(name='Sub', fontSize=8, leading=10, alignment=TA_CENTER, fontName='Helvetica'),
        'normal': ParagraphStyle(name='Normal', fontSize=8, leading=10, fontName='Helvetica'),
        'negrita': ParagraphStyle(name='Negrita', fontSize=8, leading=10, fontName='Helvetica-Bold'),
        'derecha': ParagraphStyle(name='Derecha', fontSize=8, leading=10, alignment=TA_RIGHT, fontName='Helvetica'),
    }
    
    elementos = []
    
    elementos.append(Paragraph("TICKET DE PAGO - PROVEEDOR", estilos['titulo']))
    elementos.append(Spacer(1, 5))
    elementos.append(Paragraph(f"Fecha: {pago.fecha_pago.strftime('%Y-%m-%d %H:%M:%S')}", estilos['subtitulo']))
    elementos.append(HRFlowable(width="100%", thickness=1, color="black", spaceBefore=5, spaceAfter=5))
    
    elementos.append(Paragraph(f"<b>Proveedor:</b> {pago.idcuota.idcompra.idproveedor.razonsocial}", estilos['normal']))
    elementos.append(Paragraph(f"<b>Compra N°:</b> {pago.idcuota.idcompra.numcorrelativo}", estilos['normal']))
    elementos.append(Paragraph(f"<b>Cuota N°:</b> {pago.idcuota.numero_cuota}", estilos['normal']))
    elementos.append(Paragraph(f"<b>Realizado por:</b> {pago.idusuario.nombrecompleto}", estilos['normal']))
    
    elementos.append(Spacer(1, 5))
    
    # Detalle de montos
    tipo_pago_display = pago.id_tipo_pago.nombre
    datos_tabla = [
        [Paragraph("TIPO PAGO", estilos['negrita']), Paragraph(tipo_pago_display, estilos['derecha'])],
    ]
    
    if pago.observaciones and " (S/" in pago.observaciones:
        try:
            datos_tabla[0][1] = Paragraph("MÚLTIPLE", estilos['derecha'])
            parts = pago.observaciones.split(" - ")[0].split(" | ")
            for p in parts:
                if " (S/" in p:
                    method_name = p.split(" (S/")[0].strip()
                    monto_str = p.split(" (S/")[1].split(")")[0]
                    if "[Op:" in p:
                        op_str = p.split("[Op:")[1].split("]")[0].strip()
                        method_name += f" (Op: {op_str})"
                    datos_tabla.append([Paragraph(f"- {method_name}", estilos['normal']), Paragraph(f"S/ {monto_str}", estilos['derecha'])])
        except Exception:
            pass
            
    datos_tabla.extend([
        [Paragraph("MONTO TOTAL", estilos['negrita']), Paragraph(f"S/ {pago.idcuota.total}", estilos['derecha'])],
        [Paragraph("MONTO PAGADO", estilos['negrita']), Paragraph(f"S/ {pago.monto_pago}", estilos['derecha'])],
        [Paragraph("SALDO PENDIENTE", estilos['negrita']), Paragraph(f"S/ {pago.idcuota.saldo_cuota}", estilos['derecha'])]
    ])
    
    tabla = Table(datos_tabla, colWidths=[40*mm, 30*mm])
    
    elementos.append(tabla)
    elementos.append(HRFlowable(width="100%", thickness=1, color="black", spaceBefore=5, spaceAfter=5))
    elementos.append(Paragraph("Abono procesado en sistema.", estilos['subtitulo']))
    
    doc.build(elementos)
    buffer.seek(0)
    
    return HttpResponse(buffer.getvalue(), content_type='application/pdf')
