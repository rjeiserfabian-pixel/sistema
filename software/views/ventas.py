from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, FileResponse
from django.db import transaction
from django.db.models import Max, Q
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from io import BytesIO
from software.decorators import requiere_caja_aperturada

from software.models.VentasModel import Ventas
from software.models.VentaDetalleModel import VentaDetalle
from software.models.CuotasVentaModel import CuotasVenta
from software.models.ClienteModel import Cliente
from software.models.TipoIgvModel import TipoIgv
from software.models.SeriecomprobanteModel import Seriecomprobante
from software.models.TipocomprobanteModel import Tipocomprobante
from software.models.FormaPagoModel import FormaPago
from software.models.TipoPagoModel import TipoPago
from software.models.VehiculosModel import Vehiculo
from software.models.ProductoModel import Producto
from software.models.RespuestoCompModel import RepuestoComp
from software.models.RepuestoModel import Repuesto
from software.models.compradetalleModel import CompraDetalle
from software.models.AperturaCierreCajaModel import AperturaCierreCaja
from software.models.UsuarioModel import Usuario
from software.models.stockModel import Stock
from software.models.almacenesModel import Almacenes
from software.models.Tipo_entidadModel import TipoEntidad
from software.models.AuditoriaVentasModel import AuditoriaVentas
from software.models.CreditoModel import Credito
from software.models.movimientoCajaModel import MovimientoCaja
from software.models.PagoCuotaModel import PagoCuota
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos
from software.models.DetallePagoInicialModel import DetallePagoInicial
from software.models.ZonaCreditoModel import ZonaCredito
from software.models.FactorCreditoModel import FactorCredito
from software.models.RegionModel import Region
from software.models.ServicioModel import Servicio


# Listado de ventas
def ventas(request):
    # Obtención del id del tipo de usuario desde la sesión
    id2 = request.session.get('idtipousuario')
    
    if not id2:
        return HttpResponse("<h1>No tiene acceso señor</h1>")
    
    # Validación de permisos
    permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
    
    # ✅ FILTRAR VENTAS POR SUCURSAL Y FECHA
    idusuario = request.session.get('idusuario')
    id_sucursal = request.session.get('id_sucursal')
    es_admin = (id2 == 1)
    
    # Lógica de fechas por defecto (semana actual)
    hoy = datetime.now().date()
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    
    fecha_inicio_str = request.GET.get('fecha_inicio', inicio_semana.strftime('%Y-%m-%d'))
    fecha_fin_str = request.GET.get('fecha_fin', hoy.strftime('%Y-%m-%d'))

    # Preparar kwargs para el filtro de fechas (Optimizando para DateTimeField)
    # 🚀 SERVER-SIDE PROCESSING:
    # Ya no consultamos ventas aquí. Se cargarán vía AJAX (api_listar_ventas)
    ventas_registros = []
    
    # Catálogos relacionados
    clientes = Cliente.objects.filter(estado=1)
    tipo_comprobante = Tipocomprobante.objects.filter(estado=1)
    forma_pago = FormaPago.objects.filter(estado=1)
    tipo_pago = TipoPago.objects.filter(estado=1)
    tipo_igv = TipoIgv.objects.filter(estado=1)
    serie_comprobante = Seriecomprobante.objects.filter(estado=1)
    
    # ✅ OBTENER ALMACÉN DE SESIÓN AL INICIO
    id_almacen_session = request.session.get('id_almacen')

    # ========================================
    # ✅ VEHÍCULOS - OPTIMIZADO (CON FILTRO DE PRE-CRÉDITOS)
    # ========================================
    productos_stock = {}
    
    # 🚗 OBTENER TODOS LOS VEHÍCULOS RESERVADOS EN PRE-FINANCIAMIENTO
    from software.models.PreCreditoModel import PreCredito
    vehiculos_reservados_qs = PreCredito.objects.filter(
        estado__in=['pendiente', 'aprobado']
    ).values_list('detalles_vehiculos__id_vehiculo_id', flat=True)
    
    vehiculos_reservados = set(vehiculos_reservados_qs)
    
    # Si estamos procesando una venta desde un pre-crédito específico, permitimos sus vehículos
    pre_credito_id = request.GET.get('pre_credito_id', '').strip()
    if pre_credito_id:
        try:
            pc = PreCredito.objects.get(pk=int(pre_credito_id))
            for dv in pc.detalles_vehiculos.all():
                if dv.id_vehiculo_id and dv.id_vehiculo_id in vehiculos_reservados:
                    vehiculos_reservados.remove(dv.id_vehiculo_id)
        except Exception:
            pass

    if id_almacen_session:
        stock_vehiculos = Stock.objects.filter(
            id_almacen_id=id_almacen_session,
            estado=1,
            cantidad_disponible__gt=0,
            id_vehiculo__isnull=False,
            id_vehiculo__estado=1,
            id_vehiculo__id_situacion__nombre_situacion__in=['DISPONIBLE', 'RESERVADO (PRE-FINANC.)'],
            id_vehiculo__idproducto__estado=1
        ).select_related(
            'id_vehiculo', 
            'id_vehiculo__idproducto', 
            'idcompradetalle'
        )

        for stock in stock_vehiculos:
            vehiculo = stock.id_vehiculo
            # VERIFICAR SI EL VEHÍCULO ESTÁ RESERVADO
            if vehiculo.id_vehiculo in vehiculos_reservados:
                continue

            detalle_compra = stock.idcompradetalle
            if not detalle_compra:
                # ⚠️ FALLBACK: Buscar por vehículo (para stocks antiguos)
                detalle_compra = CompraDetalle.objects.filter(
                    id_vehiculo=vehiculo
                ).order_by('-idcompradetalle').first()

            if detalle_compra:
                nom_producto = vehiculo.idproducto.nomproducto
                if nom_producto not in productos_stock:
                    productos_stock[nom_producto] = []
                
                productos_stock[nom_producto].append({
                    'id_vehiculo': vehiculo.id_vehiculo,
                    'serie_motor': vehiculo.serie_motor,
                    'serie_chasis': vehiculo.serie_chasis,
                    'precio_minimo': float(detalle_compra.precio_minimo),
                    'precio_maximo': float(detalle_compra.precio_maximo),
                    'precio_compra': float(detalle_compra.precio_compra),
                    'stock_disponible': stock.cantidad_disponible,
                })
    
    # ========================================
    # ✅ REPUESTOS - OPTIMIZADO
    # ========================================
    repuestos_stock = {}
    
    if id_almacen_session:
        stock_repuestos = Stock.objects.filter(
            id_almacen_id=id_almacen_session,
            estado=1,
            cantidad_disponible__gt=0,
            id_repuesto_comprado__isnull=False,
            id_repuesto_comprado__estado=1,
            id_repuesto_comprado__id_repuesto__estado=1
        ).select_related(
            'id_repuesto_comprado',
            'id_repuesto_comprado__id_repuesto',
            'idcompradetalle'
        )

        # --- CORRECCIÓN N+1 y precios en cero ---
        # Recolectar todos los ids de repuesto_comprado presentes en el stock
        todos_ids_rc = [
            s.id_repuesto_comprado_id
            for s in stock_repuestos
            if s.id_repuesto_comprado_id is not None
        ]

        # Una sola query: obtiene el idcompradetalle más reciente por cada RepuestoComp
        ultimo_cd_id_por_rc = dict(
            CompraDetalle.objects.filter(
                id_repuesto_comprado_id__in=todos_ids_rc
            ).values('id_repuesto_comprado_id')
             .annotate(ultimo_id=Max('idcompradetalle'))
             .values_list('id_repuesto_comprado_id', 'ultimo_id')
        )

        # Una sola query: carga los objetos CompraDetalle más recientes en memoria
        ultimos_cd = {}
        if ultimo_cd_id_por_rc:
            for cd in CompraDetalle.objects.filter(
                idcompradetalle__in=ultimo_cd_id_por_rc.values()
            ):
                ultimos_cd[cd.id_repuesto_comprado_id] = cd

        # Lotes sin ningún CompraDetalle: usar precios del catálogo base
        ids_sin_cd_alguno = [rid for rid in todos_ids_rc if rid not in ultimo_cd_id_por_rc]
        catalogo_precios = {}
        if ids_sin_cd_alguno:
            id_repuesto_base_map = dict(
                RepuestoComp.objects.filter(id_repuesto_comprado__in=ids_sin_cd_alguno)
                .values_list('id_repuesto_comprado', 'id_repuesto_id')
            )
            for rep in Repuesto.objects.filter(id_repuesto__in=id_repuesto_base_map.values()):
                for rc_id, rep_id in id_repuesto_base_map.items():
                    if rep_id == rep.id_repuesto:
                        catalogo_precios[rc_id] = rep
        # -----------------------------------------------------------------

        for stock in stock_repuestos:
            repuesto_comp = stock.id_repuesto_comprado
            rc_id = repuesto_comp.id_repuesto_comprado

            # Paso 1: usar el CD vinculado al Stock
            detalle_compra = stock.idcompradetalle

            # Paso 2: si el CD vinculado tiene precios en 0 (o no existe),
            # usar el CD más reciente para ese lote (ya cargado en memoria)
            precios_cero = (
                not detalle_compra or (
                    float(detalle_compra.precio_minimo) == 0 and
                    float(detalle_compra.precio_maximo) == 0
                )
            )
            if precios_cero:
                detalle_compra = ultimos_cd.get(rc_id)

            if detalle_compra and (
                float(detalle_compra.precio_minimo) > 0 or
                float(detalle_compra.precio_maximo) > 0
            ):
                precio_minimo_val = float(detalle_compra.precio_minimo)
                precio_maximo_val = float(detalle_compra.precio_maximo)
                precio_compra_val = float(detalle_compra.precio_compra)
            else:
                # Paso 3: último recurso — precios del catálogo base (Repuesto)
                rep_cat = catalogo_precios.get(rc_id)
                # También intentar con el catálogo del propio repuesto base
                if not rep_cat:
                    rep_cat = repuesto_comp.id_repuesto  # ya cargado por select_related
                precio_minimo_val = float(rep_cat.precio_minimo) if rep_cat else 0
                precio_maximo_val = float(rep_cat.precio_sugerido) if rep_cat else 0
                precio_compra_val = float(rep_cat.costo_unitario) if rep_cat else 0

            nom_repuesto = repuesto_comp.id_repuesto.nombre
            if nom_repuesto not in repuestos_stock:
                repuestos_stock[nom_repuesto] = []

            repuestos_stock[nom_repuesto].append({
                'id_repuesto_comprado': rc_id,
                'codigo_barras': repuesto_comp.id_repuesto.codigo_barras if repuesto_comp.id_repuesto.codigo_barras else 'N/A',
                'ubicacion': repuesto_comp.ubicacion or 'Sin ubicación',
                'precio_minimo': precio_minimo_val,
                'precio_maximo': precio_maximo_val,
                'precio_compra': precio_compra_val,
                'stock_disponible': stock.cantidad_disponible,
            })


    
    # Convertir a JSON para JavaScript
    import json
    productos_stock_json = json.dumps(productos_stock)
    repuestos_stock_json = json.dumps(repuestos_stock)

    # ── Pre-Financiamiento: cargar datos si viene redirigido desde pre-crédito aprobado ──
    pre_credito_data_json = 'null'
    pre_credito_id = request.GET.get('pre_credito_id', '').strip()
    if pre_credito_id:
        try:
            from software.models.PreCreditoModel import PreCredito
            from software.models.stockModel import Stock as _Stock
            pc = PreCredito.objects.select_related(
                'idcliente'
            ).prefetch_related(
                'detalles_vehiculos__id_vehiculo__idproducto'
            ).get(pk=int(pre_credito_id), estado='aprobado')

            # Para la vista antigua, si esperaba un solo vehículo (fallback), devolvemos el primero.
            # Idealmente la vista frontend en ventas debe soportar el array de vehículos que ya preparamos.
            precio_minimo_pc  = 0
            precio_maximo_pc  = 0
            precio_compra_pc = 0
            primer_vehiculo = pc.vehiculos_asociados[0] if pc.vehiculos_asociados else None
            if primer_vehiculo:
                # 1. Intentar obtener desde el stock del almacén actual
                stock_pc = None
                if id_almacen_session:
                    stock_pc = _Stock.objects.filter(
                        id_almacen_id=id_almacen_session,
                        id_vehiculo=primer_vehiculo,
                        estado=1
                    ).select_related('idcompradetalle').first()
                
                # 2. Si no hay stock en el almacén actual o no tiene detalle, buscar el último detalle de compra del vehículo
                detalle_compra = None
                if stock_pc and stock_pc.idcompradetalle:
                    detalle_compra = stock_pc.idcompradetalle
                else:
                    # Fallback: Buscar el último precio registrado para este vehículo
                    detalle_compra = CompraDetalle.objects.filter(
                        id_vehiculo=primer_vehiculo
                    ).order_by('-idcompradetalle').first()

                if detalle_compra:
                    precio_minimo_pc  = float(detalle_compra.precio_minimo)
                    precio_maximo_pc  = float(detalle_compra.precio_maximo)
                    precio_compra_pc = float(detalle_compra.precio_compra)

            pre_credito_data_json = json.dumps({
                'id_pre_credito': pc.id_pre_credito,
                'cliente': {
                    'idcliente':   pc.idcliente.idcliente,
                    'razonsocial': pc.idcliente.razonsocial,
                    'numdoc':      pc.idcliente.numdoc,
                },
                'vehiculos': [{
                    'id_vehiculo':   v.id_vehiculo,
                    'nombre':        v.idproducto.nomproducto if v.idproducto else None,
                    'serie_motor':   v.serie_motor,
                    'serie_chasis':  v.serie_chasis,
                    'precio_minimo':  precio_minimo_pc, # Por simplificación, le asignamos el del primer vehiculo si es que no buscamos uno por uno.
                    'precio_maximo':  precio_maximo_pc,
                    'precio_compra': precio_compra_pc,
                } for v in pc.vehiculos_asociados],
                'monto_inicial': float(pc.monto_inicial),
            })
        except Exception:
            pass  # Si falla silenciosamente, el formulario se abre vacío

    # ── Proformas: cargar datos si viene redirigido desde "Generar Venta" ──
    proforma_data_json = 'null'
    idproforma = request.GET.get('idproforma', '').strip()
    if idproforma:
        try:
            from software.models.ProformaModel import Proforma
            from software.models.ProformaDetalleModel import ProformaDetalle
            from software.models.stockModel import Stock as _Stock
            
            p = Proforma.objects.select_related('idcliente').get(pk=int(idproforma), estado=1)
            
            d_items = ProformaDetalle.objects.filter(idproforma=p).select_related(
                'id_vehiculo__idproducto'
            ).prefetch_related('id_repuesto__stock_set')
            
            detalles_proforma = []
            
            for d in d_items:
                if d.id_vehiculo:
                    # Validar si el vehículo sigue disponible en el almacén actual
                    stock_v = _Stock.objects.filter(
                        id_almacen_id=id_almacen_session,
                        id_vehiculo=d.id_vehiculo,
                        estado=1, cantidad_disponible__gt=0
                    ).first()
                    
                    detalles_proforma.append({
                        'tipo': 'vehiculo',
                        'id_item': d.id_vehiculo.id_vehiculo,
                        'nombre': d.id_vehiculo.idproducto.nomproducto if d.id_vehiculo.idproducto else 'Vehículo',
                        'cantidad': 1,
                        'precio_unitario': float(d.precio_unitario),
                        'subtotal': float(d.subtotal),
                        'disponible': True if stock_v else False
                    })
                elif d.id_repuesto:
                    # Traemos el stock total de este repuesto en el almacén actual
                    # Ya viene cacheado en su mayoría, pero si filtra por almacén específico:
                    stock_r = sum(
                        stk.cantidad_disponible 
                        for stk in d.id_repuesto.stock_set.all() 
                        if stk.id_almacen_id == id_almacen_session and stk.estado == 1
                    )
                    
                    detalles_proforma.append({
                        'tipo': 'repuesto',
                        'id_item': d.id_repuesto.id_repuesto,
                        'nombre': d.id_repuesto.nombre,
                        'cantidad_cotizada': d.cantidad,
                        'cantidad_disponible': stock_r,
                        'precio_unitario': float(d.precio_unitario),
                        'subtotal': float(d.subtotal),
                    })

            proforma_data_json = json.dumps({
                'idproforma': p.idproforma,
                'numero_proforma': p.numero_proforma,
                'cliente': {
                    'idcliente': p.idcliente.idcliente,
                    'razonsocial': p.idcliente.razonsocial,
                    'numdoc': p.idcliente.numdoc,
                } if p.idcliente else None,
                'detalles': detalles_proforma
            })
        except Exception as e:
            print(f"Error cargando proforma: {e}")
            pass

    # Optimización: Obtener lista de vendedores según el rol y la sucursal
    vendedores_filtros = {'estado': 1}
    if id_sucursal:
        vendedores_filtros['id_sucursal_id'] = id_sucursal
        
    if id2 == 6:  # Analista
        vendedores_filtros['idtipousuario'] = 2
        
    vendedores_qs = Usuario.objects.filter(**vendedores_filtros).only('idusuario', 'nombrecompleto')

    # Contexto para el template
    data = {
        'ventas_registros': ventas_registros,
        'clientes': clientes,
        'tipo_comprobante': tipo_comprobante,
        'tipo_igv': tipo_igv,
        'serie_comprobante': serie_comprobante,
        'forma_pago': forma_pago,
        'tipo_pago': tipo_pago,
        'productos_stock': productos_stock_json,
        'repuestos_stock': repuestos_stock_json,
        'idusuario': idusuario,
        'idtipousuario': id2,
        'permisos': permisos,
        'es_admin': es_admin,
        'tipos_entidad': TipoEntidad.objects.filter(estado=1),
        'pre_credito_data': pre_credito_data_json,
        'proforma_data': proforma_data_json,
        'zonas_credito': ZonaCredito.objects.filter(estado=1),
        'regiones': Region.objects.all(),
        'fecha_inicio': fecha_inicio_str,
        'fecha_fin': fecha_fin_str,
        'vendedores': vendedores_qs,
    }

    return render(request, 'ventas/ventas.html', data)

# Obtener series por tipo de comprobante (AJAX)
def obtener_series(request):
    """Obtiene las series disponibles filtradas por tipo de comprobante (AJAX)"""
    if request.method == "GET":
        idtipocomprobante = request.GET.get('idtipocomprobante')
        
        if not idtipocomprobante:
            return JsonResponse({'error': 'Tipo de comprobante no especificado'}, status=400)
        
        try:
            # Filtrar series activas por tipo de comprobante
            series = Seriecomprobante.objects.filter(
                idtipocomprobante=idtipocomprobante,
                estado=1
            ).values(
                'idseriecomprobante',
                'serie',
                'numero_actual'
            ).order_by('serie')
            
            series_list = list(series)
            
            # Agregar información adicional del próximo número
            for s in series_list:
                siguiente_numero = s['numero_actual'] + 1
                s['proximo_numero'] = f"{s['serie']}-{str(siguiente_numero).zfill(8)}"
            
            return JsonResponse({
                'ok': True,
                'series': series_list
            })
        
        except Exception as e:
            return JsonResponse({
                'ok': False,
                'error': f'Error al obtener series: {str(e)}'
            }, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=400)


def obtener_cuotas_por_zona(request):
    """API para obtener las cuotas disponibles según la zona de crédito."""
    if request.method == "GET":
        id_zona = request.GET.get('id_zona')
        if not id_zona:
            return JsonResponse({'ok': False, 'error': 'Falta id_zona'}, status=400)

        try:
            factores = FactorCredito.objects.filter(
                id_zona_id=id_zona,
                estado=1
            ).values('numero_cuotas', 'factor').order_by('numero_cuotas')

            # Renombrar 'numero_cuotas' a 'cuotas' para el frontend si es necesario, 
            # o ajustar el frontend. Ajustaré el frontend para ser consistente.
            return JsonResponse({
                'ok': True,
                'factores': list(factores)
            })
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)}, status=500)
    return JsonResponse({'error': 'Método no permitido'}, status=400)


def obtener_factor_credito(request):
    """API para obtener el factor de crédito según zona y cuotas."""
    if request.method == "GET":
        id_zona = request.GET.get('id_zona')
        cuotas = request.GET.get('cuotas')

        if not id_zona or not cuotas:
            return JsonResponse({'ok': False, 'error': 'Faltan parámetros'}, status=400)

        try:
            factor_obj = FactorCredito.objects.filter(
                id_zona_id=id_zona,
                numero_cuotas=cuotas,
                estado=1
            ).first()

            if factor_obj:
                return JsonResponse({
                    'ok': True,
                    'factor': float(factor_obj.factor)
                })
            else:
                return JsonResponse({
                    'ok': False,
                    'error': 'No se encontró un factor para esta zona y cantidad de cuotas.'
                })

        except Exception as e:
            return JsonResponse({
                'ok': False,
                'error': f'Error al obtener factor: {str(e)}'
            }, status=500)

    return JsonResponse({'error': 'Método no permitido'}, status=400)


def _validar_cabecera_venta(request):
    """
    Valida la cabecera del POST de venta.
    Retorna (JsonResponse de error, None) o (None, dict con valores parseados).
    """
    idcliente_raw = (request.POST.get("cliente") or "").strip()
    idtipocomprobante_raw = (request.POST.get("tipo_comprobante") or "").strip()
    idserie_raw = (request.POST.get("serie") or "").strip()
    fecha_venta_raw = (request.POST.get("fecha_venta") or "").strip()
    forma_pago_raw = (request.POST.get("forma_pago") or "").strip()
    tipo_pago_raw = (request.POST.get("tipo_pago") or "").strip()
    tipo_igv_raw = (request.POST.get("tipo_igv") or "").strip()
    idusuario_raw = (request.POST.get("idusuario") or "").strip()
    if not idusuario_raw:
        idusuario_raw = str(request.session.get('idusuario') or '').strip()

    if not idcliente_raw:
        return JsonResponse({'ok': False, 'error': 'Debe seleccionar un cliente para realizar la venta.'}, status=400), None
    if not idtipocomprobante_raw:
        return JsonResponse({'ok': False, 'error': 'Debe seleccionar un tipo de comprobante.'}, status=400), None
    if not idserie_raw:
        return JsonResponse({'ok': False, 'error': 'Debe seleccionar una serie de comprobante.'}, status=400), None
    if not fecha_venta_raw:
        return JsonResponse({'ok': False, 'error': 'La fecha de venta es obligatoria.'}, status=400), None
    if not forma_pago_raw:
        return JsonResponse({'ok': False, 'error': 'Debe seleccionar una forma de pago.'}, status=400), None
    if not idusuario_raw:
        return JsonResponse({'ok': False, 'error': 'No se encontró usuario para registrar la venta.'}, status=400), None

    try:
        idcliente = int(idcliente_raw)
        idtipocomprobante = int(idtipocomprobante_raw)
        idseriecomprobante = int(idserie_raw)
        id_forma_pago = int(forma_pago_raw)
        idusuario = int(idusuario_raw)
    except ValueError:
        return JsonResponse({'ok': False, 'error': 'Datos numéricos inválidos en la cabecera de venta.'}, status=400), None

    try:
        fecha_seleccionada = datetime.strptime(fecha_venta_raw, '%Y-%m-%d').date()
        # Combinar la fecha elegida con la hora actual de forma segura
        ahora = timezone.now()
        if timezone.is_aware(ahora):
            ahora = timezone.localtime(ahora)
        fecha_venta = ahora.replace(year=fecha_seleccionada.year, month=fecha_seleccionada.month, day=fecha_seleccionada.day)
    except ValueError as e:
        import traceback
        traceback.print_exc()
        print(f"ValueError original: {e}")
        return JsonResponse({'ok': False, 'error': 'La fecha de venta no es válida.'}, status=400), None

    try:
        cliente = Cliente.objects.get(idcliente=idcliente, estado=1)
    except Cliente.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'El cliente seleccionado no existe o está inactivo.'}, status=400), None

    try:
        tipo_comp = Tipocomprobante.objects.get(idtipocomprobante=idtipocomprobante, estado=1)
    except Tipocomprobante.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'El tipo de comprobante seleccionado no existe o está inactivo.'}, status=400), None
    if not Seriecomprobante.objects.filter(idseriecomprobante=idseriecomprobante, estado=1).exists():
        return JsonResponse({'ok': False, 'error': 'La serie seleccionada no existe o está inactiva.'}, status=400), None
    if not FormaPago.objects.filter(id_forma_pago=id_forma_pago, estado=1).exists():
        return JsonResponse({'ok': False, 'error': 'La forma de pago seleccionada no existe o está inactiva.'}, status=400), None

    id_tipo_pago_id = None
    if id_forma_pago == 1:
        tipo_usuario_id = None
        try:
            usu_obj = Usuario.objects.get(idusuario=idusuario)
            tipo_usuario_id = usu_obj.idtipousuario_id
        except:
            pass

        if tipo_usuario_id != 2 and not tipo_pago_raw:
            return JsonResponse({'ok': False, 'error': 'Debe seleccionar un tipo de pago para ventas al contado.'}, status=400), None
            
        if tipo_pago_raw:
            try:
                id_tipo_pago_id = int(tipo_pago_raw)
            except ValueError:
                return JsonResponse({'ok': False, 'error': 'El tipo de pago no es válido.'}, status=400), None
            if not TipoPago.objects.filter(id_tipo_pago=id_tipo_pago_id, estado=1).exists():
                return JsonResponse({'ok': False, 'error': 'El tipo de pago seleccionado no existe o está inactivo.'}, status=400), None
    elif tipo_pago_raw:
        try:
            id_tipo_pago_id = int(tipo_pago_raw)
        except ValueError:
            return JsonResponse({'ok': False, 'error': 'El tipo de pago no es válido.'}, status=400), None
        if not TipoPago.objects.filter(id_tipo_pago=id_tipo_pago_id, estado=1).exists():
            return JsonResponse({'ok': False, 'error': 'El tipo de pago seleccionado no existe o está inactivo.'}, status=400), None

    id_tipo_igv = None
    if tipo_igv_raw:
        try:
            id_tipo_igv = int(tipo_igv_raw)
        except ValueError:
            return JsonResponse({'ok': False, 'error': 'El tipo de IGV no es válido.'}, status=400), None
        if not TipoIgv.objects.filter(id_tipo_igv=id_tipo_igv, estado=1).exists():
            return JsonResponse({'ok': False, 'error': 'El tipo de IGV seleccionado no existe o está inactivo.'}, status=400), None
    else:
        # Asignar por defecto "Exonerado - Operación Onerosa" (ID 9)
        id_tipo_igv = 9

    # VALIDACIÓN SUNAT: Dirección obligatoria para Facturas (RUC)
    if "FACTURA" in tipo_comp.nombre.upper():
        if not cliente.direccion:
            return JsonResponse({'ok': False, 'error': 'La dirección del receptor es obligatoria para Facturas.'}, status=400), None

    return None, {
        'idcliente': idcliente,
        'idtipocomprobante': idtipocomprobante,
        'idseriecomprobante': idseriecomprobante,
        'fecha_venta': fecha_venta,
        'id_forma_pago': id_forma_pago,
        'id_tipo_pago_id': id_tipo_pago_id,
        'id_tipo_igv': id_tipo_igv,
        'idusuario': idusuario,
    }


def _obtener_vehiculo_valido(id_vehiculo):
    """Retorna un vehiculo vendible o None si la referencia esta rota/inactiva."""
    return Vehiculo.objects.filter(
        id_vehiculo=id_vehiculo,
        estado=1,
        idproducto__isnull=False
    ).select_related('idproducto').first()


def _obtener_repuesto_valido(id_repuesto_comprado):
    """Retorna un repuesto comprado vendible o None si la referencia esta rota/inactiva."""
    return RepuestoComp.objects.filter(
        id_repuesto_comprado=id_repuesto_comprado,
        estado=1,
        id_repuesto__isnull=False
    ).select_related('id_repuesto').first()


def _validar_lineas_venta(request, items_count, almacen, id_venta_edicion=None):
    """Valida detalle de venta, tipos de ítem, stock, cantidades y reglas de precio."""
    if items_count < 1:
        return JsonResponse({'ok': False, 'error': 'Debe agregar al menos un producto a la venta.'}, status=400)

    forma_pago = request.POST.get("forma_pago")
    tiene_detalle = False
    vehiculos_en_post = set()
    repuestos_en_post = set()

    for i in range(1, items_count + 1):
        tipo_item = request.POST.get(f"tipo_item_{i}")
        if not tipo_item:
            continue

        if tipo_item not in ("vehiculo", "repuesto", "servicio"):
            return JsonResponse({'ok': False, 'error': f'Ítem {i}: tipo de ítem no válido.'}, status=400)

        try:
            cantidad = int(request.POST.get(f"cantidad_{i}") or 0)
        except ValueError:
            return JsonResponse({'ok': False, 'error': f'Ítem {i}: cantidad inválida.'}, status=400)

        if cantidad <= 0:
            return JsonResponse({'ok': False, 'error': f'Ítem {i}: la cantidad debe ser mayor a cero.'}, status=400)

        try:
            precio_venta_contado = Decimal(request.POST.get(f"precio_venta_contado_{i}") or "0")
            precio_maximo = Decimal(request.POST.get(f"precio_maximo_{i}") or "0")
            precio_compra = Decimal(request.POST.get(f"precio_compra_{i}") or "0")
            precio_credito_raw = (request.POST.get(f"precio_credito_{i}") or "").strip()
            precio_descuento_raw = (request.POST.get(f"precio_descuento_{i}") or "").strip()
            precio_credito = Decimal(precio_credito_raw) if precio_credito_raw else None
            precio_descuento = Decimal(precio_descuento_raw) if precio_descuento_raw else None
        except Exception:
            return JsonResponse({'ok': False, 'error': f'Ítem {i}: formato de precio inválido.'}, status=400)

        if precio_venta_contado <= 0:
            return JsonResponse({
                'ok': False,
                'error': f'Ítem {i}: el precio de venta debe ser mayor a cero.'
            }, status=400)

        if forma_pago == "2":
            if precio_credito is None:
                return JsonResponse({'ok': False, 'error': f'Ítem {i}: debe ingresar el precio a crédito.'}, status=400)

        if forma_pago == "1" and precio_descuento is not None and precio_descuento > 0:
            if precio_descuento < precio_venta_contado:
                return JsonResponse({'ok': False, 'error': f'Ítem {i}: el precio con descuento no puede ser menor al P. Mínimo permitido.'}, status=400)
            if precio_descuento > precio_maximo:
                return JsonResponse({'ok': False, 'error': f'Ítem {i}: el precio con descuento no puede exceder el P. Máximo.'}, status=400)

        if tipo_item == "vehiculo":
            id_vehiculo = (request.POST.get(f"id_vehiculo_{i}") or "").strip()
            if not id_vehiculo:
                return JsonResponse({'ok': False, 'error': f'Ítem {i}: debe seleccionar un vehículo.'}, status=400)
            try:
                id_vehiculo_int = int(id_vehiculo)
            except ValueError:
                return JsonResponse({'ok': False, 'error': f'Ítem {i}: vehículo inválido.'}, status=400)

            # ✅ SI ES EDICIÓN: Si el vehículo ya estaba en la venta, ignoramos validación de stock
            # (El stock ya está reservado por esta venta)
            vehiculo = _obtener_vehiculo_valido(id_vehiculo_int)
            if not vehiculo:
                return JsonResponse({
                    'ok': False,
                    'error': f'Item {i}: el vehiculo seleccionado no existe, esta inactivo o no tiene producto asociado.'
                }, status=400)

            if id_vehiculo_int in vehiculos_en_post:
                return JsonResponse({
                    'ok': False,
                    'error': f'Item {i}: el vehiculo {vehiculo.idproducto.nomproducto} ya fue agregado en esta venta.'
                }, status=400)
            vehiculos_en_post.add(id_vehiculo_int)

            if id_venta_edicion:
                en_venta = VentaDetalle.objects.filter(
                    idventa_id=id_venta_edicion,
                    id_vehiculo_id=id_vehiculo_int,
                    estado=1
                ).first()
                if en_venta:
                    tiene_detalle = True
                    continue # Ya es parte de la venta, no requiere validar stock adicional

            # VALIDAR STOCK EN EL ALMACÉN ACTUAL
            stock = Stock.objects.filter(
                id_almacen=almacen,
                id_vehiculo_id=id_vehiculo_int,
                estado=1
            ).first()

            stock_disponible = stock.cantidad_disponible if stock else 0

            if stock_disponible < cantidad:
                otro_stock = Stock.objects.filter(id_vehiculo_id=id_vehiculo_int, cantidad_disponible__gte=cantidad, estado=1).first()
                if otro_stock:
                    return JsonResponse({
                        'ok': False,
                        'error': f'No hay stock de {vehiculo.idproducto.nomproducto} en su almacén actual. El vehículo se encuentra en {otro_stock.id_almacen.nombre_almacen}.'
                    }, status=400)
                else:
                    return JsonResponse({
                        'ok': False,
                        'error': f'No hay stock suficiente para {vehiculo.idproducto.nomproducto}. Disponible: {stock_disponible}'
                    }, status=400)
        elif tipo_item == "repuesto":
            id_repuesto = (request.POST.get(f"id_repuesto_{i}") or "").strip()
            if not id_repuesto:
                return JsonResponse({'ok': False, 'error': f'Ítem {i}: debe seleccionar un repuesto.'}, status=400)
            try:
                id_repuesto_int = int(id_repuesto)
            except ValueError:
                return JsonResponse({'ok': False, 'error': f'Ítem {i}: repuesto inválido.'}, status=400)

            # ✅ SI ES EDICIÓN: Validamos solo si la cantidad solicitada es mayor a la que ya tenía
            repuesto = _obtener_repuesto_valido(id_repuesto_int)
            if not repuesto:
                return JsonResponse({
                    'ok': False,
                    'error': f'Item {i}: el repuesto seleccionado no existe, esta inactivo o no tiene producto asociado.'
                }, status=400)

            if id_repuesto_int in repuestos_en_post:
                return JsonResponse({
                    'ok': False,
                    'error': f'Item {i}: el repuesto {repuesto.id_repuesto.nombre} ya fue agregado en esta venta.'
                }, status=400)
            repuestos_en_post.add(id_repuesto_int)

            cantidad_validar = cantidad
            if id_venta_edicion:
                en_venta = VentaDetalle.objects.filter(
                    idventa_id=id_venta_edicion,
                    id_repuesto_comprado_id=id_repuesto_int,
                    estado=1
                ).first()
                if en_venta:
                    if cantidad <= en_venta.cantidad:
                        tiene_detalle = True
                        continue # No requiere stock extra
                    cantidad_validar = cantidad - en_venta.cantidad # Solo validamos el excedente

            # VALIDAR STOCK EN EL ALMACÉN ACTUAL (Solo el excedente si es repuesto)
            stock = Stock.objects.filter(
                id_almacen=almacen,
                id_repuesto_comprado_id=id_repuesto_int,
                estado=1
            ).first()

            stock_disponible = stock.cantidad_disponible if stock else 0

            if stock_disponible < cantidad_validar:
                return JsonResponse({
                    'ok': False,
                    'error': f'No hay stock suficiente para {repuesto.id_repuesto.nombre}. Disponible: {stock_disponible}'
                }, status=400)

        elif tipo_item == "servicio":
            id_servicio = (request.POST.get(f"id_servicio_{i}") or "").strip()
            if not id_servicio:
                return JsonResponse({'ok': False, 'error': f'Ítem {i}: debe seleccionar un servicio/trámite.'}, status=400)
            try:
                id_servicio_int = int(id_servicio)
            except ValueError:
                return JsonResponse({'ok': False, 'error': f'Ítem {i}: servicio/trámite inválido.'}, status=400)
                
            from software.models.ServicioModel import Servicio
            servicio = Servicio.objects.filter(id_servicio=id_servicio_int, estado=1).first()
            if not servicio:
                return JsonResponse({'ok': False, 'error': f'Ítem {i}: el servicio/trámite seleccionado no existe o está inactivo.'}, status=400)
                
        tiene_detalle = True

    if not tiene_detalle:
        return JsonResponse({'ok': False, 'error': 'Debe agregar al menos un ítem válido a la venta.'}, status=400)

    return None


def _sincronizar_inventario(id_almacen, tipo_item, id_item, cantidad, operacion):
    """
    Sincroniza el Stock (cantidad_disponible) para Vehículos o Repuestos en un almacén específico.
    operacion: 'REDUCIR' (restar del stock) o 'AUMENTAR' (devolver al stock)
    """
    stock = None
    if tipo_item == 'vehiculo' or tipo_item == 'repuesto':
        filtro = {
            'id_almacen_id': id_almacen,
            'estado': 1
        }
        if tipo_item == 'vehiculo':
            filtro['id_vehiculo_id'] = id_item
        else:
            filtro['id_repuesto_comprado_id'] = id_item
            
        stock = Stock.objects.filter(**filtro).first()
        
    if stock:
        if operacion == 'REDUCIR':
            if not stock.descontar_stock(cantidad):
                nombre = stock.id_vehiculo.idproducto.nomproducto if stock.id_vehiculo else stock.id_repuesto_comprado.id_repuesto.nombre
                raise ValueError(f"No hay stock suficiente para {nombre}. Disponible: {stock.cantidad_disponible}")
        else:
            stock.agregar_stock(cantidad)
    else:
        # Si no existe registro de stock en ese almacén, esto es un error de integridad
        if operacion == 'REDUCIR':
            raise ValueError(f"No se encontró registro de stock para el ítem {id_item} en el almacén especificado.")



def _validar_cuotas_credito_venta(request):
    """Valida configuración de cuotas cuando la venta es a crédito."""
    if request.POST.get("forma_pago") != "2":
        return None
    if request.POST.get("tiene_cuotas") != "1":
        return JsonResponse({'ok': False, 'error': 'Debe configurar las cuotas para ventas a crédito.'}, status=400)

    try:
        cantidad_cuotas = int(request.POST.get("cantidad_cuotas") or 0)
    except ValueError:
        return JsonResponse({'ok': False, 'error': 'La cantidad de cuotas no es válida.'}, status=400)

    if cantidad_cuotas < 1:
        return JsonResponse({'ok': False, 'error': 'Debe configurar al menos una cuota para ventas a crédito.'}, status=400)

    for i in range(1, cantidad_cuotas + 1):
        numero_cuota = (request.POST.get(f"cuota_{i}_numero") or "").strip()
        monto = (request.POST.get(f"cuota_{i}_monto") or "").strip()
        interes = (request.POST.get(f"cuota_{i}_interes") or "").strip()
        total = (request.POST.get(f"cuota_{i}_total") or "").strip()
        tasa = (request.POST.get(f"cuota_{i}_tasa") or "").strip()
        fecha = (request.POST.get(f"cuota_{i}_fecha") or "").strip()

        if not numero_cuota:
            return JsonResponse({'ok': False, 'error': f'Cuota {i}: número de cuota requerido.'}, status=400)
        if not monto or not interes or not total or not tasa:
            return JsonResponse({'ok': False, 'error': f'Cuota {i}: datos incompletos.'}, status=400)

        try:
            Decimal(monto)
            Decimal(interes)
            Decimal(total)
            Decimal(tasa)
        except Exception:
            return JsonResponse({'ok': False, 'error': f'Cuota {i}: montos o tasa inválidos.'}, status=400)

        if fecha:
            try:
                datetime.strptime(fecha, '%Y-%m-%d')
            except ValueError:
                return JsonResponse({'ok': False, 'error': f'Cuota {i}: fecha de vencimiento inválida.'}, status=400)

    return None


# Nueva venta
@requiere_caja_aperturada
def nueva_venta(request):
    if request.method == "POST":
        try:
            # Copiar POST para poder modificarlo
            request.POST = request.POST.copy()
            id_forma_pago_raw = request.POST.get("forma_pago")
            if id_forma_pago_raw == "1":  # Contado
                tipos_pago_ids = request.POST.getlist('tipo_pago_id[]')
                montos_pago = request.POST.getlist('monto_pago[]')
                nros_operacion = request.POST.getlist('nro_operacion[]')

                if tipos_pago_ids:
                    # Calcular total de los pagos recibidos
                    total_recibido = sum(Decimal(m) for m in montos_pago if m)
                    request.POST['importe_recibido'] = str(total_recibido)

                    # Si hay múltiples pagos
                    if len(tipos_pago_ids) > 1:
                        # Buscar tipo de pago 'Múltiple'
                        tp_multiple = TipoPago.objects.filter(nombre__iexact='Múltiple').first()
                        if not tp_multiple:
                            tp_multiple = TipoPago.objects.filter(nombre__icontains='Multip').first()
                        
                        request.POST['tipo_pago'] = str(tp_multiple.id_tipo_pago if tp_multiple else tipos_pago_ids[0])
                        
                        # Generar string de consolidación
                        partes = []
                        for i in range(len(tipos_pago_ids)):
                            tp_id = tipos_pago_ids[i]
                            monto = montos_pago[i]
                            nro = nros_operacion[i] if i < len(nros_operacion) else ''
                            tp_obj = TipoPago.objects.filter(pk=int(tp_id)).first()
                            tp_nombre = tp_obj.nombre if tp_obj else f"Pago {tp_id}"
                            nro_str = f" (Op: {nro})" if nro else ""
                            partes.append(f"{tp_nombre}: S/ {monto}{nro_str}")
                        
                        consolidacion = " | ".join(partes)
                        observaciones_pago = f"[FRACCIONADO: {consolidacion}]"
                        
                        # Agregar a las observaciones
                        user_obs = request.POST.get("observaciones", "")
                        if user_obs:
                            request.POST['observaciones'] = f"{observaciones_pago} {user_obs}"
                        else:
                            request.POST['observaciones'] = observaciones_pago
                    else:
                        # Si solo hay un único pago
                        request.POST['tipo_pago'] = str(tipos_pago_ids[0])
                        nro = nros_operacion[0] if nros_operacion else ''
                        if nro:
                            user_obs = request.POST.get("observaciones", "")
                            obs_pago = f"[Op: {nro}]"
                            if user_obs:
                                request.POST['observaciones'] = f"{obs_pago} {user_obs}"
                            else:
                                request.POST['observaciones'] = obs_pago
            print("=" * 60)
            print("🔍 VALORES EN SESIÓN:")
            print(f"   idusuario: {request.session.get('idusuario')}")
            print(f"   id_sucursal: {request.session.get('id_sucursal')}")
            print(f"   id_almacen: {request.session.get('id_almacen')}")
            print(f"   id_caja: {request.session.get('id_caja')}")
            print("=" * 60)
            print("======= DEBUG POST VENTA =======")
            for k, v in request.POST.items():
                print(f"{k}: {v}")
            print("================================")

            # ⭐ VALIDACIÓN 1: Obtener datos de sesión
            idusuario_session = request.session.get('idusuario')
            id_caja_session = request.session.get('id_caja')
            id_almacen_session = request.session.get('id_almacen')
            id_sucursal_session = request.session.get('id_sucursal')
            
            # Obtener idempresa de la sesión con fallbacks seguros
            idempresa_session = request.session.get('idempresa')
            if not idempresa_session and id_sucursal_session:
                try:
                    from software.models.sucursalesModel import Sucursales
                    sucursal = Sucursales.objects.get(pk=id_sucursal_session)
                    idempresa_session = sucursal.idempresa_id
                except Exception:
                    pass
            if not idempresa_session:
                try:
                    from software.models.empresaModel import Empresa
                    empresa = Empresa.objects.filter(activo=True).first()
                    if empresa:
                        idempresa_session = empresa.idempresa
                except Exception:
                    pass
            
            tipo_usuario_session = request.session.get('idtipousuario')
            
            # Validar que tenga caja seleccionada (excepto si es vendedor)
            if not id_caja_session and tipo_usuario_session != 2:
                return JsonResponse({
                    'ok': False,
                    'error': 'Debe seleccionar una caja en el modal de configuración antes de vender.'
                }, status=400)
            
            # Validar que tenga almacén seleccionado
            if not id_almacen_session:
                return JsonResponse({
                    'ok': False,
                    'error': 'Debe seleccionar un almacén en el modal de configuración antes de vender.'
                }, status=400)
            
            # Validar que tenga sucursal seleccionada
            if not id_sucursal_session:
                return JsonResponse({
                    'ok': False,
                    'error': 'Debe seleccionar una sucursal en el modal de configuración antes de vender.'
                }, status=400)
            
            # ⭐ VALIDACIÓN 2: Verificar que la caja esté aperturada
            apertura = AperturaCierreCaja.objects.filter(
                idusuario_id=idusuario_session,
                id_caja_id=id_caja_session,
                estado__in=['abierta', 'reabierta']
            ).first()
            
            tipo_usuario_session = request.session.get('idtipousuario')
            
            if not apertura and tipo_usuario_session != 2:
                return JsonResponse({
                    'ok': False,
                    'error': 'La caja seleccionada no está aperturada. Por favor, aperture la caja antes de realizar ventas.',
                    'necesita_aperturar': True
                }, status=400)
            
            # ⭐ VALIDACIÓN 3: Verificar usuario
            usuario = Usuario.objects.get(idusuario=idusuario_session)
            
            if not usuario.id_sucursal:
                return JsonResponse({
                    'ok': False,
                    'error': 'Usuario sin sucursal asignada. Contacte al administrador.'
                }, status=400)
            
            # ⭐ VALIDACIÓN 4: Obtener almacén desde la SESIÓN
            try:
                almacen = Almacenes.objects.get(id_almacen=id_almacen_session, estado=1)
            except Almacenes.DoesNotExist:
                return JsonResponse({
                    'ok': False,
                    'error': 'El almacén seleccionado no existe o está inactivo.'
                }, status=400)
            
            # ⭐ VALIDACIÓN 5: Obtener caja desde la SESIÓN
            caja = None
            if tipo_usuario_session != 2:
                try:
                    from software.models.cajaModel import Caja
                    caja = Caja.objects.get(id_caja=id_caja_session, estado=1)
                except Caja.DoesNotExist:
                    return JsonResponse({
                        'ok': False,
                        'error': 'La caja seleccionada no existe o está inactiva.'
                    }, status=400)
            
            # ⭐ VALIDACIÓN 5.5: Validar forma de pago por rol
            tipo_usuario_id = usuario.idtipousuario_id
            id_forma_pago_raw = request.POST.get("forma_pago")
            
            if tipo_usuario_id == 2 and id_forma_pago_raw != "1":
                return JsonResponse({'ok': False, 'error': 'Los vendedores solo pueden realizar ventas al contado.'}, status=400)
            if tipo_usuario_id == 6 and id_forma_pago_raw != "2":
                return JsonResponse({'ok': False, 'error': 'Los analistas solo pueden realizar ventas a crédito.'}, status=400)
            
            # ⭐ VALIDACIÓN 6: Validar cabecera de venta
            err_cabecera, cabecera = _validar_cabecera_venta(request)
            if err_cabecera:
                return err_cabecera

            # ⭐ VALIDACIÓN 7: Validar items de venta
            items = int(request.POST.get("items_count") or 0)
            err_lineas = _validar_lineas_venta(request, items, almacen)
            if err_lineas:
                return err_lineas

            # ⭐ VALIDACIÓN 8: Validar cuotas de crédito (si aplica)
            err_cuotas = _validar_cuotas_credito_venta(request)
            if err_cuotas:
                return err_cuotas
            
            # ✅ Si llegó hasta aquí, todas las validaciones pasaron, continuar con la venta
            
            with transaction.atomic():
                # Obtener datos de cabecera
                idcliente = cabecera['idcliente']
                idusuario = cabecera['idusuario']
                idtipocomprobante = cabecera['idtipocomprobante']
                idseriecomprobante = cabecera['idseriecomprobante']
                fecha_venta = cabecera['fecha_venta']
                id_forma_pago = cabecera['id_forma_pago']
                id_tipo_pago_id = cabecera['id_tipo_pago_id']
                importe_recibido = request.POST.get("importe_recibido")
                vuelto = request.POST.get("vuelto")
                observaciones = request.POST.get("observaciones", "")
                
                # Validación para Contado
                if id_forma_pago == 1:  # Contado
                    if tipo_usuario_id == 2:
                        # Vendedor hace ventas "Pendientes" sin importe recibido al inicio
                        importe_recibido = Decimal('0')
                        vuelto = Decimal('0')
                    else:
                        if not importe_recibido or not vuelto:
                            raise ValueError("Para ventas al contado, debe ingresar el importe recibido y el vuelto.")
                        importe_recibido = Decimal(importe_recibido)
                        vuelto = Decimal(vuelto)
                        if importe_recibido < 0 or vuelto < 0:
                            raise ValueError("El importe recibido y el vuelto no pueden ser negativos.")
                else:
                    importe_recibido = None
                    vuelto = None

                # Obtener serie y generar número de comprobante
                serie = Seriecomprobante.objects.get(idseriecomprobante=idseriecomprobante)
                serie.numero_actual += 1
                numero_comprobante = f"{serie.serie}-{str(serie.numero_actual).zfill(8)}"
                serie.save()
                
                id_tipo_igv = cabecera['id_tipo_igv']
                estado_cobro_val = 'Pendiente' if tipo_usuario_id == 2 else 'Pagado'

                # ✅ Crear venta CON ALMACÉN, CAJA Y SUCURSAL
                venta = Ventas.objects.create(
                    idcliente_id=idcliente,
                    idusuario_id=idusuario,
                    idtipocomprobante_id=idtipocomprobante,
                    idseriecomprobante_id=idseriecomprobante,
                    id_tipo_igv_id=id_tipo_igv,
                    idempresa=idempresa_session,
                    numero_comprobante=numero_comprobante,
                    fecha_venta=fecha_venta,
                    id_forma_pago_id=id_forma_pago,
                    id_tipo_pago_id=id_tipo_pago_id,
                    importe_recibido=importe_recibido,
                    vuelto=vuelto,
                    subtotal=0,
                    total_venta=0,
                    total_ganancia=0,
                    observaciones=observaciones,
                    id_almacen_id=id_almacen_session,
                    id_caja_id=id_caja_session,
                    id_sucursal_id=id_sucursal_session,
                    estado=1,
                    estado_cobro=estado_cobro_val,
                )

                total = Decimal('0')
                total_ganancia = Decimal('0')

                # ✅ Pre-carga de servicios en 1 sola query (evita N+1)
                ids_servicios_form = [
                    int(request.POST.get(f"id_servicio_{i}"))
                    for i in range(1, items + 1)
                    if request.POST.get(f"tipo_item_{i}") == "servicio"
                    and request.POST.get(f"id_servicio_{i}", "").strip()
                ]
                servicios_precargados = {
                    s.id_servicio: s
                    for s in Servicio.objects.filter(id_servicio__in=ids_servicios_form, estado=1)
                } if ids_servicios_form else {}

                # Procesar items del detalle
                for i in range(1, items + 1):
                    tipo_item = request.POST.get(f"tipo_item_{i}")
                    if not tipo_item:
                        continue

                    cantidad = int(request.POST.get(f"cantidad_{i}") or 1)
                    precio_venta_contado = Decimal(request.POST.get(f"precio_venta_contado_{i}") or 0)
                    
                    # ✅ CORREGIDO: Buscar con el nombre correcto del campo
                    precio_credito_str = request.POST.get(f"precio_credito_{i}")
                    precio_venta_credito = Decimal(precio_credito_str) if precio_credito_str and precio_credito_str.strip() else None
                    
                    precio_compra = Decimal(request.POST.get(f"precio_compra_{i}") or 0)
                    precio_maximo = Decimal(request.POST.get(f"precio_maximo_{i}") or 0)
                    
                    # ✅ Obtener precio de descuento (solo contado)
                    precio_descuento_str = request.POST.get(f"precio_descuento_{i}")
                    precio_descuento = Decimal(precio_descuento_str) if precio_descuento_str and precio_descuento_str.strip() else None
                    
                    # ✅ DETERMINAR PRECIO FINAL SEGÚN FORMA DE PAGO
                    if id_forma_pago == 2:  # CRÉDITO
                        if not precio_venta_credito:
                            # Si no se ingresó precio crédito, usamos el P. Máximo como base
                            precio_final = precio_maximo
                        else:
                            precio_final = precio_venta_credito
                    elif id_forma_pago == 1:  # CONTADO
                        if precio_descuento:
                            precio_final = precio_descuento
                        else:
                            # SI NO HAY DESCUENTO, EL PRECIO ES EL P. MÁXIMO
                            precio_final = precio_maximo
                    else:
                        precio_final = precio_maximo
                    
                    subtotal = cantidad * precio_final
                    ganancia = (precio_final - precio_compra) * cantidad

                    if tipo_item == "vehiculo":
                        id_vehiculo = request.POST.get(f"id_vehiculo_{i}", "").strip()
                        
                        if not id_vehiculo:
                            raise ValueError(f"Debe seleccionar un vehículo para el ítem {i}")
                        
                        # ✅ ACTUALIZAR SITUACIÓN SI ES CRÉDITO
                        veh_obj = _obtener_vehiculo_valido(int(id_vehiculo))
                        if not veh_obj:
                            raise ValueError(f"El vehiculo del item {i} no existe, esta inactivo o no tiene producto asociado.")
                        if id_forma_pago == 2: # Crédito
                            from software.models.SituacionVehiculoModel import SituacionVehiculo
                            situ_credito, _ = SituacionVehiculo.objects.get_or_create(nombre_situacion='EN CREDITO', defaults={'estado': 1})
                            veh_obj.id_situacion = situ_credito
                            veh_obj.save()

                        VentaDetalle.objects.create(
                            idventa=venta,
                            tipo_item='vehiculo',
                            id_vehiculo=veh_obj,
                            id_repuesto_comprado=None,
                            cantidad=cantidad,
                            precio_venta_contado=precio_venta_contado,
                            precio_venta_descuento=precio_descuento,
                            precio_venta_credito=precio_venta_credito,
                            precio_maximo=precio_maximo,
                            precio_compra=precio_compra,
                            subtotal=subtotal,
                            ganancia=ganancia,
                            estado=1
                        )
                        # 📦 El stock se reduce automáticamente vía Signal (procesar_venta_detalle)

                    elif tipo_item == "repuesto":
                        id_repuesto = request.POST.get(f"id_repuesto_{i}", "").strip()
                        
                        if not id_repuesto:
                            raise ValueError(f"Debe seleccionar un repuesto para el ítem {i}")    
                        
                        repuesto_obj = _obtener_repuesto_valido(int(id_repuesto))
                        if not repuesto_obj:
                            raise ValueError(f"El repuesto del item {i} no existe, esta inactivo o no tiene producto asociado.")

                        VentaDetalle.objects.create(
                            idventa=venta,
                            tipo_item='repuesto',
                            id_vehiculo=None,
                            id_repuesto_comprado=repuesto_obj,
                            cantidad=cantidad,
                            precio_venta_contado=precio_venta_contado,
                            precio_venta_descuento=precio_descuento,
                            precio_venta_credito=precio_venta_credito,
                            precio_maximo=precio_maximo,
                            precio_compra=precio_compra,
                            subtotal=subtotal,
                            ganancia=ganancia,
                            estado=1
                        )
                        # 📦 El stock se reduce automáticamente vía Signal (procesar_venta_detalle)

                    elif tipo_item == "servicio":
                        id_serv = request.POST.get(f"id_servicio_{i}", "").strip()
                        if not id_serv:
                            raise ValueError(f"Debe seleccionar un servicio/trámite para el ítem {i}")
                        
                        # ✅ Usa el diccionario precargado (0 queries extra)
                        servicio_obj = servicios_precargados.get(int(id_serv))
                        if not servicio_obj:
                            raise ValueError(f"El servicio del ítem {i} no existe o está inactivo.")

                        # Para servicios: precio = precio_venta_contado enviado desde el frontend
                        precio_serv = Decimal(request.POST.get(f"precio_venta_contado_{i}") or servicio_obj.precio_defecto)
                        subtotal_serv = cantidad * precio_serv
                        ganancia_serv = subtotal_serv  # ganancia total = lo cobrado

                        VentaDetalle.objects.create(
                            idventa=venta,
                            tipo_item='servicio',
                            id_vehiculo=None,
                            id_repuesto_comprado=None,
                            id_servicio=servicio_obj,
                            cantidad=cantidad,
                            precio_venta_contado=precio_serv,
                            precio_venta_descuento=None,
                            precio_venta_credito=None,
                            precio_maximo=precio_serv,
                            precio_compra=Decimal('0'),
                            subtotal=subtotal_serv,
                            ganancia=ganancia_serv,
                            estado=1
                        )
                        # Los servicios NO afectan inventario
                        subtotal = subtotal_serv
                        ganancia = ganancia_serv

                    total += subtotal
                    total_ganancia += ganancia

                # Calcular IGV y Totales
                tipo_igv_obj = TipoIgv.objects.get(id_tipo_igv=id_tipo_igv)
                
                # Si es Gravado (códigos 10 al 17)
                if tipo_igv_obj.codigo in [10, 11, 12, 13, 14, 15, 16, 17]:
                    monto_igv = Decimal(total) * Decimal('0.18')
                else:
                    monto_igv = Decimal('0')
                
                total_venta_final = total + monto_igv

                # Actualizar totales de la venta
                venta.subtotal = total
                venta.igv = monto_igv
                venta.total_venta = total_venta_final
                venta.total_ganancia = total_ganancia

                if id_forma_pago == 1 and tipo_usuario_id != 2 and importe_recibido < total_venta_final:
                    raise ValueError("El importe recibido debe ser mayor o igual al total de la venta.")

                venta.save()
                
                # Reasignar total para que los cálculos de crédito (si los hay) usen el total con IGV
                total = total_venta_final
                
                # ========================================
                # ✅ COMPLETAR PRE-CRÉDITO (SI APLICA)
                # ========================================
                id_pre_credito = request.POST.get("id_pre_credito")
                if id_pre_credito:
                    from software.models.PreCreditoModel import PreCredito
                    try:
                        pc = PreCredito.objects.get(pk=int(id_pre_credito))
                        pc.estado = 'completado'
                        pc.save()
                        print(f"✅ PRE-CRÉDITO {id_pre_credito} MARCADO COMO COMPLETADO")
                    except Exception as e:
                        print(f"Error actualizando pre-crédito {id_pre_credito}: {e}")


                print(f"💰 TOTALES CALCULADOS:")
                print(f"   Forma de pago: {id_forma_pago} ({'CRÉDITO' if id_forma_pago == 2 else 'CONTADO'})")
                print(f"   Total venta: S/ {total}")
                print(f"   Total ganancia: S/ {total_ganancia}")

                # ========================================
                # ✅ GUARDAR CUOTAS Y CREAR CRÉDITO SI ES VENTA A CRÉDITO
                # ========================================
                if id_forma_pago == 2 and request.POST.get("tiene_cuotas") == "1":
                    cantidad_cuotas = int(request.POST.get("cantidad_cuotas") or 0)
                    
                    if cantidad_cuotas > 0:
                        # ✅ OBTENER DATOS DE CRÉDITO
                        monto_adelanto_str = request.POST.get("monto_adelanto")
                        monto_adelanto = Decimal(monto_adelanto_str) if monto_adelanto_str and monto_adelanto_str.strip() else Decimal('0')
                        
                        tasa_interes_str = request.POST.get("tasa_interes")
                        tasa_interes = Decimal(tasa_interes_str) if tasa_interes_str else Decimal('0')
                        
                        tipo_periodo = request.POST.get("tipo_periodo", "dias")
                        
                        # ✅ CALCULAR SALDO A FINANCIAR
                        saldo_financiar = total - monto_adelanto
                        
                        print(f"📊 DATOS DE CRÉDITO:")
                        print(f"   Total venta (con precio crédito): S/ {total}")
                        print(f"   Monto adelanto: S/ {monto_adelanto}")
                        print(f"   Saldo a financiar: S/ {saldo_financiar}")
                        print(f"   Cantidad cuotas: {cantidad_cuotas}")
                        print(f"   Tasa interés: {tasa_interes}%")
                        
                        # ✅ GENERAR CÓDIGO DE CRÉDITO ÚNICO (formato CR-YYYYMMDD-NNN)
                        # Cuenta solo créditos de venta (no directos) del día actual
                        _hoy_cr = venta.fecha_venta
                        _intento = 0
                        while True:
                            _count_cr = Credito.objects.filter(
                                fecha_credito__date=_hoy_cr.date(),
                                es_directo=False
                            ).count() + 1 + _intento
                            codigo_credito = f"CR-{_hoy_cr.strftime('%Y%m%d')}-{_count_cr:03d}"
                            if not Credito.objects.filter(codigo_credito=codigo_credito).exists():
                                break
                            _intento += 1
                        
                        # ✅ CREAR EL CRÉDITO
                        credito = Credito.objects.create(
                            codigo_credito=codigo_credito,
                            idventa=venta,
                            monto_total=total,  # ⭐ TOTAL CON PRECIO CRÉDITO
                            monto_adelanto=monto_adelanto,  # ⭐ MONTO INICIAL (Cuota 0)
                            saldo_pendiente=saldo_financiar,  # ⭐ SALDO A FINANCIAR (cuotas 1..N)
                            cantidad_cuotas=cantidad_cuotas,  # Cantidad de cuotas regulares (sin contar cuota 0)
                            fecha_credito=venta.fecha_venta,
                            estado_credito='activo',
                            estado=1
                        )
                        
                        print(f"✅ CRÉDITO CREADO - ID: {credito.idcredito}, Código: {codigo_credito}")
                        
                        # ⭐ CREAR CUOTA 0 (Monto Inicial) si el usuario ingresó un monto
                        if monto_adelanto > Decimal('0'):
                            fecha_cuota_0_str = request.POST.get("cuota_0_fecha", "").strip()
                            if fecha_cuota_0_str:
                                try:
                                    fecha_cuota_0 = datetime.strptime(fecha_cuota_0_str, '%Y-%m-%d').date()
                                except ValueError:
                                    fecha_cuota_0 = fecha_venta  # fallback a fecha de venta
                            else:
                                fecha_cuota_0 = fecha_venta  # por defecto: fecha de la venta
                            
                            # ✅ REGLA DE NEGOCIO: Si viene de pre-financiamiento, evaluar lo que realmente pagó
                            monto_pagado = Decimal('0')
                            saldo_cuota = monto_adelanto
                            fecha_pago = None
                            estado_pago = 'Pendiente'
                            
                            if id_pre_credito:
                                try:
                                    from software.models.PreCreditoModel import PreCredito
                                    pc_obj_for_calc = PreCredito.objects.get(pk=int(id_pre_credito))
                                    
                                    # Solo sumar si ya fue cobrado en la caja
                                    if pc_obj_for_calc.cobrado:
                                        monto_pc_pagado = Decimal(str(pc_obj_for_calc.monto_inicial))
                                    else:
                                        monto_pc_pagado = Decimal('0')
                                    
                                    monto_pagado = min(monto_pc_pagado, monto_adelanto)
                                    saldo_cuota = monto_adelanto - monto_pagado
                                    
                                    if saldo_cuota <= 0:
                                        fecha_pago = timezone.now()
                                        estado_pago = 'Pagado'
                                    elif monto_pagado > 0:
                                        estado_pago = 'Parcial'
                                except Exception as e:
                                    print(f"Error calculando saldo de inicial de Pre-Credito: {e}")

                            cuota_0 = CuotasVenta.objects.create(
                                idventa=venta,
                                idcredito=credito,        # ✅ Vincular al crédito
                                numero_cuota=0,           # ⭐ Cuota 0 = Monto Inicial
                                monto=monto_adelanto,
                                tasa=Decimal('0'),
                                interes=Decimal('0'),
                                total=monto_adelanto,
                                fecha_vencimiento=fecha_cuota_0,
                                monto_adelanto=monto_adelanto,
                                monto_pagado=monto_pagado,
                                saldo_cuota=saldo_cuota,
                                fecha_pago=fecha_pago,
                                estado_pago=estado_pago,
                                estado=1
                            )
                            print(f"  Cuota 0 (Monto Inicial): S/ {monto_adelanto}, vence={fecha_cuota_0}, estado={estado_pago}")
                            
                            # ✅ REGISTRAR PAGOS EN EL HISTORIAL (Solo para pre-financiamiento)
                            if id_pre_credito:
                                try:
                                    from software.models.PreCreditoModel import PreCredito
                                    pc_obj = PreCredito.objects.get(pk=int(id_pre_credito))
                                    
                                    if pc_obj.cobrado:
                                        detalles_pc = pc_obj.detalles_pago.all()
                                        
                                        if detalles_pc.count() > 1:
                                            # 🔄 CONSOLIDACIÓN DE PAGOS MIXTOS (NUEVA LÓGICA)
                                            monto_total_pc = sum(d.monto for d in detalles_pc)
                                            resumen_metodos = " | ".join([f"{d.id_tipo_pago.nombre}: S/ {d.monto}" + (f" (Op:{d.numero_operacion})" if d.numero_operacion else "") for d in detalles_pc])
                                            
                                            # Buscar el tipo de pago 'Múltiple'
                                            tp_multiple = TipoPago.objects.filter(nombre__iexact='Múltiple').first()
                                            if not tp_multiple:
                                                tp_multiple = TipoPago.objects.filter(nombre__icontains='Multip').first()
                                            
                                            PagoCuota.objects.create(
                                                idcuotaventa=cuota_0,
                                                idusuario_id=idusuario,
                                                id_tipo_pago=tp_multiple if tp_multiple else detalles_pc[0].id_tipo_pago,
                                                monto_pago=monto_total_pc,
                                                numero_operacion="Múltiple",
                                                observaciones=f"Pago inicial (Multipago) transferido desde Pre-Crédito #{id_pre_credito} [{resumen_metodos}]",
                                                estado=1
                                            )
                                            print(f"    → Pago inicial consolidado (Múltiple) por S/ {monto_total_pc}")
                                        else:
                                            # Pago único (Lógica original)
                                            for det in detalles_pc:
                                                PagoCuota.objects.create(
                                                    idcuotaventa=cuota_0,
                                                    idusuario_id=idusuario,
                                                    id_tipo_pago=det.id_tipo_pago,
                                                    monto_pago=det.monto,
                                                    numero_operacion=det.numero_operacion,
                                                    observaciones=f"Pago inicial transferido desde Pre-Crédito #{id_pre_credito}",
                                                    estado=1
                                                )
                                            print(f"    → {detalles_pc.count()} registro de pago creado en el historial.")
                                except Exception as e_pago:
                                    print(f"    ⚠️ Error al registrar historial de pago de inicial: {e_pago}")
                        
                        # ✅ GUARDAR CUOTAS EN CuotasVenta
                        print(f"📅 Guardando {cantidad_cuotas} cuotas en CuotasVenta...")
                        
                        suma_total_cuotas = Decimal('0')
                        suma_capital_cuotas = Decimal('0')
                        
                        for i in range(1, cantidad_cuotas + 1):
                            numero_cuota_str = request.POST.get(f"cuota_{i}_numero")
                            fecha_venc_str = request.POST.get(f"cuota_{i}_fecha")
                            monto_cuota_str = request.POST.get(f"cuota_{i}_monto")
                            interes_cuota_str = request.POST.get(f"cuota_{i}_interes")
                            total_cuota_str = request.POST.get(f"cuota_{i}_total")
                            tasa_cuota_str = request.POST.get(f"cuota_{i}_tasa")
                            
                            # Convertir a los tipos correctos
                            numero_cuota = int(numero_cuota_str) if numero_cuota_str else i
                            monto_cuota = Decimal(monto_cuota_str) if monto_cuota_str else Decimal('0')
                            interes_cuota = Decimal(interes_cuota_str) if interes_cuota_str else Decimal('0')
                            total_cuota = Decimal(total_cuota_str) if total_cuota_str else (monto_cuota + interes_cuota)
                            tasa_cuota = Decimal(tasa_cuota_str) if tasa_cuota_str else tasa_interes
                            
                            suma_capital_cuotas += monto_cuota
                            suma_total_cuotas += total_cuota
                            
                            # Parsear fecha
                            if fecha_venc_str:
                                fecha_vencimiento = datetime.strptime(fecha_venc_str, '%Y-%m-%d').date()
                            else:
                                fecha_base = fecha_venta if hasattr(fecha_venta, "year") else datetime.strptime(fecha_venta, "%Y-%m-%d").date()
                                fecha_vencimiento = fecha_base + timedelta(days=30 * i)
                            
                            # ✅ CREAR CUOTA en CuotasVenta
                            cuota = CuotasVenta.objects.create(
                                idventa=venta,
                                idcredito=credito, # ✅ Vincular al crédito
                                numero_cuota=numero_cuota,
                                monto=monto_cuota,  # Capital de la cuota (sin interés)
                                tasa=tasa_cuota,
                                interes=interes_cuota,
                                total=total_cuota,  # Capital + interés
                                fecha_vencimiento=fecha_vencimiento,
                                monto_adelanto=monto_adelanto if i == 1 else Decimal('0'),  # Solo en primera cuota
                                monto_pagado=Decimal('0'),
                                saldo_cuota=total_cuota,  # Inicialmente, saldo = total
                                fecha_pago=None,
                                estado_pago='Pendiente',
                                estado=1
                            )
                            
                            print(f"  Cuota {numero_cuota}: capital=S/ {monto_cuota}, interés=S/ {interes_cuota}, total=S/ {total_cuota}, vence={fecha_vencimiento}")
                        
                        # ✅ VALIDAR QUE LA SUMA DE CUOTAS (TOTAL) COINCIDA CON EL SALDO A FINANCIAR
                        diferencia_total = abs(suma_total_cuotas - saldo_financiar)
                        
                        print(f"\n📊 RESUMEN DE CUOTAS:")
                        print(f"   Suma capital cuotas: S/ {suma_capital_cuotas}")
                        print(f"   Suma total cuotas: S/ {suma_total_cuotas}")
                        print(f"   Saldo a financiar (Total con interés): S/ {saldo_financiar}")
                        print(f"   Diferencia: S/ {diferencia_total}")
                        
                        if diferencia_total > Decimal('0.05'):  # Tolerancia de 5 centavos
                            print(f"⚠️ ADVERTENCIA: Diferencia total mayor a tolerancia")
                        else:
                            print(f"✅ Cuotas correctas (diferencia dentro de tolerancia)")
                        
                        print(f"\n✅ RESUMEN CRÉDITO COMPLETO:")
                        print(f"   Código: {codigo_credito}")
                        print(f"   Sucursal: {venta.id_sucursal.nombre_sucursal if venta.id_sucursal else 'N/A'}")
                        print(f"   Almacén: {almacen.nombre_almacen}")
                        print(f"   Caja: {caja.nombre_caja}")
                        print(f"   Total venta: S/ {total}")
                        print(f"   Adelanto: S/ {monto_adelanto}")
                        print(f"   Saldo a financiar: {saldo_financiar}")
                        print(f"   Cantidad cuotas: {cantidad_cuotas}")
                        print(f"   Tasa interés: {tasa_interes}%")

                        # ========================================
                        # ✅ ACTUALIZAR PROFORMA A CONVERTIDA
                        # ========================================
                        idproforma_origen = request.POST.get("idproforma_origen")
                        if idproforma_origen:
                            try:
                                from software.models.ProformaModel import Proforma
                                p_origen = Proforma.objects.get(pk=int(idproforma_origen))
                                p_origen.estado = 2  # Convertida
                                p_origen.save()
                                print(f"✅ PROFORMA {idproforma_origen} MARCADA COMO CONVERTIDA")
                            except Exception as e:
                                print(f"Error actualizando proforma {idproforma_origen}: {e}")

                        return JsonResponse({
                            'ok': True,
                            'message': 'Venta a crédito registrada correctamente.',
                            'numero_comprobante': numero_comprobante,
                            'codigo_credito': codigo_credito,
                            'idventa': venta.idventa,
                            'total_venta': float(total),
                            'monto_adelanto': float(monto_adelanto),
                            'saldo_financiar': float(saldo_financiar),
                            'es_credito': True
                        })

                # ========================================
                # SI ES VENTA AL CONTADO
                # ========================================
                if estado_cobro_val == 'Pagado':
                    print(f"✅ VENTA AL CONTADO REGISTRADA - ID: {venta.idventa}")
                    print(f"   Sucursal: {venta.id_sucursal.nombre_sucursal if venta.id_sucursal else 'N/A'}")
                    print(f"   Almacén: {almacen.nombre_almacen}")
                    print(f"   Caja: {caja.nombre_caja}")
                    print(f"   Total: S/ {venta.total_venta}")
                    
                    descripcion_movimiento = f"Venta {numero_comprobante} - Cliente: {venta.idcliente.razonsocial}"
                    
                    movimiento_caja = MovimientoCaja.objects.create(
                        id_caja=caja,
                        id_movimiento=apertura,  # ✅ Asociar a la apertura actual
                        idusuario=usuario,
                        tipo_movimiento='ingreso',
                        monto=total,
                        descripcion=descripcion_movimiento,
                        idventa=venta,
                        estado=1
                    )
                    
                    print(f"✅ MOVIMIENTO DE CAJA CREADO - ID: {movimiento_caja.id_movimiento_caja}")
                    print(f"   Asociado a apertura: {apertura.id_movimiento}")
                    print(f"   Monto ingreso: S/ {total}")
                else:
                    print(f"✅ VENTA AL CONTADO REGISTRADA (PENDIENTE DE COBRO) - ID: {venta.idventa}")

                # ========================================
                # ✅ ACTUALIZAR PROFORMA A CONVERTIDA
                # ========================================
                idproforma_origen = request.POST.get("idproforma_origen")
                if idproforma_origen:
                    try:
                        from software.models.ProformaModel import Proforma
                        p_origen = Proforma.objects.get(pk=int(idproforma_origen))
                        p_origen.estado = 2  # Convertida
                        p_origen.save()
                        print(f"✅ PROFORMA {idproforma_origen} MARCADA COMO CONVERTIDA")
                    except Exception as e:
                        print(f"Error actualizando proforma {idproforma_origen}: {e}")

                return JsonResponse({
                    'ok': True,
                    'message': 'Venta registrada correctamente.',
                    'numero_comprobante': numero_comprobante,
                    'idventa': venta.idventa,
                    'es_credito': False
                })
        except ValueError as ve:
            print(f"ERROR DE VALIDACIÓN: {str(ve)}")
            return JsonResponse({
                'ok': False,
                'error': str(ve)
            })
        except Exception as e:
            print(f"ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'ok': False,
                'error': f'Error al procesar la venta: {str(e)}'
            })

    return redirect("ventas")


# ==================== COBRAR VENTA PENDIENTE ====================
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def cobrar_venta_pendiente(request):
    if request.method == "POST":
        try:
            idusuario_session = request.session.get('idusuario')
            if not idusuario_session:
                return JsonResponse({'ok': False, 'error': 'Sesión expirada.'}, status=401)
                
            usuario = Usuario.objects.get(idusuario=idusuario_session)
            if usuario.idtipousuario_id not in [1, 3, 5, 6]:
                return JsonResponse({'ok': False, 'error': 'No tiene permisos para cobrar ventas.'}, status=403)

            id_caja_session = request.session.get('id_caja')
            if not id_caja_session:
                return JsonResponse({'ok': False, 'error': 'Debe seleccionar una caja en configuración.'}, status=400)
                
            from software.models.AperturaCierreCajaModel import AperturaCierreCaja
            apertura = AperturaCierreCaja.objects.filter(
                idusuario_id=idusuario_session,
                id_caja_id=id_caja_session,
                estado__in=['abierta', 'reabierta']
            ).first()
            if not apertura:
                return JsonResponse({'ok': False, 'error': 'La caja no está aperturada.'}, status=400)

            idventa = request.POST.get("idventa")
            
            tipos_pago_ids = request.POST.getlist('tipo_pago_id[]')
            montos_pago = request.POST.getlist('monto_pago[]')
            nros_operacion = request.POST.getlist('nro_operacion[]')

            if not tipos_pago_ids:
                return JsonResponse({'ok': False, 'error': 'No se especificaron métodos de pago.'}, status=400)

            total_recibido = sum(Decimal(m) for m in montos_pago if m)

            with transaction.atomic():
                venta = Ventas.objects.select_for_update().get(idventa=idventa, estado=1)
                
                if getattr(venta, 'estado_cobro', '') == 'Pagado':
                    return JsonResponse({'ok': False, 'error': 'Esta venta ya ha sido cobrada.'}, status=400)
                
                if total_recibido < venta.total_venta:
                    return JsonResponse({'ok': False, 'error': 'El importe recibido es menor al total.'}, status=400)

                # Si hay múltiples pagos
                if len(tipos_pago_ids) > 1:
                    tp_multiple = TipoPago.objects.filter(nombre__iexact='Múltiple').first()
                    if not tp_multiple:
                        tp_multiple = TipoPago.objects.filter(nombre__icontains='Multip').first()
                    
                    venta.id_tipo_pago_id = tp_multiple.id_tipo_pago if tp_multiple else int(tipos_pago_ids[0])
                    
                    # Generar string de consolidación
                    partes = []
                    for i in range(len(tipos_pago_ids)):
                        tp_id = tipos_pago_ids[i]
                        monto = montos_pago[i]
                        nro = nros_operacion[i] if i < len(nros_operacion) else ''
                        tp_obj = TipoPago.objects.filter(pk=int(tp_id)).first()
                        tp_nombre = tp_obj.nombre if tp_obj else f"Pago {tp_id}"
                        nro_str = f" (Op: {nro})" if nro else ""
                        partes.append(f"{tp_nombre}: S/ {monto}{nro_str}")
                    
                    consolidacion = " | ".join(partes)
                    observaciones_pago = f"[FRACCIONADO: {consolidacion}]"
                    
                    obs = venta.observaciones or ""
                    venta.observaciones = f"{obs} {observaciones_pago}".strip()
                else:
                    # Si solo hay un único pago
                    venta.id_tipo_pago_id = int(tipos_pago_ids[0])
                    nro = nros_operacion[0] if nros_operacion else ''
                    if nro:
                        obs = venta.observaciones or ""
                        venta.observaciones = f"{obs} [Cobro Op: {nro}]".strip()

                # Actualizar datos de pago
                venta.importe_recibido = total_recibido
                venta.vuelto = total_recibido - venta.total_venta
                venta.estado_cobro = 'Pagado'
                venta.save()
                
                from software.models.cajaModel import Caja
                caja = Caja.objects.get(id_caja=id_caja_session)
                descripcion = f"Cobro de Venta Pendiente {venta.numero_comprobante} - Cliente: {venta.idcliente.razonsocial if venta.idcliente else ''}"
                
                MovimientoCaja.objects.create(
                    id_caja=caja,
                    id_movimiento=apertura,
                    idusuario=usuario,
                    tipo_movimiento='ingreso',
                    monto=venta.total_venta,
                    descripcion=descripcion,
                    idventa=venta,
                    estado=1
                )
                
            return JsonResponse({'ok': True, 'message': 'Cobro registrado correctamente.', 'idventa': venta.idventa})
            
        except Ventas.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'Venta no encontrada o anulada.'}, status=404)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'ok': False, 'error': str(e)}, status=500)
    return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)


# ==================== OBTENER VENTA PARA EDICIÓN ====================
def obtener_venta(request, id):
    """Obtiene los datos de una venta para edición (AJAX)"""
    try:
        venta = Ventas.objects.get(idventa=id, estado=1)
        es_credito = venta.id_forma_pago.id_forma_pago == 2

        # ✅ REGLA DE NEGOCIO: Si es crédito, verificar si ya hay algún pago registrado
        if es_credito:
            print(f"\n{'='*60}")
            print(f"🔍 [obtener_venta] Venta ID={id} ES CRÉDITO → verificando pagos...")

            # Check 1: monto_pagado > 0 en alguna cuota
            cuotas_con_pago = CuotasVenta.objects.filter(
                idventa=venta,
                estado=1,
                monto_pagado__gt=0
            )
            tiene_pagos_cuota = cuotas_con_pago.exists()
            print(f"   Check monto_pagado>0 en CuotasVenta: {tiene_pagos_cuota}")
            if tiene_pagos_cuota:
                for c in cuotas_con_pago:
                    print(f"     → Cuota #{c.numero_cuota}: monto_pagado={c.monto_pagado}")

            # Check 2: registros activos en PagoCuota
            pagos_reales = PagoCuota.objects.filter(
                idcuotaventa__idventa=venta,
                estado=1
            )
            tiene_pagos_reales = pagos_reales.exists()
            print(f"   Check PagoCuota activos: {tiene_pagos_reales} ({pagos_reales.count()} registros)")
            print(f"{'='*60}\n")

            tiene_pagos = tiene_pagos_cuota or tiene_pagos_reales

            bloqueo_parcial = False
            if tiene_pagos:
                if request.session.get('idtipousuario') == 1:
                    bloqueo_parcial = True
                else:
                    return JsonResponse({
                        'success': False,
                        'error': 'No se puede editar esta venta a crédito porque ya registra pagos o abonos realizados.',
                        'codigo': 'VENTA_CON_PAGOS_NO_EDITABLE'
                    }, status=400)
            else:
                bloqueo_parcial = False
        detalles = VentaDetalle.objects.filter(idventa=venta, estado=1).select_related(
            'id_vehiculo__idproducto',
            'id_vehiculo__idestadoproducto',
            'id_repuesto_comprado__id_repuesto'
        )

        # Formatear detalles
        detalles_list = []
        for d in detalles:
            if d.tipo_item == 'vehiculo' and d.id_vehiculo:
                detalles_list.append({
                    'idventadetalle': d.idventadetalle,
                    'tipo': 'vehiculo',
                    'id_vehiculo': d.id_vehiculo.id_vehiculo,
                    'nombre_producto': d.id_vehiculo.idproducto.nomproducto,
                    'serie_motor': d.id_vehiculo.serie_motor or '',
                    'serie_chasis': d.id_vehiculo.serie_chasis or '',
                    'placas': getattr(d.id_vehiculo, 'placas', '') or '',
                    'estado_producto': d.id_vehiculo.idestadoproducto.nombreestadoproducto if d.id_vehiculo.idestadoproducto else '',
                    'cantidad': d.cantidad,
                    'precio_compra': float(d.precio_compra),
                    'precio_venta_contado': float(d.precio_venta_contado),
                    'precio_maximo': float(d.precio_maximo) if d.precio_maximo else float(d.precio_venta_contado),
                    'p_max_seguro': float(d.precio_maximo) if d.precio_maximo else float(d.precio_venta_contado),
                    'precio_venta_descuento': float(d.precio_venta_descuento or 0),
                    'precio_venta_credito': float(d.precio_venta_credito) if d.precio_venta_credito else 0,
                    'subtotal': float(d.subtotal),
                    'ganancia': float(d.ganancia)
                })
            elif d.tipo_item == 'repuesto' and d.id_repuesto_comprado:
                detalles_list.append({
                    'idventadetalle': d.idventadetalle,
                    'tipo': 'repuesto',
                    'id_repuesto_comprado': d.id_repuesto_comprado.id_repuesto_comprado,
                    'nombre_repuesto': d.id_repuesto_comprado.id_repuesto.nombre,
                    'codigo_barras': d.id_repuesto_comprado.id_repuesto.codigo_barras or '',
                    'cantidad': d.cantidad,
                    'precio_compra': float(d.precio_compra),
                    'precio_venta_contado': float(d.precio_venta_contado),
                    'precio_maximo': float(d.precio_maximo) if d.precio_maximo else float(d.precio_venta_contado),
                    'p_max_seguro': float(d.precio_maximo) if d.precio_maximo else float(d.precio_venta_contado),
                    'precio_venta_descuento': float(d.precio_venta_descuento or 0),
                    'precio_venta_credito': float(d.precio_venta_credito) if d.precio_venta_credito else 0,
                    'subtotal': float(d.subtotal),
                    'ganancia': float(d.ganancia)
                })

        # ✅ Si es crédito, incluir datos del crédito y cuotas
        credito_data = None
        cuotas_list = []
        if es_credito:
            credito = Credito.objects.filter(idventa=venta, estado=1).first()
            if credito:
                credito_data = {
                    'idcredito': credito.idcredito,
                    'codigo_credito': credito.codigo_credito,
                    'monto_total': float(credito.monto_total or 0),
                    'monto_adelanto': float(credito.monto_adelanto or 0),
                    'saldo_pendiente': float(credito.saldo_pendiente or 0),
                    'cantidad_cuotas': int(credito.cantidad_cuotas or 0),
                    'estado_credito': credito.estado_credito,
                }
            cuotas = CuotasVenta.objects.filter(idventa=venta, estado=1).order_by('numero_cuota')
            for cuota in cuotas:
                cuotas_list.append({
                    'numero_cuota': cuota.numero_cuota,
                    'fecha_vencimiento': cuota.fecha_vencimiento.strftime('%Y-%m-%d') if cuota.fecha_vencimiento else None,
                    'monto': float(cuota.monto or 0),
                    'tasa': float(cuota.tasa or 0),
                    'interes': float(cuota.interes or 0),
                    'total': float(cuota.total or 0),
                    'monto_adelanto': float(cuota.monto_adelanto or 0),
                    'monto_pagado': float(cuota.monto_pagado or 0),
                    'saldo_cuota': float(cuota.saldo_cuota or 0),
                    'estado_pago': cuota.estado_pago or 'Pendiente',
                })

        return JsonResponse({
            'success': True,
            'venta': {
                'idventa': venta.idventa,
                'idcliente': venta.idcliente.idcliente,
                'cliente_nombre': venta.idcliente.razonsocial,
                'numero_comprobante': venta.numero_comprobante,
                'fecha_venta': venta.fecha_venta.strftime('%Y-%m-%d'),
                'idtipocomprobante': venta.idtipocomprobante.idtipocomprobante,
                'idseriecomprobante': venta.idseriecomprobante.idseriecomprobante,
                'id_tipo_igv': venta.id_tipo_igv.id_tipo_igv if venta.id_tipo_igv else None,
                'id_forma_pago': venta.id_forma_pago.id_forma_pago,
                'id_tipo_pago': venta.id_tipo_pago.id_tipo_pago if venta.id_tipo_pago else None,
                'importe_recibido': float(venta.importe_recibido) if venta.importe_recibido else 0,
                'vuelto': float(venta.vuelto) if venta.vuelto else 0,
                'observaciones': venta.observaciones or '',
                'total_venta': float(venta.total_venta),
                'total_ganancia': float(venta.total_ganancia),
                'idusuario': venta.idusuario.idusuario if venta.idusuario else None,
                'usuario_nombre': venta.idusuario.nombrecompleto if venta.idusuario else ''
            },
            'detalles': detalles_list,
            'credito_data': credito_data,
            'cuotas': cuotas_list,
        })

    except Ventas.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Venta no encontrada'
        }, status=404)
    except Exception as e:
        print(f"ERROR obtener_venta: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ==================== OBTENER DETALLE DE VENTA (MODAL) ====================
def obtener_detalle_venta(request, id):
    """
    Obtiene los datos de una venta para mostrar detalles (AJAX).
    A diferencia de `obtener_venta`, NO bloquea las ventas a crédito y también
    retorna las cuotas asociadas si corresponde.
    """
    if request.method != "GET":
        return JsonResponse({"success": False, "error": "Método no permitido"}, status=405)

    try:
        venta = Ventas.objects.get(idventa=id, estado=1)
        es_credito = int(venta.id_forma_pago.id_forma_pago) == 2

        detalles_qs = VentaDetalle.objects.filter(idventa=venta, estado=1).select_related(
            "id_vehiculo__idproducto",
            "id_vehiculo__idestadoproducto",
            "id_repuesto_comprado__id_repuesto",
            "id_servicio",
        )

        detalles_list = []
        for d in detalles_qs:
            precio_venta_contado = float(d.precio_venta_contado or 0)
            precio_venta_credito = float(d.precio_venta_credito or 0)
            precio_venta_usada = precio_venta_credito if es_credito else precio_venta_contado

            if d.tipo_item == "vehiculo" and d.id_vehiculo:
                # Priorizar el precio_maximo guardado en el detalle
                val_db = getattr(d, 'precio_maximo', None)
                print(f"🔍 DEBUG detalle {d.idventadetalle} | vehiculo {d.id_vehiculo_id} | precio_maximo en DB = {val_db} | precio_venta_contado = {d.precio_venta_contado}")
                precio_maximo = float(val_db) if val_db is not None else None
                
                # Si no está guardado (ventas antiguas), buscar en la compra original
                if precio_maximo is None:
                    from software.models.compradetalleModel import CompraDetalle
                    det_compra = CompraDetalle.objects.filter(id_vehiculo_id=d.id_vehiculo_id).order_by('-idcompradetalle').first()
                    if det_compra:
                        precio_maximo = float(det_compra.precio_maximo)
                    else:
                        precio_maximo = float(d.precio_venta_contado or 0)
                
                # Garantía final: si sigue siendo None o 0, usar precio_venta_contado
                if not precio_maximo:
                    precio_maximo = float(d.precio_venta_contado or 0)
                
                precio_minimo = float(d.precio_venta_contado)
                
                detalles_list.append({
                    "tipo": "vehiculo",
                    "cantidad": d.cantidad,
                    "precio_compra": float(d.precio_compra or 0),
                    "precio_venta_contado": precio_minimo,
                    "precio_maximo": precio_maximo,
                    "p_max_seguro": precio_maximo,
                    "precio_venta_descuento": float(d.precio_venta_descuento or 0),
                    "precio_venta_credito": precio_venta_credito,
                    "precio_venta_usada": precio_venta_usada,
                    "subtotal": float(d.subtotal or 0),
                    "ganancia": float(d.ganancia or 0),
                    "id_vehiculo": d.id_vehiculo.id_vehiculo,
                    "nombre_producto": d.id_vehiculo.idproducto.nomproducto,
                    "serie_motor": d.id_vehiculo.serie_motor or "",
                    "serie_chasis": d.id_vehiculo.serie_chasis or "",
                    "idventadetalle": d.idventadetalle,
                    "placas": getattr(d.id_vehiculo, "placas", "") or "",
                    "estado_producto": d.id_vehiculo.idestadoproducto.nombreestadoproducto
                    if d.id_vehiculo.idestadoproducto else "",
                })
            elif d.tipo_item == "repuesto" and d.id_repuesto_comprado:
                # Priorizar el precio_maximo guardado en el detalle
                val_db = getattr(d, 'precio_maximo', None)
                precio_maximo = float(val_db) if val_db is not None else None
                
                if precio_maximo is None:
                    from software.models.compradetalleModel import CompraDetalle
                    det_compra = CompraDetalle.objects.filter(id_repuesto_comprado_id=d.id_repuesto_comprado_id).order_by('-idcompradetalle').first()
                    if det_compra:
                        precio_maximo = float(det_compra.precio_maximo)
                    else:
                        precio_maximo = float(d.precio_venta_contado or 0)
                
                # Garantía final
                if not precio_maximo:
                    precio_maximo = float(d.precio_venta_contado or 0)
                
                precio_minimo = float(d.precio_venta_contado)

                detalles_list.append({
                    "tipo": "repuesto",
                    "cantidad": d.cantidad,
                    "precio_compra": float(d.precio_compra or 0),
                    "precio_venta_contado": precio_minimo,
                    "precio_maximo": precio_maximo,
                    "p_max_seguro": precio_maximo,
                    "precio_venta_descuento": float(d.precio_venta_descuento or 0),
                    "precio_venta_credito": precio_venta_credito,
                    "precio_venta_usada": precio_venta_usada,
                    "subtotal": float(d.subtotal or 0),
                    "ganancia": float(d.ganancia or 0),
                    "id_repuesto_comprado": d.id_repuesto_comprado.id_repuesto_comprado,
                    "idventadetalle": d.idventadetalle,
                    "nombre_repuesto": d.id_repuesto_comprado.id_repuesto.nombre,
                    "codigo_barras": d.id_repuesto_comprado.id_repuesto.codigo_barras or "",
                    "modelo": d.id_repuesto_comprado.id_repuesto.modelo_referencia or "",
                    "ubicacion": d.id_repuesto_comprado.ubicacion or "",
                })
            elif d.tipo_item == "servicio" and d.id_servicio:
                precio_minimo = float(d.precio_venta_contado)
                detalles_list.append({
                    "tipo": "servicio",
                    "cantidad": d.cantidad,
                    "precio_compra": 0,
                    "precio_venta_contado": precio_minimo,
                    "precio_maximo": precio_minimo,
                    "p_max_seguro": precio_minimo,
                    "precio_venta_descuento": 0,
                    "precio_venta_credito": 0,
                    "precio_venta_usada": precio_minimo,
                    "subtotal": float(d.subtotal or 0),
                    "ganancia": float(d.ganancia or 0),
                    "id_servicio": d.id_servicio.id_servicio,
                    "idventadetalle": d.idventadetalle,
                    "nombre_servicio": d.id_servicio.nombre,
                    "descripcion": d.id_servicio.descripcion or "",
                })

        cuotas_list = []
        credito_data = None
        if es_credito:
            credito = Credito.objects.filter(idventa=venta, estado=1).first()
            if credito:
                credito_data = {
                    "codigo_credito": credito.codigo_credito,
                    "monto_total": float(credito.monto_total or 0),
                    "monto_adelanto": float(credito.monto_adelanto or 0),
                    "saldo_pendiente": float(credito.saldo_pendiente or 0),
                    "cantidad_cuotas": int(credito.cantidad_cuotas or 0),
                    "estado_credito": credito.estado_credito,
                }

            cuotas = CuotasVenta.objects.filter(idventa=venta, estado=1).order_by("numero_cuota")
            for cuota in cuotas:
                cuotas_list.append({
                    "numero_cuota": cuota.numero_cuota,
                    "fecha_vencimiento": cuota.fecha_vencimiento.strftime("%Y-%m-%d") if cuota.fecha_vencimiento else None,
                    "monto": float(cuota.monto or 0),
                    "interes": float(cuota.interes or 0),
                    "total": float(cuota.total or 0),
                    "monto_adelanto": float(cuota.monto_adelanto or 0),
                    "monto_pagado": float(cuota.monto_pagado or 0),
                    "saldo_cuota": float(cuota.saldo_cuota or 0),
                    "estado_pago": cuota.estado_pago or "Pendiente",
                })

        venta_data = {
            "idventa": venta.idventa,
            "cliente_nombre": venta.idcliente.razonsocial,
            "numero_comprobante": venta.numero_comprobante,
            "fecha_venta": venta.fecha_venta.strftime("%Y-%m-%d") if venta.fecha_venta else None,
            "id_forma_pago": int(venta.id_forma_pago.id_forma_pago),
            "forma_pago_nombre": venta.id_forma_pago.nombre,
            "id_tipo_pago": venta.id_tipo_pago.id_tipo_pago if venta.id_tipo_pago and venta.estado_cobro != 'Pendiente' else None,
            "tipo_pago_nombre": venta.id_tipo_pago.nombre if venta.id_tipo_pago and venta.estado_cobro != 'Pendiente' else "—",
            "estado": int(venta.estado or 0),
            "estado_nombre": "Activo" if venta.estado == 1 else "Anulado",
            "total_venta": float(venta.total_venta or 0),
            "subtotal": float(venta.subtotal or 0),
            "igv": float(venta.igv or 0),
            "total_ganancia": float(venta.total_ganancia or 0),
            "idusuario": venta.idusuario.idusuario if venta.idusuario else None,
            "usuario_nombre": venta.idusuario.nombrecompleto if venta.idusuario else "Sistema",
        }

        return JsonResponse({
            "success": True,
            "venta": venta_data,
            "detalles": detalles_list,
            "cuotas": cuotas_list,
            "credito": credito_data,
            "bloqueo_parcial": False,
        })

    except Ventas.DoesNotExist:
        return JsonResponse({"success": False, "error": "Venta no encontrada"}, status=404)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# ==================== ACTUALIZAR VENTA (EDICIÓN) - CON AUDITORÍA ====================
@requiere_caja_aperturada
@transaction.atomic
def actualizar_venta(request, id):
    """Actualiza una venta existente (contado o crédito sin pagos)"""
    if request.method == "POST":
        try:
            # Copiar POST para poder modificarlo
            request.POST = request.POST.copy()
            id_forma_pago_raw = request.POST.get("forma_pago")
            if id_forma_pago_raw == "1":  # Contado
                tipos_pago_ids = request.POST.getlist('tipo_pago_id[]')
                montos_pago = request.POST.getlist('monto_pago[]')
                nros_operacion = request.POST.getlist('nro_operacion[]')

                if tipos_pago_ids:
                    # Calcular total de los pagos recibidos
                    total_recibido = sum(Decimal(m) for m in montos_pago if m)
                    request.POST['importe_recibido'] = str(total_recibido)

                    # Si hay múltiples pagos
                    if len(tipos_pago_ids) > 1:
                        # Buscar tipo de pago 'Múltiple'
                        tp_multiple = TipoPago.objects.filter(nombre__iexact='Múltiple').first()
                        if not tp_multiple:
                            tp_multiple = TipoPago.objects.filter(nombre__icontains='Multip').first()
                        
                        request.POST['tipo_pago'] = str(tp_multiple.id_tipo_pago if tp_multiple else tipos_pago_ids[0])
                        
                        # Generar string de consolidación
                        partes = []
                        for i in range(len(tipos_pago_ids)):
                            tp_id = tipos_pago_ids[i]
                            monto = montos_pago[i]
                            nro = nros_operacion[i] if i < len(nros_operacion) else ''
                            tp_obj = TipoPago.objects.filter(pk=int(tp_id)).first()
                            tp_nombre = tp_obj.nombre if tp_obj else f"Pago {tp_id}"
                            nro_str = f" (Op: {nro})" if nro else ""
                            partes.append(f"{tp_nombre}: S/ {monto}{nro_str}")
                        
                        consolidacion = " | ".join(partes)
                        observaciones_pago = f"[FRACCIONADO: {consolidacion}]"
                        
                        # Agregar a las observaciones
                        user_obs = request.POST.get("observaciones", "")
                        if user_obs:
                            request.POST['observaciones'] = f"{observaciones_pago} {user_obs}"
                        else:
                            request.POST['observaciones'] = observaciones_pago
                    else:
                        # Si solo hay un único pago
                        request.POST['tipo_pago'] = str(tipos_pago_ids[0])
                        nro = nros_operacion[0] if nros_operacion else ''
                        if nro:
                            user_obs = request.POST.get("observaciones", "")
                            obs_pago = f"[Op: {nro}]"
                            if user_obs:
                                request.POST['observaciones'] = f"{obs_pago} {user_obs}"
                            else:
                                request.POST['observaciones'] = obs_pago
            print("======= DEBUG POST ACTUALIZAR VENTA =======")
            for k, v in request.POST.items():
                print(f"{k}: {v}")
            print("===========================================")

            idusuario_session = request.session.get('idusuario')
            id_caja_session = request.session.get('id_caja')
            id_almacen_session = request.session.get('id_almacen')
            id_sucursal_session = request.session.get('id_sucursal')

            tipo_usuario_session = request.session.get('idtipousuario')
            if not id_caja_session and tipo_usuario_session != 2:
                return JsonResponse({'ok': False, 'error': 'Debe seleccionar una caja en el modal de configuración antes de actualizar la venta.'}, status=400)
            if not id_almacen_session:
                return JsonResponse({'ok': False, 'error': 'Debe seleccionar un almacén en el modal de configuración antes de actualizar la venta.'}, status=400)
            if not id_sucursal_session:
                return JsonResponse({'ok': False, 'error': 'Debe seleccionar una sucursal en el modal de configuración antes de actualizar la venta.'}, status=400)

            apertura = AperturaCierreCaja.objects.filter(
                idusuario_id=idusuario_session,
                id_caja_id=id_caja_session,
                estado__in=['abierta', 'reabierta']
            ).first()
            
            tipo_usuario_session = request.session.get('idtipousuario')
            
            if not apertura and tipo_usuario_session != 2:
                return JsonResponse({
                    'ok': False,
                    'error': 'La caja seleccionada no está aperturada. Por favor, aperture la caja antes de actualizar ventas.',
                    'necesita_aperturar': True
                }, status=400)

            try:
                usuario = Usuario.objects.get(idusuario=idusuario_session)
            except Usuario.DoesNotExist:
                return JsonResponse({'ok': False, 'error': 'Usuario de sesión no válido.'}, status=400)
            if not usuario.id_sucursal:
                return JsonResponse({'ok': False, 'error': 'Usuario sin sucursal asignada. Contacte al administrador.'}, status=400)

            try:
                almacen = Almacenes.objects.get(id_almacen=id_almacen_session, estado=1)
            except Almacenes.DoesNotExist:
                return JsonResponse({'ok': False, 'error': 'El almacén seleccionado no existe o está inactivo.'}, status=400)

            # Obtener la venta existente
            venta = Ventas.objects.get(idventa=id, estado=1)
            es_credito_original = venta.id_forma_pago.id_forma_pago == 2

            # ✅ REGLA DE NEGOCIO: Si es crédito, re-validar que no haya pagos (seguridad doble)
            if es_credito_original:
                tiene_pagos = CuotasVenta.objects.filter(
                    idventa=venta,
                    estado=1,
                    monto_pagado__gt=0
                ).exists()
                if tiene_pagos:
                    if request.session.get('idtipousuario') == 1:
                        # BLOQUEO PARCIAL: ACTUALIZAR SÓLO VENDEDOR
                        nuevo_vendedor = request.POST.get('idusuario')
                        if nuevo_vendedor:
                            venta.idusuario_id = nuevo_vendedor
                            venta.save()
                        return JsonResponse({
                            'ok': True,
                            'message': 'Se actualizó únicamente el vendedor debido a que la venta ya tiene pagos.',
                            'idventa': venta.idventa,
                            'numero_comprobante': venta.numero_comprobante,
                            'es_credito': True
                        })
                    else:
                        return JsonResponse({
                            'ok': False,
                            'error': 'No se puede editar esta venta a crédito porque ya registra pagos o abonos realizados.',
                            'codigo': 'VENTA_CON_PAGOS_NO_EDITABLE'
                        }, status=400)

            err_cabecera, cabecera = _validar_cabecera_venta(request)
            if err_cabecera:
                return err_cabecera

            nueva_forma_pago = cabecera['id_forma_pago']

            # ✅ Validar cuotas si la nueva forma de pago es crédito
            if nueva_forma_pago == 2:
                err_cuotas = _validar_cuotas_credito_venta(request)
                if err_cuotas:
                    return err_cuotas

            items = int(request.POST.get("items_count") or 0)
            err_lineas = _validar_lineas_venta(request, items, almacen, id_venta_edicion=id)
            if err_lineas:
                return err_lineas

            # ✅ GUARDAR DATOS ANTERIORES PARA AUDITORÍA (incluyendo detalles)
            detalles_qs = VentaDetalle.objects.filter(idventa=venta, estado=1)
            detalles_anteriores = []
            for d in detalles_qs:
                detalles_anteriores.append({
                    'idventadetalle': d.idventadetalle,
                    'tipo_item': d.tipo_item,
                    'id_vehiculo_id': d.id_vehiculo_id,
                    'id_repuesto_comprado_id': d.id_repuesto_comprado_id,
                    'cantidad': d.cantidad,
                    'precio_venta_contado': Decimal(str(d.precio_venta_contado or 0)),
                    'precio_venta_descuento': Decimal(str(d.precio_venta_descuento or 0)) if d.precio_venta_descuento else None,
                    'precio_venta_credito': Decimal(str(d.precio_venta_credito or 0)) if d.precio_venta_credito else None,
                    'precio_compra': Decimal(str(d.precio_compra or 0)),
                    'subtotal': Decimal(str(d.subtotal or 0))
                })
            datos_anteriores = {
                'numero_comprobante': venta.numero_comprobante,
                'cliente': venta.idcliente.razonsocial,
                'total': float(venta.total_venta),
                'fecha': str(venta.fecha_venta),
                'forma_pago': venta.id_forma_pago.nombre,
                'tipo_pago': venta.id_tipo_pago.nombre if venta.id_tipo_pago else 'N/A',
                'observaciones': venta.observaciones or '',
                'detalles': detalles_anteriores
            }

            # Actualizar datos principales de la venta
            # Guardar IDs de ubicación originales para la devolución de stock
            id_almacen_original = venta.id_almacen_id or id_almacen_session
            
            venta.idcliente_id = cabecera['idcliente']
            venta.idtipocomprobante_id = cabecera['idtipocomprobante']
            venta.idseriecomprobante_id = cabecera['idseriecomprobante']
            venta.id_tipo_igv_id = cabecera['id_tipo_igv']
            venta.fecha_venta = cabecera['fecha_venta']
            venta.id_forma_pago_id = nueva_forma_pago
            venta.id_tipo_pago_id = cabecera['id_tipo_pago_id']
            venta.observaciones = request.POST.get("observaciones", "")
            venta.idusuario_id = cabecera['idusuario']
            
            # Actualizar a la ubicación de la sesión actual
            venta.id_sucursal_id = id_sucursal_session
            venta.id_almacen_id = id_almacen_session
            venta.id_caja_id = id_caja_session

            if nueva_forma_pago == 1:  # Contado
                importe_recibido = request.POST.get("importe_recibido")
                vuelto = request.POST.get("vuelto")
                if not importe_recibido or not vuelto:
                    raise ValueError("Para ventas al contado, debe ingresar el importe recibido y el vuelto.")
                venta.importe_recibido = Decimal(importe_recibido)
                venta.vuelto = Decimal(vuelto)
                if venta.importe_recibido < 0 or venta.vuelto < 0:
                    raise ValueError("El importe recibido y el vuelto no pueden ser negativos.")
            else:  # Crédito
                venta.importe_recibido = None
                venta.vuelto = None

            # 🔍 RECOPILAR NUEVOS DETALLES PARA COMPARACIÓN Y GUARDADO
            nuevos_detalles_data = []
            total_calculado = Decimal('0')
            total_ganancia_calculada = Decimal('0')

            for i in range(1, items + 1):
                tipo_item = request.POST.get(f"tipo_item_{i}")
                if not tipo_item:
                    continue

                cantidad = int(request.POST.get(f"cantidad_{i}") or 1)
                p_contado = Decimal(request.POST.get(f"precio_venta_contado_{i}") or 0)
                p_credito_raw = request.POST.get(f"precio_credito_{i}")
                p_credito = Decimal(p_credito_raw) if p_credito_raw else None
                p_compra = Decimal(request.POST.get(f"precio_compra_{i}") or 0)
                p_desc_raw = request.POST.get(f"precio_descuento_{i}")
                p_desc = Decimal(p_desc_raw) if p_desc_raw and p_desc_raw.strip() else None

                p_maximo_raw = request.POST.get(f"precio_maximo_{i}")
                p_maximo = Decimal(p_maximo_raw) if p_maximo_raw and p_maximo_raw.strip() else None

                # Determinar precio final según forma de pago (igual que en nueva_venta)
                if nueva_forma_pago == 2:
                    if not p_credito: raise ValueError(f"Debe ingresar el precio a crédito para el ítem {i}.")
                    precio_f = p_credito
                elif p_desc:
                    precio_f = p_desc
                else:
                    # SI NO HAY DESCUENTO, EL PRECIO FINAL ES EL P. MÁXIMO (igual que al registrar)
                    precio_f = p_maximo if p_maximo else p_contado

                subt = cantidad * precio_f
                gan = (precio_f - p_compra) * cantidad
                
                total_calculado += subt
                total_ganancia_calculada += gan

                id_det_raw = request.POST.get(f"id_detalle_venta_{i}")
                id_det = int(id_det_raw) if id_det_raw and id_det_raw.strip() else None


                item_data = {
                    'idventadetalle': id_det,
                    'tipo_item': tipo_item,
                    'cantidad': cantidad,
                    'precio_venta_contado': float(p_contado),
                    'precio_venta_descuento': float(p_desc) if p_desc else None,
                    'precio_venta_credito': float(p_credito) if p_credito else None,
                    'precio_maximo': float(p_maximo) if p_maximo else None,
                    'precio_compra': float(p_compra),
                    'subtotal': float(subt),
                    'ganancia': float(gan),
                    'id_vehiculo_id': int(request.POST.get(f"id_vehiculo_{i}") or 0) if tipo_item == 'vehiculo' else None,
                    'id_repuesto_comprado_id': int(request.POST.get(f"id_repuesto_{i}") or 0) if tipo_item == 'repuesto' else None
                }
                nuevos_detalles_data.append(item_data)

            # 🔍 COMPARAR CON DETALLES ANTERIORES
            hay_cambios_detalle = False
            if len(nuevos_detalles_data) != len(detalles_anteriores):
                hay_cambios_detalle = True
            else:
                # Comparar contenido de los detalles (ordenado por id de item)
                nuevos_sorted = sorted(nuevos_detalles_data, key=lambda x: (x['tipo_item'], x['id_vehiculo_id'] or 0, x['id_repuesto_comprado_id'] or 0))
                viejos_sorted = sorted(detalles_anteriores, key=lambda x: (x['tipo_item'], x['id_vehiculo_id'] or 0, x['id_repuesto_comprado_id'] or 0))
                
                for n, v in zip(nuevos_sorted, viejos_sorted):
                    # Comparar todos los campos relevantes, incluyendo precios
                    if (n['tipo_item'] != v['tipo_item'] or 
                        n['id_vehiculo_id'] != v['id_vehiculo_id'] or 
                        n['id_repuesto_comprado_id'] != v['id_repuesto_comprado_id'] or 
                        n['cantidad'] != v['cantidad'] or 
                        n['precio_venta_contado'] != v['precio_venta_contado'] or
                        n['precio_venta_descuento'] != v['precio_venta_descuento'] or
                        n['precio_venta_credito'] != v['precio_venta_credito']):
                        hay_cambios_detalle = True
                        break

            if hay_cambios_detalle:
                print("🔄 CAMBIO DETECTADO EN EL DETALLE → Sincronizando stock y actualizando registros")
                
                # 📦 ⚖️ SINCRONIZACIÓN DIFERENCIAL DE STOCK (basado en items, no en IDs de registro)
                map_viejos = {(v['tipo_item'], v['id_vehiculo_id'] if v['tipo_item']=='vehiculo' else v['id_repuesto_comprado_id']): v for v in detalles_anteriores}
                map_nuevos = {(n['tipo_item'], n['id_vehiculo_id'] if n['tipo_item']=='vehiculo' else n['id_repuesto_comprado_id']): n for n in nuevos_detalles_data}

                # Devolver stock de lo que se quitó o si cambió el almacén
                for key, v in map_viejos.items():
                    if key not in map_nuevos or id_almacen_original != venta.id_almacen_id:
                        _sincronizar_inventario(id_almacen_original, key[0], key[1], v['cantidad'], 'AUMENTAR')

                # IDs que permanecen en la venta
                ids_a_mantener = [n['idventadetalle'] for n in nuevos_detalles_data if n['idventadetalle']]
                VentaDetalle.objects.filter(idventa=venta, estado=1).exclude(idventadetalle__in=ids_a_mantener).delete()

                # Procesar cada ítem nuevo o actualizado
                for n in nuevos_detalles_data:
                    if n['tipo_item'] == 'vehiculo':
                        if not _obtener_vehiculo_valido(n['id_vehiculo_id']):
                            raise ValueError("No se puede guardar la venta: uno de los vehiculos no existe, esta inactivo o no tiene producto asociado.")
                    elif n['tipo_item'] == 'repuesto':
                        if not _obtener_repuesto_valido(n['id_repuesto_comprado_id']):
                            raise ValueError("No se puede guardar la venta: uno de los repuestos no existe, esta inactivo o no tiene producto asociado.")

                    key = (n['tipo_item'], n['id_vehiculo_id'] if n['tipo_item']=='vehiculo' else n['id_repuesto_comprado_id'])
                    
                    # Sincronizar stock diferencial
                    if key in map_viejos and id_almacen_original == venta.id_almacen_id:
                        v = map_viejos[key]
                        if n['cantidad'] > v['cantidad']:
                            _sincronizar_inventario(venta.id_almacen_id, n['tipo_item'], key[1], n['cantidad'] - v['cantidad'], 'REDUCIR')
                        elif n['cantidad'] < v['cantidad']:
                            _sincronizar_inventario(venta.id_almacen_id, n['tipo_item'], key[1], v['cantidad'] - n['cantidad'], 'AUMENTAR')
                    else:
                        _sincronizar_inventario(venta.id_almacen_id, n['tipo_item'], key[1], n['cantidad'], 'REDUCIR')

                    # ACTUALIZAR O CREAR RECOGISTRO (para mantener IDs)
                    if n['idventadetalle']:
                        # Update record using its original ID
                        VentaDetalle.objects.filter(idventadetalle=n['idventadetalle']).update(
                            tipo_item=n['tipo_item'],
                            id_vehiculo_id=n['id_vehiculo_id'],
                            id_repuesto_comprado_id=n['id_repuesto_comprado_id'],
                            cantidad=n['cantidad'],
                            precio_venta_contado=Decimal(str(n['precio_venta_contado'])),
                            precio_venta_descuento=Decimal(str(n['precio_venta_descuento'])) if n['precio_venta_descuento'] else None,
                            precio_venta_credito=Decimal(str(n['precio_venta_credito'])) if n['precio_venta_credito'] else None,
                            precio_maximo=Decimal(str(n['precio_maximo'])) if n.get('precio_maximo') else None,
                            precio_compra=Decimal(str(n['precio_compra'])),
                            subtotal=Decimal(str(n['subtotal'])),
                            ganancia=Decimal(str(n['ganancia'])),
                            estado=1
                        )
                    else:
                        # Create new record
                        VentaDetalle.objects.create(
                            idventa=venta,
                            tipo_item=n['tipo_item'],
                            id_vehiculo_id=n['id_vehiculo_id'],
                            id_repuesto_comprado_id=n['id_repuesto_comprado_id'],
                            cantidad=n['cantidad'],
                            precio_venta_contado=Decimal(str(n['precio_venta_contado'])),
                            precio_venta_descuento=Decimal(str(n['precio_venta_descuento'])) if n['precio_venta_descuento'] else None,
                            precio_venta_credito=Decimal(str(n['precio_venta_credito'])) if n['precio_venta_credito'] else None,
                            precio_maximo=Decimal(str(n['precio_maximo'])) if n.get('precio_maximo') else None,
                            precio_compra=Decimal(str(n['precio_compra'])),
                            subtotal=Decimal(str(n['subtotal'])),
                            ganancia=Decimal(str(n['ganancia'])),
                            estado=1
                        )
            else:
                print("S/C ✅ DETALLE IDÉNTICO → Manteniendo registros originales (ID intacto)")

            # Actualizar totales
            print(f"📊 ACTUALIZANDO TOTALES: Subtotal={total_calculado}, Total={total_calculado}")
            venta.subtotal = total_calculado
            venta.total_venta = total_calculado
            venta.total_ganancia = total_ganancia_calculada

            venta.save()

            # ✅ ACTUALIZAR MOVIMIENTO DE CAJA (solo si es Contado y el total cambió)
            if nueva_forma_pago == 1:
                movimiento = MovimientoCaja.objects.filter(idventa=venta, tipo_movimiento='ingreso', estado=1).first()
                if movimiento:
                    if movimiento.monto != total_calculado:
                        print(f"💰 ACTUALIZANDO MOVIMIENTO DE CAJA: S/ {movimiento.monto} -> S/ {total_calculado}")
                        movimiento.monto = total_calculado
                        movimiento.descripcion = f"Venta {venta.numero_comprobante} (Editada) - Cliente: {venta.idcliente.razonsocial}"
                        movimiento.id_caja_id = id_caja_session # Por si cambió la caja
                        movimiento.save()
                else:
                    # Si por algún motivo no existía, se crea (aunque el signal debería haberlo creado al inicio)
                    MovimientoCaja.objects.create(
                        id_caja_id=id_caja_session,
                        idusuario_id=request.session.get('idusuario'),
                        idventa=venta,
                        tipo_movimiento='ingreso',
                        monto=total_calculado,
                        descripcion=f"Venta {venta.numero_comprobante} - Cliente: {venta.idcliente.razonsocial}",
                        estado=1
                    )

            # =============================================
            # ✅ ACTUALIZAR CRÉDITO Y CUOTAS (si es crédito)
            # =============================================
            if nueva_forma_pago == 2 and request.POST.get("tiene_cuotas") == "1":
                cantidad_cuotas = int(request.POST.get("cantidad_cuotas") or 0)

                monto_adelanto_str = request.POST.get("monto_adelanto")
                monto_adelanto = Decimal(monto_adelanto_str) if monto_adelanto_str and monto_adelanto_str.strip() else Decimal('0')

                tasa_interes_str = request.POST.get("tasa_interes")
                tasa_interes = Decimal(tasa_interes_str) if tasa_interes_str else Decimal('0')

                saldo_financiar = total_calculado - monto_adelanto

                # Actualizar o crear el Credito
                credito = Credito.objects.filter(idventa=venta, estado=1).first()
                if credito:
                    credito.monto_total = total_calculado
                    credito.monto_adelanto = monto_adelanto
                    credito.saldo_pendiente = saldo_financiar
                    credito.cantidad_cuotas = cantidad_cuotas
                    credito.save()
                    print(f"✅ CRÉDITO ACTUALIZADO - ID: {credito.idcredito}")
                else:
                    # Generar código si no existía (formato CR-YYYYMMDD-NNN)
                    _hoy_ed = venta.fecha_venta
                    _intento_ed = 0
                    while True:
                        _count_ed = Credito.objects.filter(
                            fecha_credito__date=_hoy_ed.date(),
                            es_directo=False
                        ).count() + 1 + _intento_ed
                        codigo_credito = f"CR-{_hoy_ed.strftime('%Y%m%d')}-{_count_ed:03d}"
                        if not Credito.objects.filter(codigo_credito=codigo_credito).exists():
                            break
                        _intento_ed += 1
                    credito = Credito.objects.create(
                        codigo_credito=codigo_credito,
                        idventa=venta,
                        monto_total=total_calculado,
                        monto_adelanto=monto_adelanto,
                        saldo_pendiente=saldo_financiar,
                        cantidad_cuotas=cantidad_cuotas,
                        fecha_credito=venta.fecha_venta,
                        estado_credito='activo',
                        estado=1
                    )
                    print(f"✅ CRÉDITO CREADO (nuevo) - ID: {credito.idcredito}")

                # Eliminar cuotas anteriores (sin pagos, ya validado) y recrear
                CuotasVenta.objects.filter(idventa=venta, estado=1).delete()

                fecha_venta = venta.fecha_venta

                # Cuota 0 (Monto Inicial)
                if monto_adelanto > Decimal('0'):
                    fecha_cuota_0_str = request.POST.get("cuota_0_fecha", "").strip()
                    if fecha_cuota_0_str:
                        try:
                            fecha_cuota_0 = datetime.strptime(fecha_cuota_0_str, '%Y-%m-%d').date()
                        except ValueError:
                            fecha_cuota_0 = fecha_venta
                    else:
                        fecha_cuota_0 = fecha_venta

                    CuotasVenta.objects.create(
                        idventa=venta,
                        numero_cuota=0,
                        monto=monto_adelanto,
                        tasa=Decimal('0'),
                        interes=Decimal('0'),
                        total=monto_adelanto,
                        fecha_vencimiento=fecha_cuota_0,
                        monto_adelanto=monto_adelanto,
                        monto_pagado=Decimal('0'),
                        saldo_cuota=monto_adelanto,
                        fecha_pago=None,
                        estado_pago='Pendiente',
                        estado=1
                    )
                    print(f"  Cuota 0 (Monto Inicial): S/ {monto_adelanto}")

                # Cuotas regulares 1..N
                for i in range(1, cantidad_cuotas + 1):
                    numero_cuota_str = request.POST.get(f"cuota_{i}_numero")
                    fecha_venc_str = request.POST.get(f"cuota_{i}_fecha")
                    monto_cuota_str = request.POST.get(f"cuota_{i}_monto")
                    interes_cuota_str = request.POST.get(f"cuota_{i}_interes")
                    total_cuota_str = request.POST.get(f"cuota_{i}_total")
                    tasa_cuota_str = request.POST.get(f"cuota_{i}_tasa")

                    numero_cuota = int(numero_cuota_str) if numero_cuota_str else i
                    monto_cuota = Decimal(monto_cuota_str) if monto_cuota_str else Decimal('0')
                    interes_cuota = Decimal(interes_cuota_str) if interes_cuota_str else Decimal('0')
                    total_cuota = Decimal(total_cuota_str) if total_cuota_str else (monto_cuota + interes_cuota)
                    tasa_cuota = Decimal(tasa_cuota_str) if tasa_cuota_str else tasa_interes

                    if fecha_venc_str:
                        fecha_vencimiento = datetime.strptime(fecha_venc_str, '%Y-%m-%d').date()
                    else:
                        fecha_base = fecha_venta if hasattr(fecha_venta, 'year') else datetime.strptime(str(fecha_venta), '%Y-%m-%d').date()
                        fecha_vencimiento = fecha_base + timedelta(days=30 * i)

                    CuotasVenta.objects.create(
                        idventa=venta,
                        numero_cuota=numero_cuota,
                        monto=monto_cuota,
                        tasa=tasa_cuota,
                        interes=interes_cuota,
                        total=total_cuota,
                        fecha_vencimiento=fecha_vencimiento,
                        monto_adelanto=monto_adelanto if i == 1 else Decimal('0'),
                        monto_pagado=Decimal('0'),
                        saldo_cuota=total_cuota,
                        fecha_pago=None,
                        estado_pago='Pendiente',
                        estado=1
                    )
                    print(f"  Cuota {numero_cuota}: capital=S/{monto_cuota}, interés=S/{interes_cuota}, total=S/{total_cuota}")

            # ✅ REGISTRAR EN AUDITORÍA (Convertir Decimals a float para JSON)
            if 'detalles' in datos_anteriores:
                for d in datos_anteriores['detalles']:
                    for k, v in d.items():
                        if isinstance(v, Decimal):
                            d[k] = float(v)

            AuditoriaVentas.objects.create(
                idventa=id,
                accion='EDICION',
                motivo='Venta actualizada',
                idusuario_id=request.session.get('idusuario'),
                datos_anteriores=datos_anteriores
            )

            print(f"✅ VENTA ACTUALIZADA - ID: {venta.idventa}")
            print(f"✅ AUDITORÍA REGISTRADA")

            return JsonResponse({
                'ok': True,
                'message': 'Venta actualizada correctamente',
                'idventa': venta.idventa,
                'numero_comprobante': venta.numero_comprobante,
                'es_credito': nueva_forma_pago == 2
            })

        except Ventas.DoesNotExist:
            return JsonResponse({
                'ok': False,
                'error': 'La venta no existe o ya fue eliminada'
            }, status=404)
        except ValueError as ve:
            print(f"ERROR DE VALIDACIÓN: {str(ve)}")
            return JsonResponse({
                'ok': False,
                'error': str(ve)
            })
        except Exception as e:
            print(f"ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'ok': False,
                'error': f'Error al actualizar la venta: {str(e)}'
            }, status=400)

    return redirect("ventas")


# ==================== ELIMINAR VENTA CON MOTIVO Y AUDITORÍA (SOLO ADMIN) ====================
def eliminar_venta(request, id):
    """Eliminación lógica de una venta (cambia estado a 0) - SOLO ADMIN con motivo obligatorio"""
    if request.method == "POST":
        try:
            # ✅ VALIDAR PERMISOS: Solo admin puede eliminar
            id_tipo_usuario = request.session.get('idtipousuario')
            
            if id_tipo_usuario != 1:  # 1 = Admin
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': 'No tiene permisos para eliminar ventas. Solo administradores pueden realizar esta acción.',
                        'codigo': 'SIN_PERMISOS'
                    }, status=403)
                return redirect('ventas')
            
            # ✅ VALIDAR MOTIVO
            motivo = request.POST.get('motivo', '').strip()
            
            if not motivo or len(motivo) < 10:
                return JsonResponse({
                    'success': False,
                    'error': 'Debe proporcionar un motivo válido (mínimo 10 caracteres)'
                }, status=400)
            
            idusuario = request.session.get('idusuario')
            
            with transaction.atomic():
                # Obtener la venta
                venta = Ventas.objects.get(idventa=id, estado=1)
                
                # ✅ VALIDAR SI ES CRÉDITO Y TIENE PAGOS
                if int(venta.id_forma_pago_id) == 2: # 2 = Crédito
                    credito = Credito.objects.filter(idventa=venta, estado=1).first()
                    if credito:
                        # Verificar si alguna cuota tiene pagos (incluyendo cuota 0)
                        hay_pagos = CuotasVenta.objects.filter(idventa=venta, monto_pagado__gt=0, estado=1).exists()
                        if hay_pagos:
                            return JsonResponse({
                                'success': False,
                                'error': 'No se puede eliminar la venta porque el crédito asociado ya posee pagos registrados (incluyendo la cuota inicial).',
                                'codigo': 'CREDITO_CON_PAGOS'
                            }, status=400)
                
                # ✅ GUARDAR DATOS PARA AUDITORÍA
                datos_venta = {
                    'numero_comprobante': venta.numero_comprobante,
                    'cliente': venta.idcliente.razonsocial,
                    'total': float(venta.total_venta),
                    'fecha': str(venta.fecha_venta),
                    'forma_pago': venta.id_forma_pago.nombre
                }
                
                # ✅ DEVOLVER PRODUCTOS AL STOCK ANTES DE ANULAR
                detalles_anular = VentaDetalle.objects.filter(idventa=venta, estado=1)
                from software.views.ventas import _sincronizar_inventario
                for d in detalles_anular:
                    if d.tipo_item == 'vehiculo' and d.id_vehiculo:
                        _sincronizar_inventario(venta.id_almacen_id, 'vehiculo', d.id_vehiculo_id, d.cantidad, 'AUMENTAR')
                        
                        # Restaurar situación del vehículo a DISPONIBLE
                        from software.models.SituacionVehiculoModel import SituacionVehiculo
                        situ_disponible, _ = SituacionVehiculo.objects.get_or_create(nombre_situacion='DISPONIBLE', defaults={'estado': 1})
                        d.id_vehiculo.id_situacion = situ_disponible
                        d.id_vehiculo.save()

                    elif d.tipo_item == 'repuesto' and d.id_repuesto_comprado:
                        _sincronizar_inventario(venta.id_almacen_id, 'repuesto', d.id_repuesto_comprado_id, d.cantidad, 'AUMENTAR')

                # Cambiar estado de la venta (soft delete)
                venta.estado = 0
                venta.save()

                # ✅ ANULAR CRÉDITO Y CUOTAS ASOCIADAS
                if int(venta.id_forma_pago_id) == 2:
                    Credito.objects.filter(idventa=venta, estado=1).update(estado=0, estado_credito='anulado')
                    CuotasVenta.objects.filter(idventa=venta, estado=1).update(estado=0)
            
            # ✅ REGISTRAR EN AUDITORÍA
            AuditoriaVentas.objects.create(
                idventa=id,
                accion='ELIMINACION',
                motivo=motivo,
                idusuario_id=idusuario,
                datos_anteriores=datos_venta
            )
            
            print(f"✅ VENTA ELIMINADA - ID: {id}")
            print(f"✅ AUDITORÍA REGISTRADA - Motivo: {motivo}")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Venta eliminada correctamente'
                })
            
            return redirect('ventas')
            
        except Ventas.DoesNotExist:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'La venta no existe'
                }, status=404)
            return redirect('ventas')
            
        except Exception as e:
            print(f"ERROR: {str(e)}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                }, status=400)
            return redirect('ventas')
    
    return redirect("ventas")
    

#Para Imprimir_comprobante
def imprimir_comprobante(request, idventa):
    """
    Genera un PDF del comprobante de venta en formato TICKET con logo y QR
    Optimizado para impresoras térmicas de 80mm - ALTURA AUTOMÁTICA
    SOLO para ventas al CONTADO
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, KeepTogether
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
        from io import BytesIO
        import qrcode
        import os
        from django.conf import settings
        from software.models.empresaModel import Empresa
        from software.utils.logo_utils import get_logo_image_for_pdf
        
        # Obtener la venta
        venta = get_object_or_404(Ventas, idventa=idventa)
        
        # No hay restricción para imprimir ticket de crédito ahora
        
        # Obtener detalles de la venta
        detalles = VentaDetalle.objects.filter(idventa=venta, estado=1)

        # OBTENER LA EMPRESA DE LA VENTA
        try:
            if venta.idempresa:
                empresa = Empresa.objects.get(idempresa=venta.idempresa, activo=True)
            else:
                # Si no tiene empresa asignada, usar la primera activa
                empresa = Empresa.objects.filter(activo=True).first()
            
            if not empresa:
                return HttpResponse("No se encontró información de la empresa. Configure los datos en el sistema.", status=400)
        except Empresa.DoesNotExist:
            return HttpResponse(f"La empresa con ID {venta.idempresa} no existe en el sistema.", status=400)
        
        # Crear el PDF en memoria con tamaño de TICKET (80mm de ancho)
        buffer = BytesIO()
        
        # Tamaño de ticket: 80mm de ancho, altura dinámica
        ticket_width = 80 * mm
        
        # Ancho útil para el contenido (80mm - 6mm de márgenes)
        ancho_util = 74 * mm
        
        # Contenedor para los elementos del PDF
        elements = []
        
        # Estilos personalizados para ticket
        styles = getSampleStyleSheet()
        
        style_company = ParagraphStyle(
            'CompanyName',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            spaceAfter=1,
            leading=11
        )
        
        style_header = ParagraphStyle(
            'TicketHeader',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.black,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            spaceAfter=2,
            leading=10
        )
        
        style_normal_center = ParagraphStyle(
            'NormalCenter',
            parent=styles['Normal'],
            fontSize=7,
            alignment=TA_CENTER,
            spaceAfter=1,
            leading=8
        )
        
        style_normal = ParagraphStyle(
            'TicketNormal',
            parent=styles['Normal'],
            fontSize=7,
            spaceAfter=1,
            leading=8
        )
        
        style_bold = ParagraphStyle(
            'TicketBold',
            parent=styles['Normal'],
            fontSize=7,
            fontName='Helvetica-Bold',
            spaceAfter=1,
            alignment=TA_CENTER,
            leading=8
        )
        
        style_small = ParagraphStyle(
            'SmallText',
            parent=styles['Normal'],
            fontSize=6,
            alignment=TA_CENTER,
            spaceAfter=0.5,
            leading=7
        )
        
        style_desc_table = ParagraphStyle(
            'DescTable',
            parent=styles['Normal'],
            fontSize=6,
            leading=7,
            alignment=TA_LEFT,
            spaceAfter=0
        )
        
        # LOGO DESDE CLOUDINARY
        logo_rl = get_logo_image_for_pdf(empresa, width_mm=30, height_mm=30, circular=True, use_ticket_logo=True)
        if logo_rl:
            elements.append(logo_rl)
            elements.append(Spacer(1, 3*mm))
        
        # ==========================================
        # ENCABEZADO - DATOS DE LA EMPRESA
        # ==========================================
        nombre_empresa = empresa.razonsocial if empresa.razonsocial else empresa.nombrecomercial
        elements.append(Paragraph(nombre_empresa.upper(), style_company))
        elements.append(Paragraph(f"RUC: {empresa.ruc}", style_normal_center))
        elements.append(Paragraph(empresa.direccion.upper(), style_normal_center))
        if empresa.ubigueo:
            elements.append(Paragraph(f"UBIGEO: {empresa.ubigueo}", style_normal_center))
        elements.append(Paragraph(f"Telf: {empresa.telefono}", style_normal_center))
        if empresa.pagina:
            elements.append(Paragraph(f"Pagina: {empresa.pagina}", style_small))
        
        elements.append(Spacer(1, 1*mm))
        elements.append(Paragraph("<b>MONEDA: SOLES (PEN)</b>", style_normal_center))
         
        elements.append(Spacer(1, 2*mm))
        elements.append(Paragraph("=" * 48, style_normal_center))
        elements.append(Spacer(1, 2*mm))
        
        # ==========================================
        # TIPO DE COMPROBANTE Y NÚMERO
        # ==========================================
        elements.append(Paragraph(f"<b>{venta.idtipocomprobante.nombre.upper()}</b>", style_header))
        elements.append(Paragraph(f"<b>{venta.numero_comprobante}</b>", style_header))
        elements.append(Spacer(1, 2*mm))
        
        # ==========================================
        # DATOS DEL CLIENTE
        # ==========================================
        cliente_nombre = venta.idcliente.razonsocial
        if len(cliente_nombre) > 35:
            cliente_nombre = cliente_nombre[:32] + '...'
        
        elements.append(Paragraph(f"<b>CLIENTE:</b>", style_bold))
        elements.append(Paragraph(f"{cliente_nombre}", style_normal_center))
        elements.append(Paragraph(f"<b>RUC/DNI:</b> {venta.idcliente.numdoc or '---'}", style_normal_center))
        if venta.idcliente.direccion:
            elements.append(Paragraph(f"<b>DIR:</b> {venta.idcliente.direccion[:40]}", style_small))
        
        if venta.idcliente.telefono:
            elements.append(Paragraph(f"<b>Tel:</b> {venta.idcliente.telefono}", style_small))
        
        elements.append(Spacer(1, 2*mm))
        elements.append(Paragraph("-" * 50, style_normal_center))
        
        # ==========================================
        # FECHA Y HORA
        # ==========================================
        fecha_str = venta.fecha_venta.strftime('%d/%m/%Y')
        try:
            hora_str = venta.fecha_venta.strftime('%I:%M %p')
        except:
            hora_str = '---'
        
        elements.append(Paragraph(f"<b>FECHA:</b> {fecha_str}  <b>HORA:</b> {hora_str}", style_normal_center))
        
        # Acortar nombre de vendedor si es muy largo
        vendedor = venta.idusuario.nombrecompleto if venta.idusuario else 'N/A'
        if len(vendedor) > 30:
            vendedor = vendedor[:27] + '...'
        elements.append(Paragraph(f"<b>VENDEDOR:</b> {vendedor}", style_small))
        
        # Buscar cajero en MovimientoCaja
        from software.models.movimientoCajaModel import MovimientoCaja
        movimiento = MovimientoCaja.objects.filter(idventa=venta, tipo_movimiento='ingreso', estado=1).first()
        
        if movimiento and movimiento.idusuario:
            cajero = movimiento.idusuario.nombrecompleto
            if len(cajero) > 30:
                cajero = cajero[:27] + '...'
            elements.append(Paragraph(f"<b>CAJERO:</b> {cajero}", style_small))
        
        # Mostrar la caja (priorizando la del cobro)
        caja_nombre = 'Caja Principal'
        if movimiento and movimiento.id_caja:
            caja_nombre = movimiento.id_caja.nombre_caja
        elif venta.id_caja:
            caja_nombre = venta.id_caja.nombre_caja
            
        elements.append(Paragraph(f"<b>CAJA:</b> {caja_nombre}", style_small))
        
        elements.append(Spacer(1, 2*mm))
        
        # ==========================================
        # DETALLE DE PRODUCTOS/SERVICIOS
        # ==========================================
        elements.append(Paragraph("-" * 50, style_normal_center))
        elements.append(Spacer(1, 1*mm))

        # Encabezado de la tabla
        data_detalle = [['CN', 'UND', 'DESCRIPCIÓN', 'P.U', 'TOTAL']]

        for detalle in detalles:
            # ✅ VALIDAR tipo de item y que los datos existan de forma resiliente
            if detalle.tipo_item == 'vehiculo' and detalle.id_vehiculo_id:
                try:
                    vehiculo = detalle.id_vehiculo
                    
                    # Validar que el vehículo tenga producto asociado
                    if not vehiculo or not vehiculo.idproducto:
                        print(f"⚠️ Detalle {detalle.idventadetalle} tiene vehículo sin producto")
                        continue
                    
                    nombre_producto = vehiculo.idproducto.nomproducto
                    codigo_int = getattr(vehiculo.idproducto, 'codigo_interno', '---') or '---'
                    unidad_med = getattr(vehiculo.idproducto.idunidad, 'codigo_sunat', 'NIU') or 'NIU'
                    
                    if len(nombre_producto) > 30:
                        nombre_producto = nombre_producto[:27] + '...'
                        
                    serie_motor = vehiculo.serie_motor[:15] if vehiculo.serie_motor else 'N/A'
                    serie_chasis = vehiculo.serie_chasis[:15] if vehiculo.serie_chasis else 'N/A'
                    
                    desc_str = f"[{codigo_int}] {nombre_producto}<br/>{serie_motor} / {serie_chasis}"
                    descripcion = Paragraph(desc_str, style_desc_table)
                except Vehiculo.DoesNotExist:
                    print(f"⚠️ ERROR: Vehículo ID {detalle.id_vehiculo_id} no existe. Omitiendo del ticket.")
                    continue
                
            elif detalle.tipo_item == 'repuesto' and detalle.id_repuesto_comprado_id:
                try:
                    repuesto = detalle.id_repuesto_comprado
                    
                    # ✅ VALIDAR que repuesto y su relación existan
                    if not repuesto or not repuesto.id_repuesto:
                        print(f"⚠️ Detalle {detalle.idventadetalle} tiene repuesto sin relación id_repuesto")
                        continue
                    
                    nombre_repuesto = repuesto.id_repuesto.nombre
                    codigo_int = getattr(repuesto.id_repuesto, 'codigo_interno', '---') or '---'
                    unidad_med = getattr(repuesto.id_repuesto.idunidad, 'codigo_sunat', 'NIU') if hasattr(repuesto.id_repuesto, 'id_unidad') else 'NIU'
                    
                    if len(nombre_repuesto) > 30:
                        nombre_repuesto = nombre_repuesto[:27] + '...'
                        
                    codigo = repuesto.id_repuesto.codigo_barras or 'S/N'
                    desc_str = f"[{codigo_int}] {nombre_repuesto}<br/>Cod: {codigo[:15]}"
                    descripcion = Paragraph(desc_str, style_desc_table)
                except Exception: # Puede ser RepuestoComp.DoesNotExist
                    print(f"⚠️ ERROR: Repuesto ID {detalle.id_repuesto_comprado_id} no existe. Omitiendo del ticket.")
                    continue
                
            elif detalle.tipo_item == 'servicio' and detalle.id_servicio_id:
                try:
                    servicio = detalle.id_servicio
                    
                    if not servicio:
                        print(f"⚠️ Detalle {detalle.idventadetalle} tiene servicio inválido")
                        continue
                        
                    nombre_servicio = servicio.nombre
                    codigo_int = 'SRV'
                    unidad_med = 'ZZ' # Unidad para servicios según SUNAT
                    
                    if len(nombre_servicio) > 40:
                        nombre_servicio = nombre_servicio[:37] + '...'
                        
                    desc_str = f"[{codigo_int}] {nombre_servicio}"
                    descripcion = Paragraph(desc_str, style_desc_table)
                except Exception:
                    print(f"⚠️ ERROR: Servicio ID {detalle.id_servicio_id} no existe. Omitiendo del ticket.")
                    continue
                
            else:
                # ✅ Si el detalle no tiene datos válidos, saltar
                print(f"⚠️ Detalle sin datos válidos - ID: {detalle.id if hasattr(detalle, 'id') else 'N/A'}, Tipo: {detalle.tipo_item}")
                continue
            
            # Cálculo matemático del precio unitario real para asegurar coherencia en el ticket
            # (Subtotal / Cantidad) refleja exactamente el precio pactado con el cliente
            if detalle.cantidad and detalle.cantidad > 0:
                precio_unitario = float(detalle.subtotal) / float(detalle.cantidad)
            else:
                precio_unitario = float(detalle.subtotal)
            
            data_detalle.append([
                str(detalle.cantidad),
                unidad_med,
                descripcion,
                f"{precio_unitario:.2f}",
                f"{detalle.subtotal:.2f}"
            ])

        # Anchos de columna para 74mm útiles
        col_widths = [6*mm, 8*mm, 35*mm, 12*mm, 13*mm]

        table_detalle = Table(data_detalle, colWidths=col_widths)
        table_detalle.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 6),
            ('ALIGN', (0, 0), (1, 0), 'CENTER'),
            ('ALIGN', (2, 0), (2, 0), 'LEFT'),
            ('ALIGN', (3, 0), (4, 0), 'RIGHT'),
            ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 6),
            ('ALIGN', (0, 1), (1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (2, -1), 'LEFT'),
            ('ALIGN', (3, 1), (4, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(table_detalle)
        
        elements.append(Spacer(1, 2*mm))
        elements.append(Paragraph("-" * 50, style_normal_center))
        elements.append(Spacer(1, 2*mm))
        
        # ==========================================
        # TOTALES
        # ==========================================
        igv_value = getattr(venta, 'igv', Decimal('0'))
        igv_code = int(venta.id_tipo_igv.codigo) if venta.id_tipo_igv and venta.id_tipo_igv.codigo else 20
        
        if igv_code in [10, 11, 12, 13, 14, 15, 16, 17]:
            data_totales = [
                ['SUBTOTAL:', f"S/ {venta.subtotal:.2f}"],
                ['IGV (18%):', f"S/ {igv_value:.2f}"],
            ]
        else:
            data_totales = [
                ['OP. EXONERADA:', f"S/ {venta.subtotal:.2f}"],
                ['IGV (0%):', f"S/ {igv_value:.2f}"],
            ]
        
        table_totales = Table(data_totales, colWidths=[50*mm, 24*mm])
        table_totales.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ]))
        elements.append(table_totales)
        
        # TOTAL
        if int(venta.id_forma_pago.id_forma_pago) == 2:
            # Si es crédito, obtener el crédito para mostrar los desgloses
            from software.models.CreditoModel import Credito
            credito = Credito.objects.filter(idventa=venta, estado=1).first()
            if credito:
                data_total = [
                    [f"TOTAL VENTA:  S/ {venta.total_venta:.2f}"],
                    [f"INICIAL:  S/ {credito.monto_adelanto:.2f}"],
                    [f"SALDO A PAGAR:  S/ {credito.saldo_pendiente:.2f}"]
                ]
            else:
                data_total = [[f"TOTAL:    S/ {venta.total_venta:.2f}"]]
        else:
            data_total = [[f"TOTAL:    S/ {venta.total_venta:.2f}"]]
            
        table_total = Table(data_total, colWidths=[ancho_util])
        table_total.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('LINEABOVE', (0, 0), (-1, 0), 1, colors.black),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        elements.append(table_total)
        
        # Importe recibido y vuelto (solo para contado)
        if venta.importe_recibido:
            elements.append(Spacer(1, 2*mm))
            data_pago = [
                ['RECIBIDO:', f"S/ {venta.importe_recibido:.2f}"],
                ['VUELTO:', f"S/ {venta.vuelto:.2f}"],
            ]
            table_pago = Table(data_pago, colWidths=[50*mm, 24*mm])
            table_pago.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('TOPPADDING', (0, 0), (-1, -1), 1),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ]))
            elements.append(table_pago)
        
        elements.append(Spacer(1, 2*mm))
        
        # ==========================================
        # FORMA DE PAGO Y TIPO
        # ==========================================
        forma_pago_nombre = venta.id_forma_pago.nombre
        tipo_pago_nombre = venta.id_tipo_pago.nombre if venta.id_tipo_pago else 'N/A'
        
        # ⭐ Mejora: Si es crédito, el tipo también debe decir Crédito
        if int(venta.id_forma_pago.id_forma_pago) == 2:
            tipo_pago_nombre = 'Crédito'
            
        elements.append(Paragraph(f"<b>FORMA DE PAGO:</b> {forma_pago_nombre}", style_normal_center))
        elements.append(Paragraph(f"<b>TIPO:</b> {tipo_pago_nombre}", style_small))
        
        # ==================== SECCIÓN DE CRÉDITO ====================
        if int(venta.id_forma_pago.id_forma_pago) == 2:
            from software.models.CreditoModel import Credito
            from software.models.CuotasVentaModel import CuotasVenta
            
            credito = Credito.objects.filter(idventa=venta, estado=1).first()
            if credito:
                elements.append(Spacer(1, 2*mm))
                elements.append(Paragraph("<b>INFORMACIÓN DE CRÉDITO</b>", style_bold))
                elements.append(Paragraph(f"Inicial: S/ {credito.monto_adelanto:.2f}", style_small))
                # ⭐ El saldo a mostrar es el saldo pendiente del crédito (Total Venta - Inicial)
                elements.append(Paragraph(f"Saldo: S/ {credito.saldo_pendiente:.2f}", style_small))
                
                # cuotas = CuotasVenta.objects.filter(idventa=venta, estado=1).order_by('numero_cuota')
                # if cuotas.exists():
                #     elements.append(Spacer(1, 1*mm))
                #     data_cuotas = [['CUOTA', 'VENCIMIENTO', 'MONTO']]
                #     for c in cuotas:
                #         venc = c.fecha_vencimiento.strftime('%d/%m/%Y') if c.fecha_vencimiento else '---'
                #         data_cuotas.append([str(c.numero_cuota), venc, f"{c.total:.2f}"])
                #     
                #     table_cuotas = Table(data_cuotas, colWidths=[15*mm, 35*mm, 24*mm])
                #     table_cuotas.setStyle(TableStyle([
                #         ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                #         ('FONTSIZE', (0, 0), (-1, -1), 6),
                #         ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                #         ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                #         ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
                #         ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                #     ]))
                #     elements.append(table_cuotas)
        
        # ==========================================
        # OBSERVACIONES
        # ==========================================
        if venta.observaciones:
            elements.append(Spacer(1, 2*mm))
            import re
            obs_text = venta.observaciones.replace('\n', '<br/>')
            obs_text = re.sub(r'\[FRACCIONADO:\s*(.*?)\]', lambda m: '<b>Pagos:</b><br/>- ' + m.group(1).replace(' | ', '<br/>- '), obs_text)
            elements.append(Paragraph(f"<b>Obs:</b> {obs_text}", style_small))
        
        # ==========================================
        # CÓDIGO QR
        # ==========================================
        try:
            elements.append(Spacer(1, 2*mm))
            
            qr_data = f"Comprobante: {venta.numero_comprobante}\n"
            qr_data += f"Cliente: {venta.idcliente.razonsocial[:30]}\n"
            qr_data += f"RUC/DNI: {venta.idcliente.numdoc or 'N/A'}\n"
            qr_data += f"Total: S/ {venta.total_venta:.2f}\n"
            qr_data += f"Fecha: {venta.fecha_venta.strftime('%d/%m/%Y')}"
            
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=8,
                border=1,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            qr_img = qr.make_image(fill_color="black", back_color="white")
            qr_buffer = BytesIO()
            qr_img.save(qr_buffer, format='PNG')
            qr_buffer.seek(0)
            
            qr_image = Image(qr_buffer, width=28*mm, height=28*mm)
            qr_image.hAlign = 'CENTER'
            elements.append(qr_image)
            
        except Exception as e:
            print(f"No se pudo generar el código QR: {str(e)}")
        
        # ==========================================
        # PIE DE PÁGINA
        # ==========================================
        elements.append(Spacer(1, 2*mm))
        elements.append(Paragraph("=" * 48, style_normal_center))
        elements.append(Spacer(1, 1*mm))
        elements.append(Paragraph("¡Gracias por su compra!", style_normal_center))
        elements.append(Paragraph("Vuelva pronto", style_small))
        
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
        response['Content-Disposition'] = f'inline; filename="ticket_{venta.numero_comprobante}.pdf"'
        
        return response
        
    except Exception as e:
        print(f"ERROR al generar comprobante: {str(e)}")
        import traceback
        traceback.print_exc()
        return HttpResponse(f"Error al generar el comprobante: {str(e)}", status=500)


# ========================================
# 🚀 SERVER-SIDE PROCESSING - VENTAS
# ========================================
def api_listar_ventas(request):
    """
    API AJAX para listar ventas con paginación, búsqueda (cliente, comprobante, vendedor) y filtro de fechas.
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    # 1. Autenticación y Permisos
    id_tipo_usuario = request.session.get('idtipousuario')
    idusuario = request.session.get('idusuario')
    id_sucursal = request.session.get('id_sucursal')

    if not id_tipo_usuario:
        return JsonResponse({'error': 'No autorizado'}, status=401)

    es_admin = (id_tipo_usuario == 1)

    # 2. Leer parámetros de la solicitud
    page_num = request.GET.get('page', '1')
    page_size = 10  # Fijo como se acordó
    search = request.GET.get('search', '').strip()
    fecha_inicio_str = request.GET.get('fecha_inicio', '').strip()
    fecha_fin_str = request.GET.get('fecha_fin', '').strip()

    # 3. Construir Filtros Base
    # Dejamos estado=1 igual que la query original
    filtros = {'estado': 1}

    # 3.1. Filtro por Sucursal
    puede_cambiar_sucursal = id_tipo_usuario in [1, 5, 6]
    
    if puede_cambiar_sucursal and id_sucursal:
        filtros['id_sucursal_id'] = id_sucursal
    elif not puede_cambiar_sucursal:
        try:
            usuario = Usuario.objects.get(idusuario=idusuario)
            filtros['id_sucursal_id'] = usuario.id_sucursal_id
        except Usuario.DoesNotExist:
            return JsonResponse({'ok': True, 'ventas': [], 'total_pages': 0})
    else:
        # Permiso de cambiar pero sin sucursal seleccionada en sesión
        return JsonResponse({'ok': True, 'ventas': [], 'total_pages': 0})

    # 3.2. Filtro por Fechas
    if fecha_inicio_str:
        filtros['fecha_venta__gte'] = f"{fecha_inicio_str} 00:00:00"
    if fecha_fin_str:
        filtros['fecha_venta__lte'] = f"{fecha_fin_str} 23:59:59"

    # 4. Query Base
    ventas_qs = Ventas.objects.filter(**filtros).select_related(
        'idcliente', 'idtipocomprobante', 'idusuario', 'id_forma_pago'
    )

    # 5. Filtro de Búsqueda Libre
    if search:
        q_search = Q(idcliente__razonsocial__icontains=search) | \
                   Q(idcliente__numdoc__icontains=search) | \
                   Q(numero_comprobante__icontains=search) | \
                   Q(idusuario__nombrecompleto__icontains=search)
        ventas_qs = ventas_qs.filter(q_search)

    # Ordenar descendente (últimas ventas primero)
    ventas_qs = ventas_qs.order_by('-idventa')

    # 6. Paginación
    paginator = Paginator(ventas_qs, page_size)
    try:
        page_obj = paginator.get_page(page_num)
    except Exception:
        page_obj = paginator.get_page(1)

    # 7. Serializar Resultados
    datos_ventas = []
    for venta in page_obj:
        # Permiso de edición
        editable = False
        if venta.estado == 1:
            if es_admin or venta.idusuario_id == idusuario:
                editable = True

        datos_ventas.append({
            'idventa': venta.idventa,
            'numero_comprobante': venta.numero_comprobante,
            'cliente_nombre': venta.idcliente.razonsocial if venta.idcliente else '',
            'fecha_venta': venta.fecha_venta.strftime("%d/%m/%Y"),
            'forma_pago_id': venta.id_forma_pago_id if venta.id_forma_pago else None,
            'total_venta': float(venta.total_venta) if venta.total_venta else 0.0,
            'total_ganancia': float(venta.total_ganancia) if venta.total_ganancia else 0.0,
            'vendedor_nombre': venta.idusuario.nombrecompleto if venta.idusuario else '',
            'estado': venta.estado,
            'estado_cobro': getattr(venta, 'estado_cobro', 'Pagado'),
            'editable': editable,
            'es_admin_front': es_admin,
            'current_user_id': idusuario
        })

    return JsonResponse({
        'ok': True,
        'ventas': datos_ventas,
        'current_page': page_obj.number,
        'total_pages': paginator.num_pages,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
        'es_admin': es_admin
    })
