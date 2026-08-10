import sys

with open('software/views/reportes.py', 'r', encoding='utf-8') as f:
    content = f.read()

helper = """
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

import re

# Insert helper function at the top
content = helper + content

# Replace in reporte_creditos
def replace_in_func(func_name, start_sig, end_sig, replace_str):
    global content
    idx_func = content.find('def ' + func_name)
    idx_start = content.find(start_sig, idx_func)
    idx_end = content.find(end_sig, idx_start)
    if idx_start != -1 and idx_end != -1:
        content = content[:idx_start] + replace_str + content[idx_end:]

# reporte_creditos replace
s_r = "estado_filtro = request.GET.get('estado', 'todos').strip()"
e_r = "ESTADOS_EXCLUIDOS = ['retenido', 'cancelado', 'reparado', 'segunda']"
r_r = "creditos_qs, search_value, lim = _get_creditos_filtrados(request, fi, ff)\n    "
replace_in_func('reporte_creditos', s_r, e_r, r_r)

# api_listar_reporte_creditos replace
s_a = "estado_filtro = request.GET.get('estado', 'todos').strip().lower()"
e_a = "records_total = creditos_qs.count()"
r_a = "creditos_qs, search_value, lim = _get_creditos_filtrados(request, fi, ff)\n    "
replace_in_func('api_listar_reporte_creditos', s_a, e_a, r_a)

# also remove the search part in api_listar_reporte_creditos which we included in helper
s_a2 = "search_value = request.GET.get('search[value]', '').strip()"
e_a2 = "records_filtered = creditos_qs.count()"
r_a2 = ""
replace_in_func('api_listar_reporte_creditos', s_a2, e_a2, r_a2)

with open('software/views/reportes.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")
