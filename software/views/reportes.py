
def _get_creditos_filtrados(request, fi, ff):
    from django.utils import timezone
    from datetime import timedelta
    from software.models.empresaModel import Empresa
    from django.db.models import Q, OuterRef, Subquery, Count
    from django.db.models.functions import Coalesce
    from software.models.CuotasVentaModel import CuotasVenta
    from software.models.CreditoModel import Credito

    estado_filtro = request.GET.get('estado', 'todos').strip().lower()
    color_mora = request.GET.get('color_mora', 'todos').strip().lower()
    codigo_filtro = request.GET.get('codigo', '').strip()
    cliente_id = request.GET.get('cliente_id', '').strip()
    sucursal_filtro = request.GET.get('sucursal', '').strip()
    frecuencia_filtro = request.GET.get('frecuencia', 'todos').strip()
    
    creditos_qs = Credito.objects.filter(fecha_credito__date__range=[fi, ff])
    
    if estado_filtro in ['cancelado', 'anulado']:
        creditos_qs = creditos_qs.filter(estado_credito=estado_filtro)
    else:
        creditos_qs = creditos_qs.filter(estado=1)
        if estado_filtro != 'todos':
            creditos_qs = creditos_qs.filter(estado_credito=estado_filtro)
            
    if codigo_filtro:
        creditos_qs = creditos_qs.filter(codigo_credito__icontains=codigo_filtro)
    if cliente_id:
        creditos_qs = creditos_qs.filter(
            Q(idcliente_id=cliente_id) |
            Q(idventa__idcliente_id=cliente_id)
        )
        
    if sucursal_filtro:
        creditos_qs = creditos_qs.filter(
            Q(idventa__id_sucursal_id=sucursal_filtro) | 
            Q(id_sucursal_id=sucursal_filtro)
        )
    if frecuencia_filtro and frecuencia_filtro != 'todos':
        creditos_qs = creditos_qs.filter(frecuencia_pago=frecuencia_filtro)

    hoy_date = timezone.now().date()
    
    oldest_cuota_venta_qs = CuotasVenta.objects.filter(
        idventa=OuterRef('idventa'),
        estado=1,
        estado_pago__in=['Pendiente', 'Parcial'],
        fecha_vencimiento__lt=hoy_date
    ).order_by('fecha_vencimiento').values('fecha_vencimiento')[:1]

    oldest_cuota_credito_qs = CuotasVenta.objects.filter(
        idcredito=OuterRef('pk'),
        estado=1,
        estado_pago__in=['Pendiente', 'Parcial'],
        fecha_vencimiento__lt=hoy_date
    ).order_by('fecha_vencimiento').values('fecha_vencimiento')[:1]

    cuotas_vencidas_venta_qs = CuotasVenta.objects.filter(
        idventa=OuterRef('idventa'),
        estado=1,
        estado_pago__in=['Pendiente', 'Parcial'],
        fecha_vencimiento__lt=hoy_date
    ).values('idventa').annotate(cnt=Count('idcuotaventa')).values('cnt')[:1]

    cuotas_vencidas_credito_qs = CuotasVenta.objects.filter(
        idcredito=OuterRef('pk'),
        estado=1,
        estado_pago__in=['Pendiente', 'Parcial'],
        fecha_vencimiento__lt=hoy_date
    ).values('idcredito').annotate(cnt=Count('idcuotaventa')).values('cnt')[:1]

    creditos_qs = creditos_qs.annotate(
        oldest_vencimiento=Coalesce(
            Subquery(oldest_cuota_venta_qs),
            Subquery(oldest_cuota_credito_qs)
        ),
        cuotas_vencidas_count=Coalesce(
            Subquery(cuotas_vencidas_venta_qs),
            Subquery(cuotas_vencidas_credito_qs),
            0
        )
    )

    empresa = Empresa.objects.first()

    lim = {
        'diario': {
            'verde':    empresa.limite_dias_verde_diario    if empresa else 5,
            'amarillo': empresa.limite_dias_amarillo_diario if empresa else 10,
        },
        'semanal': {
            'verde':    empresa.limite_dias_verde_semanal    if empresa else 20,
            'amarillo': empresa.limite_dias_amarillo_semanal if empresa else 30,
        },
        'quincenal': {
            'verde':    empresa.limite_dias_verde_quincenal    if empresa else 30,
            'amarillo': empresa.limite_dias_amarillo_quincenal if empresa else 45,
        },
        'mensual': {
            'verde':    empresa.limite_cuotas_verde_mensual    if empresa else 1,
            'amarillo': empresa.limite_cuotas_amarillo_mensual if empresa else 2,
        },
        'default': {
            'verde':    empresa.limite_dias_verde    if empresa else 10,
            'amarillo': empresa.limite_dias_amarillo if empresa else 20,
        },
    }

    if color_mora != 'todos':
        def _q_dias(freq_key, color):
            l = lim[freq_key]
            fecha_verde_ini    = hoy_date - timedelta(days=l['verde'])
            fecha_amarillo_ini = hoy_date - timedelta(days=l['amarillo'])
            if color == 'verde':
                return Q(frecuencia_pago__iexact=freq_key) & Q(
                    oldest_vencimiento__gte=fecha_verde_ini,
                    oldest_vencimiento__lt=hoy_date
                )
            elif color == 'amarillo':
                return Q(frecuencia_pago__iexact=freq_key) & Q(
                    oldest_vencimiento__gte=fecha_amarillo_ini,
                    oldest_vencimiento__lt=fecha_verde_ini
                )
            else:
                return Q(frecuencia_pago__iexact=freq_key) & Q(
                    oldest_vencimiento__lt=fecha_amarillo_ini
                )

        lm = lim['mensual']
        if color_mora == 'verde':
            q_mensual = Q(frecuencia_pago__iexact='mensual') & Q(
                cuotas_vencidas_count__gte=1,
                cuotas_vencidas_count__lte=lm['verde']
            )
            q_no_mensual = (
                _q_dias('diario', 'verde') |
                _q_dias('semanal', 'verde') |
                _q_dias('quincenal', 'verde') |
                _q_dias('default', 'verde')
            )
        elif color_mora == 'amarillo':
            q_mensual = Q(frecuencia_pago__iexact='mensual') & Q(
                cuotas_vencidas_count__gt=lm['verde'],
                cuotas_vencidas_count__lte=lm['amarillo']
            )
            q_no_mensual = (
                _q_dias('diario', 'amarillo') |
                _q_dias('semanal', 'amarillo') |
                _q_dias('quincenal', 'amarillo') |
                _q_dias('default', 'amarillo')
            )
        else:
            q_mensual = Q(frecuencia_pago__iexact='mensual') & Q(
                cuotas_vencidas_count__gt=lm['amarillo']
            )
            q_no_mensual = (
                _q_dias('diario', 'rojo') |
                _q_dias('semanal', 'rojo') |
                _q_dias('quincenal', 'rojo') |
                _q_dias('default', 'rojo')
            )

        creditos_qs = creditos_qs.filter(q_mensual | q_no_mensual)

    search_value = request.GET.get('search[value]', request.GET.get('search', '')).strip()
    if search_value:
        creditos_qs = creditos_qs.filter(
            Q(codigo_credito__icontains=search_value) |
            Q(idcliente__razonsocial__icontains=search_value) |
            Q(idventa__idcliente__razonsocial__icontains=search_value) |
            Q(idventa__numero_comprobante__icontains=search_value) |
            Q(id_vehiculo__idproducto__nomproducto__icontains=search_value) |
            Q(id_vehiculo__serie_chasis__icontains=search_value) |
            Q(id_vehiculo__serie_motor__icontains=search_value) |
            Q(idventa__ventadetalle__id_vehiculo__idproducto__nomproducto__icontains=search_value) |
            Q(idventa__ventadetalle__id_vehiculo__serie_chasis__icontains=search_value) |
            Q(idventa__ventadetalle__id_vehiculo__serie_motor__icontains=search_value) |
            Q(id_repuesto_comprado__id_repuesto__nombre__icontains=search_value) |
            Q(id_repuesto_comprado__id_repuesto__codigo_barras__icontains=search_value) |
            Q(idventa__ventadetalle__id_repuesto_comprado__id_repuesto__nombre__icontains=search_value) |
            Q(idventa__ventadetalle__id_repuesto_comprado__id_repuesto__codigo_barras__icontains=search_value)
        ).distinct()

    creditos_qs = creditos_qs.select_related('idventa', 'idventa__idcliente', 'idcliente').order_by('-idcredito')
    return creditos_qs, search_value, lim

"""
Vistas del módulo de Reportes.
Todos los reportes centralizados bajo /reportes/.
"""
from datetime import date, datetime
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q, F, OuterRef, Subquery, DecimalField, Case, When, Value
from django.db.models.functions import Coalesce, Cast

from software.models.VentasModel import Ventas
from software.models.sucursalesModel import Sucursales
from software.models.comprasModel import Compras
from software.models.ClienteModel import Cliente
from software.models.ProveedoresModel import Proveedor
from software.models.movimientoCajaModel import MovimientoCaja
from software.models.UsuarioModel import Usuario
from software.models.CreditoModel import Credito
from software.models.CuotasVentaModel import CuotasVenta
from software.models.stockModel import Stock
from software.models.compradetalleModel import CompraDetalle
from software.models.TipoPagoModel import TipoPago
from software.models.PagoCuotaModel import PagoCuota
from software.models.TipocomprobanteModel import Tipocomprobante

from software.views.report_exports import export_to_excel, export_to_pdf

def _parse_fechas(request):
    """Parsea fecha_inicio y fecha_fin del GET. Por defecto: mes actual."""
    hoy = date.today()
    fi_str = request.GET.get('fecha_inicio', hoy.replace(day=1).strftime('%Y-%m-%d'))
    ff_str = request.GET.get('fecha_fin',    hoy.strftime('%Y-%m-%d'))
    try:
        fi = datetime.strptime(fi_str, '%Y-%m-%d').date()
    except ValueError:
        fi = hoy.replace(day=1)
        fi_str = fi.strftime('%Y-%m-%d')
    try:
        ff = datetime.strptime(ff_str, '%Y-%m-%d').date()
    except ValueError:
        ff = hoy
        ff_str = ff.strftime('%Y-%m-%d')
    return fi, ff, fi_str, ff_str


# ─────────────────────────────────────────────────
#  REPORTE DE VENTAS
# ─────────────────────────────────────────────────
def reporte_ventas(request):
    idusuario = request.session.get('idusuario')
    if not idusuario:
        return redirect('iniciar_sesion')
        
    fi, ff, fi_str, ff_str = _parse_fechas(request)
    sucursal_filtro = request.GET.get('sucursal', '').strip()
    ventas_qs = Ventas.objects.filter(
        fecha_venta__date__range=[fi, ff],
        estado__in=[1, 2]
    )
    if sucursal_filtro:
        ventas_qs = ventas_qs.filter(id_sucursal_id=sucursal_filtro)
        
    vendedor_id = request.GET.get('vendedor')
    if vendedor_id:
        ventas_qs = ventas_qs.filter(idusuario_id=vendedor_id)

    forma_pago_id = request.GET.get('forma_pago')
    if forma_pago_id:
        ventas_qs = ventas_qs.filter(id_forma_pago_id=forma_pago_id)

    cliente_id = request.GET.get('cliente_id')
    if cliente_id:
        ventas_qs = ventas_qs.filter(idcliente_id=cliente_id)

    tipo_comprobante_id = request.GET.get('tipo_comprobante')
    if tipo_comprobante_id:
        ventas_qs = ventas_qs.filter(idtipocomprobante_id=tipo_comprobante_id)

    search_value = request.GET.get('search', '').strip()
    if search_value:
        ventas_qs = ventas_qs.filter(
            Q(idcliente__razonsocial__icontains=search_value) |
            Q(numero_comprobante__icontains=search_value) |
            Q(ventadetalle__id_vehiculo__serie_motor__icontains=search_value) |
            Q(ventadetalle__id_vehiculo__serie_chasis__icontains=search_value) |
            Q(ventadetalle__id_repuesto_comprado__id_repuesto__codigo_barras__icontains=search_value)
        ).distinct()

    ventas_qs = ventas_qs.select_related('idcliente', 'idusuario', 'idseriecomprobante', 'id_forma_pago', 'idtipocomprobante', 'id_sucursal').order_by('-fecha_venta', '-idventa')

    export_fmt = request.GET.get('export')
    if export_fmt in ['pdf', 'excel']:
        headers = ['Nº', 'Fecha', 'Cliente', 'Tipo Comprobante', 'Comprobante', 'Sucursal', 'Vendedor', 'Forma Pago', 'Estado', 'Total (S/)']
        data = []
        for i, v in enumerate(ventas_qs, 1):
            estado_str = "Completada" if v.estado == 1 else ("Crédito" if v.estado == 2 else "Anulada")
            data.append([
                i,
                v.fecha_venta.strftime("%d/%m/%Y"),
                v.idcliente.razonsocial if v.idcliente else '-',
                v.idtipocomprobante.nombre if v.idtipocomprobante else '-',
                v.numero_comprobante or '-',
                v.id_sucursal.nombre_sucursal if v.id_sucursal else '-',
                v.idusuario.nombrecompleto if v.idusuario else '-',
                v.id_forma_pago.nombre if v.id_forma_pago else '-',
                estado_str,
                v.total_venta
            ])
            
        if export_fmt == 'excel':
            return export_to_excel(headers, data, f'Reporte_Ventas_{fi_str}_{ff_str}')
        elif export_fmt == 'pdf':
            title = f"Reporte de Ventas ({fi_str} al {ff_str})"
            return export_to_pdf(headers, data, title, f'Reporte_Ventas_{fi_str}_{ff_str}')

    totales = ventas_qs.aggregate(
        total_ventas=Sum('total_venta'),
        total_subtotal=Sum('subtotal'),
        cantidad=Count('idventa')
    )

    return render(request, 'reportes/reporte_ventas.html', {
        'fecha_inicio': fi_str,
        'fecha_fin': ff_str,
        'vendedor_id': int(vendedor_id) if vendedor_id and vendedor_id.isdigit() else None,
        'forma_pago_id': int(forma_pago_id) if forma_pago_id and forma_pago_id.isdigit() else None,
        'cliente_id': int(cliente_id) if cliente_id and cliente_id.isdigit() else '',
        'vendedores': Usuario.objects.filter(estado=1).order_by('nombrecompleto'),
        'clientes_lista': Cliente.objects.filter(estado=1).order_by('razonsocial'),
        'totales': totales,
        'sucursales': Sucursales.objects.all(),
        'sucursal_filtro': sucursal_filtro,
        'tipos_comprobante': Tipocomprobante.objects.all().order_by('nombre'),
        'tipo_comprobante_id': int(tipo_comprobante_id) if tipo_comprobante_id and tipo_comprobante_id.isdigit() else None,
    })


def api_listar_reporte_ventas(request):
    idusuario = request.session.get('idusuario')
    if not idusuario:
        return JsonResponse({'error': 'No autenticado'}, status=401)
        
    fi, ff, fi_str, ff_str = _parse_fechas(request)
    sucursal_filtro = request.GET.get('sucursal', '').strip()
    
    ventas_qs = Ventas.objects.filter(
        fecha_venta__date__range=[fi, ff],
        estado__in=[1, 2]
    )
    if sucursal_filtro:
        ventas_qs = ventas_qs.filter(id_sucursal_id=sucursal_filtro)
        
    vendedor_id = request.GET.get('vendedor')
    if vendedor_id:
        ventas_qs = ventas_qs.filter(idusuario_id=vendedor_id)

    forma_pago_id = request.GET.get('forma_pago')
    if forma_pago_id:
        ventas_qs = ventas_qs.filter(id_forma_pago_id=forma_pago_id)

    cliente_id = request.GET.get('cliente_id')
    if cliente_id:
        ventas_qs = ventas_qs.filter(idcliente_id=cliente_id)

    tipo_comprobante_id = request.GET.get('tipo_comprobante')
    if tipo_comprobante_id:
        ventas_qs = ventas_qs.filter(idtipocomprobante_id=tipo_comprobante_id)
        
    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '').strip()

    if search_value:
        ventas_qs = ventas_qs.filter(
            Q(idcliente__razonsocial__icontains=search_value) |
            Q(numero_comprobante__icontains=search_value) |
            Q(ventadetalle__id_vehiculo__serie_motor__icontains=search_value) |
            Q(ventadetalle__id_vehiculo__serie_chasis__icontains=search_value) |
            Q(ventadetalle__id_repuesto_comprado__id_repuesto__codigo_barras__icontains=search_value)
        ).distinct()

    records_total = ventas_qs.count()
    records_filtered = records_total

    totales_agregados = ventas_qs.aggregate(
        total_ventas=Sum('total_venta'),
        total_subtotal=Sum('subtotal'),
        cantidad=Count('idventa')
    )
    
    totales_dict = {
        'total_ventas': float(totales_agregados['total_ventas'] or 0),
        'total_subtotal': float(totales_agregados['total_subtotal'] or 0),
        'cantidad': totales_agregados['cantidad'] or 0
    }

    ventas_qs = ventas_qs.select_related('idcliente', 'idusuario', 'idseriecomprobante', 'id_forma_pago', 'id_sucursal', 'idtipocomprobante').order_by('-fecha_venta', '-idventa')

    if length > -1:
        ventas_page = ventas_qs[start:start + length]
    else:
        ventas_page = ventas_qs

    data = []
    for v in ventas_page:
        estado_badge = ""
        if v.estado == 1:
            estado_badge = '<span class="badge bg-success">Completada</span>'
        elif v.estado == 2:
            estado_badge = '<span class="badge bg-warning">Crédito</span>'
        else:
            estado_badge = '<span class="badge bg-danger">Anulada</span>'
            
        data.append({
            'DT_RowId': f'row_venta_{v.idventa}',
            'fecha': v.fecha_venta.strftime("%d/%m/%Y"),
            'cliente': v.idcliente.razonsocial if v.idcliente else '-',
            'tipo_comprobante': v.idtipocomprobante.nombre if v.idtipocomprobante else '-',
            'comprobante': v.numero_comprobante or '-',
            'sucursal': v.id_sucursal.nombre_sucursal if v.id_sucursal else '-',
            'vendedor': v.idusuario.nombrecompleto if v.idusuario else '-',
            'forma_pago': v.id_forma_pago.nombre if v.id_forma_pago else '-',
            'estado': estado_badge,
            'total_venta': v.total_venta
        })

    return JsonResponse({
        'draw': draw,
        'recordsTotal': records_total,
        'recordsFiltered': records_filtered,
        'data': data,
        'totales': totales_dict
    })


# ─────────────────────────────────────────────────
#  REPORTE DE COMPRAS
# ─────────────────────────────────────────────────
def reporte_compras(request):
    idusuario = request.session.get('idusuario')
    if not idusuario:
        return redirect('iniciar_sesion')
        
    fi, ff, fi_str, ff_str = _parse_fechas(request)
    sucursal_filtro = request.GET.get('sucursal', '').strip()
    
    # Base Query
    qs = Compras.objects.filter(
        fechacompra__range=[fi, ff],
        estado=1
    )
    if sucursal_filtro:
        qs = qs.filter(id_sucursal_id=sucursal_filtro)
        
    proveedor_id = request.GET.get('proveedor')
    if proveedor_id:
        qs = qs.filter(idproveedor_id=proveedor_id)

    forma_pago_id = request.GET.get('forma_pago')
    if forma_pago_id:
        qs = qs.filter(id_forma_pago_id=forma_pago_id)
        
    search_value = request.GET.get('search', '').strip()
    if search_value:
        qs = qs.filter(
            Q(idproveedor__razonsocial__icontains=search_value) |
            Q(idproveedor__numdoc__icontains=search_value) |
            Q(numcorrelativo__icontains=search_value) |
            Q(compradetalle__id_vehiculo__serie_motor__icontains=search_value) |
            Q(compradetalle__id_vehiculo__serie_chasis__icontains=search_value) |
            Q(compradetalle__id_repuesto_comprado__id_repuesto__codigo_barras__icontains=search_value)
        ).distinct()
        
    # Totales (usando el base_qs para que coincidan con la lista)
    totales = qs.aggregate(
        total_compras=Sum('total_compra'),
        cantidad=Count('idcompra')
    )

    # Detalle con Joins para el listado
    listado_qs = qs.prefetch_related('idproveedor', 'id_forma_pago', 'id_tipo_pago').order_by('-fechacompra', '-idcompra')

    # Exportación
    export_fmt = request.GET.get('export')
    if export_fmt in ['excel', 'pdf']:
        headers = ['Fecha', 'Comprobante', 'Proveedor', 'Sucursal', 'Teléfono', 'Dirección', 'Forma Pago', 'Tipo Pago', 'Estado', 'Total (S/)']
        data = []
        for c in listado_qs:
            prov = getattr(c, 'idproveedor', None)
            prov_name = getattr(prov, 'razonsocial', '-')
            telefono = getattr(prov, 'telefono', '-') or '-'
            direccion = getattr(prov, 'direccion', '-') or '-'
            
            data.append([
                c.fechacompra.strftime("%d/%m/%Y"),
                c.numcorrelativo,
                prov_name,
                c.id_sucursal.nombre_sucursal if c.id_sucursal else '-',
                telefono,
                direccion,
                getattr(c.id_forma_pago, 'nombre', '-') if getattr(c, 'id_forma_pago', None) else '-',
                getattr(c.id_tipo_pago, 'nombre', '-') if getattr(c, 'id_tipo_pago', None) else '-',
                "Activo" if c.estado == 1 else "Inactivo",
                c.total_compra
            ])
            
        if export_fmt == 'excel':
            return export_to_excel(headers, data, f'Reporte_Compras_{fi_str}_{ff_str}')
        elif export_fmt == 'pdf':
            title = f"Reporte de Compras ({fi_str} al {ff_str})"
            return export_to_pdf(headers, data, title, f'Reporte_Compras_{fi_str}_{ff_str}')

    return render(request, 'reportes/reporte_compras.html', {
        'fecha_inicio': fi_str,
        'fecha_fin': ff_str,
        'proveedor_id': int(proveedor_id) if proveedor_id and proveedor_id.isdigit() else None,
        'forma_pago_id': int(forma_pago_id) if forma_pago_id and forma_pago_id.isdigit() else None,
        'proveedores': Proveedor.objects.filter(estado=1).order_by('razonsocial'),
        'totales': totales,
        'sucursales': Sucursales.objects.all(),
        'sucursal_filtro': sucursal_filtro,
    })


def api_listar_reporte_compras(request):
    idusuario = request.session.get('idusuario')
    if not idusuario:
        return JsonResponse({'error': 'No autenticado'}, status=401)
        
    fi, ff, fi_str, ff_str = _parse_fechas(request)
    sucursal_filtro = request.GET.get('sucursal', '').strip()
    
    qs = Compras.objects.filter(
        fechacompra__range=[fi, ff],
        estado=1
    )
    if sucursal_filtro:
        qs = qs.filter(id_sucursal_id=sucursal_filtro)
        
    proveedor_id = request.GET.get('proveedor')
    if proveedor_id:
        qs = qs.filter(idproveedor_id=proveedor_id)

    forma_pago_id = request.GET.get('forma_pago')
    if forma_pago_id:
        qs = qs.filter(id_forma_pago_id=forma_pago_id)
        
    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '').strip()

    if search_value:
        qs = qs.filter(
            Q(idproveedor__razonsocial__icontains=search_value) |
            Q(idproveedor__numdoc__icontains=search_value) |
            Q(numcorrelativo__icontains=search_value) |
            Q(compradetalle__id_vehiculo__serie_motor__icontains=search_value) |
            Q(compradetalle__id_vehiculo__serie_chasis__icontains=search_value) |
            Q(compradetalle__id_repuesto_comprado__id_repuesto__codigo_barras__icontains=search_value)
        ).distinct()

    records_total = qs.count()
    records_filtered = records_total

    totales_agregados = qs.aggregate(
        total_compras=Sum('total_compra'),
        cantidad=Count('idcompra')
    )
    
    totales_dict = {
        'total_compras': float(totales_agregados['total_compras'] or 0),
        'cantidad': totales_agregados['cantidad'] or 0
    }

    qs = qs.prefetch_related('idproveedor', 'id_forma_pago', 'id_tipo_pago', 'id_sucursal').order_by('-fechacompra', '-idcompra')

    if length > -1:
        compras_page = qs[start:start + length]
    else:
        compras_page = qs

    data = []
    for c in compras_page:
        if c.estado == 1:
            estado_badge = '<span class="badge bg-success">Activo</span>'
        else:
            estado_badge = '<span class="badge bg-danger">Inactivo</span>'
            
        prov = getattr(c, 'idproveedor', None)
        prov_name = getattr(prov, 'razonsocial', '-')
        telefono = getattr(prov, 'telefono', '-') or '-'
        direccion = getattr(prov, 'direccion', '-') or '-'
            
        data.append({
            'DT_RowId': f'row_compra_{c.idcompra}',
            'fecha': c.fechacompra.strftime("%d/%m/%Y"),
            'comprobante': c.numcorrelativo,
            'proveedor': prov_name,
            'sucursal': getattr(c.id_sucursal, 'nombre_sucursal', '-') if getattr(c, 'id_sucursal', None) else '-',
            'telefono': telefono,
            'direccion': direccion,
            'forma_pago': getattr(c.id_forma_pago, 'nombre', '-') if getattr(c, 'id_forma_pago', None) else '-',
            'tipo_pago': getattr(c.id_tipo_pago, 'nombre', '-') if getattr(c, 'id_tipo_pago', None) else '-',
            'estado': estado_badge,
            'total_compra': c.total_compra
        })

    return JsonResponse({
        'draw': draw,
        'recordsTotal': records_total,
        'recordsFiltered': records_filtered,
        'data': data,
        'totales': totales_dict
    })


# ─────────────────────────────────────────────────
#  REPORTE DE ALMACÉN (LOGÍSTICA / FÍSICO)
# ─────────────────────────────────────────────────
def reporte_almacen(request):
    idusuario = request.session.get('idusuario')
    if not idusuario:
        return redirect('iniciar_sesion')
        
    sucursal_filtro = request.GET.get('sucursal', '').strip()
    almacen_filtro = request.GET.get('almacen', '').strip()

    stock_qs = Stock.objects.filter(estado=1, cantidad_disponible__gt=0)
    if almacen_filtro:
        stock_qs = stock_qs.filter(id_almacen_id=almacen_filtro)
    elif sucursal_filtro:
        stock_qs = stock_qs.filter(id_almacen__id_sucursal_id=sucursal_filtro)

    stock_vehiculos = stock_qs.filter(
        id_vehiculo__isnull=False
    ).select_related(
        'id_vehiculo__idproducto__idmarca',
        'id_vehiculo__idproducto__idcolor',
        'id_vehiculo__idproducto__idcilindrada',
        'id_almacen'
    ).order_by('-id_stock')
    
    stock_repuestos = stock_qs.filter(
        id_repuesto_comprado__isnull=False
    ).select_related(
        'id_repuesto_comprado__id_repuesto__idmarca',
        'id_repuesto_comprado__id_repuesto__id_categoria_repuesto',
        'id_almacen'
    ).order_by('-id_stock')

    export_fmt = request.GET.get('export')
    if export_fmt:
        if export_fmt.endswith('_vehiculos'):
            headers = ['Almacén', 'Vehículo', 'Marca', 'Color', 'CHASIS', 'MOTOR', 'Año', 'Stock']
            data = []
            for s in stock_vehiculos:
                v = s.id_vehiculo
                prod = getattr(v, 'idproducto', None)
                data.append([
                    s.id_almacen.nombre_almacen if s.id_almacen else '-',
                    prod.nomproducto if prod else '-',
                    prod.idmarca.nombremarca if prod and getattr(prod, 'idmarca', None) else '-',
                    prod.idcolor.nombrecolor if prod and getattr(prod, 'idcolor', None) else '-',
                    v.serie_chasis,
                    v.serie_motor,
                    v.anio,
                    s.cantidad_disponible
                ])
            fmt = export_fmt.split('_')[0] 
            if fmt == 'excel':
                return export_to_excel(headers, data, 'Reporte_Stock_Vehiculos')
            elif fmt == 'pdf':
                return export_to_pdf(headers, data, "Stock Vehículos", 'Reporte_Stock_Vehiculos')
                
        elif export_fmt.endswith('_repuestos'):
            headers = ['Almacén', 'Repuesto', 'Marca', 'Color', 'Cód. Barras', 'Stock']
            data = []
            for s in stock_repuestos:
                rc = s.id_repuesto_comprado
                rep = rc.id_repuesto if rc else None
                data.append([
                    s.id_almacen.nombre_almacen if s.id_almacen else '-',
                    rep.nombre if rep else '-',
                    rep.idmarca.nombremarca if getattr(rep, 'idmarca', None) else '-',
                    rep.id_categoria_repuesto.nomcategoria if getattr(rep, 'id_categoria_repuesto', None) else '-',
                    rc.id_repuesto.codigo_barras if rc and rc.id_repuesto else '-',
                    s.cantidad_disponible
                ])
            fmt = export_fmt.split('_')[0]
            if fmt == 'excel':
                return export_to_excel(headers, data, 'Reporte_Stock_Repuestos')
            elif fmt == 'pdf':
                return export_to_pdf(headers, data, "Stock Repuestos", 'Reporte_Stock_Repuestos')

    if not export_fmt:
        from software.models.almacenesModel import Almacenes
        return render(request, 'reportes/reporte_almacen.html', {
            'total_vehiculos': stock_vehiculos.aggregate(t=Sum('cantidad_disponible'))['t'] or 0,
            'total_repuestos': stock_repuestos.aggregate(t=Sum('cantidad_disponible'))['t'] or 0,
            'sucursales': Sucursales.objects.all(),
            'sucursal_filtro': sucursal_filtro,
            'almacenes': Almacenes.objects.filter(estado=1),
            'almacen_filtro': almacen_filtro,
        })
    else:
        # Fallback si export_fmt no es procesado
        pass
        
from django.http import JsonResponse
from django.db.models import Q

def api_listar_almacen_vehiculos(request):
    idusuario = request.session.get('idusuario')
    if not idusuario:
        return JsonResponse({'error': 'No autenticado'}, status=401)

    sucursal_filtro = request.GET.get('sucursal', '').strip()
    almacen_filtro = request.GET.get('almacen', '').strip()

    stock_qs = Stock.objects.filter(estado=1, cantidad_disponible__gt=0, id_vehiculo__isnull=False).select_related(
        'id_vehiculo__idproducto__idmarca',
        'id_vehiculo__idproducto__idcolor',
        'id_almacen'
    ).order_by('-id_stock')

    if almacen_filtro:
        stock_qs = stock_qs.filter(id_almacen_id=almacen_filtro)
    elif sucursal_filtro:
        stock_qs = stock_qs.filter(id_almacen__id_sucursal_id=sucursal_filtro)

    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '').strip()

    if search_value:
        stock_qs = stock_qs.filter(
            Q(id_vehiculo__idproducto__nomproducto__icontains=search_value) |
            Q(id_vehiculo__idproducto__idmarca__nombremarca__icontains=search_value) |
            Q(id_vehiculo__idproducto__idcolor__nombrecolor__icontains=search_value) |
            Q(id_vehiculo__serie_chasis__icontains=search_value) |
            Q(id_vehiculo__serie_motor__icontains=search_value)
        )

    records_total = stock_qs.count()
    records_filtered = records_total

    total_vehiculos = stock_qs.aggregate(t=Sum('cantidad_disponible'))['t'] or 0

    if length > -1:
        stock_page = stock_qs[start:start + length]
    else:
        stock_page = stock_qs

    data = []
    for s in stock_page:
        v = s.id_vehiculo
        prod = getattr(v, 'idproducto', None)
        almacen_nombre = s.id_almacen.nombre_almacen if s.id_almacen else '-'
        prod_nombre = prod.nomproducto if prod else '-'
        marca = prod.idmarca.nombremarca if prod and getattr(prod, 'idmarca', None) else '-'
        color = prod.idcolor.nombrecolor if prod and getattr(prod, 'idcolor', None) else '-'
        chasis_motor = f"CHU: {v.serie_chasis or ''}<br>MOT: {v.serie_motor or ''}"
        anio = v.anio or '-'

        data.append({
            'DT_RowId': f'row_{s.id_stock}',
            'almacen': almacen_nombre,
            'producto': prod_nombre,
            'marca': marca,
            'color': color,
            'chasis_motor': chasis_motor,
            'anio': anio,
            'stock': s.cantidad_disponible
        })

    return JsonResponse({
        'draw': draw,
        'recordsTotal': records_total,
        'recordsFiltered': records_filtered,
        'data': data,
        'totales': {'total_vehiculos': total_vehiculos}
    })

def api_listar_almacen_repuestos(request):
    idusuario = request.session.get('idusuario')
    if not idusuario:
        return JsonResponse({'error': 'No autenticado'}, status=401)

    sucursal_filtro = request.GET.get('sucursal', '').strip()
    almacen_filtro = request.GET.get('almacen', '').strip()

    stock_qs = Stock.objects.filter(estado=1, cantidad_disponible__gt=0, id_repuesto_comprado__isnull=False).select_related(
        'id_repuesto_comprado__id_repuesto__idmarca',
        'id_repuesto_comprado__id_repuesto__id_categoria_repuesto',
        'id_almacen'
    ).order_by('-id_stock')

    if almacen_filtro:
        stock_qs = stock_qs.filter(id_almacen_id=almacen_filtro)
    elif sucursal_filtro:
        stock_qs = stock_qs.filter(id_almacen__id_sucursal_id=sucursal_filtro)

    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '').strip()

    if search_value:
        stock_qs = stock_qs.filter(
            Q(id_repuesto_comprado__id_repuesto__nombre__icontains=search_value) |
            Q(id_repuesto_comprado__id_repuesto__idmarca__nombremarca__icontains=search_value) |
            Q(id_repuesto_comprado__id_repuesto__id_categoria_repuesto__nomcategoria__icontains=search_value) |
            Q(id_repuesto_comprado__id_repuesto__codigo_barras__icontains=search_value)
        )

    records_total = stock_qs.count()
    records_filtered = records_total

    total_repuestos = stock_qs.aggregate(t=Sum('cantidad_disponible'))['t'] or 0

    if length > -1:
        stock_page = stock_qs[start:start + length]
    else:
        stock_page = stock_qs

    data = []
    for s in stock_page:
        rc = s.id_repuesto_comprado
        rep = rc.id_repuesto if rc else None
        almacen_nombre = s.id_almacen.nombre_almacen if s.id_almacen else '-'
        rep_nombre = rep.nombre if rep else '-'
        marca = rep.idmarca.nombremarca if rep and getattr(rep, 'idmarca', None) else '-'
        color = rep.idcolor.nombrecolor if rep and getattr(rep, 'idcolor', None) else '-'
        codigo_barras = rep.codigo_barras if rep else '-'

        data.append({
            'DT_RowId': f'row_{s.id_stock}',
            'almacen': almacen_nombre,
            'repuesto': rep_nombre,
            'marca': marca,
            'color': color,
            'codigo_barras': codigo_barras,
            'stock': s.cantidad_disponible
        })

    return JsonResponse({
        'draw': draw,
        'recordsTotal': records_total,
        'recordsFiltered': records_filtered,
        'data': data,
        'totales': {'total_repuestos': total_repuestos}
    })


# ─────────────────────────────────────────────────
#  REPORTE DE INVENTARIO (CONTABLE / ECONÓMICO)
# ─────────────────────────────────────────────────
def reporte_inventario(request):
    idusuario = request.session.get('idusuario')
    if not idusuario:
        return redirect('iniciar_sesion')
        
    sucursal_filtro = request.GET.get('sucursal', '').strip()
    almacen_filtro = request.GET.get('almacen', '').strip()

    # Filtrar stock disponible (estado=1, cantidad > 0)
    stock_qs = Stock.objects.filter(estado=1, cantidad_disponible__gt=0)
    
    if almacen_filtro:
        stock_qs = stock_qs.filter(id_almacen_id=almacen_filtro)
    elif sucursal_filtro:
        stock_qs = stock_qs.filter(id_almacen__id_sucursal_id=sucursal_filtro)

    # Definir Subqueries para buscar precios en históricos de compra si no están ligados directamente
    # Para vehículos
    latest_compra_v = CompraDetalle.objects.filter(id_vehiculo=OuterRef('id_vehiculo')).order_by('-idcompradetalle')
    sub_pc_v = Subquery(latest_compra_v.values('precio_compra')[:1], output_field=DecimalField())
    sub_pv_v = Subquery(latest_compra_v.values('precio_maximo')[:1], output_field=DecimalField())

    # Para repuestos
    latest_compra_r = CompraDetalle.objects.filter(id_repuesto_comprado=OuterRef('id_repuesto_comprado')).order_by('-idcompradetalle')
    sub_pc_r = Subquery(latest_compra_r.values('precio_compra')[:1], output_field=DecimalField())
    sub_pv_r = Subquery(latest_compra_r.values('precio_maximo')[:1], output_field=DecimalField())

    # Detalle Vehículos
    vehiculos_qs = stock_qs.filter(id_vehiculo__isnull=False).select_related(
        'id_vehiculo__idproducto',
        'idcompradetalle'
    ).annotate(
        # Precio final = Usar el ligado directo, o si no buscar en el historial de compras
        pc=Coalesce(F('idcompradetalle__precio_compra'), sub_pc_v, output_field=DecimalField()),
        pv=Coalesce(F('idcompradetalle__precio_maximo'), sub_pv_v, output_field=DecimalField())
    ).annotate(
        total_inversion=Cast(F('cantidad_disponible') * F('pc'), DecimalField(max_digits=12, decimal_places=2)),
        total_ganancia=Cast(
            Case(
                When(pv=0, then=Value(0)),
                When(pv__isnull=True, then=Value(0)),
                default=F('cantidad_disponible') * (F('pv') - F('pc')),
                output_field=DecimalField()
            ),
            DecimalField(max_digits=12, decimal_places=2)
        )
    )
    
    # Detalle Repuestos
    repuestos_qs = stock_qs.filter(id_repuesto_comprado__isnull=False).select_related(
        'id_repuesto_comprado__id_repuesto',
        'idcompradetalle'
    ).annotate(
        pc=Coalesce(F('idcompradetalle__precio_compra'), sub_pc_r, output_field=DecimalField()),
        pv=Coalesce(F('idcompradetalle__precio_maximo'), sub_pv_r, output_field=DecimalField())
    ).annotate(
        total_inversion=Cast(F('cantidad_disponible') * F('pc'), DecimalField(max_digits=12, decimal_places=2)),
        total_ganancia=Cast(
            Case(
                When(pv=0, then=Value(0)),
                When(pv__isnull=True, then=Value(0)),
                default=F('cantidad_disponible') * (F('pv') - F('pc')),
                output_field=DecimalField()
            ),
            DecimalField(max_digits=12, decimal_places=2)
        )
    )

    # Exportación a Excel y PDF
    export_fmt = request.GET.get('export')
    if export_fmt in ['excel', 'pdf']:
        headers = ['Producto/Repuesto', 'Identificador', 'Stock', 'Costo Unit.', 'Venta Unit. (P. Máx)', 'Inversión', 'Ganancia Est.']
        data = []
        for v in vehiculos_qs:
            prod_name = v.id_vehiculo.idproducto.nomproducto if v.id_vehiculo and getattr(v.id_vehiculo, 'idproducto', None) else 'Vehículo'
            chasis = v.id_vehiculo.serie_chasis if v.id_vehiculo else '-'
            motor = v.id_vehiculo.serie_motor if v.id_vehiculo else '-'
            identificador = f"CH: {chasis} | MOT: {motor}"
            data.append([
                prod_name,
                identificador,
                v.cantidad_disponible,
                v.pc if v.pc is not None else 0.00,
                v.pv if v.pv is not None else 0.00,
                v.total_inversion if v.total_inversion is not None else 0.00,
                v.total_ganancia if v.total_ganancia is not None else 0.00
            ])
            
        for r in repuestos_qs:
            rc = r.id_repuesto_comprado
            rep = rc.id_repuesto if rc else None
            rep_name = rep.nombre if rep else 'Repuesto'
            codigo = rc.id_repuesto.codigo_barras if rc and rc.id_repuesto else '-'
            data.append([
                rep_name,
                f"Cód: {codigo}",
                r.cantidad_disponible,
                r.pc if r.pc is not None else 0.00,
                r.pv if r.pv is not None else 0.00,
                r.total_inversion if r.total_inversion is not None else 0.00,
                r.total_ganancia if r.total_ganancia is not None else 0.00
            ])
            
        if export_fmt == 'excel':
            return export_to_excel(headers, data, 'Reporte_Inventario_Economico')
        elif export_fmt == 'pdf':
            title = "Reporte de Inventario (Valoración Económica)"
            return export_to_pdf(headers, data, title, 'Reporte_Inventario_Economico')

    # Cálculo de totales globales (basado en los precios calculados)
    resumen_veh = vehiculos_qs.aggregate(
        inversion=Sum('total_inversion'),
        proyectada=Sum('total_ganancia')
    )
    
    resumen_rep = repuestos_qs.aggregate(
        inversion=Sum('total_inversion'),
        proyectada=Sum('total_ganancia')
    )

    inversion_total = (resumen_veh['inversion'] or 0) + (resumen_rep['inversion'] or 0)
    ganancia_total  = (resumen_veh['proyectada'] or 0) + (resumen_rep['proyectada'] or 0)

    from software.models.almacenesModel import Almacenes
    return render(request, 'reportes/reporte_inventario.html', {
        'inversion_total': inversion_total,
        'ganancia_total': ganancia_total,
        'total_unidades': stock_qs.aggregate(t=Sum('cantidad_disponible'))['t'] or 0,
        'sucursales': Sucursales.objects.all(),
        'sucursal_filtro': sucursal_filtro,
        'frecuencia_filtro': frecuencia_filtro,
        'total_deuda': "{:.2f}".format(total_deuda),
        'almacenes': Almacenes.objects.filter(estado=1),
        'almacen_filtro': almacen_filtro,
    })

def api_listar_inventario_vehiculos(request):
    idusuario = request.session.get('idusuario')
    if not idusuario:
        return JsonResponse({'error': 'No autenticado'}, status=401)
        
    sucursal_filtro = request.GET.get('sucursal', '').strip()
    almacen_filtro = request.GET.get('almacen', '').strip()

    stock_qs = Stock.objects.filter(estado=1, cantidad_disponible__gt=0)
    if almacen_filtro:
        stock_qs = stock_qs.filter(id_almacen_id=almacen_filtro)
    elif sucursal_filtro:
        stock_qs = stock_qs.filter(id_almacen__id_sucursal_id=sucursal_filtro)

    vehiculos_qs = stock_qs.filter(id_vehiculo__isnull=False).select_related(
        'id_vehiculo__idproducto',
        'idcompradetalle'
    )

    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '').strip()

    if search_value:
        vehiculos_qs = vehiculos_qs.filter(
            Q(id_vehiculo__idproducto__nomproducto__icontains=search_value) |
            Q(id_vehiculo__serie_chasis__icontains=search_value) |
            Q(id_vehiculo__serie_motor__icontains=search_value)
        )

    records_total = vehiculos_qs.count()
    records_filtered = records_total

    # Definir Subqueries
    latest_compra_v = CompraDetalle.objects.filter(id_vehiculo=OuterRef('id_vehiculo')).order_by('-idcompradetalle')
    sub_pc_v = Subquery(latest_compra_v.values('precio_compra')[:1], output_field=DecimalField())
    sub_pv_v = Subquery(latest_compra_v.values('precio_maximo')[:1], output_field=DecimalField())

    vehiculos_qs = vehiculos_qs.annotate(
        pc=Coalesce(F('idcompradetalle__precio_compra'), sub_pc_v, output_field=DecimalField()),
        pv=Coalesce(F('idcompradetalle__precio_maximo'), sub_pv_v, output_field=DecimalField())
    ).annotate(
        total_inversion=Cast(F('cantidad_disponible') * F('pc'), DecimalField(max_digits=12, decimal_places=2)),
        total_ganancia=Cast(
            Case(
                When(pv=0, then=Value(0)),
                When(pv__isnull=True, then=Value(0)),
                default=F('cantidad_disponible') * (F('pv') - F('pc')),
                output_field=DecimalField()
            ),
            DecimalField(max_digits=12, decimal_places=2)
        )
    )

    vehiculos_qs = vehiculos_qs.order_by('id_stock')
    
    resumen_veh = vehiculos_qs.aggregate(
        inversion=Sum('total_inversion'),
        proyectada=Sum('total_ganancia'),
        cantidad=Sum('cantidad_disponible')
    )
    
    totales_dict = {
        'inversion': float(resumen_veh['inversion'] or 0),
        'ganancia': float(resumen_veh['proyectada'] or 0),
        'cantidad': resumen_veh['cantidad'] or 0
    }

    if length > -1:
        vehiculos_page = vehiculos_qs[start:start + length]
    else:
        vehiculos_page = vehiculos_qs

    data = []
    for v in vehiculos_page:
        prod_name = v.id_vehiculo.idproducto.nomproducto if v.id_vehiculo and getattr(v.id_vehiculo, 'idproducto', None) else 'Vehículo'
        chasis = v.id_vehiculo.serie_chasis if v.id_vehiculo else '-'
        motor = v.id_vehiculo.serie_motor if v.id_vehiculo else '-'
        
        data.append({
            'DT_RowId': f'row_v_{v.id_stock}',
            'producto': prod_name,
            'chasis': chasis,
            'motor': motor,
            'stock': v.cantidad_disponible,
            'costo_unit': v.pc if v.pc is not None else 0.00,
            'venta_unit': v.pv if v.pv is not None else 0.00,
            'total_inversion': v.total_inversion if v.total_inversion is not None else 0.00,
            'ganancia_est': v.total_ganancia if v.total_ganancia is not None else 0.00
        })

    return JsonResponse({
        'draw': draw,
        'recordsTotal': records_total,
        'recordsFiltered': records_filtered,
        'data': data,
        'totales': totales_dict
    })

def api_listar_inventario_repuestos(request):
    idusuario = request.session.get('idusuario')
    if not idusuario:
        return JsonResponse({'error': 'No autenticado'}, status=401)
        
    sucursal_filtro = request.GET.get('sucursal', '').strip()
    almacen_filtro = request.GET.get('almacen', '').strip()

    stock_qs = Stock.objects.filter(estado=1, cantidad_disponible__gt=0)
    if almacen_filtro:
        stock_qs = stock_qs.filter(id_almacen_id=almacen_filtro)
    elif sucursal_filtro:
        stock_qs = stock_qs.filter(id_almacen__id_sucursal_id=sucursal_filtro)

    repuestos_qs = stock_qs.filter(id_repuesto_comprado__isnull=False).select_related(
        'id_repuesto_comprado__id_repuesto',
        'idcompradetalle'
    )

    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '').strip()

    if search_value:
        repuestos_qs = repuestos_qs.filter(
            Q(id_repuesto_comprado__id_repuesto__nombre__icontains=search_value) |
            Q(id_repuesto_comprado__id_repuesto__codigo_barras__icontains=search_value)
        )

    records_total = repuestos_qs.count()
    records_filtered = records_total

    latest_compra_r = CompraDetalle.objects.filter(id_repuesto_comprado=OuterRef('id_repuesto_comprado')).order_by('-idcompradetalle')
    sub_pc_r = Subquery(latest_compra_r.values('precio_compra')[:1], output_field=DecimalField())
    sub_pv_r = Subquery(latest_compra_r.values('precio_maximo')[:1], output_field=DecimalField())

    repuestos_qs = repuestos_qs.annotate(
        pc=Coalesce(F('idcompradetalle__precio_compra'), sub_pc_r, output_field=DecimalField()),
        pv=Coalesce(F('idcompradetalle__precio_maximo'), sub_pv_r, output_field=DecimalField())
    ).annotate(
        total_inversion=Cast(F('cantidad_disponible') * F('pc'), DecimalField(max_digits=12, decimal_places=2)),
        total_ganancia=Cast(
            Case(
                When(pv=0, then=Value(0)),
                When(pv__isnull=True, then=Value(0)),
                default=F('cantidad_disponible') * (F('pv') - F('pc')),
                output_field=DecimalField()
            ),
            DecimalField(max_digits=12, decimal_places=2)
        )
    )

    repuestos_qs = repuestos_qs.order_by('id_stock')

    resumen_rep = repuestos_qs.aggregate(
        inversion=Sum('total_inversion'),
        proyectada=Sum('total_ganancia'),
        cantidad=Sum('cantidad_disponible')
    )
    
    totales_dict = {
        'inversion': float(resumen_rep['inversion'] or 0),
        'ganancia': float(resumen_rep['proyectada'] or 0),
        'cantidad': resumen_rep['cantidad'] or 0
    }

    if length > -1:
        repuestos_page = repuestos_qs[start:start + length]
    else:
        repuestos_page = repuestos_qs

    data = []
    for r in repuestos_page:
        rc = r.id_repuesto_comprado
        rep = rc.id_repuesto if rc else None
        rep_name = rep.nombre if rep else 'Repuesto'
        codigo = rc.id_repuesto.codigo_barras if rc and rc.id_repuesto else '-'
        
        data.append({
            'DT_RowId': f'row_r_{r.id_stock}',
            'producto': rep_name,
            'codigo': codigo,
            'stock': r.cantidad_disponible,
            'costo_unit': r.pc if r.pc is not None else 0.00,
            'venta_unit': r.pv if r.pv is not None else 0.00,
            'total_inversion': r.total_inversion if r.total_inversion is not None else 0.00,
            'ganancia_est': r.total_ganancia if r.total_ganancia is not None else 0.00
        })

    return JsonResponse({
        'draw': draw,
        'recordsTotal': records_total,
        'recordsFiltered': records_filtered,
        'data': data,
        'totales': totales_dict
    })


# ─────────────────────────────────────────────────
#  REPORTE DE CAJA
# ─────────────────────────────────────────────────
def reporte_caja(request):
    idusuario = request.session.get('idusuario')
    if not idusuario:
        return redirect('iniciar_sesion')
        
    fi, ff, fi_str, ff_str = _parse_fechas(request)
    sucursal_filtro = request.GET.get('sucursal', '').strip()
    tipo_movimiento = request.GET.get('tipo_movimiento', '')
    if tipo_movimiento not in ['ingreso', 'egreso']:
        tipo_movimiento = ''
    metodo_pago_id = request.GET.get('metodo_pago', '')

    export_fmt = request.GET.get('export')
    if export_fmt in ['excel', 'pdf']:
        movimientos_qs = MovimientoCaja.objects.filter(
            fecha_movimiento__date__range=[fi, ff],
            estado=1
        )
        from django.db.models import Q
        if sucursal_filtro:
            movimientos_qs = movimientos_qs.filter(
                Q(id_caja__id_sucursal_id=sucursal_filtro) |
                Q(idventa__id_sucursal_id=sucursal_filtro) |
                Q(idcompra__id_sucursal_id=sucursal_filtro) |
                Q(idusuario__id_sucursal_id=sucursal_filtro)
            )
        if tipo_movimiento:
            movimientos_qs = movimientos_qs.filter(tipo_movimiento=tipo_movimiento)
        if metodo_pago_id:
            is_efectivo = False
            try:
                tp = TipoPago.objects.get(pk=metodo_pago_id)
                if tp.nombre.lower() == 'efectivo':
                    is_efectivo = True
            except TipoPago.DoesNotExist:
                pass
            
            cond = Q(idventa__id_tipo_pago_id=metodo_pago_id) | \
                   Q(idcompra__id_tipo_pago_id=metodo_pago_id) | \
                   Q(pagos_cuota__id_tipo_pago_id=metodo_pago_id, pagos_cuota__estado=1)
                   
            if is_efectivo:
                cond |= Q(idventa__id_tipo_pago__isnull=True, idcompra__id_tipo_pago__isnull=True, pagos_cuota__isnull=True)
                
            movimientos_qs = movimientos_qs.filter(cond).distinct()
            
        search = request.GET.get('search', '').strip()
        if search:
            movimientos_qs = movimientos_qs.filter(
                Q(descripcion__icontains=search) |
                Q(idusuario__nombrecompleto__icontains=search)
            )
            
        movimientos_qs = movimientos_qs.select_related(
            'id_caja', 'idusuario', 'idventa__id_tipo_pago', 'idcompra__id_tipo_pago'
        ).prefetch_related(
            'pagos_cuota__id_tipo_pago'
        ).order_by('-fecha_movimiento', '-id_movimiento_caja')
        
        headers = ['Fecha', 'Caja', 'Usuario', 'Descripción', 'Tipo', 'Método', 'Monto (S/)']
        data = []
        for m in movimientos_qs:
            metodo_pago = "Efectivo"
            detalles_metodo = ""
            # Evaluamos en memoria para usar el prefetch_related y evitar N+1
            pagos_cuota = [p for p in m.pagos_cuota.all() if p.estado == 1]
            
            if len(pagos_cuota) > 1:
                metodo_pago = "Múltiple"
                import re as _re
                # Primero buscamos si algún pago tiene detalles [FRACCIONADO:]
                # (ocurre en multipagos: varias cuotas pagadas con mismo método fraccionado)
                frac_detail = ""
                for p in pagos_cuota:
                    if p.observaciones and '[FRACCIONADO:' in p.observaciones:
                        m_frac = _re.search(r'\[FRACCIONADO:\s*(.*?)\]', p.observaciones)
                        if m_frac:
                            frac_detail = m_frac.group(1)
                            break
                if frac_detail:
                    detalles_metodo = frac_detail
                else:
                    # Comprobar si todos los pagos de cuota tienen exactamente el mismo método y operación
                    metodos_unicos = set(p.id_tipo_pago.nombre if p.id_tipo_pago else 'Efectivo' for p in pagos_cuota)
                    ops_unicas = set(p.numero_operacion or '' for p in pagos_cuota)
                    
                    if len(metodos_unicos) == 1 and len(ops_unicas) == 1:
                        metodo_pago = metodos_unicos.pop()
                        op = ops_unicas.pop()
                        if op and op.lower() != 'múltiple':
                            detalles_metodo = f"Op: {op}"
                        else:
                            detalles_metodo = ""
                    else:
                        # Fallback: construir desde tipo y monto de cada pago
                        metodo_pago = "Múltiple"
                        arr = []
                        for p in pagos_cuota:
                            n = p.id_tipo_pago.nombre if p.id_tipo_pago else 'Efectivo'
                            op = f' (Op:{p.numero_operacion})' if p.numero_operacion and p.numero_operacion.lower() != 'múltiple' else ''
                            arr.append(f"{n}: S/ {p.monto_pago}{op}")
                        detalles_metodo = " | ".join(arr)
            elif len(pagos_cuota) == 1:
                p = pagos_cuota[0]
                if p.id_tipo_pago:
                    metodo_pago = p.id_tipo_pago.nombre
                    # Verificar por FRACCIONADO directamente (evitar fallo con tilde en 'Múltiple')
                    if p.observaciones and '[FRACCIONADO:' in p.observaciones:
                        import re
                        match = re.search(r'\[FRACCIONADO:\s*(.*?)\]', p.observaciones)
                        if match:
                            detalles_metodo = match.group(1)
            elif m.idventa and m.idventa.id_tipo_pago:
                metodo_pago = m.idventa.id_tipo_pago.nombre
                # Verificar por FRACCIONADO directamente
                if m.idventa.observaciones and '[FRACCIONADO:' in m.idventa.observaciones:
                    import re
                    match = re.search(r'\[FRACCIONADO:\s*(.*?)\]', m.idventa.observaciones)
                    if match:
                        detalles_metodo = match.group(1)
            elif m.idcompra and m.idcompra.id_tipo_pago:
                metodo_pago = m.idcompra.id_tipo_pago.nombre
                # Verificar por FRACCIONADO directamente
                if m.idcompra.observaciones and '[FRACCIONADO:' in m.idcompra.observaciones:
                    import re
                    match = re.search(r'\[FRACCIONADO:\s*(.*?)\]', m.idcompra.observaciones)
                    if match:
                        detalles_metodo = match.group(1)

            # Si se exporta a Excel/PDF y tiene detalles, lo concatenamos
            texto_metodo_export = metodo_pago
            if detalles_metodo:
                if export_fmt == 'pdf':
                    if len(detalles_metodo) > 100:
                        detalles_metodo = detalles_metodo[:97] + '...'
                    texto_metodo_export += f"<br/>({detalles_metodo})"
                else:
                    texto_metodo_export += f"\n({detalles_metodo})"

            desc = str(m.descripcion or 'S/N Descripción')
            if export_fmt == 'pdf' and len(desc) > 200:
                desc = desc[:197] + '...'

            data.append([
                m.fecha_movimiento.strftime("%d/%m/%Y %H:%M"),
                m.id_caja.nombre_caja if m.id_caja else '-',
                getattr(m.idusuario, 'nombrecompleto', '-') if getattr(m, 'idusuario', None) else '-',
                desc,
                m.tipo_movimiento.capitalize(),
                texto_metodo_export,
                m.monto
            ])
            
        total_monto = sum(float(m.monto) if str(m.tipo_movimiento).lower() == 'ingreso' else -float(m.monto) for m in movimientos_qs)
            
        if export_fmt == 'excel':
            data.append(["", "", "", "", "", "TOTAL RECAUDADO:", f"S/ {total_monto:.2f}"])
            return export_to_excel(headers, data, f'Reporte_Caja_{fi_str}_{ff_str}')
        elif export_fmt == 'pdf':
            data.append(["", "", "", "", "", '<b><font size="10">TOTAL RECAUDADO:</font></b>', f'<b><font size="10">S/ {total_monto:.2f}</font></b>'])
            title = f"Reporte de Caja ({fi_str} al {ff_str})"
            return export_to_pdf(headers, data, title, f'Reporte_Caja_{fi_str}_{ff_str}')

    tipos_pago = TipoPago.objects.filter(estado=1).order_by('nombre')

    return render(request, 'reportes/reporte_caja.html', {
        'fecha_inicio': fi_str,
        'fecha_fin': ff_str,
        'tipo_movimiento': tipo_movimiento,
        'tipos_pago': tipos_pago,
        'metodo_pago': metodo_pago_id,
        'sucursales': Sucursales.objects.all(),
        'sucursal_filtro': sucursal_filtro,
    })


def api_listar_reporte_caja(request):
    """
    API Server-Side para el Reporte de Caja
    """
    idusuario = request.session.get('idusuario')
    if not idusuario:
        return JsonResponse({'error': 'No autorizado'}, status=401)
        
    fi, ff, fi_str, ff_str = _parse_fechas(request)
    sucursal_filtro = request.GET.get('sucursal', '').strip()
    tipo_movimiento = request.GET.get('tipo_movimiento', '')
    metodo_pago_id = request.GET.get('metodo_pago', '')
    
    movimientos_qs = MovimientoCaja.objects.filter(
        fecha_movimiento__date__range=[fi, ff],
        estado=1
    )
    
    from django.db.models import Q
    if sucursal_filtro:
        movimientos_qs = movimientos_qs.filter(
            Q(id_caja__id_sucursal_id=sucursal_filtro) |
            Q(idventa__id_sucursal_id=sucursal_filtro) |
            Q(idcompra__id_sucursal_id=sucursal_filtro) |
            Q(idusuario__id_sucursal_id=sucursal_filtro)
        )
        
    if tipo_movimiento in ['ingreso', 'egreso']:
        movimientos_qs = movimientos_qs.filter(tipo_movimiento=tipo_movimiento)
        
    if metodo_pago_id:
        is_efectivo = False
        try:
            tp = TipoPago.objects.get(pk=metodo_pago_id)
            if tp.nombre.lower() == 'efectivo':
                is_efectivo = True
        except TipoPago.DoesNotExist:
            pass
            
        cond = Q(idventa__id_tipo_pago_id=metodo_pago_id) | \
               Q(idcompra__id_tipo_pago_id=metodo_pago_id) | \
               Q(pagos_cuota__id_tipo_pago_id=metodo_pago_id, pagos_cuota__estado=1)
               
        if is_efectivo:
            cond |= Q(idventa__id_tipo_pago__isnull=True, idcompra__id_tipo_pago__isnull=True, pagos_cuota__isnull=True)
            
        movimientos_qs = movimientos_qs.filter(cond).distinct()

    search_value = request.GET.get('search[value]', '').strip()
    if search_value:
        movimientos_qs = movimientos_qs.filter(
            Q(descripcion__icontains=search_value) |
            Q(idusuario__nombrecompleto__icontains=search_value)
        )
        
    # Calcular totales antes de paginar
    ingresos = movimientos_qs.filter(tipo_movimiento='ingreso').aggregate(t=Sum('monto'))['t'] or 0
    egresos = movimientos_qs.filter(tipo_movimiento='egreso').aggregate(t=Sum('monto'))['t'] or 0
    saldo_neto = ingresos - egresos
    
    # Order & Pagination
    movimientos_qs = movimientos_qs.select_related(
        'id_caja', 'idusuario', 'idventa__id_tipo_pago', 'idcompra__id_tipo_pago'
    ).prefetch_related(
        'pagos_cuota__id_tipo_pago'
    ).order_by('-fecha_movimiento', '-id_movimiento_caja')
    
    total_records = movimientos_qs.count()
    
    try:
        start = int(request.GET.get('start', 0))
        length = int(request.GET.get('length', 10))
    except ValueError:
        start = 0
        length = 10
        
    mov_page = movimientos_qs[start:start+length]
    
    import re
    # PRE-FETCH MANUAL para evitar N+1 en Pre-Créditos
    pre_credito_ids = []
    for m in mov_page:
        if 'Pre-Crédito' in (m.descripcion or ''):
            m_pre = re.search(r'Pre-Crédito\s*#(\d+)', m.descripcion)
            if m_pre:
                pre_credito_ids.append(m_pre.group(1))
    
    detalles_por_precredito = {}
    if pre_credito_ids:
        try:
            from software.models.DetallePagoInicialModel import DetallePagoInicial
            dps = DetallePagoInicial.objects.filter(id_pre_credito_id__in=pre_credito_ids).select_related('id_tipo_pago')
            for p in dps:
                pid = str(p.id_pre_credito_id)
                if pid not in detalles_por_precredito:
                    detalles_por_precredito[pid] = []
                detalles_por_precredito[pid].append(p)
        except Exception:
            pass

    data = []
    for m in mov_page:
        metodo_pago = "Efectivo"
        detalles_metodo = ""
        # Evaluamos en memoria para usar el prefetch_related y evitar N+1
        pagos_cuota = [p for p in m.pagos_cuota.all() if p.estado == 1]
        
        if len(pagos_cuota) > 1:
            frac_detail = ""
            for p in pagos_cuota:
                if p.observaciones and '[FRACCIONADO:' in p.observaciones:
                    m_frac = re.search(r'\[FRACCIONADO:\s*(.*?)\]', p.observaciones)
                    if m_frac:
                        frac_detail = m_frac.group(1)
                        break
            if frac_detail:
                metodo_pago = "Múltiple"
                detalles_metodo = frac_detail
            else:
                # Check if all payments have the exact same method
                metodos_unicos = set(p.id_tipo_pago.nombre if p.id_tipo_pago else 'Efectivo' for p in pagos_cuota)
                if len(metodos_unicos) == 1:
                    metodo_pago = metodos_unicos.pop()
                    detalles_metodo = ""
                else:
                    metodo_pago = "Múltiple"
                    arr = []
                    for p in pagos_cuota:
                        n = p.id_tipo_pago.nombre if p.id_tipo_pago else 'Efectivo'
                        op = f' (Op:{p.numero_operacion})' if p.numero_operacion and p.numero_operacion.lower() != 'múltiple' else ''
                        arr.append(f"{n}: S/ {p.monto_pago}{op}")
                    detalles_metodo = " | ".join(arr)
        elif len(pagos_cuota) == 1:
            p = pagos_cuota[0]
            if p.id_tipo_pago:
                metodo_pago = p.id_tipo_pago.nombre
                # Verificar por FRACCIONADO directamente (evitar fallo con tilde en 'Múltiple')
                if p.observaciones and '[FRACCIONADO:' in p.observaciones:
                    match = re.search(r'\[FRACCIONADO:\s*(.*?)\]', p.observaciones)
                    if match:
                        detalles_metodo = match.group(1)
        elif m.idventa and m.idventa.id_tipo_pago:
            metodo_pago = m.idventa.id_tipo_pago.nombre
            # Verificar por FRACCIONADO directamente
            if m.idventa.observaciones and '[FRACCIONADO:' in m.idventa.observaciones:
                match = re.search(r'\[FRACCIONADO:\s*(.*?)\]', m.idventa.observaciones)
                if match:
                    detalles_metodo = match.group(1)
        elif m.idcompra and m.idcompra.id_tipo_pago:
            metodo_pago = m.idcompra.id_tipo_pago.nombre
            # Verificar por FRACCIONADO directamente
            if m.idcompra.observaciones and '[FRACCIONADO:' in m.idcompra.observaciones:
                match = re.search(r'\[FRACCIONADO:\s*(.*?)\]', m.idcompra.observaciones)
                if match:
                    detalles_metodo = match.group(1)
        elif 'Pre-Crédito' in (m.descripcion or ''):
            m_pre = re.search(r'Pre-Crédito\s*#(\d+)', m.descripcion)
            if m_pre:
                pid = m_pre.group(1)
                dp_list = detalles_por_precredito.get(pid, [])
                if len(dp_list) > 1:
                    metodo_pago = "Múltiple"
                    arr = []
                    for p in dp_list:
                        n = p.id_tipo_pago.nombre if p.id_tipo_pago else 'Efectivo'
                        op = f' (Op:{p.numero_operacion})' if p.numero_operacion else ''
                        arr.append(f"{n}: S/ {p.monto}{op}")
                    detalles_metodo = " | ".join(arr)
                elif len(dp_list) == 1:
                    metodo_pago = dp_list[0].id_tipo_pago.nombre if dp_list[0].id_tipo_pago else 'Efectivo'

        data.append({
            'fecha': m.fecha_movimiento.strftime("%d/%m/%Y %H:%M"),
            'caja': m.id_caja.nombre_caja if m.id_caja else '-',
            'usuario': m.idusuario.nombrecompleto if m.idusuario else '-',
            'descripcion': m.descripcion or 'S/N Descripción',
            'tipo_movimiento': m.tipo_movimiento,
            'metodo': metodo_pago,
            'detalles_metodo': detalles_metodo,
            'monto': float(m.monto),
        })
        
    return JsonResponse({
        'draw': int(request.GET.get('draw', 1)),
        'recordsTotal': total_records,
        'recordsFiltered': total_records,
        'data': data,
        'totales': {
            'ingresos': float(ingresos),
            'egresos': float(egresos),
            'saldo_neto': float(saldo_neto)
        }
    })


# ─────────────────────────────────────────────────
#  REPORTE DE CRÉDITOS
# ─────────────────────────────────────────────────
def reporte_creditos(request):
    idusuario = request.session.get('idusuario')
    if not idusuario:
        return redirect('iniciar_sesion')
        
    fi, ff, fi_str, ff_str = _parse_fechas(request)
    creditos_qs, search_value, lim = _get_creditos_filtrados(request, fi, ff)

    # Re-read filter values for use in cuotas/export sections below
    estado_filtro = request.GET.get('estado', 'todos').strip().lower()
    codigo_filtro = request.GET.get('codigo', '').strip()
    cliente_id = request.GET.get('cliente_id', '').strip()
    sucursal_filtro = request.GET.get('sucursal', '').strip()
    frecuencia_filtro = request.GET.get('frecuencia', 'todos').strip()

    ESTADOS_EXCLUIDOS = ['retenido', 'cancelado', 'reparado', 'segunda']
    cuotas_vencidas = CuotasVenta.objects.filter(
        estado=1,
        estado_pago__in=['Pendiente', 'Parcial'],
        fecha_vencimiento__lt=date.today()
    ).exclude(
        idcredito__estado_credito__in=ESTADOS_EXCLUIDOS
    ).exclude(
        idcredito__estado=0
    ).exclude(
        idventa__credito__estado_credito__in=ESTADOS_EXCLUIDOS
    ).exclude(
        idventa__credito__estado=0
    )
    if sucursal_filtro:
        cuotas_vencidas = cuotas_vencidas.filter(
            Q(idventa__id_sucursal_id=sucursal_filtro) | 
            Q(idcredito__id_sucursal_id=sucursal_filtro)
        )
    if cliente_id:
        cuotas_vencidas = cuotas_vencidas.filter(
            Q(idcredito__idcliente_id=cliente_id) |
            Q(idcredito__idventa__idcliente_id=cliente_id) |
            Q(idventa__idcliente_id=cliente_id)
        )
    if frecuencia_filtro and frecuencia_filtro != 'todos':
        cuotas_vencidas = cuotas_vencidas.filter(
            Q(idcredito__frecuencia_pago=frecuencia_filtro) |
            Q(idventa__credito__frecuencia_pago=frecuencia_filtro)
        )
    if search_value:
        cuotas_vencidas = cuotas_vencidas.filter(
            Q(idcredito__codigo_credito__icontains=search_value) |
            Q(idventa__credito__codigo_credito__icontains=search_value) |
            Q(idcredito__idcliente__razonsocial__icontains=search_value) |
            Q(idcredito__idventa__idcliente__razonsocial__icontains=search_value) |
            Q(idventa__idcliente__razonsocial__icontains=search_value) |
            Q(idventa__numero_comprobante__icontains=search_value)
        )
        
    cuotas_vencidas = cuotas_vencidas.select_related(
        'idventa__idcliente', 
        'idventa__credito',
        'idcredito__idcliente',
        'idcredito__idventa__idcliente'
    ).order_by('fecha_vencimiento', 'idcuotaventa')

    export_fmt = request.GET.get('export')
    if export_fmt:
        if export_fmt.endswith('_creditos'):
            headers = ['Código', 'Fecha Inicio', 'Venta Ref.', 'Cliente', 'Teléfono', 'Dirección', 'Estado', 'Monto Total', 'Deuda Pendiente']
            data = []
            for c in creditos_qs:
                cliente = "-"
                telefono = "-"
                direccion = "-"
                cliente_obj = None

                if c.idventa and c.idventa.idcliente:
                    cliente_obj = c.idventa.idcliente
                elif c.idcliente:
                    cliente_obj = c.idcliente

                if cliente_obj:
                    cliente = cliente_obj.razonsocial
                    telefono = cliente_obj.telefono or '-'
                    direccion = cliente_obj.direccion or '-'

                data.append([
                    c.codigo_credito,
                    c.fecha_credito.strftime("%d/%m/%Y"),
                    c.idventa.numero_comprobante if c.idventa else '-',
                    cliente,
                    telefono,
                    direccion,
                    c.estado_credito.capitalize(),
                    c.monto_total,
                    c.saldo_pendiente
                ])
            fmt = export_fmt.split('_')[0]
            if fmt == 'excel': return export_to_excel(headers, data, f'Reporte_Creditos_{estado_filtro}')
            elif fmt == 'pdf': return export_to_pdf(headers, data, f"Reporte de Créditos ({estado_filtro})", f'Reporte_Creditos_{estado_filtro}')
            
        elif export_fmt.endswith('_moras'):
            headers = ['Código Crd.', 'Fecha Vencida', 'Nº Cuota', 'Comprobante', 'Cliente', 'Teléfono', 'Dirección', 'Estado', 'Saldo x Pagar']
            data = []
            for c in cuotas_vencidas:
                cliente = "-"
                telefono = "-"
                direccion = "-"
                cliente_obj = None
                codigo_crd = "-"
                
                if c.idcredito:
                    codigo_crd = c.idcredito.codigo_credito
                    if c.idcredito.idcliente:
                        cliente_obj = c.idcredito.idcliente
                    elif c.idcredito.idventa and c.idcredito.idventa.idcliente:
                        cliente_obj = c.idcredito.idventa.idcliente
                elif c.idventa:
                    if c.idventa.idcliente:
                        cliente_obj = c.idventa.idcliente
                    if hasattr(c.idventa, 'credito') and c.idventa.credito:
                        codigo_crd = c.idventa.credito.codigo_credito
                        
                if cliente_obj:
                    cliente = cliente_obj.razonsocial
                    telefono = cliente_obj.telefono or '-'
                    direccion = cliente_obj.direccion or '-'

                from software.views.creditos import calcular_interes_mora
                mora, _, _ = calcular_interes_mora(c)
                total_con_mora = c.saldo_cuota + mora
                
                comprobante = 'CRÉDITO DIRECTO'
                if getattr(c, 'idventa', None):
                    comprobante = c.idventa.numero_comprobante
                elif getattr(c, 'idcredito', None) and getattr(c.idcredito, 'idventa', None):
                    comprobante = c.idcredito.idventa.numero_comprobante

                data.append([
                    codigo_crd,
                    c.fecha_vencimiento.strftime("%d/%m/%Y"),
                    c.numero_cuota,
                    comprobante,
                    cliente,
                    telefono,
                    direccion,
                    c.estado_pago,
                    total_con_mora
                ])
            fmt = export_fmt.split('_')[0]
            if fmt == 'excel': return export_to_excel(headers, data, 'Reporte_Moras')
            elif fmt == 'pdf': return export_to_pdf(headers, data, "Reporte de Cuotas en Mora", 'Reporte_Moras')

    if not export_fmt:
        total_deuda = creditos_qs.aggregate(t=Sum('saldo_pendiente'))['t'] or 0
        total_cuotas_vencidas = cuotas_vencidas.count()
        clientes = Cliente.objects.filter(estado=1).order_by('razonsocial')
        c_id_int = int(cliente_id) if cliente_id.isdigit() else ''
        return render(request, 'reportes/reporte_creditos.html', {
            'fi_str': fi_str,
            'ff_str': ff_str,
            'estado_filtro': estado_filtro,
            'codigo_filtro': codigo_filtro,
            'cliente_id': c_id_int,
            'clientes': clientes,
            'total_deuda': total_deuda,
            'total_cuotas_vencidas': total_cuotas_vencidas,
            'active_tab': request.GET.get('tab', 'listado'),
            'sucursales': Sucursales.objects.all(),
            'sucursal_filtro': sucursal_filtro,
        })
    else:
        pass

def api_listar_reporte_creditos(request):
    from django.utils import timezone
    from datetime import timedelta
    from software.models.empresaModel import Empresa

    idusuario = request.session.get('idusuario')
    if not idusuario:
        return JsonResponse({'error': 'No autenticado'}, status=401)
        
    fi, ff, fi_str, ff_str = _parse_fechas(request)
    estado_filtro = request.GET.get('estado', 'todos').strip()
    color_mora = request.GET.get('color_mora', 'todos').strip()
    codigo_filtro = request.GET.get('codigo', '').strip()
    cliente_id = request.GET.get('cliente_id', '').strip()
    sucursal_filtro = request.GET.get('sucursal', '').strip()
    frecuencia_filtro = request.GET.get('frecuencia', 'todos').strip()
    id_suc = request.session.get('id_sucursal')
    
    creditos_qs = Credito.objects.filter(fecha_credito__date__range=[fi, ff])
    
    if estado_filtro in ['cancelado', 'anulado']:
        creditos_qs = creditos_qs.filter(estado_credito=estado_filtro)
    else:
        creditos_qs = creditos_qs.filter(estado=1)
        if estado_filtro != 'todos':
            creditos_qs = creditos_qs.filter(estado_credito=estado_filtro)
    if codigo_filtro:
        creditos_qs = creditos_qs.filter(codigo_credito__icontains=codigo_filtro)
    if cliente_id:
        creditos_qs = creditos_qs.filter(
            Q(idcliente_id=cliente_id) |
            Q(idventa__idcliente_id=cliente_id)
        )
        
    if sucursal_filtro:
        creditos_qs = creditos_qs.filter(
            Q(idventa__id_sucursal_id=sucursal_filtro) | 
            Q(id_sucursal_id=sucursal_filtro)
        )
    if frecuencia_filtro and frecuencia_filtro != 'todos':
        creditos_qs = creditos_qs.filter(frecuencia_pago=frecuencia_filtro)

    hoy_date = timezone.now().date()
    
    # 1. Anotar con Subquery para obtener la cuota vencida más antigua (optimización N+1)
    # Solo cuotas VENCIDAS (fecha_vencimiento < hoy)
    oldest_cuota_venta_qs = CuotasVenta.objects.filter(
        idventa=OuterRef('idventa'),
        estado=1,
        estado_pago__in=['Pendiente', 'Parcial'],
        fecha_vencimiento__lt=hoy_date
    ).order_by('fecha_vencimiento').values('fecha_vencimiento')[:1]

    oldest_cuota_credito_qs = CuotasVenta.objects.filter(
        idcredito=OuterRef('pk'),
        estado=1,
        estado_pago__in=['Pendiente', 'Parcial'],
        fecha_vencimiento__lt=hoy_date
    ).order_by('fecha_vencimiento').values('fecha_vencimiento')[:1]

    # Subquery para contar cuotas vencidas (usado para frecuencia Mensual)
    cuotas_vencidas_venta_qs = CuotasVenta.objects.filter(
        idventa=OuterRef('idventa'),
        estado=1,
        estado_pago__in=['Pendiente', 'Parcial'],
        fecha_vencimiento__lt=hoy_date
    ).values('idventa').annotate(cnt=Count('idcuotaventa')).values('cnt')[:1]

    cuotas_vencidas_credito_qs = CuotasVenta.objects.filter(
        idcredito=OuterRef('pk'),
        estado=1,
        estado_pago__in=['Pendiente', 'Parcial'],
        fecha_vencimiento__lt=hoy_date
    ).values('idcredito').annotate(cnt=Count('idcuotaventa')).values('cnt')[:1]

    creditos_qs = creditos_qs.annotate(
        oldest_vencimiento=Coalesce(
            Subquery(oldest_cuota_venta_qs),
            Subquery(oldest_cuota_credito_qs)
        ),
        cuotas_vencidas_count=Coalesce(
            Subquery(cuotas_vencidas_venta_qs),
            Subquery(cuotas_vencidas_credito_qs),
            0
        )
    )

    empresa = Empresa.objects.first()

    # ── Límites por frecuencia (leídos de la empresa) ──────────────────────
    lim = {
        'diario': {
            'verde':    empresa.limite_dias_verde_diario    if empresa else 5,
            'amarillo': empresa.limite_dias_amarillo_diario if empresa else 10,
        },
        'semanal': {
            'verde':    empresa.limite_dias_verde_semanal    if empresa else 20,
            'amarillo': empresa.limite_dias_amarillo_semanal if empresa else 30,
        },
        'quincenal': {
            'verde':    empresa.limite_dias_verde_quincenal    if empresa else 30,
            'amarillo': empresa.limite_dias_amarillo_quincenal if empresa else 45,
        },
        'mensual': {
            'verde':    empresa.limite_cuotas_verde_mensual    if empresa else 1,
            'amarillo': empresa.limite_cuotas_amarillo_mensual if empresa else 2,
        },
        # Personalizado y cualquier otro: usa los campos heredados o fallback
        'default': {
            'verde':    empresa.limite_dias_verde    if empresa else 10,
            'amarillo': empresa.limite_dias_amarillo if empresa else 20,
        },
    }

    # 2. Filtrar por color de mora (combinando todas las frecuencias con Q objects)
    if color_mora != 'todos':
        # Construir filtro para creditos NO mensuales (basados en días)
        def _q_dias(freq_key, color):
            l = lim[freq_key]
            fecha_verde_ini    = hoy_date - timedelta(days=l['verde'])
            fecha_amarillo_ini = hoy_date - timedelta(days=l['amarillo'])
            if color == 'verde':
                return Q(frecuencia_pago__iexact=freq_key) & Q(
                    oldest_vencimiento__gte=fecha_verde_ini,
                    oldest_vencimiento__lt=hoy_date
                )
            elif color == 'amarillo':
                return Q(frecuencia_pago__iexact=freq_key) & Q(
                    oldest_vencimiento__gte=fecha_amarillo_ini,
                    oldest_vencimiento__lt=fecha_verde_ini
                )
            else:  # rojo
                return Q(frecuencia_pago__iexact=freq_key) & Q(
                    oldest_vencimiento__lt=fecha_amarillo_ini
                )

        # Filtro para creditos Mensuales (basado en cuotas vencidas)
        lm = lim['mensual']
        if color_mora == 'verde':
            q_mensual = Q(frecuencia_pago__iexact='mensual') & Q(
                cuotas_vencidas_count__gte=1,
                cuotas_vencidas_count__lte=lm['verde']
            )
            q_no_mensual = (
                _q_dias('diario', 'verde') |
                _q_dias('semanal', 'verde') |
                _q_dias('quincenal', 'verde') |
                _q_dias('default', 'verde')
            )
        elif color_mora == 'amarillo':
            q_mensual = Q(frecuencia_pago__iexact='mensual') & Q(
                cuotas_vencidas_count__gt=lm['verde'],
                cuotas_vencidas_count__lte=lm['amarillo']
            )
            q_no_mensual = (
                _q_dias('diario', 'amarillo') |
                _q_dias('semanal', 'amarillo') |
                _q_dias('quincenal', 'amarillo') |
                _q_dias('default', 'amarillo')
            )
        else:  # rojo
            q_mensual = Q(frecuencia_pago__iexact='mensual') & Q(
                cuotas_vencidas_count__gt=lm['amarillo']
            )
            q_no_mensual = (
                _q_dias('diario', 'rojo') |
                _q_dias('semanal', 'rojo') |
                _q_dias('quincenal', 'rojo') |
                _q_dias('default', 'rojo')
            )

        creditos_qs = creditos_qs.filter(q_mensual | q_no_mensual)

    creditos_qs = creditos_qs.select_related('idventa', 'idventa__idcliente', 'idcliente').order_by('-idcredito')

    records_total = creditos_qs.count()

    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    records_filtered = creditos_qs.count()

    if length > -1:
        creditos_page = creditos_qs[start:start + length]
    else:
        creditos_page = creditos_qs

    data = []
    for c in creditos_page:
        cliente = "-"
        telefono = "-"
        direccion = "-"
        cliente_obj = None

        if c.idventa and c.idventa.idcliente:
            cliente_obj = c.idventa.idcliente
        elif c.idcliente:
            cliente_obj = c.idcliente

        if cliente_obj:
            cliente = cliente_obj.razonsocial
            telefono = cliente_obj.telefono or '-'
            direccion = cliente_obj.direccion or '-'

        venta_ref = c.idventa.numero_comprobante if c.idventa else '-'
        
        # Calcular color real de cada row sin N+1 gracias a las anotaciones previas
        c_color = 'sin_mora'
        freq = (c.frecuencia_pago or 'default').lower()
        if freq not in lim:
            freq = 'default'
            
        if freq == 'mensual':
            cnt = c.cuotas_vencidas_count or 0
            if cnt >= 1:
                if cnt <= lim['mensual']['verde']: c_color = 'verde'
                elif cnt <= lim['mensual']['amarillo']: c_color = 'amarillo'
                else: c_color = 'rojo'
        else:
            if c.oldest_vencimiento and c.oldest_vencimiento < hoy_date:
                dias_mora = (hoy_date - c.oldest_vencimiento).days
                if dias_mora <= lim[freq]['verde']: c_color = 'verde'
                elif dias_mora <= lim[freq]['amarillo']: c_color = 'amarillo'
                else: c_color = 'rojo'

        data.append({
            'DT_RowId': f'row_{c.idcredito}',
            'codigo': c.codigo_credito,
            'fecha_inicio': c.fecha_credito.strftime("%d/%m/%Y"),
            'venta_ref': venta_ref,
            'cliente': cliente,
            'telefono': telefono,
            'direccion': direccion,
            'estado': c.estado_credito,
            'monto_total': c.monto_total,
            'deuda_pendiente': c.saldo_pendiente,
            'idcredito': c.idcredito,
            'has_venta': bool(c.idventa),
            'color_mora': c_color
        })

    total_deuda = creditos_qs.aggregate(t=Sum('saldo_pendiente'))['t'] or 0

    return JsonResponse({
        'draw': draw,
        'recordsTotal': records_total,
        'recordsFiltered': records_filtered,
        'data': data,
        'totales': {
            'total_deuda': float(total_deuda)
        }
    })

def api_listar_reporte_moras(request):
    idusuario = request.session.get('idusuario')
    if not idusuario:
        return JsonResponse({'error': 'No autenticado'}, status=401)
        
    cliente_id = request.GET.get('cliente_id', '').strip()
    sucursal_filtro = request.GET.get('sucursal', '').strip()
    frecuencia_filtro = request.GET.get('frecuencia', 'todos').strip()
    id_suc = request.session.get('id_sucursal')
    
    ESTADOS_EXCLUIDOS = ['retenido', 'cancelado', 'reparado', 'segunda']
    cuotas_vencidas = CuotasVenta.objects.filter(
        estado=1,
        estado_pago__in=['Pendiente', 'Parcial'],
        fecha_vencimiento__lt=date.today()
    ).exclude(
        idcredito__estado_credito__in=ESTADOS_EXCLUIDOS
    ).exclude(
        idcredito__estado=0
    ).exclude(
        idventa__credito__estado_credito__in=ESTADOS_EXCLUIDOS
    ).exclude(
        idventa__credito__estado=0
    )
    if sucursal_filtro:
        cuotas_vencidas = cuotas_vencidas.filter(
            Q(idventa__id_sucursal_id=sucursal_filtro) | 
            Q(idcredito__id_sucursal_id=sucursal_filtro)
        )
    if cliente_id:
        cuotas_vencidas = cuotas_vencidas.filter(
            Q(idcredito__idcliente_id=cliente_id) |
            Q(idcredito__idventa__idcliente_id=cliente_id) |
            Q(idventa__idcliente_id=cliente_id)
        )
    if frecuencia_filtro and frecuencia_filtro != 'todos':
        cuotas_vencidas = cuotas_vencidas.filter(
            Q(idcredito__frecuencia_pago=frecuencia_filtro) |
            Q(idventa__credito__frecuencia_pago=frecuencia_filtro)
        )
    cuotas_vencidas = cuotas_vencidas.select_related(
        'idventa__idcliente', 
        'idventa__credito',
        'idcredito__idcliente',
        'idcredito__idventa__idcliente'
    ).order_by('fecha_vencimiento', 'idcuotaventa')

    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '').strip()

    if search_value:
        cuotas_vencidas = cuotas_vencidas.filter(
            Q(idcredito__codigo_credito__icontains=search_value) |
            Q(idventa__credito__codigo_credito__icontains=search_value) |
            Q(idcredito__idcliente__razonsocial__icontains=search_value) |
            Q(idcredito__idventa__idcliente__razonsocial__icontains=search_value) |
            Q(idventa__idcliente__razonsocial__icontains=search_value) |
            Q(idventa__numero_comprobante__icontains=search_value)
        )

    records_total = cuotas_vencidas.count()
    records_filtered = records_total

    if length > -1:
        moras_page = cuotas_vencidas[start:start + length]
    else:
        moras_page = cuotas_vencidas

    from software.views.creditos import calcular_interes_mora
    data = []
    for c in moras_page:
        cliente = "-"
        telefono = "-"
        direccion = "-"
        cliente_obj = None
        codigo_crd = "-"
        
        if c.idcredito:
            codigo_crd = c.idcredito.codigo_credito
            if c.idcredito.idcliente:
                cliente_obj = c.idcredito.idcliente
            elif c.idcredito.idventa and c.idcredito.idventa.idcliente:
                cliente_obj = c.idcredito.idventa.idcliente
        elif c.idventa:
            if c.idventa.idcliente:
                cliente_obj = c.idventa.idcliente
            if hasattr(c.idventa, 'credito') and c.idventa.credito:
                codigo_crd = c.idventa.credito.codigo_credito
                
        if cliente_obj:
            cliente = cliente_obj.razonsocial
            telefono = cliente_obj.telefono or '-'
            direccion = cliente_obj.direccion or '-'

        mora, _, _ = calcular_interes_mora(c)
        total_con_mora = c.saldo_cuota + mora
        
        comprobante = 'CRÉDITO DIRECTO'
        if getattr(c, 'idventa', None):
            comprobante = c.idventa.numero_comprobante
        elif getattr(c, 'idcredito', None) and getattr(c.idcredito, 'idventa', None):
            comprobante = c.idcredito.idventa.numero_comprobante

        data.append({
            'DT_RowId': f'row_mora_{c.idcuotaventa}',
            'codigo_crd': codigo_crd,
            'fecha_vencida': c.fecha_vencimiento.strftime("%d/%m/%Y"),
            'numero_cuota': f'Cuota {c.numero_cuota}',
            'comprobante': comprobante,
            'cliente': cliente,
            'telefono': telefono,
            'direccion': direccion,
            'estado': 'Ausente (Mora)' if total_con_mora > c.saldo_cuota else c.estado_pago,
            'saldo_x_pagar': total_con_mora
        })

    return JsonResponse({
        'draw': draw,
        'recordsTotal': records_total,
        'recordsFiltered': records_filtered,
        'data': data,
        'totales': {
            'total_cuotas_vencidas': records_total
        }
    })


# ─────────────────────────────────────────────────
#  REPORTE DE CONTACTOS
# ─────────────────────────────────────────────────
def reporte_contactos(request):
    idusuario = request.session.get('idusuario')
    if not idusuario:
        return redirect('iniciar_sesion')
    tipo = request.GET.get('tipo', 'clientes')
    page_number = request.GET.get('page')

    clientes_qs = Cliente.objects.filter(estado=1).order_by('razonsocial', 'idcliente')
    proveedores_qs = Proveedor.objects.filter(estado=1).order_by('razonsocial', 'idproveedor')

    export_fmt = request.GET.get('export')
    if export_fmt:
        if tipo == 'clientes':
            headers = ['Documento', 'Razón Social', 'Nombre Comercial', 'Teléfono', 'Tipo Entidad', 'Dirección']
            data = []
            for c in clientes_qs:
                entidad = c.id_tipo_entidad.tipo_entidad if getattr(c, 'id_tipo_entidad', None) else '-'
                data.append([
                    f"{c.tipo_documento} {c.numdoc}",
                    c.razonsocial,
                    c.nombre_comercial_cliente or '-',
                    c.telefono or '-',
                    entidad,
                    c.direccion or '-'
                ])
            if export_fmt == 'excel': return export_to_excel(headers, data, 'Reporte_Clientes')
            elif export_fmt == 'pdf': return export_to_pdf(headers, data, "Directorio de Clientes", 'Reporte_Clientes')
        else:
            headers = ['Documento', 'Razón Social', 'Nombre Comercial', 'Teléfono', 'Correo', 'Ubicación']
            data = []
            for p in proveedores_qs:
                data.append([
                    f"{p.tipo_documento} {p.numdoc}",
                    p.razonsocial,
                    p.nombre_comercial or '-',
                    p.telefono or '-',
                    p.email or '-',
                    p.ubicacion_completa or p.direccion or '-'
                ])
            if export_fmt == 'excel': return export_to_excel(headers, data, 'Reporte_Proveedores')
            elif export_fmt == 'pdf': return export_to_pdf(headers, data, "Directorio de Proveedores", 'Reporte_Proveedores')

    return render(request, 'reportes/reporte_contactos.html', {
        'tipo': tipo,
        'total_clientes': clientes_qs.count(),
        'total_proveedores': proveedores_qs.count(),
    })

def api_listar_contactos_clientes(request):
    idusuario = request.session.get('idusuario')
    if not idusuario:
        return JsonResponse({'error': 'No autenticado'}, status=401)
        
    clientes_qs = Cliente.objects.filter(estado=1).order_by('razonsocial', 'idcliente')

    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '').strip()

    if search_value:
        clientes_qs = clientes_qs.filter(
            Q(numdoc__icontains=search_value) |
            Q(razonsocial__icontains=search_value) |
            Q(nombre_comercial_cliente__icontains=search_value)
        )

    records_total = clientes_qs.count()
    records_filtered = records_total

    if length > -1:
        clientes_page = clientes_qs[start:start + length]
    else:
        clientes_page = clientes_qs

    data = []
    for c in clientes_page:
        entidad = c.id_tipo_entidad.tipo_entidad if getattr(c, 'id_tipo_entidad', None) else '-'
        data.append({
            'DT_RowId': f'row_c_{c.idcliente}',
            'documento': f"{c.tipo_documento} {c.numdoc}",
            'razonsocial': c.razonsocial,
            'nombre_comercial': c.nombre_comercial_cliente or '-',
            'telefono': c.telefono or 'N/E',
            'tipo_entidad': entidad,
            'direccion': c.direccion or '-'
        })

    return JsonResponse({
        'draw': draw,
        'recordsTotal': records_total,
        'recordsFiltered': records_filtered,
        'data': data
    })

def api_listar_contactos_proveedores(request):
    idusuario = request.session.get('idusuario')
    if not idusuario:
        return JsonResponse({'error': 'No autenticado'}, status=401)
        
    proveedores_qs = Proveedor.objects.filter(estado=1).order_by('razonsocial', 'idproveedor')

    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '').strip()

    if search_value:
        proveedores_qs = proveedores_qs.filter(
            Q(numdoc__icontains=search_value) |
            Q(razonsocial__icontains=search_value) |
            Q(nombre_comercial__icontains=search_value)
        )

    records_total = proveedores_qs.count()
    records_filtered = records_total

    if length > -1:
        proveedores_page = proveedores_qs[start:start + length]
    else:
        proveedores_page = proveedores_qs

    data = []
    for p in proveedores_page:
        data.append({
            'DT_RowId': f'row_p_{p.idproveedor}',
            'documento': f"{p.tipo_documento} {p.numdoc}",
            'razonsocial': p.razonsocial,
            'nombre_comercial': p.nombre_comercial or '-',
            'telefono': p.telefono or '-',
            'correo': p.email or '-',
            'ubicacion_completa': p.ubicacion_completa or 'S/ Ubicación',
            'direccion': p.direccion or ''
        })

    return JsonResponse({
        'draw': draw,
        'recordsTotal': records_total,
        'recordsFiltered': records_filtered,
        'data': data
    })

# ─────────────────────────────────────────────────
#  REPORTE DE PRE-FINANCIAMIENTO
# ─────────────────────────────────────────────────
def reporte_pre_financiamiento(request):
    idusuario = request.session.get('idusuario')
    if not idusuario:
        return redirect('iniciar_sesion')
        
    fi, ff, fi_str, ff_str = _parse_fechas(request)
    sucursal_filtro = request.GET.get('sucursal', '').strip()
    
    from software.models.PreCreditoModel import PreCredito
    
    precreditos_qs = PreCredito.objects.filter(
        fecha_registro__date__range=[fi, ff]
    )
    if sucursal_filtro:
        precreditos_qs = precreditos_qs.filter(id_sucursal_id=sucursal_filtro)
        
    estado = request.GET.get('estado')
    if estado:
        precreditos_qs = precreditos_qs.filter(estado=estado)

    cliente_id = request.GET.get('cliente_id')
    if cliente_id:
        precreditos_qs = precreditos_qs.filter(idcliente_id=cliente_id)

    precreditos_qs = precreditos_qs.select_related('idcliente', 'idusuario').order_by('-fecha_registro', '-id_pre_credito')

    export_fmt = request.GET.get('export')
    if export_fmt in ['pdf', 'excel']:
        headers = ['Nº', 'Fecha', 'Cliente', 'Doc. Cliente', 'Sucursal', 'Registrador', 'Estado', 'Monto Inicial (S/)']
        data = []
        for i, p in enumerate(precreditos_qs, 1):
            data.append([
                i,
                p.fecha_registro.strftime("%d/%m/%Y"),
                p.idcliente.razonsocial if p.idcliente else '-',
                f"{p.idcliente.tipo_documento} {p.idcliente.numdoc}" if p.idcliente else '-',
                p.id_sucursal.nombre_sucursal if p.id_sucursal else '-',
                p.idusuario.nombrecompleto if p.idusuario else '-',
                p.estado.capitalize(),
                p.monto_inicial
            ])
            
        if export_fmt == 'excel':
            return export_to_excel(headers, data, f'Reporte_Pre_Financiamiento_{fi_str}_{ff_str}')
        elif export_fmt == 'pdf':
            title = f"Reporte de Pre-Financiamiento ({fi_str} al {ff_str})"
            return export_to_pdf(headers, data, title, f'Reporte_Pre_Financiamiento_{fi_str}_{ff_str}')

    totales = precreditos_qs.aggregate(
        total_monto=Sum('monto_inicial'),
        cantidad=Count('id_pre_credito')
    )

    return render(request, 'reportes/reporte_pre_financiamiento.html', {
        'fecha_inicio': fi_str,
        'fecha_fin': ff_str,
        'estado_seleccionado': estado or '',
        'cliente_id': int(cliente_id) if cliente_id and cliente_id.isdigit() else '',
        'clientes_lista': Cliente.objects.filter(estado=1).order_by('razonsocial'),
        'totales': totales,
        'sucursales': Sucursales.objects.all(),
        'sucursal_filtro': sucursal_filtro,
    })


def api_listar_reporte_pre_financiamiento(request):
    idusuario = request.session.get('idusuario')
    if not idusuario:
        return JsonResponse({'error': 'No autenticado'}, status=401)
        
    fi, ff, fi_str, ff_str = _parse_fechas(request)
    sucursal_filtro = request.GET.get('sucursal', '').strip()
    
    from software.models.PreCreditoModel import PreCredito
    from django.db.models import Q
    
    precreditos_qs = PreCredito.objects.filter(
        fecha_registro__date__range=[fi, ff]
    )
    if sucursal_filtro:
        precreditos_qs = precreditos_qs.filter(id_sucursal_id=sucursal_filtro)

    estado = request.GET.get('estado')
    if estado:
        precreditos_qs = precreditos_qs.filter(estado=estado)

    cliente_id = request.GET.get('cliente_id')
    if cliente_id:
        precreditos_qs = precreditos_qs.filter(idcliente_id=cliente_id)
        
    records_total = precreditos_qs.count()
    records_filtered = records_total

    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '').strip()

    if search_value:
        precreditos_qs = precreditos_qs.filter(
            Q(detalles_vehiculos__id_vehiculo__idproducto__nomproducto__icontains=search_value) |
            Q(detalles_vehiculos__id_vehiculo__serie_chasis__icontains=search_value) |
            Q(detalles_vehiculos__id_vehiculo__serie_motor__icontains=search_value) |
            Q(idcliente__razonsocial__icontains=search_value) |
            Q(idcliente__numdoc__icontains=search_value)
        ).distinct()
        records_filtered = precreditos_qs.count()

    # Ordenamiento por defecto
    precreditos_qs = precreditos_qs.select_related('idcliente', 'idusuario', 'id_sucursal').order_by('-fecha_registro', '-id_pre_credito')
    
    totales_agregados = precreditos_qs.aggregate(
        total_monto=Sum('monto_inicial'),
        cantidad=Count('id_pre_credito')
    )
    
    totales_dict = {
        'total_monto': float(totales_agregados['total_monto'] or 0),
        'cantidad': totales_agregados['cantidad'] or 0
    }

    if length != -1:
        precreditos_page = precreditos_qs[start:start + length]
    else:
        precreditos_page = precreditos_qs

    data = []
    for p in precreditos_page:
        # Obtener vehiculos
        vehiculos = p.detalles_vehiculos.select_related('id_vehiculo__idproducto').all()
        vehiculos_text = "<br>".join([f"• {v.id_vehiculo.idproducto.nomproducto} <small>(Chasis: {v.id_vehiculo.serie_chasis}, Motor: {v.id_vehiculo.serie_motor})</small>" for v in vehiculos])
        
        doc_cliente = f"{p.idcliente.tipo_documento} {p.idcliente.numdoc}" if p.idcliente else '-'
        
        # Color del estado
        badge_class = 'bg-secondary'
        if p.estado == 'pendiente':
            badge_class = 'bg-warning text-dark'
        elif p.estado == 'aprobado':
            badge_class = 'bg-info'
        elif p.estado == 'completado':
            badge_class = 'bg-success'
        elif p.estado == 'rechazado':
            badge_class = 'bg-danger'
            
        estado_html = f"<span class='badge {badge_class}'>{p.estado.capitalize()}</span>"

        data.append({
            'DT_RowId': f'row_p_{p.id_pre_credito}',
            'fecha': p.fecha_registro.strftime("%d/%m/%Y %H:%M"),
            'cliente': p.idcliente.razonsocial if p.idcliente else '-',
            'doc_cliente': doc_cliente,
            'sucursal': p.id_sucursal.nombre_sucursal if p.id_sucursal else '-',
            'vehiculos': vehiculos_text or 'Sin vehículos',
            'monto_inicial': f"S/ {p.monto_inicial}",
            'estado': estado_html,
            'registrador': p.idusuario.nombrecompleto if p.idusuario else '-'
        })

    return JsonResponse({
        'draw': draw,
        'recordsTotal': records_total,
        'recordsFiltered': records_filtered,
        'data': data,
        'totales': totales_dict
    })
