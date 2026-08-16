"""
Vistas para el submódulo "Comprobantes de Venta" dentro de Facturación Electrónica.
Incluye las 3 pestañas: Factura Electrónica, Boleta de Venta y Liquidación de Compra.

Las vistas leen credenciales y modo de la tabla 'empresa' automáticamente.
Implementa Server-Side Processing (paginación, búsqueda y orden en el servidor)
para soportar grandes volúmenes de datos sin degradar el rendimiento.
"""

import logging
from datetime import datetime
from django.db.models import Q

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from software.models.VentasModel import Ventas

logger = logging.getLogger(__name__)


# ─── Utilidades comunes ────────────────────────────────────────────────────────

def _check_sesion(request):
    """Retorna True si hay sesión activa."""
    return bool(request.session.get('idusuario'))


def _base_qs(codigo_tipo):
    """
    QuerySet base sin paginación, con select_related para evitar consultas N+1.
    Trae cliente, tipo de comprobante y serie en un único JOIN.
    """
    return (
        Ventas.objects
        .filter(estado=1, idtipocomprobante__codigo=codigo_tipo)
        .select_related(
            'idcliente',
            'idtipocomprobante',
            'idseriecomprobante',
            'id_forma_pago',
        )
        .order_by('-fecha_venta')
    )


def _aplicar_filtros_fecha(qs, request):
    """
    Aplica filtros de fecha al QuerySet si se reciben los parámetros
    fecha_inicio y fecha_fin en el GET de la petición.
    """
    fecha_inicio = request.GET.get('fecha_inicio', '').strip()
    fecha_fin    = request.GET.get('fecha_fin', '').strip()

    if fecha_inicio:
        try:
            qs = qs.filter(
                fecha_venta__date__gte=datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            )
        except ValueError:
            pass

    if fecha_fin:
        try:
            qs = qs.filter(
                fecha_venta__date__lte=datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            )
        except ValueError:
            pass

    return qs


def _aplicar_busqueda(qs, search_value):
    """
    Aplica búsqueda de texto libre sobre campos de cliente y número de comprobante.
    Se hace con un único OR en la consulta SQL (no genera N+1).
    """
    if search_value:
        qs = qs.filter(
            Q(idcliente__razonsocial__icontains=search_value) |
            Q(idcliente__numdoc__icontains=search_value) |
            Q(numero_comprobante__icontains=search_value)
        )
    return qs


def _aplicar_filtro_sunat(qs, request):
    """
    Filtra por estado SUNAT si el parámetro 'sunat_estado' viene en el GET.
    Valores: 0=Pendiente, 1=Aceptado, 2=Rechazado, 3=Error
    """
    sunat_estado = request.GET.get('sunat_estado', '').strip()
    if sunat_estado != '':
        try:
            qs = qs.filter(sunat_estado=int(sunat_estado))
        except ValueError:
            pass
    return qs


def _venta_to_dict(v):
    """Serializa una instancia de Ventas a dict para respuesta JSON."""
    return {
        'idventa':          v.idventa,
        'fecha':            v.fecha_venta.strftime('%d/%m/%Y'),
        'hora':             v.fecha_venta.strftime('%H:%M'),
        'serie':            v.idseriecomprobante.serie if v.idseriecomprobante else '',
        'numero':           v.numero_comprobante,
        'comprobante':      v.numero_comprobante,
        'tipo':             v.idtipocomprobante.nombre if v.idtipocomprobante else '',
        'cliente':          v.idcliente.razonsocial if v.idcliente else '',
        'numdoc':           v.idcliente.numdoc if v.idcliente else '',
        'total':            float(v.total_venta),
        'subtotal':         float(v.subtotal),
        'igv':              float(v.igv),
        'sunat_estado':     v.sunat_estado,
        'sunat_estado_label': _estado_label(v.sunat_estado),
        'sunat_xml':        v.sunat_xml or '',
        'sunat_error':      v.sunat_error or '',
    }


def _estado_label(estado):
    """Retorna la etiqueta de texto para el estado SUNAT."""
    mapa = {0: 'Pendiente', 1: 'Aceptado', 2: 'Rechazado', 3: 'Error'}
    return mapa.get(estado, 'Pendiente')


def _server_side_response(request, qs_base):
    """
    Construye la respuesta JSON en el formato que exige DataTables Server-Side.

    Flujo sin N+1:
      1. recordsTotal  → COUNT(*) del QS sin filtros de búsqueda ni fecha.
      2. Aplicar filtros de fecha + búsqueda → qs_filtrado.
      3. recordsFiltered → COUNT(*) de qs_filtrado.
      4. Aplicar ordering del servidor.
      5. Slicing: LIMIT/OFFSET → solo filas visibles en la página actual.
      6. Serializar SOLO esas filas (el select_related ya se hizo en _base_qs).
    """
    # Parámetros DataTables
    draw         = int(request.GET.get('draw', 1))
    start        = int(request.GET.get('start', 0))
    length       = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '').strip()

    # 1. Total sin ningún filtro adicional (solo activos + tipo de comprobante)
    records_total = qs_base.count()

    # 2. Aplicar filtros de fecha + estado SUNAT + búsqueda
    qs_filtrado = _aplicar_filtros_fecha(qs_base, request)
    qs_filtrado = _aplicar_filtro_sunat(qs_filtrado, request)
    qs_filtrado = _aplicar_busqueda(qs_filtrado, search_value)

    # 3. Total filtrado
    records_filtered = qs_filtrado.count()

    # 4. Slicing → base de datos ejecuta LIMIT/OFFSET (una sola consulta SQL)
    filas = qs_filtrado[start: start + length]

    # 5. Serializar
    data = [_venta_to_dict(v) for v in filas]

    return JsonResponse({
        'draw':            draw,
        'recordsTotal':    records_total,
        'recordsFiltered': records_filtered,
        'data':            data,
    })


# ─── Vista principal (3 pestañas) ─────────────────────────────────────────────

def comprobantes_venta(request):
    """
    Vista principal del submódulo Comprobantes de Venta.
    Renderiza las tres pestañas: Factura, Boleta y Liquidación de Compra.
    """
    if not _check_sesion(request):
        return redirect('index')

    return render(request, 'facturacion/comprobantes_venta.html', {
        'titulo':     'Comprobantes de Venta',
        'breadcrumb': 'Facturación Electrónica / Comprobantes de Venta',
    })


# ─── APIs JSON para DataTables (Server-Side Processing) ──────────────────────

def api_listar_facturas(request):
    """
    Endpoint AJAX Server-Side: retorna Facturas Electrónicas (código 01).
    Devuelve solo las filas de la página solicitada con paginación real en BD.
    """
    if not _check_sesion(request):
        return JsonResponse({'error': 'Sin sesión'}, status=403)
    return _server_side_response(request, _base_qs('01'))


def api_listar_boletas(request):
    """
    Endpoint AJAX Server-Side: retorna Boletas de Venta (código 03).
    Devuelve solo las filas de la página solicitada con paginación real en BD.
    """
    if not _check_sesion(request):
        return JsonResponse({'error': 'Sin sesión'}, status=403)
    return _server_side_response(request, _base_qs('03'))


def api_listar_liquidaciones(request):
    """
    Endpoint AJAX Server-Side: retorna Liquidaciones de Compra (código 04).
    Devuelve solo las filas de la página solicitada con paginación real en BD.
    """
    if not _check_sesion(request):
        return JsonResponse({'error': 'Sin sesión'}, status=403)
    return _server_side_response(request, _base_qs('04'))


# ─── Envío a SUNAT vía AJAX ───────────────────────────────────────────────────

@require_POST
def enviar_comprobante_sunat(request, idventa):
    """
    Endpoint AJAX (POST) para enviar un comprobante a SUNAT.
    Detecta el tipo de comprobante automáticamente.
    Retorna JSON con resultado.
    """
    if not _check_sesion(request):
        return JsonResponse({'ok': False, 'msg': 'Sin sesión'}, status=403)

    try:
        venta = Ventas.objects.select_related(
            'idcliente', 'idtipocomprobante', 'idseriecomprobante', 'id_forma_pago', 'id_tipo_igv'
        ).get(idventa=idventa, estado=1)
    except Ventas.DoesNotExist:
        return JsonResponse({'ok': False, 'msg': 'Comprobante no encontrado.'})

    # Verificar que no esté ya aceptado
    if venta.sunat_estado == 1:
        return JsonResponse({'ok': False, 'msg': 'Este comprobante ya fue aceptado por SUNAT.'})

    # Importar y ejecutar el servicio
    from software.services.sunat_service import enviar_a_sunat
    try:
        exito, mensaje = enviar_a_sunat(idventa)
        # Refrescar el estado desde BD después del envío
        venta.refresh_from_db(fields=['sunat_estado'])
        return JsonResponse({
            'ok':                exito,
            'msg':               mensaje,
            'sunat_estado':      venta.sunat_estado,
            'sunat_estado_label': _estado_label(venta.sunat_estado),
        })
    except Exception as exc:
        logger.exception('Error inesperado al enviar venta %s a SUNAT', idventa)
        return JsonResponse({'ok': False, 'msg': f'Error inesperado: {str(exc)}'})
