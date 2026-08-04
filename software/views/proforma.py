"""
Vista del módulo de Proformas (Cotizaciones Comerciales).
Permite crear, listar y generar PDF de proformas para vehículos y repuestos.
"""
import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from io import BytesIO

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, FileResponse
from django.db import transaction
from django.conf import settings
from django.db.models import Q
from django.core.paginator import Paginator
import os

# ReportLab para generación de PDF profesional
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY

# Modelos
from software.models.ProformaModel import Proforma
from software.models.ProformaDetalleModel import ProformaDetalle
from software.models.ClienteModel import Cliente
from software.models.UsuarioModel import Usuario
from software.models.VehiculosModel import Vehiculo
from software.models.ProductoModel import Producto
from software.models.RepuestoModel import Repuesto
from software.models.RespuestoCompModel import RepuestoComp
from software.models.compradetalleModel import CompraDetalle
from software.models.stockModel import Stock
from software.models.empresaModel import Empresa
from software.models.Tipo_entidadModel import TipoEntidad
from software.models.RegionModel import Region
from software.models.FormaPagoModel import FormaPago
from software.models.ZonaCreditoModel import ZonaCredito
from software.utils.logo_utils import get_logo_image_for_pdf


# ─────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────
def _numero_proforma():
    """Genera el siguiente número correlativo de proforma (PF-YY-0000001)."""
    anio_actual = datetime.now().strftime('%y')
    ultima = Proforma.objects.order_by('-idproforma').first()
    if ultima:
        try:
            partes = ultima.numero_proforma.split('-')
            # Si el formato es PF-YY-NNNNNN, el último bloque es el número
            ultimo_num = int(partes[-1])
        except Exception:
            ultimo_num = 0
        nuevo_num = ultimo_num + 1
    else:
        nuevo_num = 1
    return f"PF-{anio_actual}-{str(nuevo_num).zfill(7)}"



def _catalogo_productos(request):
    """
    Construye el catálogo de productos y repuestos con stock disponible.
    ✅ Optimizado: usa SELECT con JOINs profundos para evitar consultas N+1.
    Se ejecutan exactamente 2-4 queries fijas (una o dos por tipo),
    sin importar cuántos productos o vehículos haya en la base de datos.
    """
    id_almacen_session = request.session.get('id_almacen')
    productos_stock = {}
    repuestos_stock = {}

    # ─── VEHÍCULOS ────────────────────────────────────────────────────────────
    stocks_vehiculos = list(
        Stock.objects
        .filter(
            id_almacen_id=id_almacen_session,
            estado=1,
            cantidad_disponible__gt=0,
            id_vehiculo__isnull=False,
            id_vehiculo__estado=1,
            id_vehiculo__id_situacion__nombre_situacion='DISPONIBLE',
            id_vehiculo__idproducto__estado=1,
        )
        .select_related(
            'id_vehiculo',
            'id_vehiculo__idproducto',
            'id_vehiculo__idproducto__idmarca',
            'id_vehiculo__idproducto__idcolor',
            'id_vehiculo__idproducto__idcilindrada',
            'id_vehiculo__id_situacion',
            'idcompradetalle',
        )
    )

    # Fallback batch: vehículos cuyo stock no tiene compradetalle enlazado directamente
    veh_sin_detalle = [s.id_vehiculo_id for s in stocks_vehiculos if not s.idcompradetalle_id]
    fallback_veh = {}
    if veh_sin_detalle:
        from django.db.models import Max
        # Una sola query: el último idcompradetalle por cada vehículo
        ultimos_ids = (
            CompraDetalle.objects
            .filter(id_vehiculo__in=veh_sin_detalle)
            .values('id_vehiculo')
            .annotate(ultimo=Max('idcompradetalle'))
            .values_list('ultimo', flat=True)
        )
        # Segunda query: traer esos registros
        for cd in CompraDetalle.objects.filter(idcompradetalle__in=list(ultimos_ids)):
            fallback_veh[cd.id_vehiculo_id] = cd

    for stock_rec in stocks_vehiculos:
        vehiculo = stock_rec.id_vehiculo
        producto = vehiculo.idproducto
        detalle  = stock_rec.idcompradetalle or fallback_veh.get(vehiculo.id_vehiculo)

        if not detalle:
            continue

        entrada = {
            'id_vehiculo':      vehiculo.id_vehiculo,
            'serie_motor':      vehiculo.serie_motor,
            'serie_chasis':     vehiculo.serie_chasis,
            'anio':             vehiculo.anio,
            'marca':            str(producto.idmarca),
            'color':            producto.idcolor.nombrecolor if producto.idcolor else '-',
            'cilindrada':       str(producto.idcilindrada),
            'precio_venta':     float(detalle.precio_maximo),
            'precio_compra':    float(detalle.precio_compra),
            'stock_disponible': stock_rec.cantidad_disponible,
        }
        productos_stock.setdefault(producto.nomproducto, []).append(entrada)

    # ─── REPUESTOS ────────────────────────────────────────────────────────────
    stocks_repuestos = list(
        Stock.objects
        .filter(
            id_almacen_id=id_almacen_session,
            estado=1,
            cantidad_disponible__gt=0,
            id_repuesto_comprado__isnull=False,
            id_repuesto_comprado__estado=1,
            id_repuesto_comprado__id_repuesto__estado=1,
        )
        .select_related(
            'id_repuesto_comprado',
            'id_repuesto_comprado__id_repuesto',
            'id_repuesto_comprado__id_repuesto__idmarca',
            'id_repuesto_comprado__id_repuesto__id_categoria_repuesto',
            'idcompradetalle',
        )
    )

    # Fallback batch: repuestos sin compradetalle enlazado
    rep_sin_detalle = [s.id_repuesto_comprado_id for s in stocks_repuestos if not s.idcompradetalle_id]
    fallback_rep = {}
    if rep_sin_detalle:
        from django.db.models import Max
        ultimos_ids = (
            CompraDetalle.objects
            .filter(id_repuesto_comprado__in=rep_sin_detalle)
            .values('id_repuesto_comprado')
            .annotate(ultimo=Max('idcompradetalle'))
            .values_list('ultimo', flat=True)
        )
        for cd in CompraDetalle.objects.filter(idcompradetalle__in=list(ultimos_ids)):
            fallback_rep[cd.id_repuesto_comprado_id] = cd

    for stock_rec in stocks_repuestos:
        rc       = stock_rec.id_repuesto_comprado
        repuesto = rc.id_repuesto
        detalle  = stock_rec.idcompradetalle or fallback_rep.get(rc.id_repuesto_comprado)

        if not detalle:
            continue

        entrada = {
            'id_repuesto_comprado': rc.id_repuesto_comprado,
            'codigo_barras':        rc.id_repuesto.codigo_barras if rc.id_repuesto.codigo_barras else 'N/A',
            'marca':                str(repuesto.idmarca),
            'color':                repuesto.id_categoria_repuesto.nomcategoria if repuesto.id_categoria_repuesto else '-',
            'precio_venta':         float(detalle.precio_maximo),
            'precio_compra':        float(detalle.precio_compra),
            'stock_disponible':     stock_rec.cantidad_disponible,
        }
        repuestos_stock.setdefault(repuesto.nombre, []).append(entrada)

    return json.dumps(productos_stock), json.dumps(repuestos_stock)


# ─────────────────────────────────────────────────
#  Vistas principales
# ─────────────────────────────────────────────────
def proformas(request):
    """Listado de proformas emitidas."""
    idusuario = request.session.get('idusuario')
    idempresa = request.session.get('idempresa')

    # Fechas por defecto para los filtros (igual que en pre-financiamiento)
    hoy = date.today()
    primer_dia_mes = hoy.replace(day=1)
    
    fecha_desde = primer_dia_mes.strftime('%Y-%m-%d')
    fecha_hasta = hoy.strftime('%Y-%m-%d')

    return render(request, 'proformas/proformas.html', {
        'proformas': [], # Enviamos vacío, la tabla se carga por AJAX
        'idusuario': idusuario,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
    })

def api_listar_proformas(request):
    """API para listar proformas con paginación y filtros (Server-Side)"""
    idusuario_session = request.session.get('idusuario')
    if not idusuario_session:
        return JsonResponse({'error': 'Sesión inválida.'}, status=401)
        
    page = int(request.GET.get('page', 1))
    search = request.GET.get('search', '').strip()
    estado = request.GET.get('estado', 'todos')
    fecha_desde_str = request.GET.get('fecha_desde', '').strip()
    fecha_hasta_str = request.GET.get('fecha_hasta', '').strip()

    # ── LAZY UPDATE: Anular proformas vencidas automáticamente ──
    try:
        from datetime import date
        Proforma.objects.filter(estado=1, fecha_vencimiento__lt=date.today()).update(estado=3)
    except Exception as e:
        print(f"Error en lazy update de proformas: {e}")

    # Empezamos con todas las proformas, las mas recientes primero
    qs = Proforma.objects.select_related('idcliente', 'idusuario').order_by('-idproforma')

    # Filtro por estado
    if estado == 'activa':
        qs = qs.filter(estado=1)
    elif estado == 'convertida':
        qs = qs.filter(estado=2)
    elif estado == 'anulada':
        qs = qs.filter(estado=3)

    # Filtro por búsqueda (N° Proforma o Cliente)
    if search:
        qs = qs.filter(
            Q(numero_proforma__icontains=search) | 
            Q(idcliente__razonsocial__icontains=search) |
            Q(idcliente__nombrecomercial__icontains=search)
        )

    # Filtro por rango de fechas (usando fecha_emision)
    if fecha_desde_str:
        try:
            fecha_desde = datetime.strptime(fecha_desde_str, '%Y-%m-%d').date()
            qs = qs.filter(fecha_emision__gte=fecha_desde)
        except ValueError:
            pass
            
    if fecha_hasta_str:
        try:
            fecha_hasta = datetime.strptime(fecha_hasta_str, '%Y-%m-%d').date()
            qs = qs.filter(fecha_emision__lte=fecha_hasta)
        except ValueError:
            pass

    # Paginación (10 registros por página)
    paginator = Paginator(qs, 10)
    try:
        proformas_page = paginator.page(page)
    except Exception:
        return JsonResponse({'error': 'Página inválida.'}, status=400)

    # Construir el JSON de respuesta
    data = []
    for p in proformas_page:
        # Formateo de fechas
        f_emision = p.fecha_emision.strftime('%d/%m/%Y') if p.fecha_emision else ''
        f_vence = p.fecha_vencimiento.strftime('%d/%m/%Y') if p.fecha_vencimiento else '—'
        
        data.append({
            'idproforma': p.idproforma,
            'numero_proforma': p.numero_proforma,
            'cliente': p.idcliente.razonsocial if p.idcliente else 'S/N',
            'fecha_emision': f_emision,
            'vencimiento': f_vence,
            'asesor': p.idusuario.nombrecompleto if p.idusuario else 'S/N',
            'subtotal': f"{p.subtotal:.2f}" if p.subtotal else "0.00",
            'igv': f"{p.igv:.2f}" if p.igv else "0.00",
            'total': f"{p.total:.2f}" if p.total else "0.00",
            'estado': p.estado
        })

    return JsonResponse({
        'ok': True,
        'data': data,
        'has_next': proformas_page.has_next(),
        'has_previous': proformas_page.has_previous(),
        'current_page': proformas_page.number,
        'num_pages': paginator.num_pages,
        'total_registros': paginator.count
    })


def nueva_proforma(request):
    """Interfaz interactiva para crear una nueva proforma."""
    if request.method == 'POST':
        return _guardar_proforma(request)

    # GET: renderizar el formulario
    idusuario = request.session.get('idusuario')
    clientes = Cliente.objects.filter(estado=1)
    productos_stock_json, repuestos_stock_json = _catalogo_productos(request)
    
    # Obtener datos de la empresa
    empresa = Empresa.objects.filter(activo=True).first()
    proforma_num = _numero_proforma()

    return render(request, 'proformas/nueva_proforma.html', {
        'clientes': clientes,
        'productos_stock': productos_stock_json,
        'repuestos_stock': repuestos_stock_json,
        'idusuario': idusuario,
        'empresa': empresa,
        'proforma_num': proforma_num,
        'tipos_entidad': TipoEntidad.objects.filter(estado=1),
        'hoy': date.today(),
        'hoy_str': date.today().strftime('%Y-%m-%d'),
        'vencimiento_default': (date.today() + timedelta(days=15)).strftime('%Y-%m-%d'),
        'regiones': Region.objects.all(),
        'forma_pago': FormaPago.objects.filter(estado=1),
        'zonas': ZonaCredito.objects.filter(estado=1),
    })



@transaction.atomic
def _guardar_proforma(request):
    """Procesa y guarda la proforma recibida por POST (AJAX) con validaciones robustas."""
    try:
        idusuario_session = request.session.get('idusuario')
        if not idusuario_session:
            return JsonResponse({'ok': False, 'error': 'Sesión inválida. Inicie sesión nuevamente.'}, status=401)

        idcliente_str = request.POST.get('cliente', '').strip()
        if not idcliente_str:
            return JsonResponse({'ok': False, 'error': 'Debe seleccionar un cliente de la lista.'}, status=400)

        # Validar existencia del cliente
        try:
            cliente = Cliente.objects.get(idcliente=idcliente_str, estado=1)
        except Cliente.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'El cliente seleccionado no es válido o está inactivo.'}, status=400)

        items_count = int(request.POST.get('items_count', 0))
        if items_count == 0:
            return JsonResponse({'ok': False, 'error': 'Debe agregar al menos un vehículo o repuesto.'}, status=400)

        observaciones = request.POST.get('observaciones', '').strip()
        fecha_vencimiento_str = request.POST.get('fecha_vencimiento', '').strip()
        
        # Validar fecha de vencimiento
        if fecha_vencimiento_str == 'custom' or not fecha_vencimiento_str:
            # Por defecto 15 días si no es válida
            fecha_vencimiento = date.today() + timedelta(days=15)
        else:
            try:
                fecha_vencimiento = datetime.strptime(fecha_vencimiento_str, '%Y-%m-%d').date()
            except:
                fecha_vencimiento = date.today() + timedelta(days=15)

        numero = _numero_proforma()
        idempresa = request.session.get('idempresa')

        # Creamos la cabecera
        # Leer campos de crédito
        forma_pago_id = request.POST.get('forma_pago', '1')
        es_credito = (forma_pago_id == '2')
        forma_pago_nombre = 'Crédito' if es_credito else 'Contado'
        
        monto_inicial = Decimal(request.POST.get('monto_inicial_venta', '0') or '0') if es_credito else Decimal('0')
        numero_cuotas = int(request.POST.get('cantidad_cuotas_config', '0') or '0') if es_credito else 0
        factor_aplicado = Decimal(request.POST.get('tasa_interes_venta', '0') or '0') if es_credito else Decimal('0') # Usaremos este campo o crearemos validación del factor si es necesario, pero simplificamos tomando montos
        monto_cuota = Decimal(request.POST.get('monto_cuota', '0') or '0') if es_credito else Decimal('0')
        interes_total = Decimal(request.POST.get('tasa_interes_venta', '0') or '0') if es_credito else Decimal('0')
        tipo_periodo = request.POST.get('tipo_periodo', 'mensual') if es_credito else 'mensual'

        proforma = Proforma.objects.create(
            numero_proforma=numero,
            idcliente=cliente,
            idusuario_id=idusuario_session,
            fecha_vencimiento=fecha_vencimiento,
            idempresa=idempresa,
            forma_pago=forma_pago_nombre,
            es_credito=es_credito,
            monto_inicial=monto_inicial,
            numero_cuotas=numero_cuotas,
            factor_aplicado=factor_aplicado,
            monto_cuota=monto_cuota,
            interes_total=interes_total,
            tipo_periodo=tipo_periodo,
            tiempo_entrega='Variable', 
            garantia='Según fabricante',
            observaciones=observaciones,
            subtotal=0,
            igv=0,
            descuento=0,
            total=0,
        )

        id_almacen_session = request.session.get('id_almacen')
        subtotal_acumulado = Decimal('0')

        # 1. Recolectar datos y agrupar IDs
        vehiculo_ids = []
        repuesto_ids = []
        parsed_items = []

        for i in range(1, items_count + 1):
            tipo_item = request.POST.get(f'tipo_item_{i}')
            if not tipo_item:
                continue

            cantidad = int(request.POST.get(f'cantidad_{i}', 0))
            if cantidad <= 0:
                raise ValueError(f'La cantidad del ítem {i} debe ser mayor a 0.')

            precio_unitario = Decimal(request.POST.get(f'precio_venta_contado_{i}', '0'))
            if precio_unitario < 0:
                raise ValueError(f'El precio del ítem {i} no puede ser negativo.')

            if tipo_item == 'vehiculo':
                id_v = request.POST.get(f'id_vehiculo_{i}')
                if not id_v:
                    raise ValueError(f'Debe seleccionar un vehículo para la fila {i}.')
                vehiculo_ids.append(id_v)
                parsed_items.append({'tipo': 'vehiculo', 'id': id_v, 'cantidad': cantidad, 'precio': precio_unitario, 'i': i})
            
            elif tipo_item == 'repuesto':
                id_r = request.POST.get(f'id_repuesto_{i}')
                if not id_r:
                    raise ValueError(f'Debe seleccionar un repuesto para la fila {i}.')
                repuesto_ids.append(id_r)
                parsed_items.append({'tipo': 'repuesto', 'id': id_r, 'cantidad': cantidad, 'precio': precio_unitario, 'i': i})

        if not parsed_items:
            raise ValueError('No se agregaron ítems válidos a la proforma.')

        # 2. Consultas masivas (evita consultas N+1 en la base de datos)
        vehiculos_map = {str(v.id_vehiculo): v for v in Vehiculo.objects.select_related('idproducto').filter(id_vehiculo__in=vehiculo_ids)}
        repuestos_map = {str(r.id_repuesto_comprado): r for r in RepuestoComp.objects.select_related('id_repuesto').filter(id_repuesto_comprado__in=repuesto_ids)}
        
        stock_vehiculos_map = {
            str(s.id_vehiculo_id): s 
            for s in Stock.objects.filter(id_vehiculo_id__in=vehiculo_ids, id_almacen_id=id_almacen_session, estado=1, cantidad_disponible__gt=0)
        }
        
        stock_repuestos_map = {
            str(s.id_repuesto_comprado_id): s 
            for s in Stock.objects.filter(id_repuesto_comprado_id__in=repuesto_ids, id_almacen_id=id_almacen_session, estado=1)
        }

        # 3. Validar y construir detalles
        detalles_a_crear = []
        
        for item in parsed_items:
            idx = item['i']
            cantidad = item['cantidad']
            subtotal_item = item['precio'] * cantidad
            
            det_kwargs = {
                'idproforma': proforma,
                'tipo_item': item['tipo'],
                'cantidad': cantidad,
                'precio_unitario': item['precio'],
                'descuento_item': 0,
                'subtotal': subtotal_item,
            }

            if item['tipo'] == 'vehiculo':
                vehiculo = vehiculos_map.get(item['id'])
                if not vehiculo:
                    raise ValueError(f'El vehículo en la fila {idx} no existe.')
                
                if item['id'] not in stock_vehiculos_map:
                    raise ValueError(f'El vehículo {vehiculo.idproducto.nomproducto} (Serie: {vehiculo.serie_motor}) no tiene stock disponible en el almacén seleccionado.')
                
                det_kwargs['id_vehiculo'] = vehiculo

            elif item['tipo'] == 'repuesto':
                repuesto_comp = repuestos_map.get(item['id'])
                if not repuesto_comp:
                    raise ValueError(f'El repuesto en la fila {idx} no existe.')
                
                stock = stock_repuestos_map.get(item['id'])
                if not stock or stock.cantidad_disponible < cantidad:
                    raise ValueError(f'No hay stock suficiente ({cantidad}) para el repuesto: {repuesto_comp.id_repuesto.nombre} en el almacén seleccionado.')
                
                det_kwargs['id_repuesto_id'] = repuesto_comp.id_repuesto_id
                
            detalles_a_crear.append(ProformaDetalle(**det_kwargs))
            subtotal_acumulado += subtotal_item

        # 4. Inserción masiva en la BD (Una sola consulta)
        ProformaDetalle.objects.bulk_create(detalles_a_crear)

        # Cálculos finales de impuestos (dinámico desde el frontend)
        porcentaje_igv = Decimal(request.POST.get('porcentaje_igv', '0'))
        igv_monto = (subtotal_acumulado * (porcentaje_igv / 100)).quantize(Decimal('0.01'))
        total_final = subtotal_acumulado + igv_monto

        proforma.subtotal = subtotal_acumulado
        proforma.igv = igv_monto
        proforma.total = total_final
        proforma.save()

        return JsonResponse({
            'ok': True,
            'message': f'Proforma {numero} guardada correctamente.',
            'numero_proforma': numero,
            'idproforma': proforma.idproforma
        })

    except ValueError as ve:
        transaction.set_rollback(True)
        return JsonResponse({'ok': False, 'error': str(ve)}, status=400)
    except Exception as e:
        transaction.set_rollback(True)
        import traceback
        traceback.print_exc()
        return JsonResponse({'ok': False, 'error': f'Ocurrió un error inesperado al guardar: {str(e)}'}, status=500)



def proforma_pdf(request, idproforma):
    """
    Genera el documento PDF profesional de la proforma en formato A4.
    Diseño corporativo estilo concesionario automotriz.
    """
    proforma = get_object_or_404(Proforma, idproforma=idproforma)
    detalles = ProformaDetalle.objects.filter(idproforma=proforma).select_related(
        'id_vehiculo__idproducto__idmarca',
        'id_vehiculo__idproducto__idcolor',
        'id_vehiculo__idproducto__idcilindrada',
        'id_repuesto__idmarca',
        'id_repuesto__id_categoria_repuesto',
    ).prefetch_related(
        'id_vehiculo__stocks__idcompradetalle',
        'id_repuesto__repuestocomprados',
    )

    # Datos de empresa
    empresa = Empresa.objects.filter(activo=True).first()

    # ── Buffer PDF ────────────────────────────────────────────────────
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=2 * cm,
    )

    # ── Paleta de colores corporativa ─────────────────────────────────
    DARK_BLUE   = colors.HexColor('#0D1B2A')   # Fondo encabezado
    ACCENT_BLUE = colors.HexColor('#1A73E8')   # Líneas / resaltados
    SILVER      = colors.HexColor('#B0BEC5')   # Líneas suaves
    LIGHT_GRAY  = colors.HexColor('#F4F6F8')   # Fondo filas alternas
    WHITE       = colors.white
    TEXT_DARK   = colors.HexColor('#212121')   # Texto principal
    TEXT_MUTED  = colors.HexColor('#546E7A')   # Texto secundario
    GREEN       = colors.HexColor('#1B5E20')   # Total resaltado
    GOLD        = colors.HexColor('#F4A900')   # Acento dorado

    # ── Estilos ───────────────────────────────────────────────────────
    styles = getSampleStyleSheet()

    def style(name, **kwargs):
        base = styles.get(name, styles['Normal'])
        return ParagraphStyle(name + '_custom', parent=base, **kwargs)

    s_empresa      = style('Heading1', fontSize=18, fontName='Helvetica-Bold', textColor=DARK_BLUE, leading=22, spaceAfter=4)
    s_empresa_sub  = style('Normal', fontSize=8,  fontName='Helvetica',      textColor=TEXT_MUTED, leading=10)
    s_titulo_box   = style('Normal', fontSize=9,  fontName='Helvetica-Bold', textColor=ACCENT_BLUE, spaceBefore=2, spaceAfter=1)
    s_cliente_data = style('Normal', fontSize=9,  fontName='Helvetica',      textColor=TEXT_DARK, leading=14)
    s_th           = style('Normal', fontSize=8,  fontName='Helvetica-Bold', textColor=WHITE, alignment=TA_CENTER)
    s_cell         = style('Normal', fontSize=8,  fontName='Helvetica',      textColor=TEXT_DARK, leading=11)
    s_cell_center  = style('Normal', fontSize=8,  fontName='Helvetica',      textColor=TEXT_DARK, alignment=TA_CENTER, leading=11)
    s_cell_right   = style('Normal', fontSize=8,  fontName='Helvetica',      textColor=TEXT_DARK, alignment=TA_RIGHT,  leading=11)
    s_total_label  = style('Normal', fontSize=9,  fontName='Helvetica',      textColor=TEXT_DARK, alignment=TA_RIGHT)
    s_total_final  = style('Normal', fontSize=13, fontName='Helvetica-Bold', textColor=GREEN, alignment=TA_RIGHT)
    s_condicion    = style('Normal', fontSize=10,  fontName='Helvetica',      textColor=TEXT_DARK, leading=13)
    s_nota_legal   = style('Normal', fontSize=7,  fontName='Helvetica-Oblique', textColor=TEXT_MUTED, alignment=TA_CENTER)
    s_firma_label  = style('Normal', fontSize=8,  fontName='Helvetica-Bold', textColor=TEXT_DARK, alignment=TA_CENTER)
    s_firma_sub    = style('Normal', fontSize=8,  fontName='Helvetica',      textColor=TEXT_MUTED, alignment=TA_CENTER)
    s_section_hdr  = style('Normal', fontSize=9,  fontName='Helvetica-Bold', textColor=DARK_BLUE, spaceBefore=6, spaceAfter=3)

    story = []

    # ═══════════════════════════════════════════════════════════════════
    # SECCIÓN 1: ENCABEZADO
    # ═══════════════════════════════════════════════════════════════════
    empresa_nombre = empresa.nombrecomercial if empresa else 'EMPRESA S.A.C.'
    empresa_ruc    = f"RUC: {empresa.ruc}" if empresa else 'RUC: 00000000000'
    empresa_dir    = empresa.direccion if empresa else '-'
    empresa_tel    = f"Telf.: {empresa.telefono}" if (empresa and empresa.telefono) else ''
    empresa_email  = f"Email: {empresa.pagina}" if (empresa and empresa.pagina) else ''

    col_logo = Paragraph(
        f'<font color="white" size="28">&#9670;</font>',  # rombo decorativo si no hay logo externo
        ParagraphStyle('logo_icon', fontSize=28, textColor=GOLD, alignment=TA_LEFT)
    )
    # LOGO DESDE CLOUDINARY
    logo_rl = get_logo_image_for_pdf(empresa, width_mm=35, height_mm=22, circular=False)
    left_col = logo_rl if logo_rl else col_logo

    empresa_info = [
        Paragraph(empresa_nombre, s_empresa),
        Paragraph(empresa_ruc, s_empresa_sub),
        Paragraph(empresa_dir, s_empresa_sub),
        Paragraph(empresa_tel, s_empresa_sub),
        Paragraph(empresa_email, s_empresa_sub),
    ]

    proforma_info = [
        Paragraph('<font color="#F4A900"><b>PROFORMA</b></font>',
                  ParagraphStyle('pf_num', fontSize=20, fontName='Helvetica-Bold',
                                 textColor=GOLD, alignment=TA_RIGHT, leading=24)),
        Paragraph(f'<b>N°: {proforma.numero_proforma}</b>',
                  ParagraphStyle('pf_n', fontSize=11, fontName='Helvetica-Bold',
                                 textColor=DARK_BLUE, alignment=TA_RIGHT, leading=14)),
        Paragraph(f'Fecha: {proforma.fecha_emision.strftime("%d/%m/%Y")}',
                  ParagraphStyle('pf_d', fontSize=9, fontName='Helvetica',
                                 textColor=TEXT_MUTED, alignment=TA_RIGHT)),
    ]
    if proforma.fecha_vencimiento:
        proforma_info.append(
            Paragraph(f'Válida hasta: {proforma.fecha_vencimiento.strftime("%d/%m/%Y")}',
                      ParagraphStyle('pf_v', fontSize=9, fontName='Helvetica',
                                     textColor=TEXT_MUTED, alignment=TA_RIGHT))
        )

    info_table = Table(
        [[left_col, empresa_info, proforma_info]],
        colWidths=[4.2 * cm, 9.3 * cm, 5 * cm]
    )
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), WHITE),
        ('BOX', (0, 0), (-1, -1), 0.8, SILVER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (0, 0), 10),
        ('LEFTPADDING', (1, 0), (1, 0), 8),
        ('RIGHTPADDING', (-1, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('ROUNDEDCORNERS', [6, 6, 6, 6]),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 8))

    # ═══════════════════════════════════════════════════════════════════
    # SECCIÓN 2: DATOS DEL CLIENTE
    # ═══════════════════════════════════════════════════════════════════
    cliente = proforma.idcliente
    cliente_rows = [
        [Paragraph('<b>DATOS DEL CLIENTE</b>',
                   ParagraphStyle('cli_hdr', fontSize=9, fontName='Helvetica-Bold',
                                  textColor=ACCENT_BLUE)), ''],
        [Paragraph('<b>Razón Social / Nombre:</b>', s_cliente_data),
         Paragraph(cliente.razonsocial or '-', s_cliente_data)],
        [Paragraph('<b>DNI / RUC:</b>', s_cliente_data),
         Paragraph(cliente.numdoc or '-', s_cliente_data)],
        [Paragraph('<b>Dirección:</b>', s_cliente_data),
         Paragraph(cliente.direccion or '-', s_cliente_data)],
        [Paragraph('<b>Teléfono:</b>', s_cliente_data),
         Paragraph(cliente.telefono or '-', s_cliente_data)],
    ]
    cli_table = Table(cliente_rows, colWidths=[5 * cm, 13.5 * cm])
    cli_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT_GRAY),
        ('SPAN', (0, 0), (-1, 0)),
        ('BOX', (0, 0), (-1, -1), 0.8, SILVER),
        ('INNERGRID', (0, 1), (-1, -1), 0.3, SILVER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(cli_table)
    story.append(Spacer(1, 10))

    # ─── Separar items por tipo ──────────────────────────────────────
    vehiculos_det  = [d for d in detalles if d.tipo_item == 'vehiculo']
    repuestos_det  = [d for d in detalles if d.tipo_item == 'repuesto']

    # ═══════════════════════════════════════════════════════════════════
    # SECCIÓN 3a: TABLA DE VEHÍCULOS
    # ═══════════════════════════════════════════════════════════════════
    if vehiculos_det:
        story.append(Paragraph('VEHÍCULOS', s_section_hdr))
        veh_headers = ['Ítem', 'Nombre', 'Marca', 'Color', 'Cilindrada', 'Año', 'Cant.', 'Precio Unit.', 'Subtotal']
        veh_col_w   = [1*cm, 3.5*cm, 2.5*cm, 2*cm, 2*cm, 1.5*cm, 1.2*cm, 2.5*cm, 2.3*cm]
        veh_data    = [[Paragraph(h, s_th) for h in veh_headers]]

        for idx, det in enumerate(vehiculos_det, start=1):
            prod = det.id_vehiculo.idproducto if det.id_vehiculo else None
            veh  = det.id_vehiculo

            # Nombre + series debajo en texto pequeño gris
            nombre_text = prod.nomproducto if prod else '-'
            if veh and (veh.serie_motor or veh.serie_chasis):
                motor  = veh.serie_motor or 'S/N'
                chasis = veh.serie_chasis or 'S/N'
                nombre_cell = Paragraph(
                    f'{nombre_text}<br/><font size="6.5" color="#555555">'
                    f'Motor: {motor} | Chasis: {chasis}</font>',
                    s_cell
                )
            else:
                nombre_cell = Paragraph(nombre_text, s_cell)

            fila = [
                Paragraph(str(idx), s_cell_center),
                nombre_cell,
                Paragraph(prod.idmarca.nombremarca if prod and prod.idmarca else '-', s_cell),
                Paragraph(prod.idcolor.nombrecolor if prod and prod.idcolor else '-', s_cell),
                Paragraph(prod.idcilindrada.cilindrada_cc if prod and prod.idcilindrada else '-', s_cell_center),
                Paragraph(str(det.id_vehiculo.anio or '-'), s_cell_center),
                Paragraph(str(det.cantidad), s_cell_center),
                Paragraph(f'S/ {det.precio_unitario:,.2f}', s_cell_right),
                Paragraph(f'S/ {det.subtotal:,.2f}', s_cell_right),
            ]
            veh_data.append(fila)

        veh_table = Table(veh_data, colWidths=veh_col_w, repeatRows=1)
        veh_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), DARK_BLUE),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
            ('BOX', (0, 0), (-1, -1), 0.8, SILVER),
            ('INNERGRID', (0, 0), (-1, -1), 0.3, SILVER),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(veh_table)
        story.append(Spacer(1, 8))

    # ═══════════════════════════════════════════════════════════════════
    # SECCIÓN 3b: TABLA DE REPUESTOS
    # ═══════════════════════════════════════════════════════════════════
    if repuestos_det:
        story.append(Paragraph('REPUESTOS & ACCESORIOS', s_section_hdr))
        rep_headers = ['Ítem', 'Nombre', 'Marca', 'Color', 'Cant.', 'Precio Unit.', 'Subtotal']
        rep_col_w   = [1*cm, 5*cm, 3*cm, 2.5*cm, 1.5*cm, 3*cm, 2.5*cm]
        rep_data    = [[Paragraph(h, s_th) for h in rep_headers]]

        for idx, det in enumerate(repuestos_det, start=1):
            rep = det.id_repuesto

            # Buscar el codigo_barras desde Repuesto directamente
            codigo_barras = '-'
            if rep and rep.codigo_barras:
                codigo_barras = rep.codigo_barras

            # Nombre + código de barras debajo en texto pequeño gris
            nombre_rep = rep.nombre if rep else '-'
            if codigo_barras and codigo_barras != '-':
                nombre_rep_cell = Paragraph(
                    f'{nombre_rep}<br/><font size="6.5" color="#555555">'
                    f'Cód. Barras: {codigo_barras}</font>',
                    s_cell
                )
            else:
                nombre_rep_cell = Paragraph(nombre_rep, s_cell)

            fila = [
                Paragraph(str(idx), s_cell_center),
                nombre_rep_cell,
                Paragraph(rep.idmarca.nombremarca if rep and rep.idmarca else '-', s_cell),
                Paragraph(rep.id_categoria_repuesto.nomcategoria if rep and rep.id_categoria_repuesto else '-', s_cell),
                Paragraph(str(det.cantidad), s_cell_center),
                Paragraph(f'S/ {det.precio_unitario:,.2f}', s_cell_right),
                Paragraph(f'S/ {det.subtotal:,.2f}', s_cell_right),
            ]
            rep_data.append(fila)

        rep_table = Table(rep_data, colWidths=rep_col_w, repeatRows=1)
        rep_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), DARK_BLUE),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
            ('BOX', (0, 0), (-1, -1), 0.8, SILVER),
            ('INNERGRID', (0, 0), (-1, -1), 0.3, SILVER),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(rep_table)
        story.append(Spacer(1, 8))

    # ═══════════════════════════════════════════════════════════════════
    # SECCIÓN 4: RESUMEN ECONÓMICO
    # ═══════════════════════════════════════════════════════════════════
    blank   = Paragraph('', styles['Normal'])
    # Calcular % de IGV para el label
    pct_igv = 0
    if proforma.subtotal > 0:
        pct_igv = (proforma.igv / proforma.subtotal) * 100

    summary = [
        [blank,
         Paragraph('Subtotal:', s_total_label),
         Paragraph(f'S/ {proforma.subtotal:,.2f}', s_total_label)],
        [blank,
         Paragraph(f'IGV ({pct_igv:.0f}%):', s_total_label),
         Paragraph(f'S/ {proforma.igv:,.2f}', s_total_label)],
        [blank,
         Paragraph('Descuento:', s_total_label),
         Paragraph(f'S/ {proforma.descuento:,.2f}', s_total_label)],
        [blank,
         Paragraph('<b>TOTAL:</b>', s_total_final),
         Paragraph(f'<b>S/ {proforma.total:,.2f}</b>', s_total_final)],
    ]
    sum_table = Table(summary, colWidths=[9 * cm, 5 * cm, 4.5 * cm])
    sum_table.setStyle(TableStyle([
        ('BACKGROUND', (1, 0), (2, 2), LIGHT_GRAY),
        ('BACKGROUND', (1, 3), (2, 3), colors.HexColor('#E8F5E9')),
        ('BOX', (1, 0), (2, 3), 1, ACCENT_BLUE),
        ('INNERGRID', (1, 0), (2, 3), 0.3, SILVER),
        ('LINEABOVE', (1, 3), (2, 3), 1.5, GREEN),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (1, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (1, 0), (-1, -1), 5),
        ('LEFTPADDING', (1, 0), (-1, -1), 8),
        ('RIGHTPADDING', (-1, 0), (-1, -1), 8),
    ]))
    story.append(sum_table)
    story.append(Spacer(1, 12))

    # ═══════════════════════════════════════════════════════════════════
    # SECCIÓN 4.5: INFORMACIÓN DE CRÉDITO
    # ═══════════════════════════════════════════════════════════════════
    if getattr(proforma, 'es_credito', False):
        periodo_texto = "meses"
        if getattr(proforma, 'tipo_periodo', '') == 'dias':
            periodo_texto = "días"
        elif getattr(proforma, 'tipo_periodo', '') == 'semanal':
            periodo_texto = "semanas"
        elif getattr(proforma, 'tipo_periodo', '') == 'quincenal':
            periodo_texto = "quincenas"
            
        texto_credito = f"<b>Condiciones de Financiamiento:</b> Inicial S/ {proforma.monto_inicial:,.2f} con un precio total de S/ {proforma.total:,.2f} por {proforma.numero_cuotas} {periodo_texto}. La cuota es S/ {proforma.monto_cuota:,.2f} por {proforma.numero_cuotas} {periodo_texto}."
        story.append(Paragraph(texto_credito, ParagraphStyle(
            name='CreditoStyle',
            fontName='Helvetica',
            fontSize=10,
            textColor=colors.HexColor('#0b1c3f'),
            backColor=colors.HexColor('#e3f2fd'),
            borderPadding=8,
            borderColor=colors.HexColor('#90caf9'),
            borderWidth=1,
            borderRadius=4,
            spaceAfter=10,
            alignment=TA_CENTER
        )))
        story.append(Spacer(1, 12))

    # ═══════════════════════════════════════════════════════════════════
    # SECCIÓN 5: CONDICIONES COMERCIALES
    # ═══════════════════════════════════════════════════════════════════
    story.append(HRFlowable(width='100%', thickness=0.5, color=SILVER))
    story.append(Spacer(1, 6))

    cond_data = [
        [Paragraph('<b>CONDICIONES COMERCIALES</b>',
                   ParagraphStyle('cc_hdr', fontSize=10, fontName='Helvetica-Bold',
                                  textColor=ACCENT_BLUE)), '', ''],
        [Paragraph(f'<b>Forma de pago:</b> {proforma.forma_pago}', s_condicion),
         Paragraph(f'<b>Tiempo de entrega:</b> {proforma.tiempo_entrega}', s_condicion),
         Paragraph(f'<b>Garantía:</b> {proforma.garantia}', s_condicion)],
    ]
    cond_table = Table(cond_data, colWidths=[6.1 * cm, 6.2 * cm, 6.2 * cm])
    cond_table.setStyle(TableStyle([
        ('SPAN', (0, 0), (-1, 0)),
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT_GRAY),
        ('BOX', (0, 0), (-1, -1), 0.8, SILVER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(cond_table)
    
    if empresa and getattr(empresa, 'condiciones_comerciales', None):
        cond_text = empresa.condiciones_comerciales.replace('\n', '<br/>')
        story.append(Spacer(1, 6))
        story.append(Paragraph(cond_text, s_condicion))

    if proforma.observaciones:
        story.append(Spacer(1, 4))
        obs_text = proforma.observaciones.replace('\n', '<br/>')
        story.append(Paragraph(f'<b>Observaciones:</b><br/>{obs_text}', s_condicion))

    story.append(Spacer(1, 6))
    story.append(Paragraph(
        '⚠  Este documento es una PROFORMA (cotización) y NO constituye comprobante de pago. '
        'Los precios son referenciales y válidos hasta la fecha indicada.',
        s_nota_legal
    ))
    story.append(Spacer(1, 16))

    # ═══════════════════════════════════════════════════════════════════
    # SECCIÓN 6: ÁREA DE FIRMA
    # ═══════════════════════════════════════════════════════════════════
    asesor = proforma.idusuario
    asesor_nombre = asesor.nombrecompleto if asesor else '___________________________'

    firma_data = [
        ['', ''],
        [Paragraph('_________________________', s_firma_label),
         Paragraph('_________________________', s_firma_label)],
        [Paragraph('Sello y Firma Autorizada', s_firma_label),
         Paragraph('Aceptación del Cliente', s_firma_label)],
        [Paragraph(empresa_nombre, s_firma_sub),
         Paragraph('Confirmación de pedido', s_firma_sub)],
    ]
    firma_table = Table(firma_data, colWidths=[9.25 * cm, 9.25 * cm])
    firma_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('LINEBELOW', (0, 1), (0, 1), 0.8, DARK_BLUE),
        ('LINEBELOW', (1, 1), (1, 1), 0.8, DARK_BLUE),
        ('BOX', (0, 0), (-1, -1), 0.5, SILVER),
        ('ROWBACKGROUNDS', (0, 0), (-1, 0), [LIGHT_GRAY]),
    ]))
    story.append(firma_table)

    # ── Generar PDF ───────────────────────────────────────────────────
    doc.build(story)
    buffer.seek(0)

    response = FileResponse(
        buffer,
        content_type='application/pdf',
        as_attachment=False,
    )
    response['Content-Disposition'] = (
        f'inline; filename="Proforma_{proforma.numero_proforma}.pdf"'
    )
    return response


def eliminar_proforma(request, idproforma):
    """Anula (eliminación lógica) de una proforma."""
    if request.method == 'POST':
        proforma = get_object_or_404(Proforma, idproforma=idproforma)
        proforma.estado = 3  # Anulada
        proforma.save()
        return JsonResponse({'ok': True, 'message': 'Proforma anulada correctamente.'})
    return JsonResponse({'ok': False, 'error': 'Método no permitido.'}, status=405)


def editar_proforma(request, idproforma):
    """Interfaz para editar una proforma existente."""
    proforma = get_object_or_404(Proforma, idproforma=idproforma)
    
    if request.method == 'POST':
        return _actualizar_proforma(request, idproforma)

    # GET: renderizar el formulario con datos precargados
    idusuario = request.session.get('idusuario')
    clientes = Cliente.objects.filter(estado=1)
    productos_stock_json, repuestos_stock_json = _catalogo_productos(request)
    
    # Datos de la empresa
    empresa = Empresa.objects.filter(activo=True).first()
    
    # Calcular porcentaje de IGV real
    porcentaje_igv = 0
    if proforma.subtotal > 0:
        porcentaje_igv = (proforma.igv / proforma.subtotal * 100).quantize(Decimal('0'))

    # Obtener detalles para precargar en el JS
    detalles_qs = list(ProformaDetalle.objects.filter(idproforma=proforma).select_related(
        'id_vehiculo__idproducto__idcolor', 
        'id_repuesto__id_categoria_repuesto'
    ))
    
    # ─── BULK FETCH PRECIOS BASE ───
    from software.models.CompraModel import CompraDetalle
    from software.models.RespuestoCompModel import RepuestoComp

    # Para vehículos
    vehiculos_ids = [d.id_vehiculo_id for d in detalles_qs if d.tipo_item == 'vehiculo' and d.id_vehiculo_id]
    precio_vehiculos = {}
    if vehiculos_ids:
        cds_v = CompraDetalle.objects.filter(id_vehiculo_id__in=vehiculos_ids).order_by('idcompradetalle')
        for cd in cds_v:
            precio_vehiculos[cd.id_vehiculo_id] = float(cd.precio_maximo)

    # Para repuestos
    repuestos_ids = [d.id_repuesto_id for d in detalles_qs if d.tipo_item == 'repuesto' and d.id_repuesto_id]
    codigo_repuestos = {}
    precio_repuestos = {}
    if repuestos_ids:
        rc_list = RepuestoComp.objects.filter(id_repuesto_id__in=repuestos_ids).select_related('id_repuesto')
        rc_dict = {}
        for rc in rc_list:
            rc_dict[rc.id_repuesto_id] = rc
            codigo_repuestos[rc.id_repuesto_id] = rc.id_repuesto.codigo_barras if rc.id_repuesto else 'S/N'
        
        rc_comprados_ids = [rc.id_repuesto_comprado for rc in rc_list]
        cds_r = CompraDetalle.objects.filter(id_repuesto_comprado__in=rc_comprados_ids).order_by('idcompradetalle')
        for cd in cds_r:
            precio_repuestos[cd.id_repuesto_comprado] = float(cd.precio_maximo)
            
    detalles_json = []
    for d in detalles_qs:
        item = {
            'tipo': d.tipo_item,
            'cantidad': d.cantidad,
            'precio': float(d.precio_unitario),
            'subtotal': float(d.subtotal),
            'precio_base': 0.0,
        }
        if d.tipo_item == 'vehiculo' and d.id_vehiculo:
            prod = d.id_vehiculo.idproducto
            item.update({
                'id_item': d.id_vehiculo_id,
                'nombre_producto': prod.nomproducto if prod else 'N/A',
                'detalle_text': f"Serie Motor: {d.id_vehiculo.serie_motor or 'S/N'}",
                'anio': d.id_vehiculo.anio or '-',
                'color': prod.idcolor.nombrecolor if (prod and prod.idcolor) else '-',
                'stock': 1,
                'precio_base': precio_vehiculos.get(d.id_vehiculo_id, 0.0),
            })
        elif d.tipo_item == 'repuesto' and d.id_repuesto:
            rc = rc_dict.get(d.id_repuesto_id)
            codigo = codigo_repuestos.get(d.id_repuesto_id, 'S/N')
            precio_base = precio_repuestos.get(rc.id_repuesto_comprado, 0.0) if rc else 0.0
            
            item.update({
                'id_item': d.id_repuesto_id,
                'nombre_producto': d.id_repuesto.nombre if d.id_repuesto else 'N/A',
                'detalle_text': f"Código: {codigo}",
                'anio': '-',
                'color': d.id_repuesto.id_categoria_repuesto.nomcategoria if (d.id_repuesto and d.id_repuesto.id_categoria_repuesto) else '-',
                'stock': d.cantidad,
                'precio_base': precio_base,
            })
        detalles_json.append(item)

    return render(request, 'proformas/nueva_proforma.html', {
        'proforma_edit': proforma,
        'detalles_edit_json': json.dumps(detalles_json),
        'porcentaje_igv_edit': porcentaje_igv,
        'clientes': clientes,
        'productos_stock': productos_stock_json,
        # ...
        'repuestos_stock': repuestos_stock_json,
        'idusuario': idusuario,
        'empresa': empresa,
        'proforma_num': proforma.numero_proforma,
        'tipos_entidad': TipoEntidad.objects.filter(estado=1),
        'hoy': proforma.fecha_emision,
        'hoy_str': proforma.fecha_emision.strftime('%Y-%m-%d'),
        'vencimiento_default': proforma.fecha_vencimiento.strftime('%Y-%m-%d') if proforma.fecha_vencimiento else '',
        'regiones': Region.objects.all(),
    })


@transaction.atomic
def _actualizar_proforma(request, idproforma):
    """Actualiza una proforma existente."""
    try:
        proforma = get_object_or_404(Proforma, idproforma=idproforma)
        
        idusuario_session = request.session.get('idusuario')
        if not idusuario_session:
            return JsonResponse({'ok': False, 'error': 'Sesión inválida.'}, status=401)

        idcliente_str = request.POST.get('cliente', '').strip()
        if not idcliente_str:
            return JsonResponse({'ok': False, 'error': 'Debe seleccionar un cliente.'}, status=400)

        cliente = Cliente.objects.get(idcliente=idcliente_str, estado=1)
        items_count = int(request.POST.get('items_count', 0))
        
        observaciones = request.POST.get('observaciones', '').strip()
        fecha_vencimiento_str = request.POST.get('fecha_vencimiento', '').strip()
        
        if fecha_vencimiento_str == 'custom' or not fecha_vencimiento_str:
            fecha_vencimiento = date.today() + timedelta(days=15)
        else:
            try:
                fecha_vencimiento = datetime.strptime(fecha_vencimiento_str, '%Y-%m-%d').date()
            except:
                fecha_vencimiento = date.today() + timedelta(days=15)

        # Actualizamos cabecera
        proforma.idcliente = cliente
        proforma.fecha_vencimiento = fecha_vencimiento
        proforma.observaciones = observaciones
        
        # Eliminamos detalles anteriores para reemplazarlos
        ProformaDetalle.objects.filter(idproforma=proforma).delete()

        subtotal_acumulado = Decimal('0')
        valid_items = 0

        for i in range(1, items_count + 1):
            tipo_item = request.POST.get(f'tipo_item_{i}')
            if not tipo_item: continue

            cantidad = int(request.POST.get(f'cantidad_{i}', 0))
            if cantidad <= 0: continue

            precio_unitario = Decimal(request.POST.get(f'precio_venta_contado_{i}', '0'))
            subtotal_item = precio_unitario * cantidad

            det_kwargs = {
                'idproforma': proforma,
                'tipo_item': tipo_item,
                'cantidad': cantidad,
                'precio_unitario': precio_unitario,
                'descuento_item': 0,
                'subtotal': subtotal_item,
            }

            if tipo_item == 'vehiculo':
                id_v = request.POST.get(f'id_vehiculo_{i}')
                if id_v:
                    det_kwargs['id_vehiculo'] = Vehiculo.objects.get(id_vehiculo=id_v)
            elif tipo_item == 'repuesto':
                id_r = request.POST.get(f'id_repuesto_{i}')
                if id_r:
                    # En la proforma original se guardaba id_repuesto_id del Repuesto
                    # Aquí intentamos mantener la consistencia
                    try:
                        # Primero probamos si es un RepuestoComp ID (comportamiento original del front)
                        rc = RepuestoComp.objects.get(id_repuesto_comprado=id_r)
                        det_kwargs['id_repuesto_id'] = rc.id_repuesto_id
                    except:
                        # Si no, asumimos que es directamente el ID del Repuesto
                        det_kwargs['id_repuesto_id'] = id_r

            ProformaDetalle.objects.create(**det_kwargs)
            subtotal_acumulado += subtotal_item
            valid_items += 1

        if valid_items == 0:
            raise ValueError('Debe agregar al menos un ítem.')

        porcentaje_igv = Decimal(request.POST.get('porcentaje_igv', '0'))
        igv_monto = (subtotal_acumulado * (porcentaje_igv / 100)).quantize(Decimal('0.01'))
        
        proforma.subtotal = subtotal_acumulado
        proforma.igv = igv_monto
        proforma.total = subtotal_acumulado + igv_monto
        proforma.save()

        return JsonResponse({
            'ok': True,
            'message': 'Proforma actualizada correctamente.',
            'idproforma': proforma.idproforma,
            'numero_proforma': proforma.numero_proforma
        })

    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)
