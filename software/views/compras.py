from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, FileResponse
from django.conf import settings
from io import BytesIO
import os

# ReportLab para generación de PDF
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

from software.models.comprasModel import Compras
from software.models.ProveedoresModel import Proveedor
from software.models.FormaPagoModel import FormaPago
from software.models.TipoPagoModel import TipoPago
from software.models.compradetalleModel import CompraDetalle
from software.models.RespuestoCompModel import RepuestoComp
from software.models.VehiculosModel import Vehiculo
from software.models.ProductoModel import Producto
from software.models.RepuestoModel import Repuesto
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos
from software.models.estadoproductoModel import EstadoProducto
from django.db import transaction
from django.db.models import Q, Max
from software.models.cuotaModel import Cuota
from software.models.TipoclienteModel import Tipocliente
from software.models.VentasModel import Ventas
from software.models.AperturaCierreCajaModel import AperturaCierreCaja
from software.models.SituacionVehiculoModel import SituacionVehiculo
from software.models.RespuestoCompModel import RepuestoComp
from software.models.UsuarioModel import Usuario
from software.decorators import requiere_caja_aperturada
from software.models.Tipo_entidadModel import TipoEntidad
from datetime import datetime, timedelta
from django.utils import timezone

# Debe coincidir con el catálogo: id 2 = Crédito (compras al crédito no exigen tipo de pago).
FORMA_PAGO_CREDITO_ID = 2

def _sincronizar_inventario_compra(id_almacen, tipo_item, id_item, cantidad, operacion):
    """
    Sincroniza el Stock para Vehículos o Repuestos en un almacén.
    operacion: 'AUMENTAR' o 'REDUCIR'
    """
    from software.models.stockModel import Stock
    stock = None
    if tipo_item == 'vehiculo':
        stock, _ = Stock.objects.get_or_create(
            id_almacen_id=id_almacen,
            id_vehiculo_id=id_item,
            defaults={'cantidad_disponible': 0, 'estado': 1}
        )
    elif tipo_item == 'repuesto':
        stock, _ = Stock.objects.get_or_create(
            id_almacen_id=id_almacen,
            id_repuesto_comprado_id=id_item,
            defaults={'cantidad_disponible': 0, 'estado': 1}
        )
    
    if stock:
        if operacion == 'AUMENTAR':
            stock.agregar_stock(cantidad)
        elif operacion == 'REDUCIR':
            stock.descontar_stock(cantidad)

def _validar_cabecera_compra(request):
    """
    Valida cabecera del POST de compra.
    Soporta múltiples métodos de pago (tipo_pago_id[], monto_pago[], nro_operacion[]).
    Retorna (JsonResponse de error, None) o (None, dict con ids, fechacompra y observaciones).
    Anti N+1: carga todos los TipoPago activos en UNA sola query y valida en memoria.
    """
    proveedor_raw = (request.POST.get('proveedor') or '').strip()
    tipo_cliente_raw = (request.POST.get('tipo_cliente') or '').strip()
    forma_pago_raw = (request.POST.get('forma_pago') or '').strip()
    numcorrelativo = (request.POST.get('numcorrelativo') or '').strip()
    fechacompra_raw = (request.POST.get('fechacompra') or '').strip()

    if not proveedor_raw:
        return JsonResponse({
            'ok': False,
            'error': 'Debe seleccionar un proveedor.'
        }, status=400), None
    if not tipo_cliente_raw:
        return JsonResponse({
            'ok': False,
            'error': 'Debe seleccionar un tipo de comprobante.'
        }, status=400), None
    if not forma_pago_raw:
        return JsonResponse({
            'ok': False,
            'error': 'Debe seleccionar una forma de pago.'
        }, status=400), None
    if not numcorrelativo:
        return JsonResponse({
            'ok': False,
            'error': 'El número correlativo es obligatorio.'
        }, status=400), None
    if len(numcorrelativo) > 25:
        return JsonResponse({
            'ok': False,
            'error': 'El número correlativo no puede exceder 25 caracteres.'
        }, status=400), None
    if not fechacompra_raw:
        return JsonResponse({
            'ok': False,
            'error': 'La fecha de compra es obligatoria.'
        }, status=400), None

    try:
        idproveedor = int(proveedor_raw)
        idtipocliente = int(tipo_cliente_raw)
        forma_pago_id = int(forma_pago_raw)
    except (TypeError, ValueError):
        return JsonResponse({
            'ok': False,
            'error': 'Datos de cabecera inválidos.'
        }, status=400), None

    try:
        Proveedor.objects.get(idproveedor=idproveedor, estado=1)
    except Proveedor.DoesNotExist:
        return JsonResponse({
            'ok': False,
            'error': 'El proveedor seleccionado no existe o está inactivo.'
        }, status=400), None

    try:
        Tipocliente.objects.get(idtipocliente=idtipocliente, estado=1)
    except Tipocliente.DoesNotExist:
        return JsonResponse({
            'ok': False,
            'error': 'El tipo de comprobante seleccionado no es válido.'
        }, status=400), None

    try:
        FormaPago.objects.get(id_forma_pago=forma_pago_id, estado=1)
    except FormaPago.DoesNotExist:
        return JsonResponse({
            'ok': False,
            'error': 'La forma de pago seleccionada no es válida.'
        }, status=400), None

    # ── VALIDACIÓN DE TIPO(S) DE PAGO ─────────────────────────────────────────
    # Anti N+1: cargar TODOS los TipoPago activos en UNA sola query.
    # Validaciones posteriores se hacen en memoria (sin más hits a la BD).
    tipos_pago_qs = TipoPago.objects.filter(estado=1).values('id_tipo_pago', 'nombre')
    tipos_pago_dict = {tp['id_tipo_pago']: tp['nombre'] for tp in tipos_pago_qs}

    tipo_pago_id = None
    observaciones = None

    if forma_pago_id != FORMA_PAGO_CREDITO_ID:
        # ── Contado: leer lista de métodos de pago múltiples ──────────────────
        tipos_ids_raw = request.POST.getlist('tipo_pago_id[]')
        montos_raw = request.POST.getlist('monto_pago[]')
        nros_op_raw = request.POST.getlist('nro_operacion[]')

        # Compatibilidad hacia atrás: si el frontend envía el campo simple
        if not tipos_ids_raw:
            tipo_pago_simple = (request.POST.get('tipo_pago') or '').strip()
            if not tipo_pago_simple:
                return JsonResponse({
                    'ok': False,
                    'error': 'Debe seleccionar un tipo de pago para compras al contado.'
                }, status=400), None
            try:
                tipo_pago_id = int(tipo_pago_simple)
            except (TypeError, ValueError):
                return JsonResponse({'ok': False, 'error': 'Tipo de pago inválido.'}, status=400), None
            if tipo_pago_id not in tipos_pago_dict:
                return JsonResponse({'ok': False, 'error': 'El tipo de pago seleccionado no es válido.'}, status=400), None
        else:
            # Nuevo camino: múltiples métodos de pago
            if len(tipos_ids_raw) == 0:
                return JsonResponse({
                    'ok': False,
                    'error': 'Debe registrar al menos un método de pago.'
                }, status=400), None

            partes_obs = []
            for idx, tp_raw in enumerate(tipos_ids_raw):
                try:
                    tp_id = int(tp_raw)
                except (TypeError, ValueError):
                    return JsonResponse({'ok': False, 'error': f'Método de pago {idx+1} inválido.'}, status=400), None

                if tp_id not in tipos_pago_dict:
                    return JsonResponse({
                        'ok': False,
                        'error': f'El método de pago {idx+1} seleccionado no es válido.'
                    }, status=400), None

                nombre_tp = tipos_pago_dict[tp_id]
                es_efectivo = 'efectivo' in nombre_tp.lower()

                # N° operación obligatorio para métodos distintos de Efectivo
                nro_op = (nros_op_raw[idx] if idx < len(nros_op_raw) else '').strip()
                if not es_efectivo and not nro_op:
                    return JsonResponse({
                        'ok': False,
                        'error': f'El N° de Operación es obligatorio para "{nombre_tp}".'
                    }, status=400), None

                monto_str = (montos_raw[idx] if idx < len(montos_raw) else '0').strip()
                try:
                    monto = float(monto_str)
                except (TypeError, ValueError):
                    monto = 0.0

                if monto <= 0:
                    return JsonResponse({
                        'ok': False,
                        'error': f'El monto para el método de pago "{nombre_tp}" debe ser mayor a 0.'
                    }, status=400), None

                parte = f'{nombre_tp}: S/{monto:.2f}'
                if nro_op:
                    parte += f' (Op: {nro_op})'
                partes_obs.append(parte)

            # Resolver id_tipo_pago a guardar en la cabecera
            if len(tipos_ids_raw) == 1:
                tipo_pago_id = int(tipos_ids_raw[0])
                # Observaciones solo si hay N° operación
                if partes_obs and '(Op:' in partes_obs[0]:
                    observaciones = f'[Op: {nros_op_raw[0].strip()}]' if nros_op_raw else None
            else:
                # Buscar tipo "Múltiple" en memoria (sin nueva query)
                tipo_multiple_id = None
                for tp_id_m, nombre_m in tipos_pago_dict.items():
                    if 'múltipl' in nombre_m.lower() or 'multipl' in nombre_m.lower():
                        tipo_multiple_id = tp_id_m
                        break
                tipo_pago_id = tipo_multiple_id if tipo_multiple_id else int(tipos_ids_raw[0])
                observaciones = '[FRACCIONADO: ' + ' | '.join(partes_obs) + ']'

    else:
        # ── Crédito: no requiere tipo de pago del formulario ──────────────────
        tipo_pago_simple = (request.POST.get('tipo_pago') or '').strip()
        if tipo_pago_simple:
            try:
                tp_id_c = int(tipo_pago_simple)
            except (TypeError, ValueError):
                return JsonResponse({'ok': False, 'error': 'Tipo de pago inválido.'}, status=400), None
            if tp_id_c not in tipos_pago_dict:
                return JsonResponse({'ok': False, 'error': 'El tipo de pago seleccionado no es válido.'}, status=400), None
            tipo_pago_id = tp_id_c

    try:
        fecha_compra = datetime.strptime(fechacompra_raw, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({
            'ok': False,
            'error': 'La fecha de compra no es válida.'
        }, status=400), None

    if forma_pago_id == FORMA_PAGO_CREDITO_ID:
        if request.POST.get('tiene_cuotas') != '1':
            return JsonResponse({
                'ok': False,
                'error': 'Debe configurar las cuotas para compras a crédito.'
            }, status=400), None

    return None, {
        'idproveedor': idproveedor,
        'idtipocliente': idtipocliente,
        'id_forma_pago': forma_pago_id,
        'id_tipo_pago': tipo_pago_id,
        'numcorrelativo': numcorrelativo,
        'fechacompra': fecha_compra,
        'observaciones': observaciones,
    }


def _validar_lineas_compra(request, items_count):
    """Retorna JsonResponse de error o None si todo es válido."""
    if items_count < 1:
        return JsonResponse({
            'ok': False,
            'error': 'Debe agregar al menos un producto a la compra.'
        }, status=400)

    tiene_detalle = False
    for i in range(1, items_count + 1):
        tipo_item = request.POST.get(f"tipo_item_{i}")
        if not tipo_item:
            continue
        if tipo_item not in ('vehiculo', 'repuesto'):
            return JsonResponse({
                'ok': False,
                'error': f'Ítem {i}: tipo de ítem no válido.'
            }, status=400)
        try:
            cantidad = int(request.POST.get(f"cantidad_{i}") or 0)
            precio_compra = float(request.POST.get(f"precio_compra_{i}") or 0)
            precio_minimo = float(request.POST.get(f"precio_minimo_{i}") or 0)
            precio_maximo = float(request.POST.get(f"precio_maximo_{i}") or 0)
        except (TypeError, ValueError):
            return JsonResponse({
                'ok': False,
                'error': f'Ítem {i}: cantidad o precios inválidos.'
            }, status=400)
        if cantidad <= 0 or precio_compra <= 0 or precio_minimo <= 0 or precio_maximo <= 0:
            return JsonResponse({
                'ok': False,
                'error': f'Ítem {i}: la cantidad y los precios deben ser mayores a cero.'
            }, status=400)

        if tipo_item == 'vehiculo':
            if not (request.POST.get(f"idproducto_{i}", "") or "").strip():
                return JsonResponse({
                    'ok': False,
                    'error': f'Ítem {i}: debe seleccionar un producto.'
                }, status=400)
            if cantidad != 1:
                return JsonResponse({
                    'ok': False,
                    'error': f'Ítem {i}: la cantidad para vehículos debe ser siempre 1 (cada vehículo tiene una serie de motor/chasis única).'
                }, status=400)
            if not (request.POST.get(f"idestadoproducto_{i}", "") or "").strip():
                return JsonResponse({
                    'ok': False,
                    'error': f'Ítem {i}: debe seleccionar el estado del producto.'
                }, status=400)
        else:
            if not (request.POST.get(f"id_repuesto_{i}", "") or "").strip():
                return JsonResponse({
                    'ok': False,
                    'error': f'Ítem {i}: debe seleccionar un repuesto.'
                }, status=400)
        tiene_detalle = True

    if not tiene_detalle:
        return JsonResponse({
            'ok': False,
            'error': 'Debe agregar al menos un ítem válido a la compra.'
        }, status=400)
    return None


def _validar_cuotas_credito(request):
    """Solo cuando forma_pago es crédito y tiene_cuotas=1. Retorna JsonResponse o None."""
    if request.POST.get("forma_pago") != str(FORMA_PAGO_CREDITO_ID):
        return None
    if request.POST.get("tiene_cuotas") != "1":
        return None
    try:
        cuotas = int(request.POST.get("credito_cuotas") or 0)
    except ValueError:
        return JsonResponse({
            'ok': False,
            'error': 'Número de cuotas inválido.'
        }, status=400)
    if cuotas < 1:
        return JsonResponse({
            'ok': False,
            'error': 'Debe configurar al menos una cuota para compras a crédito.'
        }, status=400)

    fechacompra_raw = (request.POST.get('fechacompra') or '').strip()
    for i in range(1, cuotas + 1):
        if request.POST.get(f'numero_cuota_{i}') is None or request.POST.get(f'numero_cuota_{i}') == '':
            return JsonResponse({
                'ok': False,
                'error': f'Datos incompletos en la cuota {i}.'
            }, status=400)
        try:
            float(request.POST.get(f'monto_{i}') or 0)
            float(request.POST.get(f'tasa_{i}') or 0)
            float(request.POST.get(f'interes_{i}') or 0)
            float(request.POST.get(f'total_{i}') or 0)
        except (TypeError, ValueError):
            return JsonResponse({
                'ok': False,
                'error': f'Cuota {i}: montos inválidos.'
            }, status=400)
        fv = (request.POST.get(f'fecha_vencimiento_{i}') or '').strip()
        if not fv and not fechacompra_raw:
            return JsonResponse({
                'ok': False,
                'error': f'Cuota {i}: fecha de vencimiento requerida.'
            }, status=400)
    return None


def compras(request):
    # Obtención del id del tipo de usuario desde la sesión
    id2 = request.session.get('idtipousuario')
    
    if not id2:
        return HttpResponse("<h1>No tiene acceso señor</h1>")
    
    # Validación de permisos
    permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
    
    # FILTRAR COMPRAS POR SUCURSAL
    idusuario = request.session.get('idusuario')
    id_sucursal = request.session.get('id_sucursal')
    id_almacen = request.session.get('id_almacen')
    es_admin = (id2 == 1)
    
    # Verificar si la sucursal seleccionada es la principal
    es_sucursal_principal = False
    if id_sucursal:
        try:
            from software.models.sucursalesModel import Sucursales
            sucursal = Sucursales.objects.get(id_sucursal=id_sucursal)
            es_sucursal_principal = sucursal.es_principal
        except Sucursales.DoesNotExist:
            es_sucursal_principal = False

    # Lógica de fechas por defecto (semana actual)
    hoy = datetime.now().date()
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    
    fecha_inicio_str = request.GET.get('fecha_inicio', inicio_semana.strftime('%Y-%m-%d'))
    fecha_fin_str = request.GET.get('fecha_fin', hoy.strftime('%Y-%m-%d'))
    
    # ✅ OMITIDO PARA SERVER-SIDE PROCESSING
    # La consulta se delega a api_listar_compras()
    compras_list = []
    
    # Catálogos relacionados
    from software.models.marcaModel import Marca
    from software.models.categoriaModel import Categoria
    from software.models.cilindradaModel import Cilindrada
    from software.models.colorModel import Color
    from software.models.modeloModel import Modelo
    from software.models.UnidadesModel import Unidades
    from software.models.ConfiguracionVehicularModel import ConfiguracionVehicular
    from software.models.DetalleColorModel import DetalleColor
    from software.models.MarcaRepuestoModel import MarcaRepuesto
    from software.models.CategoriaRepuestoModel import CategoriaRepuesto
    from software.models.GarantiaRepuestoModel import GarantiaRepuesto

    proveedor = Proveedor.objects.filter(estado=1)
    tipocliente = Tipocliente.objects.filter(estado=1)
    formapago = FormaPago.objects.filter(estado=1)
    tipopago = TipoPago.objects.filter(estado=1)
    repuestocomprado = RepuestoComp.objects.filter(estado=1)
    vehiculo = Vehiculo.objects.filter(estado=1)
    producto = Producto.objects.filter(estado=1)
    repuesto = Repuesto.objects.filter(estado=1).select_related('idmarca', 'id_categoria_repuesto', 'idunidad')
    estadoproducto = EstadoProducto.objects.filter(estado=1)
    tipos_entidad = TipoEntidad.objects.filter(estado=1)
    # Catálogos extra para modales de registro rápido
    marcas = Marca.objects.filter(estado=1).order_by('nombremarca')
    categorias = Categoria.objects.filter(estado=1).order_by('nomcategoria')
    cilindradas = Cilindrada.objects.filter(estado=1).order_by('cilindrada_cc')
    colores = Color.objects.filter(estado=1).order_by('nombrecolor')
    detalles_color = DetalleColor.objects.filter(estado=1).order_by('nombre')
    modelos_catalogo = Modelo.objects.filter(estado=1).order_by('nombremodelo')
    unidades_catalogo = Unidades.objects.filter(estado=1).order_by('abrunidad')
    configuraciones_veh = ConfiguracionVehicular.objects.filter(estado=1).order_by('nombre')
    categorias_rep = CategoriaRepuesto.objects.filter(estado=1).order_by('nomcategoria')
    marcas_rep = MarcaRepuesto.objects.filter(estado=1).order_by('nombremarca')
    garantias_rep = GarantiaRepuesto.objects.filter(estado=1).order_by('nombre')

    # Contexto para el template
    data = {
        'compras_registros': compras_list,
        'proveedor': proveedor,
        'tipo_cliente': tipocliente,
        'forma_pago': formapago,
        'tipo_pago': tipopago,
        'repuestos_comprados': repuestocomprado,
        'vehiculo': vehiculo,
        'producto': producto,
        'catalogo_repuestos': repuesto,
        'estado_producto': estadoproducto,
        'permisos': permisos,
        'es_admin': es_admin,
        'es_sucursal_principal': es_sucursal_principal,
        'tipos_entidad': tipos_entidad,
        'fecha_inicio': fecha_inicio_str,
        'fecha_fin': fecha_fin_str,
        # Catálogos para registro rápido
        'marcas': marcas,
        'categorias': categorias,
        'cilindradas': cilindradas,
        'colores': colores,
        'detalles_color': detalles_color,
        'modelos_catalogo': modelos_catalogo,
        'unidades_catalogo': unidades_catalogo,
        'configuraciones_veh': configuraciones_veh,
        'categorias_rep': categorias_rep,
        'marcas_rep': marcas_rep,
        'garantias_rep': garantias_rep,
    }
    
    return render(request, 'compras/compras.html', data)

# Nueva compra
@requiere_caja_aperturada
def nueva_compra(request):
    if request.method == "POST":
        try:
            print("======= DEBUG POST COMPRA =======")
            for k, v in request.POST.items():
                print(f"{k}: {v}")
            print("=================================")

            # VALIDACIÓN 1: Obtener datos de sesión
            idusuario_session = request.session.get('idusuario')
            id_caja_session = request.session.get('id_caja')
            id_almacen_session = request.session.get('id_almacen')
            id_sucursal_session = request.session.get('id_sucursal')
            
            # VALIDACIÓN 2: Verificar que solo sucursal principal puede comprar
            if not id_sucursal_session:
                return JsonResponse({
                    'ok': False,
                    'error': 'Debe seleccionar una sucursal en el modal de configuración antes de realizar compras.'
                }, status=400)
            
            try:
                from software.models.sucursalesModel import Sucursales
                sucursal = Sucursales.objects.get(id_sucursal=id_sucursal_session)
                
                if not sucursal.es_principal:
                    return JsonResponse({
                        'ok': False,
                        'error': 'Solo la sucursal principal puede realizar compras. Sucursal actual: ' + sucursal.nombre_sucursal,
                        'codigo': 'NO_ES_SUCURSAL_PRINCIPAL'
                    }, status=403)
                    
            except Sucursales.DoesNotExist:
                return JsonResponse({
                    'ok': False,
                    'error': 'La sucursal seleccionada no existe.'
                }, status=400)
            
            # Validar que tenga caja seleccionada
            if not id_caja_session:
                return JsonResponse({
                    'ok': False,
                    'error': 'Debe seleccionar una caja en el modal de configuración antes de comprar.'
                }, status=400)
            
            # Validar que tenga almacén seleccionado
            if not id_almacen_session:
                return JsonResponse({
                    'ok': False,
                    'error': 'Debe seleccionar un almacén en el modal de configuración antes de comprar.'
                }, status=400)
            
            # VALIDACIÓN 3: Verificar que la caja esté aperturada solo si afecta caja
            afecta_caja = request.POST.get('afecta_caja') == '1'
            apertura = None
            
            if afecta_caja:
                apertura = AperturaCierreCaja.objects.filter(
                    idusuario_id=idusuario_session,
                    id_caja_id=id_caja_session,
                    estado__in=['abierta', 'reabierta']
                ).first()
                
                if not apertura:
                    return JsonResponse({
                        'ok': False,
                        'error': 'La caja seleccionada no está aperturada. Por favor, aperture la caja antes de realizar compras.',
                        'necesita_aperturar': True
                    }, status=400)

            err_resp, cabecera = _validar_cabecera_compra(request)
            if err_resp:
                return err_resp

            items = int(request.POST.get("items_count") or 0)
            err_lineas = _validar_lineas_compra(request, items)
            if err_lineas:
                return err_lineas

            err_cuotas = _validar_cuotas_credito(request)
            if err_cuotas:
                return err_cuotas

            tipo_cambio_val = float(request.POST.get("tipo_cambio") or 1.00)
            
            with transaction.atomic():
                compra = Compras.objects.create(
                    idproveedor_id=cabecera['idproveedor'],
                    idtipocliente_id=cabecera['idtipocliente'],
                    id_forma_pago_id=cabecera['id_forma_pago'],
                    id_tipo_pago_id=cabecera['id_tipo_pago'],
                    numcorrelativo=cabecera['numcorrelativo'],
                    fechacompra=cabecera['fechacompra'],
                    observaciones=cabecera.get('observaciones'),
                    tipo_cambio=tipo_cambio_val,
                    id_sucursal_id=id_sucursal_session,
                    id_almacen_id=id_almacen_session,
                    estado=1,
                )

                total = 0
                nuevos_detalles = []
                print(f"DEBUG items_count: {items}")

                # --- PRE-FETCH FECHAS DE ÚLTIMA COMPRA (evita N+1) ---
                # Recolectar todos los id_repuesto del formulario en una sola pasada
                ids_repuesto_en_carrito = set()
                for _i in range(1, items + 1):
                    if request.POST.get(f"tipo_item_{_i}") == "repuesto":
                        _id = request.POST.get(f"id_repuesto_{_i}", "").strip()
                        if _id:
                            ids_repuesto_en_carrito.add(int(_id))

                # Una sola consulta con Max por cada repuesto del carrito
                from software.models.compradetalleModel import CompraDetalle as _CD
                ultimas_fechas_compra = dict(
                    _CD.objects.filter(
                        id_repuesto_comprado__id_repuesto_id__in=ids_repuesto_en_carrito,
                        idcompra__estado=1
                    ).values('id_repuesto_comprado__id_repuesto_id')
                     .annotate(ultima=Max('idcompra__fechacompra'))
                     .values_list('id_repuesto_comprado__id_repuesto_id', 'ultima')
                )

                # Una sola consulta para traer el costo_unitario del catálogo
                # (se usa como fallback si no se ingresó costo en el formulario)
                costos_catalogo = dict(
                    Repuesto.objects.filter(
                        id_repuesto__in=ids_repuesto_en_carrito
                    ).values_list('id_repuesto', 'costo_unitario')
                )
                # -------------------------------------------------------

                for i in range(1, items + 1):
                    tipo_item = request.POST.get(f"tipo_item_{i}")
                    if not tipo_item:
                        continue

                    cantidad = int(request.POST.get(f"cantidad_{i}") or 0)
                    precio_compra = float(request.POST.get(f"precio_compra_{i}") or 0)
                    precio_minimo = float(request.POST.get(f"precio_minimo_{i}") or 0)
                    precio_maximo = float(request.POST.get(f"precio_maximo_{i}") or 0)
                    margen_minimo = float(request.POST.get(f"margen_minimo_{i}") or 0)
                    margen_maximo = float(request.POST.get(f"margen_maximo_{i}") or 0)
                    moneda_i = request.POST.get(f"moneda_{i}", "PEN").strip()
                    precio_dolares_i = float(request.POST.get(f"precio_dolares_{i}") or 0.00)


                    if tipo_item == "vehiculo":
                        idproducto = request.POST.get(f"idproducto_{i}", "").strip()
                        idestadoproducto = request.POST.get(f"idestadoproducto_{i}", "").strip()
                        
                        if not idproducto:
                            raise ValueError(f"Debe seleccionar un producto para el ítem {i}")
                        
                        if not idestadoproducto:
                            raise ValueError(f"Debe seleccionar el estado del producto para el ítem {i}")
                        
                        situacion_disponible, _ = SituacionVehiculo.objects.get_or_create(nombre_situacion='DISPONIBLE', defaults={'estado': 1})
                        vehiculo = Vehiculo.objects.create(
                            id_situacion=situacion_disponible,
                            idproducto_id=int(idproducto),
                            serie_motor=request.POST.get(f"serie_motor_{i}", "").strip(),
                            serie_chasis=request.POST.get(f"serie_chasis_{i}", "").strip(),
                            anio=request.POST.get(f"anio_{i}", "").strip(),
                            idestadoproducto_id=int(idestadoproducto),
                            imperfecciones=request.POST.get(f"imperfecciones_{i}", "").strip(),
                            placas=request.POST.get(f"placas_{i}", "").strip(),
                            estado=1
                        )
                        nuevos_detalles.append(CompraDetalle(
                            idcompra=compra,
                            id_vehiculo=vehiculo,
                            id_repuesto_comprado=None,
                            cantidad=cantidad,
                            moneda=moneda_i,
                            precio_dolares=precio_dolares_i,
                            precio_compra=precio_compra,
                            precio_minimo=precio_minimo,
                            precio_maximo=precio_maximo,
                            margen_minimo=margen_minimo,
                            margen_maximo=margen_maximo,
                            subtotal=cantidad * precio_compra
                        ))

                    elif tipo_item == "repuesto":
                        id_repuesto = request.POST.get(f"id_repuesto_{i}", "").strip()
                        
                        if not id_repuesto:
                            raise ValueError(f"Debe seleccionar un repuesto para el ítem {i}")
                        
                        ubicacion = request.POST.get(f"descripcion_{i}", "").strip()
                        repuesto, _ = RepuestoComp.objects.get_or_create(
                            id_repuesto_id=int(id_repuesto),
                            ubicacion=ubicacion,
                            defaults={'estado': 1}
                        )

                        # Si no se ingresó costo, usar el costo_unitario del catálogo (lookup en memoria, sin N+1)
                        if precio_compra == 0:
                            costo_cat = costos_catalogo.get(int(id_repuesto))
                            if costo_cat:
                                precio_compra = float(costo_cat)

                        # --- SINCRONIZAR PRECIOS DEL CATÁLOGO (sin N+1) ---
                        ultima_fecha = ultimas_fechas_compra.get(int(id_repuesto))
                        if not ultima_fecha or (compra.fechacompra and ultima_fecha and compra.fechacompra >= ultima_fecha):
                            Repuesto.objects.filter(id_repuesto=int(id_repuesto)).update(
                                precio_minimo=precio_minimo,
                                precio_sugerido=precio_maximo,
                            )
                        # ---------------------------------------------------

                        nuevos_detalles.append(CompraDetalle(
                            idcompra=compra,
                            id_repuesto_comprado=repuesto,
                            id_vehiculo=None,
                            cantidad=cantidad,
                            moneda=moneda_i,
                            precio_dolares=precio_dolares_i,
                            precio_compra=precio_compra,
                            precio_minimo=precio_minimo,
                            precio_maximo=precio_maximo,
                            margen_minimo=margen_minimo,
                            margen_maximo=margen_maximo,
                            subtotal=cantidad * precio_compra
                        ))

                    total += cantidad * precio_compra

                CompraDetalle.objects.bulk_create(nuevos_detalles)
                for d in nuevos_detalles:
                    if d.id_vehiculo_id:
                        _sincronizar_inventario_compra(compra.id_almacen_id, 'vehiculo', d.id_vehiculo_id, d.cantidad, 'AUMENTAR')
                    elif d.id_repuesto_comprado_id:
                        _sincronizar_inventario_compra(compra.id_almacen_id, 'repuesto', d.id_repuesto_comprado_id, d.cantidad, 'AUMENTAR')

                compra.total_compra = total
                compra.save()

                # Guardar cuotas si aplica
                monto_egreso_caja = 0
                descripcion_egreso = ""

                if str(cabecera['id_forma_pago']) == str(FORMA_PAGO_CREDITO_ID):
                    if request.POST.get("tiene_cuotas") == "1":
                        cuotas = int(request.POST.get("credito_cuotas") or 0)
                        total_adelanto = 0
                        for i in range(1, cuotas + 1):
                            monto_adelanto_cuota = float(request.POST.get(f"monto_adelanto_{i}", 0) or 0)
                            total_adelanto += monto_adelanto_cuota
                            numero_cuota = int(request.POST.get(f"numero_cuota_{i}"))
                            
                            # USAR LA FECHA QUE VIENE DEL FORMULARIO (ya configurada en el modal)
                            fecha_vencimiento_str = request.POST.get(f"fecha_vencimiento_{i}")
                            
                            # Convertir string a date
                            if fecha_vencimiento_str:
                                fecha_vencimiento = datetime.strptime(fecha_vencimiento_str, '%Y-%m-%d').date()
                            else:
                                # Fallback: si no viene fecha, calcular automáticamente
                                fecha_compra = cabecera['fechacompra']
                                fecha_vencimiento = fecha_compra + timedelta(days=30 * numero_cuota)
                            
                            Cuota.objects.create(
                                idcompra=compra,
                                numero_cuota=numero_cuota,
                                monto=float(request.POST.get(f"monto_{i}")),
                                tasa=float(request.POST.get(f"tasa_{i}")),
                                interes=float(request.POST.get(f"interes_{i}")),
                                total=float(request.POST.get(f"total_{i}")),
                                fecha_vencimiento=fecha_vencimiento,  # ✅ Fecha del formulario
                                monto_adelanto=monto_adelanto_cuota,
                                estado=1
                            )

                        if total_adelanto > 0:
                            monto_egreso_caja = total_adelanto
                            descripcion_egreso = f"Pago inicial (adelanto) de Compra Crédito {compra.numcorrelativo} - Proveedor: {compra.idproveedor.razonsocial}"

                        print(f"✅ {cuotas} cuotas guardadas correctamente")
                else:
                    # Compra al contado
                    monto_egreso_caja = total
                    descripcion_egreso = f"Pago de Compra Contado {compra.numcorrelativo} - Proveedor: {compra.idproveedor.razonsocial}"

                # Verificar si afecta a caja (ya lo calculamos antes, pero lo podemos reusar)
                # afecta_caja = request.POST.get('afecta_caja') == '1'

                # Crear movimiento de caja si hay monto a registrar y afecta a caja
                if monto_egreso_caja > 0 and afecta_caja:
                    from software.models.movimientoCajaModel import MovimientoCaja
                    from django.db.models import Sum
                    from decimal import Decimal
                    
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
                    
                    if saldo_actual < Decimal(str(monto_egreso_caja)):
                        raise ValueError(f"Fondos insuficientes en la caja para la compra. Saldo actual: S/ {saldo_actual:.2f}, Monto requerido: S/ {monto_egreso_caja:.2f}.")

                    MovimientoCaja.objects.create(
                        id_caja_id=id_caja_session,
                        idusuario_id=idusuario_session,
                        id_movimiento=apertura,
                        idcompra=compra,
                        tipo_movimiento='egreso',
                        monto=monto_egreso_caja,
                        descripcion=descripcion_egreso,
                        estado=1
                    )

                print(f"COMPRA REGISTRADA - ID: {compra.idcompra}")
                print(f"Sucursal: {sucursal.nombre_sucursal}")
                print(f"Caja: {apertura.id_caja.nombre_caja if apertura else 'No afecta caja'}")

            return JsonResponse({
                'ok': True,
                'message': 'Compra registrada correctamente.'
            })

        except ValueError as ve:
            print(f"ERROR DE VALIDACIÓN: {str(ve)}")
            return JsonResponse({
                'ok': False,
                'error': str(ve)
            }, status=400)
        except Exception as e:
            print(f"ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'ok': False,
                'error': f'Error al procesar la compra: {str(e)}'
            }, status=500)

    return redirect("compras")


# OBTENER COMPRA PARA EDICIÓN
def obtener_compra(request, id):
    """Obtiene los datos de una compra para edición"""
    try:
        compra = Compras.objects.get(idcompra=id, estado=1)


        detalles = CompraDetalle.objects.filter(idcompra=compra).select_related(
            'id_vehiculo__idproducto',
            'id_vehiculo__idestadoproducto',
            'id_repuesto_comprado__id_repuesto'
        )
        
        # Formatear detalles
        detalles_list = []
        for d in detalles:
            if d.id_vehiculo:
                detalles_list.append({
                    'idcompradetalle': d.idcompradetalle,
                    'tipo': 'vehiculo',
                    'id_producto': d.id_vehiculo.idproducto.idproducto,
                    'nombre': d.id_vehiculo.idproducto.nomproducto,
                    'serie_motor': d.id_vehiculo.serie_motor or '',
                    'serie_chasis': d.id_vehiculo.serie_chasis or '',
                    'anio': d.id_vehiculo.anio or '',
                    'estado_producto': d.id_vehiculo.idestadoproducto.idestadoproducto,
                    'placas': d.id_vehiculo.placas or '',
                    'imperfecciones': d.id_vehiculo.imperfecciones or '',
                    'cantidad': d.cantidad,
                    'precio_compra': float(d.precio_compra),
                    'precio_minimo': float(d.precio_minimo),
                    'precio_maximo': float(d.precio_maximo),
                    'margen_minimo': float(d.margen_minimo),
                    'margen_maximo': float(d.margen_maximo)
                })
            elif d.id_repuesto_comprado:
                detalles_list.append({
                    'idcompradetalle': d.idcompradetalle,
                    'tipo': 'repuesto',
                    'id_repuesto': d.id_repuesto_comprado.id_repuesto.id_repuesto,
                    'nombre': d.id_repuesto_comprado.id_repuesto.nombre,
                    'codigo_barras': d.id_repuesto_comprado.id_repuesto.codigo_barras or '',
                    'modelo': d.id_repuesto_comprado.id_repuesto.modelo_referencia or '',
                    'descripcion': d.id_repuesto_comprado.ubicacion or '',
                    'cantidad': d.cantidad,
                    'precio_compra': float(d.precio_compra),
                    'precio_minimo': float(d.precio_minimo),
                    'precio_maximo': float(d.precio_maximo),
                    'margen_minimo': float(d.margen_minimo),
                    'margen_maximo': float(d.margen_maximo)
                })
        
        #CORRECCIÓN: Obtener cuotas con related_name='cuota'
        cuotas = []
        if compra.cuota.exists():
            for cuota in compra.cuota.all():
                cuotas.append({
                    'numero_cuota': cuota.numero_cuota,
                    'monto': float(cuota.monto),
                    'tasa': float(cuota.tasa),
                    'interes': float(cuota.interes),
                    'total': float(cuota.total),
                    'fecha_vencimiento': cuota.fecha_vencimiento.strftime('%Y-%m-%d'),
                    'monto_adelanto': float(cuota.monto_adelanto)
                })
        
        # Obtener si afecta caja
        afecta_caja = False
        try:
            from software.models.cajaModel import MovimientoCaja
            afecta_caja = MovimientoCaja.objects.filter(idcompra=compra.idcompra).exists()
        except Exception:
            pass

        # Obtener métodos de pago
        pagos_list = []
        if compra.id_forma_pago.id_forma_pago != 2:
            if compra.observaciones and '[FRACCIONADO:' in compra.observaciones:
                import re
                obs = compra.observaciones.replace('[FRACCIONADO:', '').replace(']', '').strip()
                partes = obs.split('|')
                for parte in partes:
                    parte = parte.strip()
                    if not parte: continue
                    m = re.match(r'^(.*?):\s*S/([\d.]+)(?:\s*\(Op:\s*(.*?)\))?$', parte)
                    if m:
                        nombre_tp = m.group(1).strip()
                        monto = float(m.group(2))
                        operacion = m.group(3).strip() if m.group(3) else ''
                        try:
                            from software.models.comprasModel import TipoPago
                            tp = TipoPago.objects.filter(nombre__iexact=nombre_tp).first()
                            tp_id = tp.id_tipo_pago if tp else ''
                        except Exception:
                            tp_id = ''
                        pagos_list.append({
                            'id_tipo_pago': tp_id,
                            'nombre': nombre_tp,
                            'monto': monto,
                            'operacion': operacion
                        })
            else:
                monto = float(compra.total_compra)
                operacion = ''
                if compra.observaciones and '[Op:' in compra.observaciones:
                    import re
                    m = re.search(r'\[Op:\s*(.*?)\]', compra.observaciones)
                    if m:
                        operacion = m.group(1).strip()
                pagos_list.append({
                    'id_tipo_pago': compra.id_tipo_pago.id_tipo_pago if compra.id_tipo_pago else '',
                    'nombre': compra.id_tipo_pago.nombre if compra.id_tipo_pago else '',
                    'monto': monto,
                    'operacion': operacion
                })

        return JsonResponse({
            'success': True,
            'compra': {
                'idcompra': compra.idcompra,
                'idproveedor': compra.idproveedor.idproveedor,
                'proveedor_nombre': compra.idproveedor.razonsocial,
                'numcorrelativo': compra.numcorrelativo,
                'fechacompra': compra.fechacompra.strftime('%Y-%m-%d'),
                'idtipocliente': compra.idtipocliente.idtipocliente,
                'id_forma_pago': compra.id_forma_pago.id_forma_pago,
                'id_tipo_pago': compra.id_tipo_pago.id_tipo_pago if compra.id_tipo_pago else None,
                'total_compra': float(compra.total_compra),
                'afecta_caja': afecta_caja
            },
            'pagos_list': pagos_list,
            'detalles': detalles_list,
            'cuotas': cuotas
        })
        
    except Compras.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Compra no encontrada'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ACTUALIZAR COMPRA
@requiere_caja_aperturada
@transaction.atomic
def actualizar_compra(request, id):
    """Actualiza una compra existente - CON REUTILIZACIÓN DE REPUESTOS/VEHÍCULOS"""
    if request.method == "POST":
        try:
            print("======= DEBUG POST ACTUALIZAR COMPRA =======")
            for k, v in request.POST.items():
                print(f"{k}: {v}")
            print("=================================")
            
            # Obtener la compra existente
            compra = Compras.objects.get(idcompra=id, estado=1)


            err_resp, cabecera = _validar_cabecera_compra(request)
            if err_resp:
                return err_resp

            items = int(request.POST.get("items_count") or 0)
            err_lineas = _validar_lineas_compra(request, items)
            if err_lineas:
                return err_lineas

            err_cuotas = _validar_cuotas_credito(request)
            if err_cuotas:
                return err_cuotas
            
            # Guardar datos anteriores para auditoría
            datos_anteriores = {
                'numcorrelativo': compra.numcorrelativo,
                'proveedor': compra.idproveedor.razonsocial,
                'total': float(compra.total_compra),
                'fecha': str(compra.fechacompra),
                'forma_pago': compra.id_forma_pago.nombre,
                'tipo_pago': compra.id_tipo_pago.nombre if compra.id_tipo_pago else 'Crédito'
            }
            
            # Actualizar datos principales
            compra.idproveedor_id = cabecera['idproveedor']
            compra.idtipocliente_id = cabecera['idtipocliente']
            compra.id_forma_pago_id = cabecera['id_forma_pago']
            compra.id_tipo_pago_id = cabecera['id_tipo_pago']
            compra.numcorrelativo = cabecera['numcorrelativo']
            compra.fechacompra = cabecera['fechacompra']
            
            # Eliminar cuotas antiguas si existen
            Cuota.objects.filter(idcompra=compra).delete()
            
            total = 0
            items = int(request.POST.get("items_count") or 0)

            # 1. Recuperar los idcompradetalle del POST que siguen presentes
            ids_mantenidos = []
            for i in range(1, items + 1):
                pk_val = request.POST.get(f"idcompradetalle_{i}")
                if pk_val:
                    ids_mantenidos.append(int(pk_val))

            # --- REDUCIR STOCK DE DETALLES ANTIGUOS Y BORRAR LOS ELIMINADOS ---
            detalles_antiguos = CompraDetalle.objects.filter(idcompra=compra)
            for d in detalles_antiguos:
                if d.id_vehiculo_id:
                    _sincronizar_inventario_compra(compra.id_almacen_id, 'vehiculo', d.id_vehiculo_id, d.cantidad, 'REDUCIR')
                elif d.id_repuesto_comprado_id:
                    _sincronizar_inventario_compra(compra.id_almacen_id, 'repuesto', d.id_repuesto_comprado_id, d.cantidad, 'REDUCIR')
                
                # Si el detalle ya no vuelve en el POST, lo eliminamos permanentemente
                if d.idcompradetalle not in ids_mantenidos:
                    d.delete()
            # ------------------------------------------------------------------
            nuevos_detalles = []
            detalles_agregados_para_stock = []
            
            for i in range(1, items + 1):
                tipo_item = request.POST.get(f"tipo_item_{i}")
                if not tipo_item:
                    continue
                
                idcompradetalle_str = request.POST.get(f"idcompradetalle_{i}")
                detalle_obj = None
                if idcompradetalle_str:
                    try:
                        detalle_obj = CompraDetalle.objects.get(idcompradetalle=int(idcompradetalle_str))
                    except CompraDetalle.DoesNotExist:
                        pass

                cantidad = int(request.POST.get(f"cantidad_{i}") or 0)
                precio_compra = float(request.POST.get(f"precio_compra_{i}") or 0)
                precio_minimo = float(request.POST.get(f"precio_minimo_{i}") or 0)
                precio_maximo = float(request.POST.get(f"precio_maximo_{i}") or 0)
                margen_minimo = float(request.POST.get(f"margen_minimo_{i}") or 0)
                margen_maximo = float(request.POST.get(f"margen_maximo_{i}") or 0)

                if tipo_item == "vehiculo":
                    idproducto = request.POST.get(f"idproducto_{i}", "").strip()
                    idestadoproducto = request.POST.get(f"idestadoproducto_{i}", "").strip()
                    serie_motor = request.POST.get(f"serie_motor_{i}", "").strip()
                    serie_chasis = request.POST.get(f"serie_chasis_{i}", "").strip()
                    placas = request.POST.get(f"placas_{i}", "").strip()
                    imperfecciones = request.POST.get(f"imperfecciones_{i}", "").strip()
                    anio_str = request.POST.get(f"anio_{i}", "").strip()
                    # Robustez contra 'undefined' o valores no numéricos
                    anio = None
                    if anio_str and anio_str != 'undefined':
                        try:
                            anio = int(float(anio_str)) # float primero para atrapar '2024.0'
                        except (ValueError, TypeError):
                            anio = None
                    
                    if not idproducto:
                        raise ValueError(f"Debe seleccionar un producto para el ítem {i}")
                    
                    if not idestadoproducto:
                        raise ValueError(f"Debe seleccionar el estado del producto para el ítem {i}")
                    
                    # BUSCAR O CREAR - No duplica si ya existe
                    situacion_disponible, _ = SituacionVehiculo.objects.get_or_create(nombre_situacion='DISPONIBLE', defaults={'estado': 1})
                    if serie_motor and serie_chasis:
                        vehiculo, created = Vehiculo.objects.get_or_create(
                            serie_motor=serie_motor,
                            serie_chasis=serie_chasis,
                            defaults={
                                'id_situacion': situacion_disponible,
                                'idproducto_id': int(idproducto),
                                'idestadoproducto_id': int(idestadoproducto),
                                'imperfecciones': imperfecciones,
                                'placas': placas,
                                'anio': anio,
                                'estado': 1
                            }
                        )
                        if not created:
                            vehiculo.idproducto_id = int(idproducto)
                            vehiculo.idestadoproducto_id = int(idestadoproducto)
                            vehiculo.imperfecciones = imperfecciones
                            vehiculo.placas = placas
                            vehiculo.anio = anio
                            vehiculo.save()
                    else:
                        situacion_disponible, _ = SituacionVehiculo.objects.get_or_create(nombre_situacion='DISPONIBLE', defaults={'estado': 1})
                        vehiculo = Vehiculo.objects.create(
                            id_situacion=situacion_disponible,
                            idproducto_id=int(idproducto),
                            serie_motor=serie_motor,
                            serie_chasis=serie_chasis,
                            anio=anio,
                            idestadoproducto_id=int(idestadoproducto),
                            imperfecciones=imperfecciones,
                            placas=placas,
                            estado=1
                        )
                    
                    if detalle_obj:
                        detalle_obj.id_vehiculo = vehiculo
                        detalle_obj.cantidad = cantidad
                        detalle_obj.precio_compra = precio_compra
                        detalle_obj.precio_minimo = precio_minimo
                        detalle_obj.precio_maximo = precio_maximo
                        detalle_obj.margen_minimo = margen_minimo
                        detalle_obj.margen_maximo = margen_maximo
                        detalle_obj.subtotal = cantidad * precio_compra
                        detalle_obj.save()
                        detalles_agregados_para_stock.append(detalle_obj)
                    else:
                        nuevo = CompraDetalle(
                            idcompra=compra,
                            id_vehiculo=vehiculo,
                            id_repuesto_comprado=None,
                            cantidad=cantidad,
                            precio_compra=precio_compra,
                            precio_minimo=precio_minimo,
                            precio_maximo=precio_maximo,
                            margen_minimo=margen_minimo,
                            margen_maximo=margen_maximo,
                            subtotal=cantidad * precio_compra
                        )
                        nuevos_detalles.append(nuevo)
                        detalles_agregados_para_stock.append(nuevo)

                elif tipo_item == "repuesto":
                    id_repuesto = request.POST.get(f"id_repuesto_{i}", "").strip()
                    ubicacion = request.POST.get(f"descripcion_{i}", "").strip()
                    
                    if not id_repuesto:
                        raise ValueError(f"Debe seleccionar un repuesto para el ítem {i}")
                    
                    #BUSCAR O CREAR - No duplica si ya existe
                    repuesto, created = RepuestoComp.objects.get_or_create(
                        id_repuesto_id=int(id_repuesto),
                        ubicacion=ubicacion,
                        defaults={
                            'estado': 1
                        }
                    )
                    if not created:
                        repuesto.estado = 1
                        repuesto.save()
                    
                    # --- SINCRONIZAR PRECIOS DEL CATÁLOGO ---
                    ultima_compra = Compras.objects.filter(
                        estado=1,
                        compradetalle__id_repuesto_comprado__id_repuesto_id=int(id_repuesto)
                    ).order_by('-fechacompra').first()

                    if not ultima_compra or (compra.fechacompra and ultima_compra.fechacompra and compra.fechacompra >= ultima_compra.fechacompra):
                        base_repuesto = Repuesto.objects.get(id_repuesto=int(id_repuesto))
                        base_repuesto.precio_minimo = precio_minimo
                        base_repuesto.precio_sugerido = precio_maximo
                        base_repuesto.save(update_fields=['precio_minimo', 'precio_sugerido'])
                    # -----------------------------------------

                    if detalle_obj:
                        detalle_obj.id_repuesto_comprado = repuesto
                        detalle_obj.cantidad = cantidad
                        detalle_obj.precio_compra = precio_compra
                        detalle_obj.precio_minimo = precio_minimo
                        detalle_obj.precio_maximo = precio_maximo
                        detalle_obj.margen_minimo = margen_minimo
                        detalle_obj.margen_maximo = margen_maximo
                        detalle_obj.subtotal = cantidad * precio_compra
                        detalle_obj.save()
                        detalles_agregados_para_stock.append(detalle_obj)
                    else:
                        nuevo = CompraDetalle(
                            idcompra=compra,
                            id_repuesto_comprado=repuesto,
                            id_vehiculo=None,
                            cantidad=cantidad,
                            precio_compra=precio_compra,
                            precio_minimo=precio_minimo,
                            precio_maximo=precio_maximo,
                            margen_minimo=margen_minimo,
                            margen_maximo=margen_maximo,
                            subtotal=cantidad * precio_compra
                        )
                        nuevos_detalles.append(nuevo)
                        detalles_agregados_para_stock.append(nuevo)

                total += cantidad * precio_compra
            
            # --- AUMENTAR STOCK CON TODOS LOS DETALLES ---
            if nuevos_detalles:
                CompraDetalle.objects.bulk_create(nuevos_detalles)
            
            for d in detalles_agregados_para_stock:
                if d.id_vehiculo_id:
                    _sincronizar_inventario_compra(compra.id_almacen_id, 'vehiculo', d.id_vehiculo_id, d.cantidad, 'AUMENTAR')
                elif d.id_repuesto_comprado_id:
                    _sincronizar_inventario_compra(compra.id_almacen_id, 'repuesto', d.id_repuesto_comprado_id, d.cantidad, 'AUMENTAR')
            # ------------------------------------------

            # Actualizar total
            compra.total_compra = total
            compra.save()
            
            # Guardar cuotas si aplica
            monto_egreso_caja = 0
            descripcion_egreso = ""
            
            if str(cabecera['id_forma_pago']) == str(FORMA_PAGO_CREDITO_ID):
                if request.POST.get("tiene_cuotas") == "1":
                    cuotas = int(request.POST.get("credito_cuotas") or 0)
                    total_adelanto = 0
                    
                    for i in range(1, cuotas + 1):
                        monto_adelanto_cuota = float(request.POST.get(f"monto_adelanto_{i}", 0) or 0)
                        total_adelanto += monto_adelanto_cuota
                        numero_cuota = int(request.POST.get(f"numero_cuota_{i}"))
                        
                        # ✅ USAR LA FECHA QUE VIENE DEL FORMULARIO
                        fecha_vencimiento_str = request.POST.get(f"fecha_vencimiento_{i}")
                        
                        if fecha_vencimiento_str:
                            fecha_vencimiento = datetime.strptime(fecha_vencimiento_str, '%Y-%m-%d').date()
                        else:
                            # Fallback
                            fecha_compra = cabecera['fechacompra']
                            fecha_vencimiento = fecha_compra + timedelta(days=30 * numero_cuota)
                        
                        Cuota.objects.create(
                            idcompra=compra,
                            numero_cuota=numero_cuota,
                            monto=float(request.POST.get(f"monto_{i}")),
                            tasa=float(request.POST.get(f"tasa_{i}")),
                            interes=float(request.POST.get(f"interes_{i}")),
                            total=float(request.POST.get(f"total_{i}")),
                            fecha_vencimiento=fecha_vencimiento,  # ✅ Fecha del formulario
                            monto_adelanto=monto_adelanto_cuota,
                            estado=1
                        )
                        
                    if total_adelanto > 0:
                        monto_egreso_caja = total_adelanto
                        descripcion_egreso = f"Pago inicial (adelanto) de Compra Crédito {compra.numcorrelativo} - Proveedor: {compra.idproveedor.razonsocial}"
            else:
                # Contado
                monto_egreso_caja = total
                descripcion_egreso = f"Pago de Compra Contado {compra.numcorrelativo} - Proveedor: {compra.idproveedor.razonsocial}"

            # Actualizar movimiento de caja
            from software.models.movimientoCajaModel import MovimientoCaja
            movimiento_existente = MovimientoCaja.objects.filter(idcompra=compra, tipo_movimiento='egreso').first()
            
            if monto_egreso_caja > 0:
                idusuario_session = request.session.get('idusuario')
                id_caja_session = request.session.get('id_caja')
                apertura = AperturaCierreCaja.objects.filter(
                    idusuario_id=idusuario_session,
                    id_caja_id=id_caja_session,
                    estado__in=['abierta', 'reabierta']
                ).first()
                if apertura:
                    from django.db.models import Sum
                    from decimal import Decimal
                    
                    ingresos = MovimientoCaja.objects.filter(
                        id_movimiento=apertura,
                        tipo_movimiento='ingreso',
                        estado=1
                    ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
                    
                    egresos_qs = MovimientoCaja.objects.filter(
                        id_movimiento=apertura,
                        tipo_movimiento='egreso',
                        estado=1
                    )
                    if movimiento_existente:
                        egresos_qs = egresos_qs.exclude(id_movimiento_caja=movimiento_existente.id_movimiento_caja)
                    egresos = egresos_qs.aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
                    
                    saldo_inicial = apertura.saldo_inicial or Decimal('0.00')
                    saldo_actual = saldo_inicial + ingresos - egresos
                    
                    if saldo_actual < Decimal(str(monto_egreso_caja)):
                        raise ValueError(f"Fondos insuficientes en la caja para actualizar la compra. Saldo disponible: S/ {saldo_actual:.2f}, Monto requerido: S/ {monto_egreso_caja:.2f}.")

                if movimiento_existente:
                    movimiento_existente.monto = monto_egreso_caja
                    movimiento_existente.descripcion = descripcion_egreso
                    movimiento_existente.estado = 1
                    movimiento_existente.save()
                else:
                    if apertura:
                        MovimientoCaja.objects.create(
                            id_caja_id=id_caja_session,
                            idusuario_id=idusuario_session,
                            id_movimiento=apertura,
                            idcompra=compra,
                            tipo_movimiento='egreso',
                            monto=monto_egreso_caja,
                            descripcion=descripcion_egreso,
                            estado=1
                        )
            else:
                # Si el monto ahora es 0 (ej. cambió a crédito sin inicial), anular el movimiento si existe
                if movimiento_existente:
                    movimiento_existente.estado = 0
                    movimiento_existente.monto = 0
                    movimiento_existente.save()
            
            # REGISTRAR EN AUDITORÍA
            from software.models.AuditoriaComprasModel import AuditoriaCompras
            AuditoriaCompras.objects.create(
                idcompra=id,
                accion='EDICION',
                motivo='Compra actualizada',
                idusuario_id=request.session.get('idusuario'),
                datos_anteriores=datos_anteriores
            )
            
            print(f"COMPRA ACTUALIZADA - ID: {compra.idcompra}")
            
            return JsonResponse({
                'ok': True,
                'message': 'Compra actualizada correctamente'
            })
            
        except Compras.DoesNotExist:
            return JsonResponse({
                'ok': False,
                'error': 'La compra no existe o ya fue eliminada'
            }, status=404)
        except ValueError as ve:
            print(f"ERROR DE VALIDACIÓN: {str(ve)}")
            return JsonResponse({
                'ok': False,
                'error': str(ve)
            }, status=400)
        except Exception as e:
            print(f"ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'ok': False,
                'error': f'Error al actualizar la compra: {str(e)}'
            }, status=500)
    
    return redirect("compras")


# ELIMINAR COMPRA (Eliminación lógica - SOLO ADMIN)
def eliminar_compra(request, id):
    """Eliminación lógica de una compra (cambia estado a 0) - SOLO ADMIN"""
    if request.method == "POST":
        try:
            # VALIDAR PERMISOS: Solo admin puede eliminar
            id_tipo_usuario = request.session.get('idtipousuario')
            
            if id_tipo_usuario != 1:  # 1 = Admin
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': 'No tiene permisos para eliminar compras. Solo administradores pueden realizar esta acción.',
                        'codigo': 'SIN_PERMISOS'
                    }, status=403)
                return redirect('compras')
            
            motivo = request.POST.get('motivo', '')
            idusuario = request.session.get('idusuario')
            
            # Cambiar estado de la compra
            compra = Compras.objects.get(idcompra=id)
            
            # --- REDUCIR STOCK AL ELIMINAR ---
            detalles_compra = CompraDetalle.objects.filter(idcompra=compra)
            for d in detalles_compra:
                if d.id_vehiculo_id:
                    _sincronizar_inventario_compra(compra.id_almacen_id, 'vehiculo', d.id_vehiculo_id, d.cantidad, 'REDUCIR')
                elif d.id_repuesto_comprado_id:
                    _sincronizar_inventario_compra(compra.id_almacen_id, 'repuesto', d.id_repuesto_comprado_id, d.cantidad, 'REDUCIR')
            # ---------------------------------
            
            # Guardar datos para auditoría
            datos_compra = {
                'numcorrelativo': compra.numcorrelativo,
                'proveedor': compra.idproveedor.razonsocial,
                'total': float(compra.total_compra),
                'fecha': str(compra.fechacompra)
            }
            
            compra.estado = 0
            compra.save()
            
            # REGISTRAR EN AUDITORÍA
            from software.models.AuditoriaComprasModel import AuditoriaCompras
            AuditoriaCompras.objects.create(
                idcompra=id,
                accion='ELIMINACION',
                motivo=motivo,
                idusuario_id=idusuario,
                datos_anteriores=datos_compra
            )
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Compra eliminada correctamente'
                })
            
            return redirect('compras')
            
        except Compras.DoesNotExist:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'La compra no existe'
                }, status=404)
            return redirect('compras')
            
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                }, status=400)
            return redirect('compras')
    
    return redirect("compras")


# ─────────────────────────────────────────────────────────────────────
# GENERACIÓN DE PDF DEL DETALLE DE COMPRA
# ─────────────────────────────────────────────────────────────────────
def compra_pdf(request, idcompra):
    """
    Genera el PDF del detalle de compra con diseño corporativo premium.
    Incluye: encabezado, información general, tabla de productos/repuestos
    y plan de cuotas (si la compra es a crédito).
    """
    from software.models.empresaModel import Empresa
    from software.utils.logo_utils import get_logo_image_for_pdf

    compra  = get_object_or_404(Compras, idcompra=idcompra, estado=1)
    detalles = CompraDetalle.objects.filter(idcompra=compra).select_related(
        'id_vehiculo__idproducto',
        'id_vehiculo__idestadoproducto',
        'id_repuesto_comprado__id_repuesto',
    )
    cuotas  = compra.cuota.all().order_by('numero_cuota')
    empresa = Empresa.objects.filter(activo=True).first()

    # ── Buffer PDF ──────────────────────────────────────────────────────
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=2 * cm,
    )

    # ── Paleta de colores ───────────────────────────────────────────────
    DARK_BLUE    = colors.HexColor('#0D1B2A')
    ACCENT_BLUE  = colors.HexColor('#1565C0')
    TEAL         = colors.HexColor('#00897B')
    SILVER       = colors.HexColor('#B0BEC5')
    LIGHT_GRAY   = colors.HexColor('#F4F6F8')
    YELLOW_BG    = colors.HexColor('#FFF8E1')
    YELLOW_HDR   = colors.HexColor('#F9A825')
    WHITE        = colors.white
    TEXT_DARK    = colors.HexColor('#212121')
    TEXT_MUTED   = colors.HexColor('#546E7A')
    GREEN        = colors.HexColor('#2E7D32')
    ORANGE       = colors.HexColor('#E65100')
    PENDING_BG   = colors.HexColor('#FF8F00')

    # ── Estilos ─────────────────────────────────────────────────────────
    styles = getSampleStyleSheet()

    def mk(name, **kw):
        return ParagraphStyle(name, parent=styles['Normal'], **kw)

    s_empresa_nom = mk('emp_nom', fontSize=18, fontName='Helvetica-Bold',
                       textColor=DARK_BLUE, leading=22, spaceAfter=4)
    s_empresa_sub = mk('emp_sub', fontSize=8, fontName='Helvetica',
                       textColor=TEXT_MUTED, leading=10)
    s_titulo_doc  = mk('tit_doc', fontSize=20, fontName='Helvetica-Bold',
                       textColor=TEXT_DARK, leading=24, alignment=TA_CENTER)
    s_correlativo = mk('corr', fontSize=13, fontName='Helvetica-Bold',
                       textColor=ACCENT_BLUE, alignment=TA_CENTER, leading=16)
    s_id_compra   = mk('idc', fontSize=9, fontName='Helvetica',
                       textColor=TEXT_MUTED, alignment=TA_RIGHT)
    s_info_label  = mk('inf_lbl', fontSize=7, fontName='Helvetica-Bold',
                       textColor=TEXT_MUTED, leading=9)
    s_info_valor  = mk('inf_val', fontSize=9, fontName='Helvetica-Bold',
                       textColor=TEXT_DARK, leading=12)

    # Colores para badges: medios y equilibrados (no demasiado oscuros, no pasteles)
    BADGE_BLUE   = colors.HexColor('#2563EB')  # azul medio
    BADGE_TEAL   = colors.HexColor('#0D9488')  # verde teal medio
    BADGE_SLATE  = colors.HexColor('#475569')  # gris pizarra
    BADGE_ORANGE = colors.HexColor('#D97706')  # naranja ambar

    def badge(text, bg_color, fg_color=WHITE):
        """
        Badge con esquinas redondeadas usando tabla anidada.
        Genera un badge compacto con fondo sólido y texto blanco,
        similar a los badges del diseño de referencia.
        """
        p = Paragraph(
            f'<b>{text}</b>',
            mk(f'bdg_p_{text[:5].replace(" ","_")}',
               fontSize=8, fontName='Helvetica-Bold',
               textColor=fg_color, alignment=TA_CENTER, leading=10)
        )
        tbl = Table([[p]])
        tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), bg_color),
            ('ROUNDEDCORNERS', [4, 4, 4, 4]),
            ('TOPPADDING',    (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING',   (0, 0), (-1, -1), 8),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
        ]))
        return tbl

    s_sec_hdr   = mk('sec_hdr', fontSize=10, fontName='Helvetica-Bold',
                     textColor=TEAL, spaceBefore=6, spaceAfter=4)
    s_th        = mk('th', fontSize=8, fontName='Helvetica-Bold',
                     textColor=WHITE, alignment=TA_CENTER)
    s_cell      = mk('cell', fontSize=8, fontName='Helvetica',
                     textColor=TEXT_DARK, leading=11)
    s_cell_c    = mk('cell_c', fontSize=8, fontName='Helvetica',
                     textColor=TEXT_DARK, alignment=TA_CENTER, leading=11)
    s_cell_r    = mk('cell_r', fontSize=8, fontName='Helvetica',
                     textColor=TEXT_DARK, alignment=TA_RIGHT, leading=11)
    s_cell_br   = mk('cell_br', fontSize=9, fontName='Helvetica-Bold',
                     textColor=GREEN, alignment=TA_RIGHT, leading=12)
    s_total_lbl = mk('tot_lbl', fontSize=10, fontName='Helvetica-Bold',
                     textColor=TEXT_DARK, alignment=TA_RIGHT)
    s_total_val = mk('tot_val', fontSize=13, fontName='Helvetica-Bold',
                     textColor=GREEN, alignment=TA_RIGHT)
    s_cuota_hdr = mk('cut_hdr', fontSize=8, fontName='Helvetica-Bold',
                     textColor=TEXT_DARK, alignment=TA_CENTER)
    s_firma_lbl = mk('frm_lbl', fontSize=8, fontName='Helvetica-Bold',
                     textColor=TEXT_DARK, alignment=TA_CENTER)

    story = []

    # ════════════════════════════════════════════════════════════════
    # SECCIÓN 1 – ENCABEZADO
    # ════════════════════════════════════════════════════════════════
    empresa_nombre = empresa.nombrecomercial if empresa else 'EMPRESA S.A.C.'
    empresa_ruc    = f"RUC: {empresa.ruc}" if empresa else 'RUC: 00000000000'
    empresa_dir    = empresa.direccion if empresa else '-'
    empresa_tel    = f"Telf.: {empresa.telefono}" if (empresa and empresa.telefono) else ''
    empresa_web    = f"Email: {empresa.pagina}" if (empresa and empresa.pagina) else ''

    # Logo desde Cloudinary
    logo_rl = get_logo_image_for_pdf(empresa, width_mm=35, height_mm=22, circular=False)
    logo_elem = logo_rl if logo_rl else Paragraph(
        '<font color="#F9A825" size="28">&#9670;</font>',
        mk('logo_fb', fontSize=28, textColor=YELLOW_HDR, alignment=TA_LEFT)
    )

    info_empresa = [Paragraph(empresa_nombre, s_empresa_nom),
                    Paragraph(empresa_ruc, s_empresa_sub),
                    Paragraph(empresa_dir, s_empresa_sub)]
    if empresa_tel:
        info_empresa.append(Paragraph(empresa_tel, s_empresa_sub))
    if empresa_web:
        info_empresa.append(Paragraph(empresa_web, s_empresa_sub))

    col_titulo = [
        Paragraph('<font color="#1565C0"><b>DETALLE DE COMPRA</b></font>',
                  mk('tit_doc_c', fontSize=14, fontName='Helvetica-Bold', textColor=ACCENT_BLUE, alignment=TA_RIGHT, leading=18)),
        Paragraph(f'<b>#{compra.numcorrelativo}</b>',
                  mk('corr_c', fontSize=11, fontName='Helvetica-Bold', textColor=DARK_BLUE, alignment=TA_RIGHT, leading=14)),
        Paragraph(f'Fecha: {compra.fechacompra.strftime("%d/%m/%Y")}',
                  mk('fecha_c', fontSize=9, fontName='Helvetica', textColor=TEXT_MUTED, alignment=TA_RIGHT, leading=12))
    ]

    hdr_tbl = Table(
        [[logo_elem, info_empresa, col_titulo]],
        colWidths=[4.2 * cm, 9.3 * cm, 5 * cm]
    )
    hdr_tbl.setStyle(TableStyle([
        ('BACKGROUND',   (0, 0), (-1, -1), WHITE),
        ('BOX',          (0, 0), (-1, -1), 0.8, SILVER),
        ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING',  (0, 0), (0, 0), 10),
        ('LEFTPADDING',  (1, 0), (1, 0), 8),
        ('RIGHTPADDING', (-1, 0), (-1, -1), 10),
        ('TOPPADDING',   (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 12),
        ('ROUNDEDCORNERS', [6, 6, 6, 6]),
    ]))
    story.append(hdr_tbl)
    story.append(Spacer(1, 8))

    # ════════════════════════════════════════════════════════════════
    # SECCIÓN 2 – INFORMACIÓN GENERAL
    # ════════════════════════════════════════════════════════════════
    proveedor_nombre = compra.idproveedor.razonsocial if compra.idproveedor else '-'
    fecha_str        = compra.fechacompra.strftime('%d/%m/%Y') if compra.fechacompra else '-'
    tipo_comp        = compra.idtipocliente.nomtipocliente if compra.idtipocliente else '-'
    forma_pago_nom   = compra.id_forma_pago.nombre if compra.id_forma_pago else '-'
    sucursal_nom     = compra.id_sucursal.nombre_sucursal if compra.id_sucursal else '-'

    if compra.id_tipo_pago:
        tipo_pago_nom = compra.id_tipo_pago.nombre
        tp_bg = BADGE_TEAL
    elif compra.id_forma_pago and compra.id_forma_pago.id_forma_pago == 2:
        tipo_pago_nom = 'Crédito'
        tp_bg = BADGE_ORANGE
    else:
        tipo_pago_nom = forma_pago_nom
        tp_bg = BADGE_TEAL

    fp_bg = BADGE_BLUE if 'contado' in forma_pago_nom.lower() else BADGE_ORANGE

    tipo_cam_str = f"{float(compra.tipo_cambio):.4f}" if compra.tipo_cambio else "1.0000"
    
    # Fila 1: Proveedor | Fecha | Correlativo | Tipo de Cambio
    r1 = Table([
        [Paragraph('PROVEEDOR', s_info_label),
         Paragraph('FECHA COMPRA', s_info_label),
         Paragraph('N\u00b0 CORRELATIVO', s_info_label),
         Paragraph('TIPO DE CAMBIO', s_info_label)],
        [Paragraph(proveedor_nombre, s_info_valor),
         Paragraph(fecha_str, s_info_valor),
         Paragraph(compra.numcorrelativo, s_info_valor),
         Paragraph(tipo_cam_str, s_info_valor)],
    ], colWidths=[6.5 * cm, 3.5 * cm, 4.0 * cm, 3.5 * cm])
    r1.setStyle(TableStyle([
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING',   (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 3),
        ('LEFTPADDING',  (0, 0), (-1, -1), 6),
    ]))

    # Fila 2: Tipo comp | Forma pago | Tipo pago | Sucursal (sin colores)
    r2 = Table([
        [Paragraph('TIPO COMPROBANTE', s_info_label),
         Paragraph('FORMA DE PAGO', s_info_label),
         Paragraph('TIPO DE PAGO', s_info_label),
         Paragraph('SUCURSAL', s_info_label)],
        [Paragraph(tipo_comp,      s_info_valor),
         Paragraph(forma_pago_nom, s_info_valor),
         Paragraph(tipo_pago_nom,  s_info_valor),
         Paragraph(sucursal_nom,   s_info_valor)],
    ], colWidths=[4.375 * cm, 4.375 * cm, 4.375 * cm, 4.375 * cm])
    r2.setStyle(TableStyle([
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING',   (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 3),
        ('LEFTPADDING',  (0, 0), (-1, -1), 6),
    ]))

    info_box = Table([
        [Paragraph('<b>Informaci\u00f3n General</b>',
                   mk('ig_t', fontSize=10, fontName='Helvetica-Bold', textColor=ACCENT_BLUE))],
        [r1],
        [r2],
    ], colWidths=[17.5 * cm])
    info_box.setStyle(TableStyle([
        ('BACKGROUND',   (0, 0), (-1, -1), LIGHT_GRAY),
        ('BOX',          (0, 0), (-1, -1), 1, SILVER),
        ('TOPPADDING',   (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING',(0, 0), (-1, 0), 4),
        ('TOPPADDING',   (0, 1), (-1, -1), 4),
        ('BOTTOMPADDING',(0, 1), (-1, -1), 8),
        ('LEFTPADDING',  (0, 0), (-1, -1), 10),
    ]))
    story.append(info_box)
    story.append(Spacer(1, 12))

    # ════════════════════════════════════════════════════════════════
    # SECCIÓN 3 – TABLA DE PRODUCTOS / REPUESTOS
    # ════════════════════════════════════════════════════════════════
    story.append(Paragraph('Productos / Repuestos', s_sec_hdr))

    prod_hdrs  = ['#', 'TIPO', 'DETALLE', 'CANT.', 'MON.', 'PRECIO $', 'P. COMPRA', 'P. VENTA', 'SUBTOTAL']
    prod_col_w = [0.8*cm, 1.7*cm, 6.1*cm, 1.2*cm, 1.1*cm, 1.8*cm, 2.0*cm, 2.0*cm, 1.8*cm]
    prod_data  = [[Paragraph(h, s_th) for h in prod_hdrs]]

    for idx, det in enumerate(detalles, start=1):
        if det.id_vehiculo:
            tipo_badge = badge('Vehículo', BADGE_BLUE)
            prod_obj   = det.id_vehiculo.idproducto
            nombre     = prod_obj.nomproducto if prod_obj else '-'
            v          = det.id_vehiculo
            extras = []
            if v.serie_motor:          extras.append(f'· Motor: {v.serie_motor}')
            if v.serie_chasis:         extras.append(f'· Chasis: {v.serie_chasis}')
            if v.anio:                 extras.append(f'· Año: {v.anio}')
            if v.placas:               extras.append(f'· Placas: {v.placas}')
            if hasattr(v, 'idestadoproducto') and v.idestadoproducto:
                extras.append(f'· {v.idestadoproducto.nombreestadoproducto}')
        elif det.id_repuesto_comprado:
            tipo_badge = badge('Repuesto', BADGE_TEAL)
            rc         = det.id_repuesto_comprado
            nombre     = rc.id_repuesto.nombre if rc.id_repuesto else '-'
            extras = []
            if rc.id_repuesto and rc.id_repuesto.codigo_barras: extras.append(f'· Código: {rc.id_repuesto.codigo_barras}')
            if rc.id_repuesto and rc.id_repuesto.modelo_referencia: extras.append(f'· Modelo: {rc.id_repuesto.modelo_referencia}')
            if rc.ubicacion:   extras.append(f'· Ubicación: {rc.ubicacion}')
        else:
            tipo_badge = Paragraph('-', s_cell_c)
            nombre     = '-'
            extras     = []

        detalle_txt = f'<b>{nombre}</b>'
        if extras:
            detalle_txt += '<br/>' + '<br/>'.join(
                [f'<font color="#546E7A" size="7">{e}</font>' for e in extras]
            )

        # Badge de cantidad: tabla anidada con esquinas redondeadas
        cant_p = Paragraph(
            f'<b>{det.cantidad}</b>',
            mk(f'cant_p_{idx}', fontSize=9, fontName='Helvetica-Bold',
               textColor=WHITE, alignment=TA_CENTER, leading=10)
        )
        cant_badge = Table([[cant_p]])
        cant_badge.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), BADGE_BLUE),
            ('ROUNDEDCORNERS', [4, 4, 4, 4]),
            ('TOPPADDING',    (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING',   (0, 0), (-1, -1), 6),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
        ]))

        precio_dol = float(det.precio_dolares) if det.precio_dolares else 0.0
        moneda = det.moneda if det.moneda else 'PEN'
        precio_dol_str = f'$ {precio_dol:,.2f}' if precio_dol > 0 else '-'

        prod_data.append([
            Paragraph(str(idx), s_cell_c),
            tipo_badge,
            Paragraph(detalle_txt, s_cell),
            cant_badge,
            Paragraph(f'<b>{moneda}</b>', s_cell_c),
            Paragraph(precio_dol_str, s_cell_c),
            Paragraph(f'S/.\n{float(det.precio_compra):,.2f}', s_cell_c),
            Paragraph(f'S/.\n{float(det.precio_maximo):,.2f}', s_cell_c),
            Paragraph(f'<b>S/.\n{float(det.subtotal):,.2f}</b>', s_cell_br),
        ])

    # Fila de total: Mini-tabla alineada a la derecha para emparejar Label y Valor sin mucho espacio
    lbl_p = Paragraph('<b>TOTAL<br/>COMPRA:</b>', s_total_lbl)
    val_p = Paragraph(f'<b>S/. {float(compra.total_compra):,.2f}</b>', s_total_val)
    
    mini_tbl = Table([[lbl_p, val_p]], hAlign='RIGHT')
    mini_tbl.setStyle(TableStyle([
        ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING',  (0, 0), (0, 0), 0),
        ('RIGHTPADDING', (0, 0), (0, 0), 2),  # espacio reducido entre label y valor
        ('LEFTPADDING',  (1, 0), (1, 0), 0),
        ('RIGHTPADDING', (1, 0), (1, 0), 0),  # flush right al borde de la celda padre
        ('TOPPADDING',   (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 0),
    ]))

    prod_data.append([
        Paragraph('', s_cell), Paragraph('', s_cell),
        Paragraph('', s_cell), Paragraph('', s_cell),
        Paragraph('', s_cell), Paragraph('', s_cell),
        mini_tbl,
        Paragraph('', s_cell), Paragraph('', s_cell),
    ])

    prod_tbl = Table(prod_data, colWidths=prod_col_w, repeatRows=1)
    prod_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0), DARK_BLUE),
        ('ROWBACKGROUNDS',(0, 1), (-1, -2), [WHITE, LIGHT_GRAY]),
        ('BACKGROUND',    (0, -1), (-1, -1), WHITE),
        ('BOX',           (0, 0), (-1, -1), 0.8, SILVER),
        ('INNERGRID',     (0, 0), (-1, -2), 0.3, SILVER),
        ('LINEABOVE',     (0, -1), (-1, -1), 1.5, ACCENT_BLUE),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 4),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
        # Unir columnas 6, 7 y 8 solo en la fila de total para que la mini-tabla fluya a la derecha
        ('SPAN',          (6, -1), (8, -1)),
        ('ALIGN',         (6, -1), (8, -1), 'RIGHT'),
    ]))
    story.append(prod_tbl)

    # ════════════════════════════════════════════════════════════════
    # SECCIÓN 3.5 – MÉTODOS DE PAGO (si existen múltiples pagos)
    # ════════════════════════════════════════════════════════════════
    pagos_list = []
    if compra.id_forma_pago and compra.id_forma_pago.id_forma_pago != 2: # No es crédito
        if compra.observaciones and '[FRACCIONADO:' in compra.observaciones:
            import re
            obs = compra.observaciones.replace('[FRACCIONADO:', '').replace(']', '').strip()
            partes = obs.split('|')
            for parte in partes:
                parte = parte.strip()
                if not parte: continue
                m = re.match(r'^(.*?):\s*S/([\d.]+)(?:\s*\(Op:\s*(.*?)\))?$', parte)
                if m:
                    pagos_list.append({
                        'nombre': m.group(1).strip(),
                        'monto': float(m.group(2)),
                        'operacion': m.group(3).strip() if m.group(3) else 'Sin detalle'
                    })
        else:
            monto = float(compra.total_compra) if compra.total_compra else 0.0
            operacion = 'Sin detalle'
            if compra.observaciones and '[Op:' in compra.observaciones:
                import re
                m = re.search(r'\[Op:\s*(.*?)\]', compra.observaciones)
                if m:
                    operacion = m.group(1).strip()
            pagos_list.append({
                'nombre': compra.id_forma_pago.nombre,
                'monto': monto,
                'operacion': operacion
            })

    if pagos_list:
        story.append(Spacer(1, 14))
        story.append(Paragraph('Métodos de Pago Registrados', s_sec_hdr))
        
        pagos_hdrs  = ['MÉTODO / CAJA', 'DETALLE / N° OPERACIÓN', 'MONTO ABONADO']
        pagos_col_w = [5*cm, 9.5*cm, 3*cm]
        pagos_data  = [[Paragraph(h, s_th) for h in pagos_hdrs]]
        
        for mov in pagos_list:
            pagos_data.append([
                Paragraph(mov['nombre'], s_cell),
                Paragraph(mov['operacion'], s_cell),
                Paragraph(f"<b>S/. {float(mov['monto']):,.2f}</b>", mk('pd_v', fontSize=8, fontName='Helvetica-Bold', textColor=TEAL, alignment=TA_RIGHT)),
            ])
            
        pagos_tbl = Table(pagos_data, colWidths=pagos_col_w)
        pagos_tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, 0), DARK_BLUE),
            ('ROWBACKGROUNDS',(0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
            ('BOX',           (0, 0), (-1, -1), 0.8, SILVER),
            ('INNERGRID',     (0, 0), (-1, -1), 0.3, SILVER),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING',    (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING',   (0, 0), (-1, -1), 4),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
            ('ALIGN',         (2, 0), (2, -1), 'RIGHT'),
        ]))
        story.append(pagos_tbl)

    # ════════════════════════════════════════════════════════════════
    # SECCIÓN 4 – PLAN DE CUOTAS (solo si la compra es a crédito)
    # ════════════════════════════════════════════════════════════════
    if cuotas.exists():
        story.append(Spacer(1, 14))
        story.append(Paragraph('Plan de Cuotas', s_sec_hdr))

        cuota_hdrs  = ['CUOTA', 'FECHA VENCIMIENTO', 'MONTO', 'INTERÉS', 'TOTAL', 'PAGADO', 'SALDO', 'ESTADO']
        cuota_col_w = [1.5*cm, 3.2*cm, 2.3*cm, 2.3*cm, 2.3*cm, 2.3*cm, 2.3*cm, 2.3*cm]
        cuota_data  = [[Paragraph(h, s_cuota_hdr) for h in cuota_hdrs]]

        for cuota in cuotas:
            pagado    = float(cuota.monto_pagado) if cuota.monto_pagado else 0
            pagado_txt = f'S/. {pagado:,.2f}' if pagado > 0 else '-'
            
            # Calculamos el saldo restando ambos como float
            saldo     = float(cuota.total) - pagado
            saldo_txt = f'S/. {saldo:,.2f}'
            
            if saldo <= 0:
                estado_texto = 'PAGADO'
                bg_estado = GREEN
            else:
                estado_texto = 'PENDIENTE'
                bg_estado = PENDING_BG

            # Badge de estado: tabla anidada con ancho fijo para evitar overflow
            est_p = Paragraph(
                f'<b>{estado_texto}</b>',
                mk(f'est_p_{cuota.numero_cuota}', fontSize=7, fontName='Helvetica-Bold',
                   textColor=WHITE, alignment=TA_CENTER, leading=10)
            )
            estado_badge = Table([[est_p]], colWidths=[2.0 * cm])
            estado_badge.setStyle(TableStyle([
                ('BACKGROUND',    (0, 0), (-1, -1), bg_estado),
                ('ROUNDEDCORNERS', [4, 4, 4, 4]),
                ('TOPPADDING',    (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('LEFTPADDING',   (0, 0), (-1, -1), 3),
                ('RIGHTPADDING',  (0, 0), (-1, -1), 3),
            ]))
            cuota_data.append([
                Paragraph(str(cuota.numero_cuota), s_cell_c),
                Paragraph(cuota.fecha_vencimiento.strftime('%d/%m/%Y'), s_cell_c),
                Paragraph(f'S/.\n{float(cuota.monto):,.2f}', s_cell_c),
                Paragraph(f'S/. {float(cuota.interes):,.2f}', s_cell_c),
                Paragraph(f'S/.\n{float(cuota.total):,.2f}', s_cell_c),
                Paragraph(pagado_txt, s_cell_c),
                Paragraph(saldo_txt, s_cell_c),
                estado_badge,
            ])

        cuota_tbl = Table(cuota_data, colWidths=cuota_col_w, repeatRows=1)
        cuota_tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, 0), YELLOW_HDR),
            ('ROWBACKGROUNDS',(0, 1), (-1, -1), [YELLOW_BG, WHITE]),
            ('BOX',           (0, 0), (-1, -1), 0.8, SILVER),
            ('INNERGRID',     (0, 0), (-1, -1), 0.3, SILVER),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING',    (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING',   (0, 0), (-1, -1), 4),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
        ]))
        story.append(cuota_tbl)

    # ════════════════════════════════════════════════════════════════
    # SECCIÓN 5 – FIRMAS
    # ════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width='100%', thickness=0.5, color=SILVER, dash=(4, 4)))
    story.append(Spacer(1, 16))

    firma_data = [
        ['', ''],
        [Paragraph('________________________', s_firma_lbl),
         Paragraph('________________________', s_firma_lbl)],
        [Paragraph('FIRMA DEL COMPRADOR', s_firma_lbl),
         Paragraph('FIRMA DEL PROVEEDOR / SELLO', s_firma_lbl)],
    ]
    firma_tbl = Table(firma_data, colWidths=[8.75 * cm, 8.75 * cm])
    firma_tbl.setStyle(TableStyle([
        ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN',        (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING',   (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 3),
        ('LINEBELOW',    (0, 1), (0, 1), 0.8, DARK_BLUE),
        ('LINEBELOW',    (1, 1), (1, 1), 0.8, DARK_BLUE),
    ]))
    story.append(firma_tbl)

    # ── Generar y devolver PDF ──────────────────────────────────────────
    doc.build(story)
    buffer.seek(0)

    response = FileResponse(buffer, content_type='application/pdf', as_attachment=False)
    response['Content-Disposition'] = (
        f'inline; filename="Compra_{compra.numcorrelativo}.pdf"'
    )
    return response


# ─────────────────────────────────────────────────────────────────────────────
# API: CREAR PRODUCTO (VEHÍCULO DEL CATÁLOGO) DESDE MODAL DE COMPRA
# ─────────────────────────────────────────────────="────────────────────────────
def api_crear_producto_compra(request):
    """
    Crea un nuevo Producto (base de vehículo) desde el modal de registro rápido
    en el formulario de compras. Devuelve JSON con el id y nombre del producto creado.
    """
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido.'}, status=405)

    idusuario = request.session.get('idusuario')
    if not idusuario:
        return JsonResponse({'ok': False, 'error': 'No autenticado.'}, status=401)

    try:
        from software.models.marcaModel import Marca
        from software.models.categoriaModel import Categoria
        from software.models.cilindradaModel import Cilindrada
        from software.models.colorModel import Color
        from software.models.modeloModel import Modelo
        from software.models.UnidadesModel import Unidades
        from software.models.ConfiguracionVehicularModel import ConfiguracionVehicular
        from software.models.DetalleColorModel import DetalleColor

        nomproducto = (request.POST.get('nomproducto') or '').strip()
        idmarca     = request.POST.get('idmarca')
        idcategoria = request.POST.get('idcategoria')
        idcilindrada = request.POST.get('idcilindrada')
        idcolor     = request.POST.get('idcolor')
        id_detalle_color = request.POST.get('id_detalle_color') or None
        idunidad    = request.POST.get('idunidad')
        idmodelo    = request.POST.get('idmodelo') or None
        id_configuracion = request.POST.get('id_configuracion') or None
        codigo_interno = (request.POST.get('codigo_interno') or '').strip()
        imagen = 'sin_imagen.jpg'  # valor por defecto

        if not nomproducto:
            return JsonResponse({'ok': False, 'error': 'El nombre del producto es obligatorio.'}, status=400)
        if not idmarca:
            return JsonResponse({'ok': False, 'error': 'Debe seleccionar una marca.'}, status=400)
        if not idcategoria:
            return JsonResponse({'ok': False, 'error': 'Debe seleccionar una categoría.'}, status=400)
        if not idcilindrada:
            return JsonResponse({'ok': False, 'error': 'Debe seleccionar una cilindrada.'}, status=400)
        if not idcolor:
            return JsonResponse({'ok': False, 'error': 'Debe seleccionar un color.'}, status=400)
        if not idunidad:
            return JsonResponse({'ok': False, 'error': 'Debe seleccionar una unidad.'}, status=400)

        nuevo_producto = Producto.objects.create(
            nomproducto=nomproducto,
            idmarca_id=int(idmarca),
            idcategoria_id=int(idcategoria),
            idcilindrada_id=int(idcilindrada),
            idcolor_id=int(idcolor),
            id_detalle_color_id=int(id_detalle_color) if id_detalle_color else None,
            idunidad_id=int(idunidad),
            idmodelo_id=int(idmodelo) if idmodelo else None,
            id_configuracion_id=int(id_configuracion) if id_configuracion else None,
            codigo_interno=codigo_interno if codigo_interno else None,
            imagenprod=imagen,
            estado=1,
        )

        return JsonResponse({
            'ok': True,
            'id': nuevo_producto.idproducto,
            'nombre': nuevo_producto.nomproducto,
            'mensaje': f'Producto "{nuevo_producto.nomproducto}" creado correctamente.'
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


# ─────────────────────────────────────────────────────────────────────────────
# API: CREAR REPUESTO (CATÁLOGO) DESDE MODAL DE COMPRA
# ─────────────────────────────────────────────────────────────────────────────
def api_crear_repuesto_compra(request):
    """
    Crea un nuevo Repuesto base desde el modal de registro rápido en el formulario
    de compras. Devuelve JSON con el id y nombre del repuesto creado.
    """
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido.'}, status=405)

    idusuario = request.session.get('idusuario')
    if not idusuario:
        return JsonResponse({'ok': False, 'error': 'No autenticado.'}, status=401)

    try:
        from software.models.MarcaRepuestoModel import MarcaRepuesto
        from software.models.CategoriaRepuestoModel import CategoriaRepuesto
        from software.models.GarantiaRepuestoModel import GarantiaRepuesto
        from software.models.UnidadesModel import Unidades

        nombre    = (request.POST.get('nombre') or '').strip()
        idmarca   = request.POST.get('idmarca_rep')
        idunidad  = request.POST.get('idunidad_rep')
        idcategoria = request.POST.get('idcategoria_rep') or None
        idgarantia  = request.POST.get('id_garantia_repuesto') or None
        modelo_ref  = request.POST.get('modelo_referencia') or None
        codigo_interno = (request.POST.get('codigo_interno') or '').strip()
        codigo_barras  = (request.POST.get('codigo_barras') or '').strip()
        compatibilidad = request.POST.get('compatibilidad') or None
        descripcion    = request.POST.get('descripcion') or None
        observaciones  = request.POST.get('observaciones') or None
        
        stock_minimo   = int(request.POST.get('stock_minimo') or 0)
        stock_maximo   = int(request.POST.get('stock_maximo') or 0)
        costo_unitario = float(request.POST.get('costo_unitario') or 0.0)
        precio_minimo  = float(request.POST.get('precio_minimo') or 0.0)
        precio_sugerido= float(request.POST.get('precio_sugerido') or 0.0)

        if not nombre:
            return JsonResponse({'ok': False, 'error': 'El nombre del repuesto es obligatorio.'}, status=400)
        if not idmarca:
            return JsonResponse({'ok': False, 'error': 'Debe seleccionar una marca.'}, status=400)
        if not idunidad:
            return JsonResponse({'ok': False, 'error': 'Debe seleccionar una unidad.'}, status=400)

        nuevo_repuesto = Repuesto.objects.create(
            nombre=nombre,
            idmarca_id=int(idmarca),
            idunidad_id=int(idunidad),
            id_categoria_repuesto_id=int(idcategoria) if idcategoria else None,
            id_garantia_repuesto_id=int(idgarantia) if idgarantia else None,
            modelo_referencia=modelo_ref,
            codigo_interno=codigo_interno if codigo_interno else None,
            codigo_barras=codigo_barras if codigo_barras else None,
            compatibilidad=compatibilidad,
            descripcion=descripcion,
            observaciones=observaciones,
            stock_minimo=stock_minimo,
            stock_maximo=stock_maximo,
            costo_unitario=costo_unitario,
            precio_minimo=precio_minimo,
            precio_sugerido=precio_sugerido,
            estado=1,
        )

        return JsonResponse({
            'ok': True,
            'id': nuevo_repuesto.id_repuesto,
            'nombre': nuevo_repuesto.nombre,
            'mensaje': f'Repuesto "{nuevo_repuesto.nombre}" creado correctamente.'
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

def api_validar_series_vehiculo(request):
    serie_motor = request.GET.get('motor', '').strip()
    serie_chasis = request.GET.get('chasis', '').strip()
    
    if serie_motor or serie_chasis:
        query = Q()
        if serie_motor:
            query |= Q(serie_motor=serie_motor)
        if serie_chasis:
            query |= Q(serie_chasis=serie_chasis)
            
        if Vehiculo.objects.filter(query).exists():
            return JsonResponse({'existe': True, 'mensaje': 'La Serie Motor o Serie Chasis ya se encuentra registrada en el sistema.'})
            
    return JsonResponse({'existe': False})


# ========================================
# 🚀 SERVER-SIDE PROCESSING - COMPRAS
# ========================================
from django.core.paginator import Paginator

def api_listar_compras(request):
    """
    API AJAX para listar compras con paginación, búsqueda (proveedor, RUC, comprobante) y filtro de fechas.
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    # 1. Autenticación y Permisos
    id_tipo_usuario = request.session.get('idtipousuario')
    idusuario = request.session.get('idusuario')
    id_sucursal = request.session.get('id_sucursal')
    id_almacen = request.session.get('id_almacen')

    if not id_tipo_usuario:
        return JsonResponse({'error': 'No autorizado'}, status=401)

    es_admin = (id_tipo_usuario == 1)

    # 2. Leer parámetros de la solicitud
    page_num = request.GET.get('page', '1')
    page_size = 10
    search = request.GET.get('search', '').strip()
    
    # 3. Construir Filtros Base
    filtros = {'estado': 1}

    # 3.1 Filtro de Fechas
    hoy = datetime.now().date()
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    
    fecha_inicio_str = request.GET.get('fecha_inicio', '').strip()
    fecha_fin_str = request.GET.get('fecha_fin', '').strip()

    if not fecha_inicio_str and not search:
        fecha_inicio_str = inicio_semana.strftime('%Y-%m-%d')
    if not fecha_fin_str and not search:
        fecha_fin_str = hoy.strftime('%Y-%m-%d')

    if fecha_inicio_str:
        filtros['fechacompra__gte'] = fecha_inicio_str
    if fecha_fin_str:
        filtros['fechacompra__lte'] = fecha_fin_str

    # 4. Query Base
    base_queryset = Compras.objects.filter(**filtros).exclude(numcorrelativo='STOCKDIR').select_related(
        'idproveedor',
        'idtipocliente',
        'id_forma_pago',
        'id_tipo_pago',
        'id_sucursal'
    )

    # Filtro por sucursal / almacen
    if es_admin:
        if id_almacen:
            base_queryset = base_queryset.filter(id_almacen_id=id_almacen)
        elif id_sucursal:
            base_queryset = base_queryset.filter(id_sucursal_id=id_sucursal)
    else:
        try:
            usuario = Usuario.objects.get(idusuario=idusuario)
            if id_almacen:
                base_queryset = base_queryset.filter(id_almacen_id=id_almacen)
            else:
                base_queryset = base_queryset.filter(id_sucursal=usuario.id_sucursal)
        except Usuario.DoesNotExist:
            return JsonResponse({'ok': True, 'compras': [], 'total_pages': 0})

    # 5. Filtro de Búsqueda Libre
    if search:
        q_search = Q(idproveedor__razonsocial__icontains=search) | \
                   Q(idproveedor__numdoc__icontains=search) | \
                   Q(numcorrelativo__icontains=search)
        base_queryset = base_queryset.filter(q_search)

    # Ordenar descendente (últimas compras primero)
    compras_qs = base_queryset.order_by('-idcompra')

    # 6. Paginación
    paginator = Paginator(compras_qs, page_size)
    try:
        page_obj = paginator.get_page(page_num)
    except Exception:
        page_obj = paginator.get_page(1)

    # 7. Serializar Resultados
    import re
    datos_compras = []
    for compra in page_obj:
        pagos_list = []
        if compra.id_forma_pago and compra.id_forma_pago.id_forma_pago != 2: # No es crédito
            if compra.observaciones and '[FRACCIONADO:' in compra.observaciones:
                obs = compra.observaciones.replace('[FRACCIONADO:', '').replace(']', '').strip()
                partes = obs.split('|')
                for parte in partes:
                    parte = parte.strip()
                    if not parte: continue
                    m = re.match(r'^(.*?):\s*S/([\d.]+)(?:\s*\(Op:\s*(.*?)\))?$', parte)
                    if m:
                        pagos_list.append({
                            'nombre': m.group(1).strip(),
                            'monto': float(m.group(2)),
                            'operacion': m.group(3).strip() if m.group(3) else 'Sin detalle'
                        })
            else:
                monto = float(compra.total_compra) if compra.total_compra else 0.0
                operacion = 'Sin detalle'
                if compra.observaciones and '[Op:' in compra.observaciones:
                    m = re.search(r'\[Op:\s*(.*?)\]', compra.observaciones)
                    if m:
                        operacion = m.group(1).strip()
                pagos_list.append({
                    'nombre': compra.id_forma_pago.nombre if compra.id_forma_pago else '',
                    'monto': monto,
                    'operacion': operacion
                })

        datos_compras.append({
            'idcompra': compra.idcompra,
            'numcorrelativo': compra.numcorrelativo if compra.numcorrelativo else '',
            'proveedor_nombre': compra.idproveedor.razonsocial if compra.idproveedor else '',
            'fechacompra': compra.fechacompra.strftime("%d/%m/%Y") if compra.fechacompra else '',
            'forma_pago_id': compra.id_forma_pago_id if compra.id_forma_pago else None,
            'forma_pago_nombre': compra.id_forma_pago.nombre if compra.id_forma_pago else '',
            'total_compra': float(compra.total_compra) if compra.total_compra else 0.0,
            'estado': compra.estado,
            'pagos_list': pagos_list,
            'editable': True if compra.estado == 1 else False # Ajustar permisos si es necesario en js
        })

    return JsonResponse({
        'ok': True,
        'compras': datos_compras,
        'current_page': page_obj.number,
        'total_pages': paginator.num_pages,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous()
    })

# ==================== OBTENER DETALLE DE COMPRA (MODAL AJAX) ====================
def api_obtener_detalle_compra(request, id):
    """
    Obtiene los datos de una compra para mostrar detalles en el modal (AJAX).
    """
    if request.method != 'GET':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)

    try:
        compra = Compras.objects.get(idcompra=id)
        
        # Parsear pagos desde observaciones
        import re
        pagos_list = []
        if compra.id_forma_pago and compra.id_forma_pago.id_forma_pago != 2:
            if compra.observaciones and '[FRACCIONADO:' in compra.observaciones:
                obs = compra.observaciones.replace('[FRACCIONADO:', '').replace(']', '').strip()
                partes = obs.split('|')
                for parte in partes:
                    parte = parte.strip()
                    if not parte: continue
                    m = re.match(r'^(.*?):\s*S/([\d.]+)(?:\s*\(Op:\s*(.*?)\))?$', parte)
                    if m:
                        pagos_list.append({
                            'nombre': m.group(1).strip(),
                            'monto': float(m.group(2)),
                            'operacion': m.group(3).strip() if m.group(3) else 'Sin detalle'
                        })
            else:
                monto = float(compra.total_compra) if compra.total_compra else 0.0
                operacion = 'Sin detalle'
                if compra.observaciones and '[Op:' in compra.observaciones:
                    m = re.search(r'\[Op:\s*(.*?)\]', compra.observaciones)
                    if m:
                        operacion = m.group(1).strip()
                pagos_list.append({
                    'nombre': compra.id_forma_pago.nombre if compra.id_forma_pago else '',
                    'monto': monto,
                    'operacion': operacion
                })

        # Detalles
        detalles_qs = CompraDetalle.objects.filter(idcompra=compra).select_related(
            'id_vehiculo__idproducto',
            'id_vehiculo__idestadoproducto',
            'id_repuesto_comprado__id_repuesto',
        )

        detalles_list = []
        for d in detalles_qs:
            item = {
                'cantidad': d.cantidad,
                'moneda': d.moneda if d.moneda else 'PEN',
                'precio_dolares': float(d.precio_dolares) if d.precio_dolares else 0,
                'precio_compra': float(d.precio_compra) if d.precio_compra else 0,
                'precio_minimo': float(d.precio_minimo) if d.precio_minimo else 0,
                'precio_maximo': float(d.precio_maximo) if d.precio_maximo else 0,
                'subtotal': float(d.subtotal) if d.subtotal else 0,
            }
            if d.id_vehiculo:
                item['tipo'] = 'vehiculo'
                item['nombre'] = d.id_vehiculo.idproducto.nomproducto if d.id_vehiculo.idproducto else ''
                item['motor'] = d.id_vehiculo.serie_motor or '-'
                item['chasis'] = d.id_vehiculo.serie_chasis or '-'
                item['anio'] = d.id_vehiculo.anio or '-'
                item['placas'] = d.id_vehiculo.placas or ''
                item['estado'] = d.id_vehiculo.idestadoproducto.nombreestadoproducto if d.id_vehiculo.idestadoproducto else '-'
            elif d.id_repuesto_comprado:
                item['tipo'] = 'repuesto'
                item['nombre'] = d.id_repuesto_comprado.id_repuesto.nombre if d.id_repuesto_comprado.id_repuesto else ''
                item['codigo'] = d.id_repuesto_comprado.id_repuesto.codigo_barras or ''
                item['modelo'] = d.id_repuesto_comprado.id_repuesto.modelo_referencia or ''
                item['ubicacion'] = d.id_repuesto_comprado.ubicacion or ''
            
            detalles_list.append(item)

        # Cuotas (si es a crédito)
        cuotas_list = []
        if compra.id_forma_pago and compra.id_forma_pago.id_forma_pago == 2:
            cuotas_qs = compra.cuota.all().order_by('numero_cuota')
            for cuota in cuotas_qs:
                saldo = cuota.calcular_saldo()
                if saldo <= 0:
                    estado = 'PAGADO'
                elif cuota.monto_pagado > 0:
                    estado = 'PARCIAL'
                else:
                    estado = 'PENDIENTE'
                
                cuotas_list.append({
                    'numero_cuota': cuota.numero_cuota,
                    'fecha_vencimiento': cuota.fecha_vencimiento.strftime('%d/%m/%Y') if cuota.fecha_vencimiento else '',
                    'monto': float(cuota.monto) if cuota.monto else 0,
                    'interes': float(cuota.interes) if cuota.interes else 0,
                    'total': float(cuota.total) if cuota.total else 0,
                    'monto_pagado': float(cuota.monto_pagado) if cuota.monto_pagado else 0,
                    'saldo': float(saldo),
                    'estado': estado
                })

        compra_data = {
            'idcompra': compra.idcompra,
            'numcorrelativo': compra.numcorrelativo,
            'proveedor': compra.idproveedor.razonsocial if compra.idproveedor else '',
            'fechacompra': compra.fechacompra.strftime('%d/%m/%Y') if compra.fechacompra else '',
            'tipo_comprobante': compra.idtipocliente.nomtipocliente if compra.idtipocliente else '',
            'forma_pago': compra.id_forma_pago.nombre if compra.id_forma_pago else '',
            'forma_pago_id': compra.id_forma_pago_id,
            'tipo_pago': compra.id_tipo_pago.nombre if compra.id_tipo_pago else '',
            'sucursal': compra.id_sucursal.nombre_sucursal if compra.id_sucursal else '-',
            'total_compra': float(compra.total_compra) if compra.total_compra else 0,
            'estado': compra.estado,
            'tipo_cambio': float(compra.tipo_cambio) if compra.tipo_cambio else 1.0,
            'pagos_list': pagos_list,
            'cuotas_list': cuotas_list,
            'detalles': detalles_list
        }

        return JsonResponse({'ok': True, 'compra': compra_data})
    except Compras.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Compra no encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)