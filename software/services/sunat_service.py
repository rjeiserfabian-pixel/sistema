import requests
import json
from django.conf import settings
from software.models.VentasModel import Ventas
from software.models.VentaDetalleModel import VentaDetalle
from software.models.empresaModel import Empresa
from datetime import datetime
import traceback

def enviar_a_sunat(venta_id):
    try:
        # Obtenemos la venta
        venta = Ventas.objects.get(idventa=venta_id)
        
        if not venta.idtipocomprobante:
            return False, "Tipo de comprobante no válido o no definido"
        
        empresa = Empresa.objects.first() # Suponiendo que hay una sola empresa
        if not empresa:
            return False, "No se encontraron datos de la empresa"

        cliente = venta.idcliente
        
        # URL de la API (ajustar segun entorno)
        url_api = "http://localhost/API_SUNAT/API_SUNAT/post.php"
        
        # Detalle de la venta
        detalles = VentaDetalle.objects.filter(idventa=venta_id)
        items_payload = []
        total_acumulado_igv = 0
        total_acumulado_gravada = 0
        total_acumulado_exonerada = 0
        
        # Primero detectar el tipo de IGV global de la venta
        # ID 2 suele ser Exonerado (20), ID 1 suele ser Gravado (10)
        es_exonerada = (venta.id_tipo_igv and (venta.id_tipo_igv.id_tipo_igv == 2 or str(venta.id_tipo_igv.codigo) == "20"))
        
        # Forzar exonerada si los montos coinciden y el IGV es cero (común en este sistema)
        if not es_exonerada and float(venta.total_venta or 0) == float(venta.subtotal or 0) and float(venta.total_venta or 0) > 0:
            es_exonerada = True

        for d in detalles:
            # Determinamos precio unitario y evitamos "None"
            if venta.id_forma_pago and venta.id_forma_pago.id_forma_pago == 1:
                precio_unitario = float(d.precio_venta_contado or 0)
            else:
                precio_unitario = float(d.precio_venta_credito if d.precio_venta_credito is not None else (d.precio_venta_contado or 0))

            # SKIP items with price 0.0 (ghost items)
            if precio_unitario <= 0:
                continue

            # Determinamos nombre y código del producto según su tipo
            nombre_producto = "Producto"
            codigo_producto = "000"
            if d.tipo_item == 'vehiculo' and d.id_vehiculo:
                nombre_producto = f"{d.id_vehiculo.idproducto.nomproducto} - Motor: {d.id_vehiculo.serie_motor}"
                codigo_producto = str(d.id_vehiculo.idproducto.idproducto)
            elif d.tipo_item == 'repuesto' and d.id_repuesto_comprado:
                nombre_producto = d.id_repuesto_comprado.id_repuesto.nombre if d.id_repuesto_comprado.id_repuesto else d.id_repuesto_comprado.descripcion
                codigo_producto = str(d.id_repuesto_comprado.id_repuesto.id_repuesto) if d.id_repuesto_comprado.id_repuesto else "0"

            cantidad = float(d.cantidad) if d.cantidad else 1.0
            item_total = precio_unitario * cantidad
            
            # Si es gravada, desglosar IGV del precio unitario
            if not es_exonerada:
                precio_base = precio_unitario / 1.18
                igv_item = item_total - (precio_base * cantidad)
                total_acumulado_gravada += (precio_base * cantidad)
                total_acumulado_igv += igv_item
                tipo_igv_item = "10"
            else:
                precio_base = precio_unitario
                total_acumulado_exonerada += item_total
                tipo_igv_item = "20"

            items_payload.append({
                "cantidad": cantidad,
                "codigo_unidad": "NIU", 
                "producto": nombre_producto[:200],
                "precio_base": "{:.2f}".format(precio_base),
                "tipo_igv_codigo": tipo_igv_item,
                "codigo_producto": codigo_producto,
                "codigo_sunat": "-"
            })

        # Si no hay items validos, error
        if not items_payload:
            return False, "La venta no tiene productos válidos para enviar (precios en 0)"

        # Limpiar el número de comprobante (enviar solo la parte numérica)
        # Si numero_comprobante es "F001-00000034", enviar solo "34"
        num_limpio = str(venta.numero_comprobante).split('-')[-1].lstrip('0')
        if not num_limpio: num_limpio = "0"

        # Estructuramos el JSON
        payload = {
            "empresa": {
                "ruc": empresa.ruc if hasattr(empresa, 'ruc') else "20604051984", 
                "razon_social": empresa.razonsocial if hasattr(empresa, 'razonsocial') else "MONSTRUO E.I.R.L.",
                "nombre_comercial": empresa.nombrecomercial if hasattr(empresa, 'nombrecomercial') else "MONSTRUO",
                "domicilio_fiscal": empresa.direccion if hasattr(empresa, 'direccion') else "AV. LA MOLINA NRO. 571",
                "ubigeo": empresa.ubigueo if hasattr(empresa, 'ubigueo') and empresa.ubigueo else "220601",
                "departamento": "SAN MARTIN",
                "provincia": "MARISCAL CACERES",
                "distrito": "JUANJUI",
                "modo": empresa.mododev if hasattr(empresa, 'mododev') else 0,
                "usu_secundario_produccion_user": empresa.usersec if hasattr(empresa, 'usersec') and empresa.usersec else "MODDATOS",
                "usu_secundario_produccion_password": empresa.passwordsec if hasattr(empresa, 'passwordsec') and empresa.passwordsec else "moddatos"
            },
            "cliente": {
                "codigo_tipo_entidad": "6" if cliente.numdoc and len(cliente.numdoc) == 11 else "1",
                "numero_documento": cliente.numdoc or "00000000",
                "razon_social_nombres": cliente.razonsocial or "CLIENTE VARIOS",
                "cliente_direccion": cliente.direccion if cliente.direccion else "Sin direccion"
            },
            "venta": {
                "tipo_documento_codigo": "01" if "Factura" in (venta.idtipocomprobante.nombre if venta.idtipocomprobante else "") else "03", 
                "serie": venta.idseriecomprobante.serie if venta.idseriecomprobante else "F001",
                "numero": num_limpio,
                "fecha_emision": venta.fecha_venta.strftime("%Y-%m-%d"),
                "hora_emision": venta.fecha_venta.strftime("%H:%M:%S"),
                "fecha_vencimiento": venta.fecha_venta.strftime("%Y-%m-%d"), # Vencimiento igual a emision hoy
                "moneda_id": 1, 
                "total_gravada": "{:.2f}".format(total_acumulado_gravada),
                "total_exonerada": "{:.2f}".format(total_acumulado_exonerada),
                "total_igv": "{:.2f}".format(total_acumulado_igv),
                "total_a_pagar": "{:.2f}".format(float(venta.total_venta or 0)),
                "forma_pago_id": 2 if venta.id_forma_pago and venta.id_forma_pago.id_forma_pago == 2 else 1,
                "nota": "Venta generada desde el sistema"
            },
            "items": items_payload,
            "cuotas": []
        }

        # Si la venta es a crédito y tiene cuotas, añadirlas y recalcular monto neto
        if payload["venta"]["forma_pago_id"] == 2:
            from software.models.CuotasVentaModel import CuotasVenta
            cuotas_existentes = CuotasVenta.objects.filter(idventa=venta_id).order_by('fecha_vencimiento')
            
            # Recopilar montos de cuotas en una lista temporal
            lista_cuotas = []
            suma_cuotas_db = 0
            for c in cuotas_existentes:
                monto_c = float(c.total or 0)
                suma_cuotas_db += monto_c
                lista_cuotas.append({
                    "monto": monto_c,
                    "fecha_cuota": c.fecha_vencimiento.strftime("%Y-%m-%d")
                })
            
            # TRUCO DE CUOTA 0: Si la suma de cuotas no cuadra con el total (por el adelanto),
            # insertamos una "Cuota 0" con el monto del adelanto para que SUNAT vea el 100% de la deuda.
            total_factura = float(venta.total_venta or 0)
            if round(suma_cuotas_db, 2) < round(total_factura, 2):
                adelanto = total_factura - suma_cuotas_db
                # Insertamos al inicio como Cuota 0 (pago inmediato del adelanto)
                payload["cuotas"].append({
                    "monto": "{:.2f}".format(adelanto),
                    "fecha_cuota": venta.fecha_venta.strftime("%Y-%m-%d")
                })
            
            # Añadimos el resto de cuotas de la DB
            for c_temp in lista_cuotas:
                payload["cuotas"].append({
                    "monto": "{:.2f}".format(c_temp["monto"]),
                    "fecha_cuota": c_temp["fecha_cuota"]
                })
            
            # El monto neto ahora es el total (porque incluimos el adelanto como cuota inmediata)
            payload["venta"]["monto_neto"] = "{:.2f}".format(total_factura)
        
        # Enviar el monto neto asumiendo que la API PHP lo usará para cac:PaymentTerms
        if "monto_neto" not in payload["venta"]:
            payload["venta"]["monto_neto"] = payload["venta"]["total_a_pagar"]

        # Enviamos la petición
        print(f"DEBUG: Enviando payload a {url_api}")
        print(json.dumps(payload, indent=2))
        
        response = requests.post(
            url_api, 
            json=payload, 
            timeout=15
        )
        
        print(f"DEBUG: Status Code {response.status_code}")
        print(f"DEBUG: Raw Response: {response.text}")
        
        if response.status_code == 200:
            try:
                # Limpiar la respuesta si tiene basura (espacios o warnings PHP)
                clean_response = response.text.replace('<br />', '').replace('<b>', '').replace('</b>', '').replace('Warning:', '').strip()
                # Extraer el JSON si hay texto antes o despues
                if '{' in clean_response:
                    clean_response = clean_response[clean_response.find('{'):clean_response.rfind('}')+1]
                
                resultado = json.loads(clean_response)
            except Exception as e:
                error_msg = f"Error procesando JSON de respuesta: {str(e)} - Respuesta cruda: {response.text[:200]}"
                venta.sunat_estado = 3
                venta.sunat_error = error_msg
                venta.save()
                return False, f"Respuesta no válida: {error_msg}"

            if resultado.get('exito') == True or (isinstance(resultado.get('data'), dict) and resultado.get('data').get('respuesta_sunat_codigo') == "0"):
                # Guardamos como aceptado
                venta.sunat_estado = 1
                data = resultado.get('data', {})
                venta.sunat_pdf = data.get('ruta_pdf', '')
                venta.sunat_xml = data.get('ruta_xml', '')
                venta.sunat_hash = data.get('codigo_hash', {}).get('0', '')
                venta.sunat_error = 'ACEPTADO POR SUNAT'
                venta.save()
                return True, "Enviado y aceptado correctamente"
            else:
                # Si hay error en la respuesta
                error_info = resultado.get('mensaje') or (resultado.get('data', {}).get('error_mensaje') if isinstance(resultado.get('data'), dict) else None)
                venta.sunat_estado = 2
                venta.sunat_error = error_info or json.dumps(resultado)
                venta.save()
                return False, f"Rechazado: {venta.sunat_error}"
        else:
            venta.sunat_estado = 3
            venta.sunat_error = f"HTTP {response.status_code}: {response.text[:200]}"
            venta.save()
            return False, f"Error del servidor PHP: Status {response.status_code}"
            
    except Exception as e:
        error_msg = str(e)
        try:
            venta.sunat_estado = 3
            venta.sunat_error = f"Excepción Django: {error_msg}"[:500] 
            venta.save()
        except:
            pass
        return False, f"Error interno: {str(e)}"
