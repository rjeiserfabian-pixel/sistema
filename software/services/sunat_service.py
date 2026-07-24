"""
Servicio de integración con la API SUNAT (PHP).
Maneja la comunicación con los endpoints para emitir:
  - Factura Electrónica (código 01)
  - Boleta de Venta (código 03)
  - Liquidación de Compra (código 04)

Las credenciales y el modo (Desarrollo/Producción) se leen
dinámicamente desde el modelo Empresa, según lo configurado
en el módulo de Configuración del sistema.
"""

import requests
import json
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

# ─── URL base de la API PHP ────────────────────────────────────────────────────
# En producción esta URL cambiará; por ahora apunta al servidor local.
SUNAT_API_BASE = "http://localhost/API_SUNAT"

ENDPOINT_COMPROBANTE = f"{SUNAT_API_BASE}/post.php"
ENDPOINT_LIQUIDACION = f"{SUNAT_API_BASE}/liquidacion.php"

TIMEOUT_SEGUNDOS = 30  # Tiempo máximo de espera por respuesta


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers internos
# ═══════════════════════════════════════════════════════════════════════════════

def _get_empresa():
    """Obtiene el primer registro activo de Empresa."""
    from software.models.empresaModel import Empresa
    return Empresa.objects.filter(activo=True).first()


def _build_empresa_payload(empresa):
    """Construye el bloque 'empresa' que va en todos los JSON."""
    return {
        "ruc": empresa.ruc,
        "razon_social": empresa.razonsocial,
        "nombre_comercial": empresa.nombrecomercial or empresa.razonsocial,
        "domicilio_fiscal": empresa.direccion,
        "ubigeo": empresa.ubigueo or "150101",
        "departamento": "LIMA",   # TODO: leer de la BD si se agrega campo
        "provincia": "LIMA",
        "distrito": "LIMA",
        "modo": empresa.mododev,           # 0=Beta, 1=Producción
        "usu_secundario_produccion_user": empresa.usersec or "",
        "usu_secundario_produccion_password": empresa.passwordsec or "",
        "cuenta_detraccion": "",
    }


def _build_empresa_payload_simple(empresa):
    """Bloque empresa simplificado (para liquidación, tiene campos extra)."""
    return {
        "ruc": empresa.ruc,
        "razon_social": empresa.razonsocial,
        "nombre_comercial": empresa.nombrecomercial or empresa.razonsocial,
        "domicilio_fiscal": empresa.direccion,
        "ubigeo": empresa.ubigueo or "150101",
        "departamento": "LIMA",
        "provincia": "LIMA",
        "distrito": "LIMA",
        "modo": empresa.mododev,
        "usu_secundario_produccion_user": empresa.usersec or "",
        "usu_secundario_produccion_password": empresa.passwordsec or "",
    }


def _float(valor):
    """Convierte Decimal/None a float seguro para JSON."""
    if valor is None:
        return None
    return float(Decimal(str(valor)))


def _post_to_api(endpoint, payload):
    """
    Realiza el POST a la API PHP y retorna (exito: bool, data: dict).
    En caso de error de red o timeout, retorna (False, {'error': '...'}).
    """
    try:
        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT_SEGUNDOS,
        )
        response.raise_for_status()
        data = response.json()
        logger.info("Respuesta SUNAT API: %s", json.dumps(data, ensure_ascii=False)[:500])
        return True, data
    except requests.exceptions.Timeout:
        msg = "Tiempo de espera agotado al conectar con la API SUNAT."
        logger.error(msg)
        return False, {"error": msg}
    except requests.exceptions.ConnectionError:
        msg = "No se pudo conectar con la API SUNAT. Verifique que el servidor esté activo."
        logger.error(msg)
        return False, {"error": msg}
    except requests.exceptions.RequestException as exc:
        msg = f"Error en la petición a la API SUNAT: {str(exc)}"
        logger.error(msg)
        return False, {"error": msg}
    except ValueError:
        msg = "La API SUNAT devolvió una respuesta no válida (no es JSON)."
        logger.error(msg)
        return False, {"error": msg}


def _procesar_respuesta(data):
    """
    Analiza la respuesta de la API PHP y retorna:
      (exito: bool, descripcion: str, campos_extra: dict)
    La respuesta exitosa tiene: data.error == "false" y data.respuesta_sunat_codigo == "0"
    """
    inner = data.get("data", data)  # Algunos endpoints envuelven en "data"
    error_flag = str(inner.get("error", "true")).lower()
    codigo_sunat = str(inner.get("respuesta_sunat_codigo", "")).strip()
    descripcion = inner.get("respuesta_sunat_descripcion", "Sin descripción")

    exito = (error_flag == "false" and codigo_sunat == "0")

    campos_extra = {
        "sunat_xml": inner.get("ruta_xml", ""),
        "sunat_hash": inner.get("codigo_hash", ""),
        "sunat_cdr": inner.get("ruta_cdr", ""),
        "respuesta_descripcion": descripcion,
        "respuesta_codigo": codigo_sunat,
    }
    return exito, descripcion, campos_extra


# ═══════════════════════════════════════════════════════════════════════════════
# Función principal de despacho (usada por la vista existente)
# ═══════════════════════════════════════════════════════════════════════════════

def enviar_a_sunat(idventa):
    """
    Mantiene compatibilidad con la vista existente (sunat.py).
    Detecta el tipo de comprobante por el código y delega al emisor correcto.
    Retorna (exito: bool, mensaje: str).
    """
    from software.models.VentasModel import Ventas
    try:
        venta = Ventas.objects.select_related(
            'idcliente', 'idtipocomprobante', 'idseriecomprobante'
        ).get(idventa=idventa)
    except Ventas.DoesNotExist:
        return False, "Venta no encontrada."

    codigo = venta.idtipocomprobante.codigo.strip()

    if codigo == "01":
        return emitir_factura(venta)
    elif codigo == "03":
        return emitir_boleta(venta)
    elif codigo == "04":
        return emitir_liquidacion(venta)
    else:
        return False, f"Tipo de comprobante '{codigo}' no soportado en la integración SUNAT."


# ═══════════════════════════════════════════════════════════════════════════════
# Emisión de Factura Electrónica (código 01)
# ═══════════════════════════════════════════════════════════════════════════════

def emitir_factura(venta):
    """
    Emite una Factura Electrónica ante SUNAT.
    Parámetro: instancia de Ventas con select_related a cliente, serie, tipo.
    Retorna (exito: bool, mensaje: str).
    """
    empresa = _get_empresa()
    if not empresa:
        return False, "No se encontró configuración de empresa."

    detalles = _obtener_items(venta)
    if not detalles:
        return False, "La venta no tiene items para facturar."

    cliente = venta.idcliente
    serie_obj = venta.idseriecomprobante
    fecha = venta.fecha_venta

    # Determinar tipo de entidad del cliente
    codigo_tipo_entidad = "6"  # RUC por defecto para facturas
    if hasattr(cliente, 'id_tipo_entidad') and cliente.id_tipo_entidad:
        codigo_tipo_entidad = cliente.id_tipo_entidad.codigo or "6"

    payload = {
        "empresa": _build_empresa_payload(empresa),
        "cliente": {
            "codigo_tipo_entidad": codigo_tipo_entidad,
            "numero_documento": cliente.numdoc,
            "razon_social_nombres": cliente.razonsocial,
            "cliente_direccion": cliente.direccion or "",
        },
        "venta": {
            "tipo_documento_codigo": "01",
            "serie": serie_obj.serie,
            "numero": venta.numero_comprobante,
            "fecha_emision": fecha.strftime("%Y-%m-%d"),
            "hora_emision": fecha.strftime("%H:%M:%S"),
            "fecha_vencimiento": fecha.strftime("%Y-%m-%d"),
            "moneda_id": 1,  # Soles
            "forma_pago_id": 1 if venta.id_forma_pago.id_forma_pago == 1 else 2,
            "total_gravada": _float(venta.subtotal),
            "total_igv": _float(venta.igv),
            "total_exonerada": None,
            "total_inafecta": None,
            "total_gratuita": None,
            "total_gratuita_igv": None,
            "total_bolsa": None,
            "orden_compra": "",
            "nota": venta.observaciones or "",
            "detraccion_codigo": "",
            "detraccion_porcentaje": None,
            "percepcion_codigo": "",
            "percepcion_porcentaje": None,
            "retencion_porcentaje": None,
        },
        "items": detalles,
        "cuotas": [],
        "guias_adjuntas": [],
        "anticipos": [],
    }

    exito_red, data = _post_to_api(ENDPOINT_COMPROBANTE, payload)
    if not exito_red:
        _marcar_error(venta, data.get("error", "Error de conexión"))
        return False, data.get("error", "Error de conexión")

    exito, descripcion, extra = _procesar_respuesta(data)
    _actualizar_venta_sunat(venta, exito, descripcion, extra)
    return exito, descripcion


# ═══════════════════════════════════════════════════════════════════════════════
# Emisión de Boleta de Venta (código 03)
# ═══════════════════════════════════════════════════════════════════════════════

def emitir_boleta(venta):
    """
    Emite una Boleta de Venta ante SUNAT.
    Parámetro: instancia de Ventas con select_related a cliente, serie, tipo.
    Retorna (exito: bool, mensaje: str).
    """
    empresa = _get_empresa()
    if not empresa:
        return False, "No se encontró configuración de empresa."

    detalles = _obtener_items(venta)
    if not detalles:
        return False, "La venta no tiene items para emitir boleta."

    cliente = venta.idcliente
    serie_obj = venta.idseriecomprobante
    fecha = venta.fecha_venta

    # Para boletas, el tipo de entidad puede ser DNI (1) o RUC (6)
    codigo_tipo_entidad = "1"  # DNI por defecto para boletas
    if hasattr(cliente, 'id_tipo_entidad') and cliente.id_tipo_entidad:
        codigo_tipo_entidad = cliente.id_tipo_entidad.codigo or "1"

    payload = {
        "empresa": _build_empresa_payload(empresa),
        "cliente": {
            "codigo_tipo_entidad": codigo_tipo_entidad,
            "numero_documento": cliente.numdoc,
            "razon_social_nombres": cliente.razonsocial,
            "cliente_direccion": cliente.direccion or "",
        },
        "venta": {
            "tipo_documento_codigo": "03",
            "serie": serie_obj.serie,
            "numero": venta.numero_comprobante,
            "fecha_emision": fecha.strftime("%Y-%m-%d"),
            "hora_emision": fecha.strftime("%H:%M:%S"),
            "moneda_id": 1,
            "forma_pago_id": 1 if venta.id_forma_pago.id_forma_pago == 1 else 2,
            "total_gravada": _float(venta.subtotal),
            "total_igv": _float(venta.igv),
            "total_exonerada": None,
            "total_inafecta": None,
        },
        "items": detalles,
        "cuotas": [],
        "guias_adjuntas": [],
        "anticipos": [],
    }

    exito_red, data = _post_to_api(ENDPOINT_COMPROBANTE, payload)
    if not exito_red:
        _marcar_error(venta, data.get("error", "Error de conexión"))
        return False, data.get("error", "Error de conexión")

    exito, descripcion, extra = _procesar_respuesta(data)
    _actualizar_venta_sunat(venta, exito, descripcion, extra)
    return exito, descripcion


# ═══════════════════════════════════════════════════════════════════════════════
# Emisión de Liquidación de Compra (código 04)
# ═══════════════════════════════════════════════════════════════════════════════

def emitir_liquidacion(venta):
    """
    Emite una Liquidación de Compra ante SUNAT.
    Este tipo de comprobante aplica para compras a personas naturales sin RUC.
    Parámetro: instancia de Ventas con select_related a cliente, serie, tipo.
    Retorna (exito: bool, mensaje: str).
    """
    empresa = _get_empresa()
    if not empresa:
        return False, "No se encontró configuración de empresa."

    detalles = _obtener_items(venta)
    if not detalles:
        return False, "La venta no tiene items para la liquidación."

    cliente = venta.idcliente
    serie_obj = venta.idseriecomprobante
    fecha = venta.fecha_venta

    payload = {
        "empresa": _build_empresa_payload_simple(empresa),
        "proveedor": {
            "numero_documento": cliente.numdoc,
            "nombres": cliente.razonsocial,
            "direccion": cliente.direccion or "",
            "ubigeo": "150101",
            "departamento": "LIMA",
            "provincia": "LIMA",
            "distrito": "LIMA",
        },
        "lugar_operacion": {
            "direccion": empresa.direccion,
            "ubigeo": empresa.ubigueo or "150101",
            "departamento": "LIMA",
            "provincia": "LIMA",
            "distrito": "LIMA",
        },
        "venta": {
            "tipo_documento_codigo": "04",
            "serie": serie_obj.serie,
            "numero": venta.numero_comprobante,
            "fecha_emision": fecha.strftime("%Y-%m-%d"),
            "hora_emision": fecha.strftime("%H:%M:%S"),
            "forma_pago_id": 1 if venta.id_forma_pago.id_forma_pago == 1 else 2,
            "total_gravada": _float(venta.subtotal),
            "total_igv": _float(venta.igv),
            "total_exonerada": None,
            "total_inafecta": None,
            "nota": venta.observaciones or "",
        },
        "items": detalles,
        "cuotas": [],
        "guias_adjuntas": [],
    }

    exito_red, data = _post_to_api(ENDPOINT_LIQUIDACION, payload)
    if not exito_red:
        _marcar_error(venta, data.get("error", "Error de conexión"))
        return False, data.get("error", "Error de conexión")

    exito, descripcion, extra = _procesar_respuesta(data)
    _actualizar_venta_sunat(venta, exito, descripcion, extra)
    return exito, descripcion


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers de items y actualización de BD
# ═══════════════════════════════════════════════════════════════════════════════

def _obtener_items(venta):
    """
    Construye la lista de items para el JSON de SUNAT a partir de VentaDetalle.
    Soporta vehiculos, repuestos y servicios.
    """
    from software.models.VentaDetalleModel import VentaDetalle

    detalles = VentaDetalle.objects.filter(idventa=venta, estado=1).select_related(
        'id_vehiculo', 'id_repuesto_comprado', 'id_servicio'
    )

    items = []
    for det in detalles:
        # Determinar nombre, código producto y código SUNAT según tipo de item
        if det.tipo_item == 'vehiculo' and det.id_vehiculo:
            veh = det.id_vehiculo
            nombre = f"{getattr(veh, 'nombre', '')}".strip() or "VEHICULO"
            codigo_prod = getattr(veh, 'serie', f"VEH{det.idventadetalle}")
            codigo_sunat = "50202201"  # Partes y accesorios de vehículos
        elif det.tipo_item == 'repuesto' and det.id_repuesto_comprado:
            rep = det.id_repuesto_comprado
            nombre = getattr(rep, 'descripcion', 'REPUESTO') or 'REPUESTO'
            codigo_prod = getattr(rep, 'codigo', f"REP{det.idventadetalle}")
            codigo_sunat = "44101701"  # Accesorios y repuestos
        elif det.tipo_item == 'servicio' and det.id_servicio:
            srv = det.id_servicio
            nombre = getattr(srv, 'nombre', 'SERVICIO') or 'SERVICIO'
            codigo_prod = f"SRV{det.idventadetalle}"
            codigo_sunat = "84111506"  # Servicios generales
        else:
            nombre = "PRODUCTO"
            codigo_prod = f"PROD{det.idventadetalle}"
            codigo_sunat = "50202201"

        # Determinar el tipo de IGV basado en la venta
        tipo_igv = "10"  # Gravado por defecto
        if hasattr(venta, 'id_tipo_igv') and venta.id_tipo_igv:
            tipo_igv_codigo = str(getattr(venta.id_tipo_igv, 'codigo', '10')).strip()
            tipo_igv = tipo_igv_codigo if tipo_igv_codigo else "10"

        precio_base = _float(det.precio_venta_contado)
        if precio_base is None or precio_base <= 0:
            precio_base = _float(det.subtotal) or 0

        items.append({
            "codigo_producto": str(codigo_prod)[:50],
            "producto": str(nombre).upper()[:250],
            "codigo_sunat": codigo_sunat,
            "cantidad": int(det.cantidad),
            "codigo_unidad": "NIU",  # Unidad de medida estándar
            "precio_base": precio_base,
            "tipo_igv_codigo": tipo_igv,
            "descuento_precio_base": 0,
            "bolsa": False,
        })

    return items


def _actualizar_venta_sunat(venta, exito, descripcion, extra):
    """Actualiza los campos SUNAT en el registro de Ventas."""
    from software.models.VentasModel import Ventas
    venta.sunat_estado = 1 if exito else 2
    venta.sunat_xml = extra.get("sunat_xml", "")
    venta.sunat_hash = extra.get("sunat_hash", "")
    venta.sunat_error = None if exito else descripcion
    venta.save(update_fields=["sunat_estado", "sunat_xml", "sunat_hash", "sunat_error"])
    logger.info(
        "Venta %s actualizada: estado_sunat=%s, descripcion=%s",
        venta.idventa, venta.sunat_estado, descripcion
    )


def _marcar_error(venta, mensaje):
    """Marca la venta con estado de error de conexión (3)."""
    venta.sunat_estado = 3
    venta.sunat_error = str(mensaje)[:500]
    venta.save(update_fields=["sunat_estado", "sunat_error"])
