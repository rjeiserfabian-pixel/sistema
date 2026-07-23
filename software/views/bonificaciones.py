from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from django.db.models import Sum, Count, Q

from software.models.BonificacionModel import (
    ReglaBonificacion, 
    RangoBonificacion, 
    MetaVendedor, 
    CalculoBonificacion
)
from software.models.UsuarioModel import Usuario
from software.models.VentasModel import Ventas
from software.models.VentaDetalleModel import VentaDetalle
from software.models.CreditoModel import Credito
from software.models.CuotasVentaModel import CuotasVenta

# -------------------------------------------------------------
# CONFIGURACIN DE REGLAS
# -------------------------------------------------------------

def listar_reglas(request):
    id2 = request.session.get('idtipousuario')
    if not id2:
        return redirect('login')
        
    reglas = ReglaBonificacion.objects.all()
    return render(request, 'bonificaciones/reglas.html', {'reglas': reglas})

def guardar_regla(request):
    id2 = request.session.get('idtipousuario')
    if not id2:
        return redirect('login')
        
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        tipo_producto = request.POST.get('tipo_producto')
        tipo_comision = request.POST.get('tipo_comision')
        fecha_inicio = request.POST.get('fecha_inicio')
        
        # Para vehículos
        porcentaje_val = request.POST.get('porcentaje')
        porcentaje = porcentaje_val if (tipo_producto == 'Vehiculo' and porcentaje_val and porcentaje_val.strip()) else None
        
        # Validar fecha_inicio para no crashear
        if not fecha_inicio:
            from datetime import date
            fecha_inicio = date.today()
            
        regla = ReglaBonificacion.objects.create(
            nombre=nombre,
            tipo_producto=tipo_producto,
            tipo_comision=tipo_comision,
            porcentaje=porcentaje,
            fecha_inicio=fecha_inicio,
            estado=True
        )
        
        # Si es de repuestos, procesar los rangos dinámicos
        if tipo_producto == 'Repuesto':
            minimos = request.POST.getlist('monto_minimo[]')
            maximos = request.POST.getlist('monto_maximo[]')
            porcentajes = request.POST.getlist('rango_porcentaje[]')
            
            for i in range(len(minimos)):
                if not minimos[i] or not porcentajes[i]:
                    continue # Saltar si están vacíos
                m_max = maximos[i] if maximos[i] and maximos[i].strip() else None
                RangoBonificacion.objects.create(
                    regla=regla,
                    monto_minimo=minimos[i],
                    monto_maximo=m_max,
                    porcentaje=porcentajes[i]
                )
                
        return redirect('listar_reglas_bonificacion')
    return redirect('listar_reglas_bonificacion')

def eliminar_regla(request, id):
    id2 = request.session.get('idtipousuario')
    if not id2:
        return redirect('login')
        
    regla = get_object_or_404(ReglaBonificacion, id_regla=id)
    regla.delete()
    return redirect('listar_reglas_bonificacion')

def editar_regla(request):
    id2 = request.session.get('idtipousuario')
    if not id2:
        return redirect('login')
        
    if request.method == 'POST':
        id_regla = request.POST.get('id_regla_edit')
        regla = get_object_or_404(ReglaBonificacion, id_regla=id_regla)
        
        regla.nombre = request.POST.get('nombre_edit')
        
        if regla.tipo_producto == 'Vehiculo':
            pct = request.POST.get('porcentaje_edit')
            regla.porcentaje = pct if pct and pct.strip() else None
            
        regla.save()
        
        if regla.tipo_producto == 'Repuesto':
            regla.rangos.all().delete()
            minimos = request.POST.getlist('monto_minimo_edit[]')
            maximos = request.POST.getlist('monto_maximo_edit[]')
            porcentajes = request.POST.getlist('rango_porcentaje_edit[]')
            
            for i in range(len(minimos)):
                if not minimos[i] or not porcentajes[i]:
                    continue
                m_max = maximos[i] if maximos[i] and maximos[i].strip() else None
                RangoBonificacion.objects.create(
                    regla=regla,
                    monto_minimo=minimos[i],
                    monto_maximo=m_max,
                    porcentaje=porcentajes[i]
                )
                
    return redirect('listar_reglas_bonificacion')


# -------------------------------------------------------------
# METAS POR VENDEDOR
# -------------------------------------------------------------

def listar_metas(request):
    id2 = request.session.get('idtipousuario')
    if not id2:
        return redirect('login')
        
    metas = MetaVendedor.objects.all().order_by('-mes_anio')
    vendedores = Usuario.objects.filter(estado=1)
    return render(request, 'bonificaciones/metas.html', {'metas': metas, 'vendedores': vendedores})

def buscar_vendedores(request):
    """API para autocompletar vendedores en el formulario de metas."""
    id2 = request.session.get('idtipousuario')
    if not id2:
        return JsonResponse({'error': 'No autorizado'}, status=403)
    
    q = request.GET.get('q', '').strip()
    vendedores = Usuario.objects.filter(estado=1)
    if q:
        vendedores = vendedores.filter(nombrecompleto__icontains=q)
    
    data = [
        {'id': v.idusuario, 'nombre': v.nombrecompleto}
        for v in vendedores[:15]
    ]
    return JsonResponse(data, safe=False)

def guardar_meta(request):
    id2 = request.session.get('idtipousuario')
    if not id2: return redirect('login')
    if request.method == 'POST':
        vendedor_id = request.POST.get('vendedor')
        mes_anio = request.POST.get('mes_anio')
        if len(mes_anio) == 7: # Formato YYYY-MM
            mes_anio = f"{mes_anio}-01"
        categoria = request.POST.get('categoria')
        meta_unidades = request.POST.get('meta_unidades')
        meta_soles = request.POST.get('meta_soles')
        porcentaje_bono = request.POST.get('porcentaje_bono', '0')
        
        MetaVendedor.objects.create(
            vendedor_id=vendedor_id,
            mes_anio=mes_anio,
            categoria=categoria,
            meta_unidades=meta_unidades if meta_unidades and categoria in ['Vehiculos', 'Ambas'] else None,
            meta_soles=meta_soles if meta_soles and categoria in ['Repuestos', 'Ambas'] else None,
            porcentaje_bono=porcentaje_bono if porcentaje_bono else '0'
        )
    return redirect('listar_metas_bonificacion')

def eliminar_meta(request, id):
    id2 = request.session.get('idtipousuario')
    if not id2: return redirect('login')
    meta = get_object_or_404(MetaVendedor, id_meta=id)
    meta.delete()
    return redirect('listar_metas_bonificacion')

def editar_meta(request):
    id2 = request.session.get('idtipousuario')
    if not id2: return redirect('login')
    if request.method == 'POST':
        id_meta = request.POST.get('id_meta_edit')
        meta = get_object_or_404(MetaVendedor, id_meta=id_meta)
        meta.vendedor_id = request.POST.get('vendedor_edit')
        
        mes_anio = request.POST.get('mes_anio_edit')
        if len(mes_anio) == 7:
            mes_anio = f"{mes_anio}-01"
        meta.mes_anio = mes_anio
        
        categoria = request.POST.get('categoria_edit')
        meta.categoria = categoria
        meta_unidades = request.POST.get('meta_unidades_edit')
        meta_soles = request.POST.get('meta_soles_edit')
        porcentaje_bono = request.POST.get('porcentaje_bono_edit', '0')
        
        meta.meta_unidades = meta_unidades if meta_unidades and categoria in ['Vehiculos', 'Ambas'] else None
        meta.meta_soles = meta_soles if meta_soles and categoria in ['Repuestos', 'Ambas'] else None
        meta.porcentaje_bono = porcentaje_bono if porcentaje_bono else '0'
        meta.save()
    return redirect('listar_metas_bonificacion')


# -------------------------------------------------------------
# MOTOR DE CALCULO
# -------------------------------------------------------------

def motor_calculo(request):
    id2 = request.session.get('idtipousuario')
    if not id2:
        return redirect('login')
        
    return render(request, 'bonificaciones/calculos.html', {'calculos': []})

def api_listar_calculos(request):
    id2 = request.session.get('idtipousuario')
    if not id2:
        return JsonResponse({'error': 'No autorizado'}, status=401)
        
    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '')
    
    queryset = CalculoBonificacion.objects.all().order_by('-id_calculo')
    
    if search_value:
        from django.db.models import Q
        queryset = queryset.filter(
            Q(vendedor__nombrecompleto__icontains=search_value) |
            Q(estado__icontains=search_value)
        )
        
    recordsTotal = CalculoBonificacion.objects.count()
    recordsFiltered = queryset.count()
    
    # Paginar
    if length != -1:
        queryset = queryset[start:start+length]
        
    data = []
    for c in queryset:
        data.append({
            'id_calculo': c.id_calculo,
            'vendedor': c.vendedor.nombrecompleto if c.vendedor else '',
            'fecha_inicio': c.fecha_inicio_periodo.strftime('%d/%m/%Y') if c.fecha_inicio_periodo else '',
            'fecha_fin': c.fecha_fin_periodo.strftime('%d/%m/%Y') if c.fecha_fin_periodo else '',
            'total_vehiculos': c.total_vehiculos_vendidos,
            'total_repuestos': str(c.total_repuestos_vendidos),
            'comision_vehiculos': str(c.comision_vehiculos),
            'comision_repuestos': str(c.comision_repuestos),
            'bono_meta': str(c.bono_meta),
            'total_pagar': str(c.total_pagar),
            'estado': c.estado,
        })
        
    return JsonResponse({
        'draw': draw,
        'recordsTotal': recordsTotal,
        'recordsFiltered': recordsFiltered,
        'data': data
    })

def ejecutar_calculo(request):
    id2 = request.session.get('idtipousuario')
    if not id2:
        return redirect('login')
        
    if request.method == 'POST':
        fecha_inicio = request.POST.get('fecha_inicio')
        fecha_fin = request.POST.get('fecha_fin')
        
        # Determinar si el periodo es de un mes completo
        from datetime import datetime, timedelta
        import calendar
        
        f_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
        f_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        
        es_mensual = False
        if f_inicio.day == 1 and f_inicio.month == f_fin.month and f_inicio.year == f_fin.year:
            ultimo_dia = calendar.monthrange(f_inicio.year, f_inicio.month)[1]
            if f_fin.day == ultimo_dia:
                es_mensual = True
        
        vendedor_id = request.POST.get('vendedor')

        # Verificar si hay superposición con cualquier cálculo (incluso 'Calculado')
        overlap_query = CalculoBonificacion.objects.filter(
            fecha_inicio_periodo__lte=fecha_fin,
            fecha_fin_periodo__gte=fecha_inicio,
            estado__in=['Calculado', 'Aprobado', 'Pagado']
        )
        if vendedor_id:
            overlap_query = overlap_query.filter(vendedor_id=vendedor_id)

        if overlap_query.exists():
            ultimo_calculo = overlap_query.order_by('-fecha_fin_periodo').first()
            vendedores_bloqueados = list(overlap_query.values_list('vendedor__nombrecompleto', flat=True).distinct())
            nombres = ', '.join(vendedores_bloqueados)
            
            if ultimo_calculo:
                siguiente_dia = (ultimo_calculo.fecha_fin_periodo + timedelta(days=1)).strftime('%d/%m/%Y')
                mensaje = f'Hay cálculos previos que se cruzan en estas fechas para: {nombres}. Puede iniciar un nuevo cálculo a partir del {siguiente_dia}.'
            else:
                mensaje = f'Ya existe un cálculo que se cruza en estas fechas para: {nombres}.'
                
            return JsonResponse({'error': True, 'mensaje': mensaje}, status=400)
        
        # 1. Obtener reglas activas
        regla_vehiculos = ReglaBonificacion.objects.filter(tipo_producto='Vehiculo', estado=True).last()
        reglas_repuestos = ReglaBonificacion.objects.filter(tipo_producto='Repuesto', estado=True)
        rangos_repuestos = []
        for r in reglas_repuestos:
            rangos_repuestos.extend(list(r.rangos.all()))
        rangos_repuestos = sorted(rangos_repuestos, key=lambda x: x.monto_minimo)
            
        # 2. Filtrar ventas del periodo (excluyendo anuladas -> estado 0)
        ventas_periodo = Ventas.objects.filter(
            fecha_venta__date__gte=fecha_inicio,
            fecha_venta__date__lte=fecha_fin,
            estado=1
        )
        if vendedor_id:
            ventas_periodo = ventas_periodo.filter(idusuario_id=vendedor_id)
        
        # Agrupar datos por vendedor
        data_vendedores = {}
        
        for venta in ventas_periodo:
            vendedor = venta.idusuario
            
            if venta.id_forma_pago and venta.id_forma_pago.nombre.upper() == 'CREDITO':
                try:
                    credito = venta.credito
                    
                    # Verificar la cuota 0 (inicial) y cuota 1
                    cuotas_iniciales = credito.cuotas.filter(numero_cuota__in=[0, 1])
                    
                    if not cuotas_iniciales.exists():
                        continue
                        
                    es_valido = True
                    for cuota in cuotas_iniciales:
                        if cuota.estado_pago != 'Pagado':
                            es_valido = False
                            break
                            
                    if not es_valido:
                        continue # Saltamos esta venta si falta pagar la inicial o la cuota 1
                except:
                    # Si hay un error con el crédito, no comisiona por precaución
                    continue
                    
            if vendedor.idusuario not in data_vendedores:
                data_vendedores[vendedor.idusuario] = {
                    'vendedor': vendedor,
                    'total_vehiculos': 0,
                    'total_repuestos': Decimal('0.00'),
                    'comision_vehiculos': Decimal('0.00')
                }
                
            # Analizar detalles
            detalles = VentaDetalle.objects.filter(idventa=venta)
            for det in detalles:
                # Validar de qu categora es
                es_vehiculo = False
                es_repuesto = False
                
                if det.tipo_item == 'vehiculo' or det.id_vehiculo:
                    es_vehiculo = True
                elif det.tipo_item == 'repuesto' or det.id_repuesto_comprado:
                    es_repuesto = True
                    
                try:
                    subtotal = Decimal(str(det.subtotal))
                except:
                    subtotal = Decimal('0.00')
                
                if es_vehiculo:
                    data_vendedores[vendedor.idusuario]['total_vehiculos'] += det.cantidad
                    if regla_vehiculos and regla_vehiculos.porcentaje:
                        comision = subtotal * (regla_vehiculos.porcentaje / Decimal('100.00'))
                        data_vendedores[vendedor.idusuario]['comision_vehiculos'] += comision
                        
                elif es_repuesto:
                    data_vendedores[vendedor.idusuario]['total_repuestos'] += subtotal
                    
        # 3. Procesar resultados finales por vendedor
        for v_id, data in data_vendedores.items():
            comision_rep = Decimal('0.00')
            tot_rep = data['total_repuestos']
            
            # Calcular comisin repuestos segn escala
            if rangos_repuestos and tot_rep > 0:
                for idx, rango in enumerate(rangos_repuestos):
                    if rango.monto_minimo <= tot_rep:
                        if not rango.monto_maximo or tot_rep <= rango.monto_maximo:
                            comision_rep = tot_rep * (rango.porcentaje / Decimal('100.00'))
                            break
                        # Si es el último rango y lo supera, aplicamos este tope máximo
                        elif idx == len(rangos_repuestos) - 1:
                            comision_rep = tot_rep * (rango.porcentaje / Decimal('100.00'))
                            break
                            
            # 4. Calcular Metas
            bono_meta = Decimal('0.00')
            pct_cumplimiento = Decimal('0.00')
            
            if es_mensual:
                metas = MetaVendedor.objects.filter(
                    vendedor=data['vendedor'],
                    mes_anio__month=f_inicio.month,
                    mes_anio__year=f_inicio.year
                )
                
                suma_pct = Decimal('0.00')
                total_metas = metas.count()
                
                for meta in metas:
                    pct_individual = Decimal('0.00')
                    porcentaje_bono = meta.porcentaje_bono if meta.porcentaje_bono else Decimal('0.00')
                    
                    if meta.categoria == 'Vehiculos' and meta.meta_unidades:
                        pct_individual = (Decimal(data['total_vehiculos']) / Decimal(meta.meta_unidades)) * 100
                        if pct_individual >= 100:
                            bono_meta += data['comision_vehiculos'] * (porcentaje_bono / Decimal('100.00'))
                            
                    elif meta.categoria == 'Repuestos' and meta.meta_soles:
                        pct_individual = (tot_rep / meta.meta_soles) * 100
                        if pct_individual >= 100:
                            bono_meta += comision_rep * (porcentaje_bono / Decimal('100.00'))
                            
                    elif meta.categoria == 'Ambas' and meta.meta_unidades and meta.meta_soles:
                        pct_veh = (Decimal(data['total_vehiculos']) / Decimal(meta.meta_unidades)) * 100
                        pct_rep = (tot_rep / meta.meta_soles) * 100
                        pct_individual = (pct_veh + pct_rep) / Decimal('2.0')
                        
                        if pct_veh >= 100 and pct_rep >= 100:
                            bono_meta += (data['comision_vehiculos'] + comision_rep) * (porcentaje_bono / Decimal('100.00'))
                            
                    suma_pct += pct_individual
                    
                if total_metas > 0:
                    pct_cumplimiento = suma_pct / Decimal(str(total_metas))
                        
            total_pagar = data['comision_vehiculos'] + comision_rep + bono_meta
            
            CalculoBonificacion.objects.create(
                vendedor=data['vendedor'],
                fecha_inicio_periodo=fecha_inicio,
                fecha_fin_periodo=fecha_fin,
                total_vehiculos_vendidos=data['total_vehiculos'],
                total_repuestos_vendidos=tot_rep,
                porcentaje_cumplimiento=pct_cumplimiento,
                comision_vehiculos=data['comision_vehiculos'],
                comision_repuestos=comision_rep,
                bono_meta=bono_meta,
                total_pagar=total_pagar,
                estado='Calculado'
            )
        
        return redirect('motor_calculo_bonificacion')
    return redirect('motor_calculo_bonificacion')

def eliminar_calculo(request, id_calculo):
    id2 = request.session.get('idtipousuario')
    if not id2:
        return redirect('login')
    calculo = get_object_or_404(CalculoBonificacion, id_calculo=id_calculo)
    if calculo.estado == 'Calculado':
        calculo.delete()
    return redirect('motor_calculo_bonificacion')

def cambiar_estado_calculo(request, id_calculo, estado):
    id2 = request.session.get('idtipousuario')
    if not id2:
        return redirect('login')
        
    calculo = get_object_or_404(CalculoBonificacion, id_calculo=id_calculo)
    
    if estado == 'Pagado' and calculo.estado != 'Pagado':
        id_caja_session = request.session.get('id_caja')
        idusuario_session = request.session.get('idusuario')
        
        if not id_caja_session:
            return JsonResponse({'error': 'Debe seleccionar una caja en configuración antes de registrar el pago.'}, status=400)
            
        from software.models.cajaModel import Caja
        from software.models.AperturaCierreCajaModel import AperturaCierreCaja
        from software.models.movimientoCajaModel import MovimientoCaja
        from software.models.UsuarioModel import Usuario
        from django.db.models import Sum
        from decimal import Decimal
        
        apertura = AperturaCierreCaja.objects.filter(
            idusuario_id=idusuario_session,
            id_caja_id=id_caja_session,
            estado__in=['abierta', 'reabierta']
        ).first()
        
        if not apertura:
            return JsonResponse({'error': 'La caja seleccionada no está aperturada. Aperture la caja para poder registrar el pago de comisión.'}, status=400)
            
        # 1. Calcular Saldo Actual
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
        saldo_actual = saldo_inicial + ingresos - egresos
        
        if saldo_actual < calculo.total_pagar:
            return JsonResponse({
                'error': f'Fondos insuficientes en la caja. Saldo actual: S/ {saldo_actual:.2f}, Monto a pagar: S/ {calculo.total_pagar:.2f}.'
            }, status=400)
            
        caja = Caja.objects.get(id_caja=id_caja_session)
        usuario = Usuario.objects.get(idusuario=idusuario_session)
        
        # Crear el movimiento de egreso en caja
        MovimientoCaja.objects.create(
            id_caja=caja,
            id_movimiento=apertura,
            idusuario=usuario,
            tipo_movimiento='egreso',
            monto=calculo.total_pagar,
            descripcion=f"Pago de comisiones del {calculo.fecha_inicio_periodo.strftime('%d/%m/%Y')} al {calculo.fecha_fin_periodo.strftime('%d/%m/%Y')} a {calculo.vendedor.nombrecompleto}",
            estado=1
        )
        
    calculo.estado = estado
    calculo.save()
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'ok': True})
    return redirect('motor_calculo_bonificacion')

def detalle_calculo(request, id_calculo):
    """Devuelve JSON con las ventas individuales que formaron parte de este cálculo."""
    id2 = request.session.get('idtipousuario')
    if not id2:
        return JsonResponse({'error': 'No autorizado'}, status=403)
        
    calculo = get_object_or_404(CalculoBonificacion, id_calculo=id_calculo)
    
    # Obtener las reglas activas durante ese cálculo (simulado a la última activa)
    regla_vehiculos = ReglaBonificacion.objects.filter(tipo_producto='Vehiculo', estado=True).last()
    reglas_repuestos = ReglaBonificacion.objects.filter(tipo_producto='Repuesto', estado=True)
    nombres_repuestos = " + ".join([r.nombre for r in reglas_repuestos])
    
    reglas_info = {
        'vehiculos': f"{regla_vehiculos.nombre} ({regla_vehiculos.porcentaje}%)" if regla_vehiculos and regla_vehiculos.porcentaje else "Sin regla activa",
        'repuestos': f"{nombres_repuestos} (Escala/Rangos)" if reglas_repuestos else "Sin regla activa"
    }
    
    ventas_periodo = Ventas.objects.filter(
        idusuario=calculo.vendedor,
        fecha_venta__date__gte=calculo.fecha_inicio_periodo,
        fecha_venta__date__lte=calculo.fecha_fin_periodo,
        estado=1
    ).order_by('fecha_venta')
    
    detalles_res = []
    
    for venta in ventas_periodo:
        # Misma lógica de validación de crédito que en el motor
        if venta.id_forma_pago and venta.id_forma_pago.nombre.upper() == 'CREDITO':
            try:
                credito = venta.credito
                
                cuotas_iniciales = credito.cuotas.filter(numero_cuota__in=[0, 1])
                
                if not cuotas_iniciales.exists():
                    continue
                    
                es_valido = True
                for cuota in cuotas_iniciales:
                    if cuota.estado_pago != 'Pagado':
                        es_valido = False
                        break
                        
                if not es_valido:
                    continue
            except:
                continue
                
        # Si pasó, contabilizamos sus detalles
        detalles_bd = VentaDetalle.objects.filter(idventa=venta)
        unid_vehiculos = 0
        valor_vehiculos = Decimal('0.00')
        comision_vehiculos = Decimal('0.00')
        total_repuestos = Decimal('0.00')
        
        for det in detalles_bd:
            es_vehiculo = False
            es_repuesto = False
            
            if det.tipo_item == 'vehiculo' or det.id_vehiculo:
                es_vehiculo = True
            elif det.tipo_item == 'repuesto' or det.id_repuesto_comprado:
                es_repuesto = True
                
            try:
                subtotal = Decimal(str(det.subtotal))
            except:
                subtotal = Decimal('0.00')
                
            if es_vehiculo:
                unid_vehiculos += det.cantidad
                valor_vehiculos += subtotal
                if regla_vehiculos and regla_vehiculos.porcentaje:
                    comision_vehiculos += subtotal * (regla_vehiculos.porcentaje / Decimal('100.00'))
            elif es_repuesto:
                total_repuestos += subtotal
                
        # Solo agregar a la lista si tiene vehículos o repuestos
        if unid_vehiculos > 0 or total_repuestos > 0:
            nombre_cliente = venta.idcliente.razonsocial if venta.idcliente else "Cliente Vario"
            
            tipo_codigo = venta.idtipocomprobante.codigo if venta.idtipocomprobante else ''
            serie = venta.idseriecomprobante.serie if venta.idseriecomprobante else ''
            
            comprobante = venta.numero_comprobante
            
            detalles_res.append({
                'fecha': venta.fecha_venta.strftime('%d/%m/%Y'),
                'comprobante': comprobante,
                'cliente': nombre_cliente,
                'vehiculos': unid_vehiculos,
                'valor_vehiculos': float(valor_vehiculos),
                'regla_porcentaje': float(regla_vehiculos.porcentaje) if regla_vehiculos and regla_vehiculos.porcentaje and unid_vehiculos > 0 else None,
                'comision_vehiculos': float(comision_vehiculos),
                'repuestos': float(total_repuestos)
            })
            
    rango_aplicado = None
    tot_rep = calculo.total_repuestos_vendidos
    rangos_repuestos = RangoBonificacion.objects.filter(regla__in=reglas_repuestos).order_by('monto_minimo')
    for idx, rango in enumerate(rangos_repuestos):
        if rango.monto_minimo <= tot_rep:
            if not rango.monto_maximo or tot_rep <= rango.monto_maximo:
                rango_aplicado = rango
                break
            elif idx == len(rangos_repuestos) - 1:
                rango_aplicado = rango
                break
                
    return JsonResponse({
        'ventas': detalles_res, 
        'reglas': reglas_info,
        'totales': {
            'comision_repuestos': float(calculo.comision_repuestos),
            'total_repuestos_vendidos': float(calculo.total_repuestos_vendidos)
        },
        'rango_aplicado': float(rango_aplicado.porcentaje) if rango_aplicado else None
    })


# -------------------------------------------------------------
# REPORTES
# -------------------------------------------------------------

def reportes(request):
    id2 = request.session.get('idtipousuario')
    if not id2:
        return redirect('login')
        
    estado_filtro = request.GET.get('estado', '')
    
    from django.db.models import Sum, Count, Q
    calculos = CalculoBonificacion.objects.all()
    if estado_filtro:
        calculos = calculos.filter(estado=estado_filtro)
        
    totales = calculos.aggregate(
        total_pagado=Sum('total_pagar', filter=Q(estado='Pagado')),
        pendientes=Count('id_calculo', filter=~Q(estado='Pagado')),
        vendedores=Count('vendedor_id', distinct=True),
        total_calculos=Count('id_calculo')
    )

    context = {
        'calculos': [], # Vaciado para Server-Side Processing
        'total_pagado': totales['total_pagado'] or 0,
        'pendientes': totales['pendientes'] or 0,
        'vendedores': totales['vendedores'] or 0,
        'total_calculos': totales['total_calculos'] or 0,
        'estado_filtro': estado_filtro,
    }
    
    return render(request, 'bonificaciones/reportes.html', context)


def pdf_calculo(request, id_calculo):
    """Genera un PDF profesional del cálculo de bonificación usando ReportLab."""
    id2 = request.session.get('idtipousuario')
    if not id2:
        return redirect('login')

    from io import BytesIO
    from django.http import FileResponse, HttpResponse
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm, mm
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    from software.models.empresaModel import Empresa
    from software.utils.logo_utils import get_logo_image_for_pdf

    calculo = get_object_or_404(CalculoBonificacion, id_calculo=id_calculo)

    regla_vehiculos = ReglaBonificacion.objects.filter(tipo_producto='Vehiculo', estado=True).last()
    reglas_repuestos = ReglaBonificacion.objects.filter(tipo_producto='Repuesto', estado=True)
    rangos_repuestos = []
    for r in reglas_repuestos:
        rangos_repuestos.extend(list(r.rangos.all()))
    rangos_repuestos = sorted(rangos_repuestos, key=lambda x: x.monto_minimo)

    empresa = Empresa.objects.filter(activo=True).first()

    ventas_periodo = Ventas.objects.filter(
        idusuario=calculo.vendedor,
        fecha_venta__date__gte=calculo.fecha_inicio_periodo,
        fecha_venta__date__lte=calculo.fecha_fin_periodo,
        estado=1
    ).order_by('fecha_venta')

    detalles_ventas = []
    for venta in ventas_periodo:
        if venta.id_forma_pago and venta.id_forma_pago.nombre.upper() == 'CREDITO':
            try:
                credito = venta.credito
                cuotas_iniciales = credito.cuotas.filter(numero_cuota__in=[0, 1])
                if not cuotas_iniciales.exists() or not all(c.estado_pago == 'Pagado' for c in cuotas_iniciales):
                    continue
            except:
                continue

        detalles_bd = VentaDetalle.objects.filter(idventa=venta)
        unid_v = 0
        valor_v = Decimal('0.00')
        com_v   = Decimal('0.00')
        tot_r   = Decimal('0.00')

        for det in detalles_bd:
            try:
                subtotal = Decimal(str(det.subtotal))
            except:
                subtotal = Decimal('0.00')
            if det.tipo_item == 'vehiculo' or det.id_vehiculo:
                unid_v += det.cantidad
                valor_v += subtotal
                if regla_vehiculos and regla_vehiculos.porcentaje:
                    com_v += subtotal * (regla_vehiculos.porcentaje / Decimal('100'))
            elif det.tipo_item == 'repuesto' or det.id_repuesto_comprado:
                tot_r += subtotal

        if unid_v > 0 or tot_r > 0:
            tipo_cod = venta.idtipocomprobante.codigo if venta.idtipocomprobante else ''
            serie    = venta.idseriecomprobante.serie if venta.idseriecomprobante else ''
            comp     = f"{tipo_cod} {serie}-{venta.numero_comprobante}".strip()
            nombre_c = venta.idcliente.razonsocial if venta.idcliente else 'Cliente Varios'
            detalles_ventas.append({
                'fecha': venta.fecha_venta.strftime('%d/%m/%Y'),
                'comprobante': comp,
                'cliente': nombre_c,
                'vehiculos': unid_v,
                'valor_vehiculos': valor_v,
                'comision_vehiculos': com_v,
                'repuestos': tot_r,
            })

    # Rango aplicado repuestos
    rango_aplicado = None
    tot_rep = calculo.total_repuestos_vendidos
    for idx, rango in enumerate(rangos_repuestos):
        if rango.monto_minimo <= tot_rep:
            if not rango.monto_maximo or tot_rep <= rango.monto_maximo:
                rango_aplicado = rango
                break
            elif idx == len(rangos_repuestos) - 1:
                rango_aplicado = rango
                break

    # ── COLORES ──────────────────────────────────────────────────────────
    PURPLE_MAIN = colors.HexColor('#667eea')
    PURPLE_DARK = colors.HexColor('#764ba2')
    BG_CARD     = colors.HexColor('#f3f5fe') # Light purple for cards
    BORDER_CARD = colors.HexColor('#d3d9f3')
    BG_INFO     = colors.HexColor('#f8fafc')
    TEXT_DARK   = colors.HexColor('#1f2937')
    TEXT_MUTED  = colors.HexColor('#6b7280')
    WHITE       = colors.white

    # Badge Colors
    if calculo.estado == 'Pagado':
        BG_BADGE, TXT_BADGE = colors.HexColor('#d1fae5'), colors.HexColor('#065f46')
    elif calculo.estado == 'Calculado':
        BG_BADGE, TXT_BADGE = colors.HexColor('#fef3c7'), colors.HexColor('#92400e')
    elif calculo.estado == 'Aprobado':
        BG_BADGE, TXT_BADGE = colors.HexColor('#dbeafe'), colors.HexColor('#1e40af')
    else:
        BG_BADGE, TXT_BADGE = colors.HexColor('#f3f4f6'), colors.HexColor('#374151')

    # ── PDF ──────────────────────────────────────────────────────────────
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm,
    )

    styles = getSampleStyleSheet()
    def style(name, **kw):
        return ParagraphStyle(name + '_bon', parent=styles.get(name, styles['Normal']), **kw)

    s_title       = style('Heading1', fontSize=18, fontName='Helvetica-Bold', textColor=PURPLE_MAIN, leading=20, spaceAfter=2)
    s_subtitle    = style('Normal',   fontSize=9,  fontName='Helvetica',      textColor=TEXT_MUTED, leading=10)
    s_badge       = style('Normal',   fontSize=9,  fontName='Helvetica-Bold', textColor=TXT_BADGE, alignment=TA_CENTER)
    
    s_label       = style('Normal',   fontSize=8,  fontName='Helvetica',      textColor=TEXT_MUTED, leading=10, textTransform='uppercase')
    s_val_info    = style('Normal',   fontSize=10, fontName='Helvetica-Bold', textColor=TEXT_DARK, leading=12)
    
    s_card_lbl    = style('Normal',   fontSize=8,  fontName='Helvetica',      textColor=TEXT_MUTED, alignment=TA_CENTER, textTransform='uppercase')
    s_card_val    = style('Normal',   fontSize=13, fontName='Helvetica-Bold', textColor=PURPLE_MAIN, alignment=TA_CENTER, leading=16)
    s_card_t_lbl  = style('Normal',   fontSize=8,  fontName='Helvetica',      textColor=colors.HexColor('#e0e0e0'), alignment=TA_CENTER, textTransform='uppercase')
    s_card_t_val  = style('Normal',   fontSize=14, fontName='Helvetica-Bold', textColor=WHITE, alignment=TA_CENTER, leading=16)
    
    s_sec_title   = style('Normal',   fontSize=11, fontName='Helvetica-Bold', textColor=TEXT_DARK, spaceBefore=8, spaceAfter=4)
    s_th          = style('Normal',   fontSize=8,  fontName='Helvetica-Bold', textColor=WHITE)
    s_cell        = style('Normal',   fontSize=8,  fontName='Helvetica',      textColor=TEXT_DARK)

    story = []

    # ═══════════════════════ ENCABEZADO ═══════════════════════════════
    logo_rl  = get_logo_image_for_pdf(empresa, width_mm=35, height_mm=20, circular=False)
    left_col = logo_rl if logo_rl else Paragraph('', styles['Normal'])

    title_block = [
        Paragraph("📊 Reporte de Bonificación", s_title),
        Paragraph("Detalle de comisiones calculadas para el período indicado", s_subtitle)
    ]

    # Usar tabla para alinear y poner el badge a la derecha
    header_tbl = Table(
        [[left_col, title_block, Paragraph(calculo.estado.upper(), s_badge)]], 
        colWidths=[4.2*cm, 10.5*cm, 3.3*cm]
    )
    header_tbl.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND',    (2, 0), (2, 0), BG_BADGE),
        ('ROUNDEDCORNERS',(2, 0), (2, 0), [10, 10, 10, 10]),
        ('TOPPADDING',    (2, 0), (2, 0), 6),
        ('BOTTOMPADDING', (2, 0), (2, 0), 6),
        ('LEFTPADDING',   (0, 0), (0, 0), 0),
        ('LINEBELOW',     (0, 0), (-1, 0), 1.5, PURPLE_MAIN),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 15))

    # ═══════════════════════ INFO VENDEDOR ════════════════════════════
    info_data = [[
        [Paragraph("VENDEDOR", s_label), Paragraph(calculo.vendedor.nombrecompleto if calculo.vendedor else '---', s_val_info)],
        [Paragraph("PERÍODO", s_label), Paragraph(f"{calculo.fecha_inicio_periodo.strftime('%d/%m/%Y')} — {calculo.fecha_fin_periodo.strftime('%d/%m/%Y')}", s_val_info)],
        [Paragraph("FECHA DE CÁLCULO", s_label), Paragraph(calculo.fecha_calculo.strftime('%d/%m/%Y %H:%M'), s_val_info)]
    ]]
    info_tbl = Table(info_data, colWidths=[6*cm, 6*cm, 6*cm])
    info_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), BG_INFO),
        ('ROUNDEDCORNERS',[8, 8, 8, 8]),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING',   (0, 0), (-1, -1), 15),
        ('TOPPADDING',    (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 15))

    # ═══════════════════════ TARJETAS RESUMEN ══════════════════════════
    def make_card(lbl, val, is_total=False):
        t = Table([[Paragraph(lbl, s_card_t_lbl if is_total else s_card_lbl)], 
                   [Paragraph(val, s_card_t_val if is_total else s_card_val)]],
                  colWidths=[4.1*cm if not is_total else 8.5*cm])
        bg_col = PURPLE_DARK if is_total else BG_CARD
        t.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), bg_col),
            ('BOX',           (0, 0), (-1, -1), 0.5, BORDER_CARD if not is_total else PURPLE_DARK),
            ('ROUNDEDCORNERS',[8, 8, 8, 8]),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING',    (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        return t

    row1 = [
        make_card('VEHÍCULOS', f"{calculo.total_vehiculos_vendidos} und."),
        make_card('REPUESTOS', f"S/ {calculo.total_repuestos_vendidos:,.2f}"),
        make_card('COM. VEHÍCULOS', f"S/ {calculo.comision_vehiculos:,.2f}"),
        make_card('COM. REPUESTOS', f"S/ {calculo.comision_repuestos:,.2f}")
    ]
    row2 = [
        make_card('BONO META', f"S/ {calculo.bono_meta:,.2f}"),
        make_card('% META ALCANZADA', f"{calculo.porcentaje_cumplimiento:.2f}%"),
        make_card('TOTAL A PAGAR', f"S/ {calculo.total_pagar:,.2f}", is_total=True)
    ]

    grid1 = Table([row1], colWidths=[4.4*cm, 4.4*cm, 4.4*cm, 4.4*cm])
    grid1.setStyle(TableStyle([('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0)]))
    story.append(grid1)
    story.append(Spacer(1, 8))

    grid2 = Table([row2], colWidths=[4.4*cm, 4.4*cm, 8.8*cm])
    grid2.setStyle(TableStyle([('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0)]))
    story.append(grid2)
    story.append(Spacer(1, 15))

    # ═══════════════════════ REGLAS APLICADAS ══════════════════════════
    if regla_vehiculos or reglas_repuestos:
        rules_story = [Paragraph("📋 <b>Reglas de Comisión Aplicadas</b>", style('Normal', fontSize=10, textColor=colors.HexColor('#3730a3'))), Spacer(1, 6)]
        
        if regla_vehiculos:
            rules_story.append(Paragraph(f"🚗 <b>Vehículos:</b> {regla_vehiculos.nombre} — <b>{regla_vehiculos.porcentaje}% sobre subtotal</b>", s_cell))
            rules_story.append(Spacer(1, 4))
            
        if reglas_repuestos and rangos_repuestos:
            nombres = " + ".join([r.nombre for r in reglas_repuestos])
            rules_story.append(Paragraph(f"🔧 <b>Repuestos:</b> {nombres} — Escala por Volumen:", s_cell))
            rules_story.append(Spacer(1, 4))
            
            r_data = [['DESDE (S/)', 'HASTA (S/)', '% COMISIÓN', '¿APLICADO?']]
            for r in rangos_repuestos:
                aplicado = r == rango_aplicado
                hasta = f"S/ {r.monto_maximo:,.2f}" if r.monto_maximo else "En adelante"
                r_data.append([
                    f"S/ {r.monto_minimo:,.2f}",
                    hasta,
                    f"{r.porcentaje}%",
                    "✔ APLICADO" if aplicado else "—"
                ])
            rt = Table(r_data, colWidths=[4*cm, 4*cm, 3.5*cm, 3.5*cm])
            rt.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3730a3')),
                ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f0f4ff'), WHITE]),
                ('BOX', (0, 0), (-1, -1), 0.5, BORDER_CARD),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_CARD),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            rules_story.append(rt)
            
            if rango_aplicado:
                rules_story.append(Spacer(1, 4))
                rules_story.append(Paragraph(f"<font color='#065f46'>✔ Se aplicó el <b>{rango_aplicado.porcentaje}%</b> sobre el total de repuestos <b>S/ {calculo.total_repuestos_vendidos:,.2f}</b> → Comisión: <b>S/ {calculo.comision_repuestos:,.2f}</b></font>", s_cell))

        rules_box = Table([[rules_story]], colWidths=[17.6*cm])
        rules_box.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0f4ff')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#c7d2fe')),
            ('ROUNDEDCORNERS', (0, 0), (-1, -1), [8, 8, 8, 8]),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
        ]))
        story.append(rules_box)
        story.append(Spacer(1, 15))

    # ═══════════════════════ VENTAS CONSIDERADAS ══════════════════════
    story.append(Paragraph("<b>Ventas Consideradas en el Cálculo</b>", s_sec_title))
    
    if detalles_ventas:
        v_hdrs = ['FECHA', 'COMPROBANTE', 'CLIENTE', 'VEHÍCULOS', 'VALOR VEH. (S/)', 'COM. VEH. (S/)', 'REPUESTOS (S/)']
        v_data = [[Paragraph(h, s_th) for h in v_hdrs]]
        
        for d in detalles_ventas:
            v_data.append([
                Paragraph(d['fecha'], s_cell),
                Paragraph(d['comprobante'], s_cell),
                Paragraph(d['cliente'], s_cell),
                Paragraph(str(d['vehiculos']) if d['vehiculos'] > 0 else '-', style('Normal', fontSize=8, alignment=TA_CENTER)),
                Paragraph(f"{d['valor_vehiculos']:,.2f}" if d['valor_vehiculos'] > 0 else '-', style('Normal', fontSize=8, alignment=TA_RIGHT)),
                Paragraph(f"{d['comision_vehiculos']:,.2f}" if d['comision_vehiculos'] > 0 else '-', style('Normal', fontSize=8, alignment=TA_RIGHT)),
                Paragraph(f"{d['repuestos']:,.2f}" if d['repuestos'] > 0 else '-', style('Normal', fontSize=8, alignment=TA_RIGHT)),
            ])
            
        # Footer de totales
        v_data.append([
            Paragraph("<b>TOTAL</b>", s_th), '', '',
            Paragraph(f"<b>{calculo.total_vehiculos_vendidos}</b>", style('Normal', fontSize=8, textColor=WHITE, alignment=TA_CENTER)),
            Paragraph("<b>—</b>", style('Normal', fontSize=8, textColor=WHITE, alignment=TA_RIGHT)),
            Paragraph(f"<b>{calculo.comision_vehiculos:,.2f}</b>", style('Normal', fontSize=8, textColor=WHITE, alignment=TA_RIGHT)),
            Paragraph(f"<b>{calculo.total_repuestos_vendidos:,.2f}</b>", style('Normal', fontSize=8, textColor=WHITE, alignment=TA_RIGHT)),
        ])
            
        vt = Table(v_data, colWidths=[2*cm, 3.5*cm, 4.5*cm, 1.8*cm, 2*cm, 2*cm, 2*cm], repeatRows=1)
        vt.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), PURPLE_DARK),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [WHITE, BG_INFO]),
            ('BACKGROUND', (0, -1), (-1, -1), TEXT_DARK),
            ('SPAN', (0, -1), (2, -1)),
            ('BOX', (0, 0), (-1, -1), 0.5, BORDER_CARD),
            ('INNERGRID', (0, 0), (-1, -2), 0.5, BORDER_CARD),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(vt)
    else:
        story.append(Paragraph('No se encontraron ventas válidas para este período.', s_subtitle))

    story.append(Spacer(1, 30))
    
    # ═══════════════════════ FIRMAS ═══════════════════════════════════
    firma_data = [
        [Paragraph(f"<b>{calculo.vendedor.nombrecompleto}</b><br/>Vendedor / Beneficiario", style('Normal', fontSize=9, textColor=TEXT_MUTED, alignment=TA_CENTER)),
         Paragraph("<b>Gerencia / Aprobador</b><br/>V°B° Aprobación de pago", style('Normal', fontSize=9, textColor=TEXT_MUTED, alignment=TA_CENTER))]
    ]
    firma_tbl = Table(firma_data, colWidths=[8*cm, 8*cm])
    firma_tbl.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (0, 0), 1, TEXT_MUTED),
        ('LINEABOVE', (1, 0), (1, 0), 1, TEXT_MUTED),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    story.append(firma_tbl)

    doc.build(story)
    buffer.seek(0)

    response = FileResponse(buffer, content_type='application/pdf', as_attachment=False)
    response['Content-Disposition'] = (
        f'inline; filename="bonificacion_{calculo.vendedor.nombrecompleto.replace(" ","_")}_{calculo.id_calculo}.pdf"'
    )
    return response

# -------------------------------------------------------------
# API PARA SERVER-SIDE PROCESSING DE REPORTES
# -------------------------------------------------------------
def api_listar_reportes(request):
    id2 = request.session.get('idtipousuario')
    if not id2:
        return JsonResponse({'error': 'No autorizado'}, status=403)
        
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '').strip()
    estado_filtro = request.GET.get('estado', '')

    calculos_qs = CalculoBonificacion.objects.all().order_by('-fecha_calculo')
    
    if estado_filtro:
        calculos_qs = calculos_qs.filter(estado=estado_filtro)
        
    if search_value:
        q_search = Q(vendedor__nombrecompleto__icontains=search_value) | Q(estado__icontains=search_value)
        calculos_qs = calculos_qs.filter(q_search)
        
    records_total = CalculoBonificacion.objects.count()
    records_filtered = calculos_qs.count()
    
    calculos_page = calculos_qs[start:start+length]
    
    data = []
    for c in calculos_page:
        data.append({
            'DT_RowId': f'row_{c.id_calculo}',
            'vendedor': c.vendedor.nombrecompleto if c.vendedor else 'N/A',
            'periodo': f'{c.fecha_inicio_periodo.strftime("%d/%m/%Y")} - {c.fecha_fin_periodo.strftime("%d/%m/%Y")}',
            'vehiculos': f'{c.total_vehiculos_vendidos} und.',
            'repuestos': float(c.total_repuestos_vendidos),
            'comision_vehiculos': float(c.comision_vehiculos),
            'comision_repuestos': float(c.comision_repuestos),
            'bono_meta': float(c.bono_meta),
            'total_pagar': float(c.total_pagar),
            'estado': c.estado,
            'id_calculo': c.id_calculo
        })
        
    return JsonResponse({
        'draw': int(request.GET.get('draw', 1)),
        'recordsTotal': records_total,
        'recordsFiltered': records_filtered,
        'data': data
    })
