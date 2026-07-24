from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Sum
from django.utils import timezone
from decimal import Decimal

from software.models.ClienteModel import Cliente
from software.models.CreditoModel import Credito
from software.models.CuotasVentaModel import CuotasVenta
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos
from django.core.cache import cache
from software.models.empresaModel import Empresa
from software.views.creditos import calcular_interes_mora

def _calcular_mora_dict(cuota_dict, empresa, hoy):
    if cuota_dict.get('interes_mora_manual') is not None:
        return cuota_dict['interes_mora_manual']
    
    fecha_vencimiento = cuota_dict.get('fecha_vencimiento')
    if not fecha_vencimiento or cuota_dict.get('estado_pago') == 'Pagado':
        return Decimal('0')
        
    if hoy <= fecha_vencimiento:
        return Decimal('0')
        
    dias_retraso = (hoy - fecha_vencimiento).days
    
    dias_inicio = empresa.dias_mora_inicio if empresa and empresa.dias_mora_inicio else 4
    tasa_base = empresa.interes_mora_base if empresa else Decimal('5.00')

    if empresa and not empresa.cobrar_mora:
        return Decimal('0')

    if dias_retraso < dias_inicio:
        return Decimal('0')
    
    tasa_adicional = dias_retraso - dias_inicio
    tasa_final = tasa_base + tasa_adicional
    
    saldo_cuota = cuota_dict.get('saldo_cuota', Decimal('0'))
    return (saldo_cuota * tasa_final / 100).quantize(Decimal('0.01'))

def index(request):
    """
    Vista principal del módulo Cuentas por Cobrar.
    Renderiza el esqueleto de la aplicación móvil (cards) y delega la carga
    de datos a la API Server-Side.
    """
    id2 = request.session.get('idtipousuario')
    if id2:
        permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
        data = {
            'permisos': permisos
        }
        return render(request, 'cuentas_por_cobrar/index.html', data)
    else:
        return render(request, 'login.html')

def api_listar_clientes_cobrar(request):
    """
    API Server-Side para listar los clientes que tienen deudas (cuotas pendientes).
    Adaptado para una vista tipo "Tarjetas" (Mobile-First).
    """
    id2 = request.session.get('idtipousuario')
    if not id2:
        return JsonResponse({'error': 'No autorizado'}, status=401)

    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search', '').strip()

    # 1. Encontrar todos los créditos activos o en mora
    creditos_activos = Credito.objects.filter(estado=1, estado_credito__in=['activo', 'mora'])
    
    # 2. Extraer los IDs de clientes que tienen estos créditos
    clientes_ids_ventas = creditos_activos.filter(idventa__isnull=False).values_list('idventa__idcliente', flat=True)
    clientes_ids_directos = creditos_activos.filter(idcliente__isnull=False).values_list('idcliente', flat=True)
    
    todos_ids_clientes = set(list(clientes_ids_ventas) + list(clientes_ids_directos))
    
    # 3. Filtrar clientes
    queryset = Cliente.objects.filter(estado=1, idcliente__in=todos_ids_clientes)
    total_records = queryset.count()

    if search_value:
        queryset = queryset.filter(
            Q(numdoc__icontains=search_value) |
            Q(razonsocial__icontains=search_value) |
            Q(nombre_comercial_cliente__icontains=search_value) |
            Q(telefono__icontains=search_value)
        )
    
    filtered_records = queryset.count()
    queryset = queryset.order_by('razonsocial')

    if length != -1:
        clientes_page = list(queryset[start:start + length])
    else:
        clientes_page = list(queryset)

    # 4. OPTIMIZACIÓN ORM: Obtener todas las cuotas relevantes de estos clientes en 1 sola consulta SQL
    client_ids = [c.idcliente for c in clientes_page]
    
    cuotas = CuotasVenta.objects.filter(
        Q(idventa__idcliente__in=client_ids, idventa__credito__estado=1, idventa__credito__estado_credito__in=['activo', 'mora']) |
        Q(idcredito__idcliente__in=client_ids, idcredito__estado=1, idcredito__estado_credito__in=['activo', 'mora']),
        estado=1,
        estado_pago__in=['Pendiente', 'Parcial']
    ).values(
        'idventa__idcliente', 
        'idcredito__idcliente', 
        'saldo_cuota', 
        'fecha_vencimiento',
        'interes_mora_manual',
        'estado_pago'
    )
    
    empresa = cache.get('config_empresa_mora')
    if not empresa:
        empresa = Empresa.objects.all().first()
        if empresa:
            cache.set('config_empresa_mora', empresa, 3600)
            
    hoy = timezone.now().date()
    client_stats = {c_id: {'saldo': Decimal('0.00'), 'vencidas': 0} for c_id in client_ids}
    
    for cuota in cuotas:
        c_id = cuota['idventa__idcliente'] or cuota['idcredito__idcliente']
        if c_id in client_stats:
            mora = _calcular_mora_dict(cuota, empresa, hoy)
            client_stats[c_id]['saldo'] += cuota['saldo_cuota'] + mora
            if cuota['fecha_vencimiento'] and cuota['fecha_vencimiento'] < hoy:
                client_stats[c_id]['vencidas'] += 1

    # 5. Serialización
    data = []
    for cliente in clientes_page:
        stats = client_stats[cliente.idcliente]
        data.append({
            'idcliente': cliente.idcliente,
            'numdoc': cliente.numdoc,
            'razonsocial': cliente.razonsocial,
            'telefono': cliente.telefono or '',
            'direccion': cliente.direccion or '',
            'saldo_total': str(stats['saldo']),
            'cuotas_vencidas': stats['vencidas']
        })

    return JsonResponse({
        'recordsTotal': total_records,
        'recordsFiltered': filtered_records,
        'data': data
    })

from django.db import transaction
from software.models.AperturaCierreCajaModel import AperturaCierreCaja
from software.models.TipoPagoModel import TipoPago
from software.models.PagoCuotaModel import PagoCuota
from software.models.movimientoCajaModel import MovimientoCaja

def detalle_cobro(request, idcliente):
    """
    Renderiza la pantalla de cobro para un cliente.
    Filtra TODAS sus cuotas vencidas/pendientes de TODOS sus créditos activos.
    """
    id2 = request.session.get('idtipousuario')
    if not id2:
        return render(request, 'login.html')

    cliente = get_object_or_404(Cliente, idcliente=idcliente)

    creditos = Credito.objects.filter(
        Q(idventa__idcliente=cliente.idcliente) | Q(idcliente=cliente.idcliente),
        estado=1,
        estado_credito__in=['activo', 'mora']
    )

    if not creditos.exists():
        return render(request, 'cuentas_por_cobrar/formulario_cobro.html', {'cliente': cliente, 'cuotas': [], 'total_deuda': 0})

    todas_cuotas = []
    for c in creditos:
        if c.idventa:
            cuotas = CuotasVenta.objects.filter(idventa=c.idventa, estado=1, estado_pago__in=['Pendiente', 'Parcial'])
        else:
            cuotas = CuotasVenta.objects.filter(idcredito=c, estado=1, estado_pago__in=['Pendiente', 'Parcial'])
        todas_cuotas.extend(list(cuotas))

    # Ordenar cronológicamente
    todas_cuotas.sort(key=lambda x: (x.fecha_vencimiento, x.numero_cuota))

    total_deuda = Decimal('0')
    for c in todas_cuotas:
        mora, _, _ = calcular_interes_mora(c)
        c.mora_calculada = mora
        c.saldo_total = c.saldo_cuota + mora
        total_deuda += c.saldo_total
    metodos_pago = TipoPago.objects.filter(estado=1)

    data = {
        'cliente': cliente,
        'cuotas': todas_cuotas,
        'total_deuda': total_deuda,
        'metodos_pago': metodos_pago
    }
    return render(request, 'cuentas_por_cobrar/formulario_cobro.html', data)

def procesar_cobro(request):
    """
    Procesa un pago global y lo distribuye entre las cuotas.
    Soporta pagos parciales y genera recibos RI o RM.
    """
    if request.method == 'POST':
        try:
            with transaction.atomic():
                idusuario = request.session.get('idusuario')
                if not idusuario:
                    return JsonResponse({'ok': False, 'error': 'Sesión expirada.'}, status=401)
                
                tipos_pago_ids = request.POST.getlist('tipo_pago_id[]')
                nros_operacion = request.POST.getlist('nro_operacion[]')
                montos_metodos = request.POST.getlist('monto_pago_item[]')

                monto_total_pagar = Decimal('0')
                desglose_pagos = []
                for i in range(len(tipos_pago_ids)):
                    if not tipos_pago_ids[i] or not montos_metodos[i]: continue
                    t_id = int(tipos_pago_ids[i])
                    m_val = Decimal(montos_metodos[i])
                    n_op = nros_operacion[i].strip() if i < len(nros_operacion) else ''
                    if m_val <= 0: continue
                    monto_total_pagar += m_val
                    tp_obj = get_object_or_404(TipoPago, id_tipo_pago=t_id)
                    desglose_pagos.append({'nombre': tp_obj.nombre, 'monto': m_val, 'op': n_op, 'id': t_id})
                
                if monto_total_pagar <= 0:
                    return JsonResponse({'ok': False, 'error': 'El monto a pagar debe ser mayor a 0.'}, status=400)
                
                if len(desglose_pagos) > 1:
                    tp_multiple = TipoPago.objects.filter(nombre__iexact='Múltiple').first()
                    id_tipo_pago_final = tp_multiple.id_tipo_pago if tp_multiple else desglose_pagos[0]['id']
                    detalle_obs = " | ".join([f"{d['nombre']}: S/ {d['monto']}" + (f" (Op:{d['op']})" if d['op'] else "") for d in desglose_pagos])
                    observaciones_final = f"[FRACCIONADO: {detalle_obs}]"
                    numero_operacion_final = "Múltiple"
                elif desglose_pagos:
                    id_tipo_pago_final = desglose_pagos[0]['id']
                    numero_operacion_final = desglose_pagos[0]['op']
                    observaciones_final = 'Cobro App Móvil'
                else:
                    return JsonResponse({'ok': False, 'error': 'No se enviaron métodos de pago válidos.'}, status=400)
                
                cuotas_ids_str = request.POST.get('cuotas_ids', '')
                cuotas_ids_list = request.POST.getlist('cuotas_ids[]')
                
                if cuotas_ids_str:
                    cuotas_ids = [int(x) for x in cuotas_ids_str.split(',') if x.strip()]
                elif cuotas_ids_list:
                    cuotas_ids = [int(x) for x in cuotas_ids_list if str(x).strip()]
                else:
                    return JsonResponse({'ok': False, 'error': 'No se seleccionaron cuotas.'}, status=400)
                
                # Obtener las cuotas en el mismo orden que el front
                cuotas = list(CuotasVenta.objects.filter(idcuotaventa__in=cuotas_ids))
                # Forzar orden cronológico real por si acaso
                cuotas.sort(key=lambda x: (x.fecha_vencimiento, x.numero_cuota))
                
                apertura_actual = AperturaCierreCaja.objects.filter(
                    idusuario_id=idusuario,
                    estado__in=['abierta', 'reabierta']
                ).first()
                if not apertura_actual:
                    return JsonResponse({'ok': False, 'error': 'No tiene una caja abierta.'}, status=400)
                
                pagos_creados = []
                monto_restante = monto_total_pagar
                creditos_afectados = set()
                
                for cuota in cuotas:
                    if monto_restante <= 0:
                        break
                    
                    mora, _, _ = calcular_interes_mora(cuota)
                    saldo_total_vld = cuota.saldo_cuota + mora
                    
                    if saldo_total_vld <= monto_restante:
                        monto_aplicado = saldo_total_vld
                    else:
                        monto_aplicado = monto_restante
                        
                    pago = PagoCuota.objects.create(
                        idcuotaventa=cuota,
                        idusuario_id=idusuario,
                        id_tipo_pago_id=id_tipo_pago_final,
                        monto_pago=monto_aplicado,
                        numero_operacion=numero_operacion_final,
                        observaciones=observaciones_final,
                        estado=1,
                        fecha_pago=timezone.now()
                    )
                    pagos_creados.append(pago)
                    
                    interes_mora_cobrado = min(monto_aplicado, mora)
                    monto_capital = monto_aplicado - interes_mora_cobrado
                    
                    cuota.interes_mora += interes_mora_cobrado
                    cuota.monto_pagado += monto_capital
                    cuota.saldo_cuota -= monto_capital
                    if cuota.saldo_cuota <= 0:
                        cuota.estado_pago = 'Pagado'
                        cuota.fecha_pago = timezone.now()
                    else:
                        cuota.estado_pago = 'Parcial'
                    cuota.save()
                    
                    monto_restante -= monto_aplicado
                    creditos_afectados.add(cuota.idventa.credito if cuota.idventa else cuota.idcredito)
                
                if not pagos_creados:
                    return JsonResponse({'ok': False, 'error': 'No se aplicó pago.'}, status=400)
                
                cliente = cuotas[0].idventa.idcliente if cuotas[0].idventa else cuotas[0].idcredito.idcliente
                es_multiple = len(pagos_creados) > 1
                
                movimiento_caja = MovimientoCaja.objects.create(
                    id_caja=apertura_actual.id_caja,
                    id_movimiento=apertura_actual,
                    idusuario_id=idusuario,
                    tipo_movimiento='ingreso',
                    monto=monto_total_pagar - monto_restante,
                    descripcion=f"Cobro App - Cliente: {cliente.razonsocial}",
                    estado=1
                )
                
                pagos_ids_str = ','.join([str(p.idpagocuota) for p in pagos_creados])
                marker = f'[MULTIPAGO:{pagos_ids_str}]' if es_multiple else ''
                
                for pago in pagos_creados:
                    pago.id_movimiento_caja = movimiento_caja
                    if marker:
                        pago.observaciones = f"{pago.observaciones} {marker}".strip()
                    pago.save()
                
                for credito in creditos_afectados:
                    credito.actualizar_estado()
                
                if es_multiple:
                    url_recibo = f"/creditos/recibo-pago-multiple/{pagos_ids_str}/"
                else:
                    url_recibo = f"/creditos/recibo-pago/{pagos_creados[0].idpagocuota}/"
                    
                return JsonResponse({
                    'ok': True,
                    'url_recibo': url_recibo,
                    'message': 'Cobro registrado correctamente.'
                })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'ok': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'ok': False, 'error': 'Método inválido.'}, status=405)
