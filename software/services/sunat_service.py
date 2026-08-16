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


def _get_ubicacion_empresa(empresa):
    """Lee departamento, provincia y distrito desde los FK de ubicación de la empresa."""
    try:
        departamento = empresa.id_region_gerente.nombre_region.upper() if empresa.id_region_gerente else "SAN MARTIN"
    except Exception:
        departamento = "SAN MARTIN"
    try:
        provincia = empresa.id_provincia_gerente.nombre_provincia.upper() if empresa.id_provincia_gerente else departamento
    except Exception:
        provincia = departamento
    try:
        distrito = empresa.id_distrito_gerente.nombre_distrito.upper() if empresa.id_distrito_gerente else departamento
    except Exception:
        distrito = departamento
    return departamento, provincia, distrito


def _build_empresa_payload(empresa):
    """Construye el bloque 'empresa' que va en todos los JSON."""
    departamento, provincia, distrito = _get_ubicacion_empresa(empresa)
    return {
        "ruc": empresa.ruc,
        "razon_social": empresa.razonsocial,
        "nombre_comercial": empresa.nombrecomercial or empresa.razonsocial,
        "domicilio_fiscal": empresa.direccion,
        "ubigeo": empresa.ubigueo or "150101",
        "departamento": departamento,
        "provincia": provincia,
        "distrito": distrito,
        "modo": empresa.mododev,           # 0=Beta, 1=Producción
        "usu_secundario_produccion_user": empresa.usersec or "",
        "usu_secundario_produccion_password": empresa.passwordsec or "",
        "cuenta_detraccion": "",
    }


def _build_empresa_payload_simple(empresa):
    """Bloque empresa simplificado (para liquidación, tiene campos extra)."""
    departamento, provincia, distrito = _get_ubicacion_empresa(empresa)
    return {
        "ruc": empresa.ruc,
        "razon_social": empresa.razonsocial,
        "nombre_comercial": empresa.nombrecomercial or empresa.razonsocial,
        "domicilio_fiscal": empresa.direccion,
        "ubigeo": empresa.ubigueo or "150101",
        "departamento": departamento,
        "provincia": provincia,
        "distrito": distrito,
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
        import re
        response.raise_for_status()
        # Intentar extraer JSON si hay Warnings/Notices de PHP en la respuesta
        match = re.search(r'(\{.*\})', response.text, re.DOTALL)
        if match:
            data = json.loads(match.group(1))
        else:
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
    except ValueError as exc:
        msg = f"La API SUNAT devolvió una respuesta no válida (no es JSON). Respuesta PHP: {response.text[:300]}"
        logger.error(msg)
        return False, {"error": msg}
    except requests.exceptions.RequestException as exc:
        msg = f"Error en la petición a la API SUNAT: {str(exc)}"
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

    if not serie_obj.serie.upper().startswith('F'):
        return False, f"La serie de la Factura debe iniciar con 'F'. (Serie actual: {serie_obj.serie})"

    # Determinar tipo de entidad del cliente
    codigo_tipo_entidad = "6" if len(cliente.numdoc) == 11 else ("1" if len(cliente.numdoc) == 8 else "0")

    # Determinar forma de pago (1=Contado, 2=Crédito)
    forma_pago_id = 1 if venta.id_forma_pago.id_forma_pago == 1 else 2
    
    # Manejo de fecha de vencimiento y cuotas para ventas a crédito
    fecha_vencimiento_str = fecha.strftime("%Y-%m-%d")
    lista_cuotas = []
    
    if forma_pago_id == 2:
        from software.models.CuotasVentaModel import CuotasVenta
        cuotas_db = CuotasVenta.objects.filter(idventa=venta, estado=1).order_by('numero_cuota')
        if cuotas_db.exists():
            # La fecha de vencimiento general suele ser la de la última cuota
            ultima_cuota = cuotas_db.last()
            fecha_vencimiento_str = ultima_cuota.fecha_vencimiento.strftime("%Y-%m-%d")
            
            # Llenar arreglo de cuotas para SUNAT
            for c in cuotas_db:
                lista_cuotas.append({
                    "numero": c.numero_cuota,
                    "monto": _float(c.total),
                    "fecha": c.fecha_vencimiento.strftime("%Y-%m-%d")
                })

    # Extraer solo el número (por si viene como F001-0000001)
    numero_str = venta.numero_comprobante
    if "-" in numero_str:
        numero_str = numero_str.split("-")[-1]

    # Determinar categoría de impuestos basado en el tipo de IGV
    tipo_igv = "10"
    if hasattr(venta, 'id_tipo_igv') and venta.id_tipo_igv:
        tipo_igv = str(getattr(venta.id_tipo_igv, 'codigo', '10')).strip() or "10"

    total_gravada = _float(venta.subtotal) if tipo_igv.startswith('1') else None
    total_exonerada = _float(venta.subtotal) if tipo_igv.startswith('2') else None
    total_inafecta = _float(venta.subtotal) if tipo_igv.startswith('3') else None

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
            "numero": numero_str,
            "fecha_emision": fecha.strftime("%Y-%m-%d"),
            "hora_emision": fecha.strftime("%H:%M:%S"),
            "fecha_vencimiento": fecha_vencimiento_str,
            "moneda_id": 2 if venta.moneda == 'USD' else (3 if venta.moneda == 'EUR' else 1),
            "forma_pago_id": forma_pago_id,
            "total_gravada": total_gravada,
            "total_igv": _float(venta.igv),
            "total_exonerada": total_exonerada,
            "total_inafecta": total_inafecta,
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
        "cuotas": lista_cuotas,
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
    codigo_tipo_entidad = "6" if len(cliente.numdoc) == 11 else ("1" if len(cliente.numdoc) == 8 else "0")

    # Extraer solo el número (por si viene como B001-0000001)
    numero_str = venta.numero_comprobante
    if "-" in numero_str:
        numero_str = numero_str.split("-")[-1]

    # Determinar categoría de impuestos basado en el tipo de IGV
    tipo_igv = "10"
    if hasattr(venta, 'id_tipo_igv') and venta.id_tipo_igv:
        tipo_igv = str(getattr(venta.id_tipo_igv, 'codigo', '10')).strip() or "10"

    total_gravada = _float(venta.subtotal) if tipo_igv.startswith('1') else None
    total_exonerada = _float(venta.subtotal) if tipo_igv.startswith('2') else None
    total_inafecta = _float(venta.subtotal) if tipo_igv.startswith('3') else None

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
            "numero": numero_str,
            "fecha_emision": fecha.strftime("%Y-%m-%d"),
            "hora_emision": fecha.strftime("%H:%M:%S"),
            "moneda_id": 1,
            "forma_pago_id": 1 if venta.id_forma_pago.id_forma_pago == 1 else 2,
            "total_gravada": total_gravada,
            "total_igv": _float(venta.igv),
            "total_exonerada": total_exonerada,
            "total_inafecta": total_inafecta,
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

    # Extraer solo el número
    numero_str = venta.numero_comprobante
    if "-" in numero_str:
        numero_str = numero_str.split("-")[-1]

    # Determinar categoría de impuestos basado en el tipo de IGV
    tipo_igv = "10"
    if hasattr(venta, 'id_tipo_igv') and venta.id_tipo_igv:
        tipo_igv = str(getattr(venta.id_tipo_igv, 'codigo', '10')).strip() or "10"

    total_gravada = _float(venta.subtotal) if tipo_igv.startswith('1') else None
    total_exonerada = _float(venta.subtotal) if tipo_igv.startswith('2') else None
    total_inafecta = _float(venta.subtotal) if tipo_igv.startswith('3') else None

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
            "numero": numero_str,
            "fecha_emision": fecha.strftime("%Y-%m-%d"),
            "hora_emision": fecha.strftime("%H:%M:%S"),
            "forma_pago_id": 1 if venta.id_forma_pago.id_forma_pago == 1 else 2,
            "total_gravada": total_gravada,
            "total_igv": _float(venta.igv),
            "total_exonerada": total_exonerada,
            "total_inafecta": total_inafecta,
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

        # Calcular precio_base desde el subtotal del detalle para garantizar
        # que la suma de líneas cuadre con el total del comprobante ante SUNAT.
        # SUNAT verifica: sum(precio_base * cantidad) == total_gravada|exonerada|inafecta
        cantidad = int(det.cantidad) or 1
        subtotal_det = _float(det.subtotal) or 0
        
        # precio_base es el precio unitario SIN IGV
        tipo_igv_cat = tipo_igv[0] if tipo_igv else "1"
        
        if tipo_igv_cat == "1":
            # Gravado: precio_base = subtotal sin IGV / cantidad
            precio_base = round(subtotal_det / cantidad, 10)
        else:
            # Exonerado/Inafecto: el subtotal ya es el valor de venta (sin IGV)
            precio_base = round(subtotal_det / cantidad, 10)

        if precio_base <= 0:
            precio_base = _float(det.precio_venta_contado) or 0

        items.append({
            "codigo_producto": str(codigo_prod)[:50],
            "producto": str(nombre).upper()[:250],
            "codigo_sunat": codigo_sunat,
            "cantidad": cantidad,
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
