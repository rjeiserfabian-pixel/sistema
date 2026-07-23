from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404

from software.models.VehiculosModel import Vehiculo
from software.models.RepuestoModel import Repuesto
from software.models.RespuestoCompModel import RepuestoComp
from software.models.compradetalleModel import CompraDetalle
from software.models.VentaDetalleModel import VentaDetalle
from software.models.stockModel import Stock
from software.models.CreditoModel import Credito
from software.models.detalleTransferenciaModel import DetalleTransferencia
from software.models.AuditoriaVentasModel import AuditoriaVentas
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos
from software.models.empresaModel import Empresa
from software.utils.trazabilidad_pdf_service import generar_pdf_vehiculo, generar_pdf_repuesto


def trazabilidad(request):
    """Vista principal del modulo de Trazabilidad."""
    id2 = request.session.get('idtipousuario')
    if not id2:
        return HttpResponse("<h1>No tiene acceso</h1>")
    permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
    context = {'permisos': permisos}
    return render(request, 'trazabilidad/trazabilidad.html', context)


def _get_trazabilidad_vehiculo_data(termino):
    """Lógica extraída para obtener datos de trazabilidad del vehículo sin N+1."""
    base_qs = Vehiculo.objects.select_related(
        'idproducto__idmarca', 'idproducto__idmodelo',
        'idproducto__idcolor', 'idproducto__idcategoria',
        'idestadoproducto', 'id_situacion',
    )
    vehiculo = base_qs.filter(serie_motor__iexact=termino).first() or \
               base_qs.filter(serie_chasis__iexact=termino).first()

    if not vehiculo:
        return {'ok': False, 'error': f'No se encontro ningun vehiculo con la serie "{termino}".'}

    compra_det = CompraDetalle.objects.filter(id_vehiculo=vehiculo).select_related(
        'idcompra__idproveedor', 'idcompra__id_almacen'
    ).first()

    venta_det = VentaDetalle.objects.filter(id_vehiculo=vehiculo).select_related(
        'idventa__idcliente', 'idventa__idusuario',
        'idventa__idtipocomprobante', 'idventa__id_forma_pago',
    ).first()

    stock = Stock.objects.filter(id_vehiculo=vehiculo).select_related('id_almacen').first()

    credito = Credito.objects.filter(id_vehiculo=vehiculo).select_related('id_garante').first()
    if not credito and venta_det:
        try:
            credito = Credito.objects.select_related('id_garante').get(idventa=venta_det.idventa)
        except Credito.DoesNotExist:
            credito = None

    transferencias = list(
        DetalleTransferencia.objects.filter(id_vehiculo=vehiculo).select_related(
            'id_transferencia__id_almacen_origen',
            'id_transferencia__id_almacen_destino',
            'id_transferencia__idusuario_solicita',
        ).order_by('id_transferencia__fecha_transferencia')
    )

    auditorias = []
    if venta_det:
        auditorias = list(
            AuditoriaVentas.objects.filter(
                idventa=venta_det.idventa_id
            ).select_related('idusuario').order_by('fecha_auditoria')
        )

    if venta_det and venta_det.idventa.estado == 0:
        estado_actual, estado_label, estado_color = 'anulado', 'Anulado', 'danger'
    elif credito and credito.estado_credito == 'retenido':
        estado_actual, estado_label, estado_color = 'retenido', 'Vehiculo Retenido', 'warning'
    elif credito and credito.estado_credito in ('activo', 'mora'):
        estado_actual, estado_label, estado_color = 'credito', f'En Credito ({credito.estado_credito.title()})', 'info'
    elif venta_det and venta_det.idventa.estado == 1:
        estado_actual, estado_label, estado_color = 'vendido', 'Vendido', 'success'
    elif stock and stock.cantidad_disponible > 0:
        estado_actual, estado_label, estado_color = 'disponible', 'Disponible en Stock', 'primary'
    else:
        estado_actual, estado_label, estado_color = 'sin_informacion', 'Sin informacion', 'secondary'

    producto = vehiculo.idproducto
    data = {
        'ok': True,
        'vehiculo': {
            'id': vehiculo.id_vehiculo,
            'nombre': producto.nomproducto if producto else 'Sin nombre',
            'marca': producto.idmarca.nombremarca if producto and producto.idmarca else '-',
            'modelo': producto.idmodelo.nombremodelo if producto and producto.idmodelo else '-',
            'color': producto.idcolor.nombrecolor if producto and producto.idcolor else '-',
            'categoria': producto.idcategoria.nomcategoria if producto and producto.idcategoria else '-',
            'serie_motor': vehiculo.serie_motor,
            'serie_chasis': vehiculo.serie_chasis,
            'anio': vehiculo.anio or '-',
            'placas': vehiculo.placas or '-',
            'estado_actual': estado_actual,
            'estado_label': estado_label,
            'estado_color': estado_color,
        },
        'compra': None, 'venta': None, 'credito': None, 'stock': None,
        'transferencias': [], 'auditorias': [],
    }

    if compra_det and compra_det.idcompra:
        c = compra_det.idcompra
        almacen_nombre = '-'
        if getattr(c, 'id_almacen', None):
            almacen_nombre = c.id_almacen.nombre_almacen
        elif stock and getattr(stock, 'id_almacen', None):
            almacen_nombre = stock.id_almacen.nombre_almacen
            
        data['compra'] = {
            'fecha': c.fechacompra.strftime('%d/%m/%Y') if c.fechacompra else '-',
            'proveedor': c.idproveedor.razonsocial if c.idproveedor else 'Sin proveedor',
            'precio_compra': f"S/ {compra_det.precio_compra:,.2f}",
            'comprobante': c.numcorrelativo or '-',
            'almacen': almacen_nombre,
        }

    if venta_det:
        v = venta_det.idventa
        try:
            nombre_cliente = v.idcliente.razonsocial if v.idcliente else '-'
            doc_cliente = v.idcliente.numdoc if v.idcliente else '-'
        except Exception:
            nombre_cliente = '-'
            doc_cliente = '-'
        data['venta'] = {
            'fecha': v.fecha_venta.strftime('%d/%m/%Y %I:%M %p') if v.fecha_venta else '-',
            'cliente': nombre_cliente,
            'cliente_doc': doc_cliente,
            'precio_venta': f"S/ {venta_det.subtotal:,.2f}",
            'comprobante': v.numero_comprobante or '-',
            'tipo_comprobante': v.idtipocomprobante.nombre if v.idtipocomprobante else '-',
            'forma_pago': v.id_forma_pago.nombre if v.id_forma_pago else '-',
            'estado': 'Activa' if v.estado == 1 else 'Anulada',
            'almacen': v.id_almacen.nombre_almacen if getattr(v, 'id_almacen', None) else '-',
        }

    if credito:
        try:
            garante_str = f"{credito.id_garante.nombre} {credito.id_garante.apellido}" if credito.id_garante else 'Sin garante'
        except Exception:
            garante_str = 'Sin garante'
        data['credito'] = {
            'codigo': credito.codigo_credito,
            'monto_total': f"S/ {credito.monto_total:,.2f}",
            'adelanto': f"S/ {credito.monto_adelanto:,.2f}",
            'saldo': f"S/ {credito.saldo_pendiente:,.2f}",
            'cuotas': credito.cantidad_cuotas,
            'estado': credito.estado_credito.title(),
            'garante': garante_str,
        }

    if stock:
        data['stock'] = {
            'almacen': stock.id_almacen.nombre_almacen if stock.id_almacen else '-',
            'cantidad': stock.cantidad_disponible,
        }

    for t in transferencias:
        tr = t.id_transferencia
        data['transferencias'].append({
            'fecha': tr.fecha_transferencia.strftime('%d/%m/%Y') if tr.fecha_transferencia else '-',
            'origen': tr.id_almacen_origen.nombre_almacen if tr.id_almacen_origen else (tr.lugar_origen or '-'),
            'destino': tr.id_almacen_destino.nombre_almacen if tr.id_almacen_destino else (tr.lugar_destino or '-'),
            'estado': tr.estado.replace('_', ' ').title(),
            'guia': tr.numero_guia or '-',
        })

    for a in auditorias:
        try:
            user_str = f"{a.idusuario.nombre} {a.idusuario.apellido}"
        except Exception:
            user_str = '-'
        data['auditorias'].append({
            'fecha': a.fecha_auditoria.strftime('%d/%m/%Y %I:%M %p') if a.fecha_auditoria else '-',
            'accion': a.accion,
            'motivo': a.motivo or '-',
            'usuario': user_str,
        })

    return data


def buscar_vehiculo(request):
    """API interna: Retorna JSON con el historial completo del vehiculo."""
    termino = (request.GET.get('q') or '').strip()
    if not termino or len(termino) < 3:
        return JsonResponse({'ok': False, 'error': 'Ingresa al menos 3 caracteres para buscar.'})

    data = _get_trazabilidad_vehiculo_data(termino)
    return JsonResponse(data)


def _get_trazabilidad_repuesto_data(termino):
    """Lógica extraída para obtener datos de trazabilidad del repuesto sin N+1."""
    repuesto = Repuesto.objects.select_related(
        'idmarca', 'id_categoria_repuesto', 'idunidad', 'id_garantia_repuesto'
    ).filter(codigo_barras__iexact=termino, estado=1).first()

    if not repuesto:
        return {'ok': False, 'error': f'No se encontro ningun repuesto con el codigo "{termino}".'}

    ids_instancias = list(
        RepuestoComp.objects.filter(id_repuesto=repuesto).values_list('pk', flat=True)
    )

    compras_det = list(
        CompraDetalle.objects.filter(id_repuesto_comprado__in=ids_instancias).select_related(
            'idcompra__idproveedor', 'idcompra__id_almacen'
        ).order_by('idcompra__fechacompra')
    )

    ventas_det = list(
        VentaDetalle.objects.filter(id_repuesto_comprado__in=ids_instancias).select_related(
            'idventa__idcliente', 'idventa__idtipocomprobante', 'idventa__id_forma_pago'
        ).order_by('idventa__fecha_venta')
    )

    stocks = list(
        Stock.objects.filter(id_repuesto_comprado__in=ids_instancias).select_related('id_almacen')
    )

    total_ingresado = sum(c.cantidad for c in compras_det)
    total_vendido = sum(v.cantidad for v in ventas_det if v.idventa.estado == 1)
    stock_total = sum(s.cantidad_disponible for s in stocks)

    data = {
        'ok': True,
        'repuesto': {
            'nombre': repuesto.nombre,
            'marca': repuesto.idmarca.nombre if repuesto.idmarca else '-',
            'categoria': repuesto.id_categoria_repuesto.nombre if repuesto.id_categoria_repuesto else '-',
            'codigo_barras': repuesto.codigo_barras or '-',
            'codigo_interno': repuesto.codigo_interno or '-',
            'compatibilidad': repuesto.compatibilidad or '-',
            'garantia': repuesto.id_garantia_repuesto.nombre if repuesto.id_garantia_repuesto else '-',
            'total_ingresado': total_ingresado,
            'total_vendido': total_vendido,
            'stock_actual': stock_total,
        },
        'compras': [],
        'ventas': [],
        'stock_detalle': [],
    }

    for c in compras_det:
        comp = c.idcompra
        almacen_nombre = '-'
        if getattr(comp, 'id_almacen', None):
            almacen_nombre = comp.id_almacen.nombre_almacen
        elif stocks and getattr(stocks[0], 'id_almacen', None):
            almacen_nombre = stocks[0].id_almacen.nombre_almacen
            
        data['compras'].append({
            'fecha': comp.fechacompra.strftime('%d/%m/%Y') if comp.fechacompra else '-',
            'proveedor': comp.idproveedor.razonsocial if comp.idproveedor else 'Sin proveedor',
            'cantidad': c.cantidad,
            'precio_unitario': f"S/ {c.precio_compra:,.2f}",
            'subtotal': f"S/ {float(c.subtotal):,.2f}",
            'comprobante': comp.numcorrelativo or '-',
            'almacen': almacen_nombre,
        })

    for v in ventas_det:
        venta = v.idventa
        try:
            cliente_str = venta.idcliente.razonsocial if venta.idcliente else '-'
            doc_cliente = venta.idcliente.numdoc if venta.idcliente else '-'
        except Exception:
            cliente_str = '-'
            doc_cliente = '-'
        data['ventas'].append({
            'fecha': venta.fecha_venta.strftime('%d/%m/%Y %I:%M %p') if venta.fecha_venta else '-',
            'cliente': cliente_str,
            'cliente_doc': doc_cliente,
            'cantidad': v.cantidad,
            'precio_unitario': f"S/ {v.precio_venta_contado:,.2f}",
            'subtotal': f"S/ {v.subtotal:,.2f}",
            'comprobante': venta.numero_comprobante or '-',
            'tipo_comprobante': venta.idtipocomprobante.nombre if venta.idtipocomprobante else '-',
            'estado': 'Activa' if venta.estado == 1 else 'Anulada',
            'almacen': venta.id_almacen.nombre_almacen if getattr(venta, 'id_almacen', None) else '-',
        })

    for s in stocks:
        data['stock_detalle'].append({
            'almacen': s.id_almacen.nombre_almacen if s.id_almacen else '-',
            'cantidad': s.cantidad_disponible,
        })

    return data


def buscar_repuesto(request):
    """API interna: Busca repuestos por codigo de barras. Retorna JSON."""
    termino = (request.GET.get('q') or '').strip()
    if not termino or len(termino) < 2:
        return JsonResponse({'ok': False, 'error': 'Ingresa al menos 2 caracteres para buscar.'})

    data = _get_trazabilidad_repuesto_data(termino)
    return JsonResponse(data)


def pdf_trazabilidad_vehiculo(request, serie):
    """Genera el PDF de la trazabilidad del vehículo."""
    data = _get_trazabilidad_vehiculo_data(serie)
    if not data.get('ok'):
        return HttpResponse(data.get('error'), status=404)
        
    empresa = Empresa.objects.filter(activo=True).first()
    return generar_pdf_vehiculo(data, empresa)


def pdf_trazabilidad_repuesto(request, codigo):
    """Genera el PDF de la trazabilidad del repuesto."""
    data = _get_trazabilidad_repuesto_data(codigo)
    if not data.get('ok'):
        return HttpResponse(data.get('error'), status=404)
        
    empresa = Empresa.objects.filter(activo=True).first()
    return generar_pdf_repuesto(data, empresa)
