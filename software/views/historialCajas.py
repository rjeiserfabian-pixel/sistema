# software/views/historialCajas.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta, datetime, date
from decimal import Decimal
from django.core.mail import send_mail
from django.conf import settings
import random

from software.models.AperturaCierreCajaModel import AperturaCierreCaja
from software.models.ReaperturaCajaModel import ReaperturaCaja
from software.models.UsuarioModel import Usuario
from software.models.cajaModel import Caja
from software.models.twoFactorModel import TwoFactorCode
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos
from software.views.report_exports import export_to_pdf


def historial_cajas(request):
    """
    Vista principal del historial de cajas
    """
    idusuario = request.session.get('idusuario')
    id_tipo_usuario = request.session.get('idtipousuario')
    
    if not idusuario or not id_tipo_usuario:
        return redirect('login')
    
    # Verificar permisos
    permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id_tipo_usuario)
    es_admin = id_tipo_usuario == 1
    
    # Obtener filtros o establecer fechas por defecto
    hoy_date = datetime.now()
    fecha_desde = request.GET.get('fecha_desde', hoy_date.replace(day=1).strftime('%Y-%m-%d'))
    fecha_hasta = request.GET.get('fecha_hasta', hoy_date.strftime('%Y-%m-%d'))
    estado_filtro = request.GET.get('estado', 'todos')
    id_caja_filtro = request.GET.get('id_caja', '')
    
    # Lista vacía para la carga inicial (Server-Side Processing)
    aperturas = []
    
    # Obtener cajas para el selector de filtros
    cajas = Caja.objects.filter(estado=1)
    
    # Verificar si tiene caja abierta actualmente
    tiene_caja_abierta = AperturaCierreCaja.objects.filter(
        idusuario_id=idusuario,
        estado__in=['abierta', 'reabierta']
    ).exists()
    
    data = {
        'aperturas': aperturas,
        'cajas': cajas,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'estado_filtro': estado_filtro,
        'id_caja_filtro': id_caja_filtro,
        'tiene_caja_abierta': tiene_caja_abierta,
        'es_admin': es_admin,
        'permisos': permisos,
    }
    
    return render(request, 'historial_cajas/historial.html', data)

def api_listar_historial(request):
    """
    API para listado de historial de cajas con Paginación nativa
    """
    idusuario = request.session.get('idusuario')
    id_tipo_usuario = request.session.get('idtipousuario')
    
    if not idusuario or not id_tipo_usuario:
        return JsonResponse({'ok': False, 'error': 'No autorizado'}, status=401)
        
    es_admin = id_tipo_usuario == 1
    
    # Parámetros de paginación y filtros
    page_number = request.GET.get('page', 1)
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')
    estado_filtro = request.GET.get('estado', 'todos')
    id_caja_filtro = request.GET.get('id_caja', '')
    busqueda_usuario = request.GET.get('busqueda_usuario', '').strip()
    
    # Query base
    if es_admin:
        aperturas = AperturaCierreCaja.objects.all()
    else:
        aperturas = AperturaCierreCaja.objects.filter(idusuario_id=idusuario)
        
    aperturas = aperturas.select_related('id_caja', 'idusuario').order_by('-fecha_apertura', '-hora_apertura')
    
    # Aplicar filtros
    if fecha_desde:
        aperturas = aperturas.filter(fecha_apertura__gte=fecha_desde)
        
    if fecha_hasta:
        try:
            fecha_hasta_dt = datetime.strptime(fecha_hasta, '%Y-%m-%d')
            fecha_hasta_dt = fecha_hasta_dt.replace(hour=23, minute=59, second=59)
            aperturas = aperturas.filter(fecha_apertura__lte=fecha_hasta_dt)
        except:
            pass
            
    if estado_filtro != 'todos':
        aperturas = aperturas.filter(estado=estado_filtro)
        
    if id_caja_filtro:
        aperturas = aperturas.filter(id_caja_id=id_caja_filtro)
        
    # Búsqueda por Usuario/Vendedor
    if busqueda_usuario:
        aperturas = aperturas.filter(
            Q(idusuario__nombrecompleto__icontains=busqueda_usuario) |
            Q(idusuario__correo__icontains=busqueda_usuario) |
            Q(idusuario__dni__icontains=busqueda_usuario)
        )
        
    total_registros = aperturas.count()
    
    # Paginación
    from django.core.paginator import Paginator
    paginator = Paginator(aperturas, 10)  # 10 por página
    page_obj = paginator.get_page(page_number)
    
    # Lógica de reabrir caja
    tiene_caja_abierta = AperturaCierreCaja.objects.filter(
        idusuario_id=idusuario,
        estado__in=['abierta', 'reabierta']
    ).exists()
    
    from django.conf import settings
    if settings.USE_TZ:
        hoy = timezone.now()
    else:
        hoy = datetime.now()
        
    hace_7_dias = hoy - timedelta(days=7)
    
    data = []
    for a in page_obj:
        fecha_ap_dt = a.fecha_apertura
        puede_reabrirse = False
        
        if fecha_ap_dt:
            if isinstance(fecha_ap_dt, date) and not isinstance(fecha_ap_dt, datetime):
                fecha_ap_dt = datetime.combine(fecha_ap_dt, datetime.min.time())
                
            if settings.USE_TZ and isinstance(fecha_ap_dt, datetime):
                if timezone.is_naive(fecha_ap_dt):
                    fecha_ap_dt = timezone.make_aware(fecha_ap_dt)
                    
            try:
                puede_reabrirse = (
                    a.estado == 'cerrada' and
                    fecha_ap_dt >= hace_7_dias and
                    not tiene_caja_abierta
                )
            except:
                pass
                
        fue_reabierta = ReaperturaCaja.objects.filter(id_movimiento=a).exists()
        
        data.append({
            'id_movimiento': a.id_movimiento,
            'caja': f"{a.id_caja.nombre_caja} (Nro: {a.id_caja.numero_caja})" if a.id_caja else 'N/A',
            'usuario': a.idusuario.nombrecompleto if a.idusuario else 'N/A',
            'fecha_apertura': a.fecha_apertura.strftime('%d/%m/%Y') if a.fecha_apertura else '---',
            'hora_apertura': a.hora_apertura.strftime('%H:%M') if a.hora_apertura else '',
            'fecha_cierre': a.fecha_cierre.strftime('%d/%m/%Y') if a.fecha_cierre else '---',
            'hora_cierre': a.hora_cierre.strftime('%H:%M') if a.hora_cierre else '',
            'saldo_inicial': float(a.saldo_inicial) if a.saldo_inicial is not None else 0.0,
            'saldo_final': float(a.saldo_final) if a.saldo_final is not None else None,
            'estado': a.estado,
            'puede_reabrirse': puede_reabrirse,
            'fue_reabierta': fue_reabierta,
        })
        
    return JsonResponse({
        'ok': True,
        'aperturas': data,
        'stats': {
            'total_registros': total_registros
        },
        'pagination': {
            'has_previous': page_obj.has_previous(),
            'has_next': page_obj.has_next(),
            'current_page': page_obj.number,
            'num_pages': paginator.num_pages,
            'previous_page_number': page_obj.previous_page_number() if page_obj.has_previous() else None,
            'next_page_number': page_obj.next_page_number() if page_obj.has_next() else None,
            'start_index': page_obj.start_index() if total_registros > 0 else 0,
            'end_index': page_obj.end_index() if total_registros > 0 else 0
        }
    })

def solicitar_reapertura(request, id_movimiento):
    """
    Solicita la reapertura de una caja cerrada
    Envía código 2FA al dueño del negocio
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        from django.conf import settings
        
        idusuario = request.session.get('idusuario')
        
        if not idusuario:
            return JsonResponse({
                'ok': False,
                'error': 'No autenticado'
            }, status=401)
        
        apertura = get_object_or_404(AperturaCierreCaja, id_movimiento=id_movimiento)
        
        if apertura.estado != 'cerrada':
            return JsonResponse({
                'ok': False,
                'error': 'Solo se pueden reabrir cajas cerradas'
            }, status=400)
        
        # ✅ Usar datetime.now() o timezone.now() según configuración
        if settings.USE_TZ:
            hoy = timezone.now()
        else:
            hoy = datetime.now()
        
        hace_7_dias = hoy - timedelta(days=7)
        
        fecha_apertura = apertura.fecha_apertura
        
        if fecha_apertura:
            if isinstance(fecha_apertura, date) and not isinstance(fecha_apertura, datetime):
                fecha_apertura = datetime.combine(fecha_apertura, datetime.min.time())
            
            if settings.USE_TZ and isinstance(fecha_apertura, datetime):
                if timezone.is_naive(fecha_apertura):
                    fecha_apertura = timezone.make_aware(fecha_apertura)
            
            try:
                if fecha_apertura < hace_7_dias:
                    return JsonResponse({
                        'ok': False,
                        'error': 'Solo se pueden reabrir cajas de los últimos 7 días'
                    }, status=400)
            except:
                pass
        else:
            return JsonResponse({
                'ok': False,
                'error': 'La apertura no tiene fecha válida'
            }, status=400)
        
        # Verificar que el usuario NO tenga otra caja abierta
        tiene_caja_abierta = AperturaCierreCaja.objects.filter(
            idusuario_id=idusuario,
            estado__in=['abierta', 'reabierta']
        ).exists()
        
        if tiene_caja_abierta:
            return JsonResponse({
                'ok': False,
                'error': 'Debe cerrar su caja actual antes de reabrir una anterior'
            }, status=400)
        
        # Resto del código igual...
        motivo = request.POST.get('motivo', '').strip()
        
        if not motivo or len(motivo) < 10:
            return JsonResponse({
                'ok': False,
                'error': 'Debe proporcionar un motivo válido (mínimo 10 caracteres)'
            }, status=400)
        
        try:
            dueno = Usuario.objects.get(es_dueno=True, estado=1)
        except Usuario.DoesNotExist:
            return JsonResponse({
                'ok': False,
                'error': 'No se ha configurado el dueño del negocio. Contacte al administrador.'
            }, status=400)
        except Usuario.MultipleObjectsReturned:
            dueno = Usuario.objects.filter(es_dueno=True, estado=1).first()
        
        codigo = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        request.session['reapertura_codigo'] = codigo
        request.session['reapertura_id_movimiento'] = id_movimiento
        request.session['reapertura_motivo'] = motivo
        request.session['reapertura_usuario_solicitante'] = idusuario
        
        from software.utils.encryption_utils import EncryptionManager
        try:
            correo_dueno = EncryptionManager.decrypt_email(dueno.correo)
        except:
            correo_dueno = dueno.correo
        
        usuario_solicitante = Usuario.objects.get(idusuario=idusuario)
        
        asunto = '🔐 Código de Verificación - Reapertura de Caja'
        mensaje = f"""
Hola {dueno.nombrecompleto},

{usuario_solicitante.nombrecompleto} ha solicitado reabrir una caja cerrada.

DETALLES:
- Caja: {apertura.id_caja.nombre_caja if apertura.id_caja else 'N/A'}
- Fecha apertura original: {apertura.fecha_apertura.strftime('%d/%m/%Y %H:%M') if apertura.fecha_apertura else 'N/A'}
- Fecha cierre: {apertura.fecha_cierre.strftime('%d/%m/%Y %H:%M') if apertura.fecha_cierre else 'N/A'}
- Motivo: {motivo}

Tu código de verificación es:

{codigo}

Este código expirará en 10 minutos.

Si no autorizas esta acción, ignora este mensaje.

Saludos,
Sistema de Gestión
        """
        
        send_mail(
            asunto,
            mensaje,
            settings.DEFAULT_FROM_EMAIL,
            [correo_dueno],
            fail_silently=False,
        )
        
        print(f"✅ Código 2FA enviado al dueño: {codigo}")
        
        correo_oculto = correo_dueno[:3] + '***@' + correo_dueno.split('@')[1] if '@' in correo_dueno else '***'
        
        return JsonResponse({
            'ok': True,
            'message': f'Código de verificación enviado al correo del dueño',
            'correo_dueno': correo_oculto
        })
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'ok': False,
            'error': f'Error al solicitar reapertura: {str(e)}'
        }, status=500)


def verificar_codigo_reapertura(request):
    """
    Verifica el código 2FA y reabre la caja
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        codigo_ingresado = request.POST.get('codigo', '').strip()
        
        if not codigo_ingresado:
            return JsonResponse({
                'ok': False,
                'error': 'Por favor ingrese el código'
            }, status=400)
        
        # Obtener datos de sesión
        codigo_correcto = request.session.get('reapertura_codigo')
        id_movimiento = request.session.get('reapertura_id_movimiento')
        motivo = request.session.get('reapertura_motivo')
        usuario_solicitante_id = request.session.get('reapertura_usuario_solicitante')
        
        if not codigo_correcto or not id_movimiento:
            return JsonResponse({
                'ok': False,
                'error': 'Sesión expirada. Solicite un nuevo código.'
            }, status=400)
        
        # Verificar código
        if codigo_ingresado != codigo_correcto:
            return JsonResponse({
                'ok': False,
                'error': 'Código incorrecto'
            }, status=400)
        
        # ✅ Código correcto - REABRIR CAJA
        apertura = get_object_or_404(AperturaCierreCaja, id_movimiento=id_movimiento)
        
        # Cambiar estado a "reabierta"
        apertura.estado = 'reabierta'
        apertura.save()
        
        # Registrar en auditoría
        reapertura = ReaperturaCaja.objects.create(
            id_movimiento=apertura,
            usuario_solicitante_id=usuario_solicitante_id,
            motivo=motivo,
            codigo_2fa_enviado=codigo_correcto,
            estado='reabierta'
        )
        
        # Actualizar sesión del usuario
        request.session['id_caja'] = apertura.id_caja.id_caja
        
        # Limpiar datos temporales
        request.session.pop('reapertura_codigo', None)
        request.session.pop('reapertura_id_movimiento', None)
        request.session.pop('reapertura_motivo', None)
        request.session.pop('reapertura_usuario_solicitante', None)
        
        print(f"✅ CAJA REABIERTA")
        print(f"   ID Movimiento: {apertura.id_movimiento}")
        print(f"   Caja: {apertura.id_caja.nombre_caja}")
        print(f"   Usuario: {apertura.idusuario.nombrecompleto}")
        print(f"   Motivo: {motivo}")
        
        return JsonResponse({
            'ok': True,
            'success': True,
            'message': 'Caja reabierta correctamente. Puede realizar los movimientos necesarios.',
            'id_reapertura': reapertura.id_reapertura
        })
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'ok': False,
            'error': f'Error al verificar código: {str(e)}'
        }, status=500)


def cerrar_caja_reabierta(request, id_movimiento):
    """
    Cierra una caja que fue reabierta
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        idusuario = request.session.get('idusuario')
        
        apertura = get_object_or_404(AperturaCierreCaja, id_movimiento=id_movimiento)
        
        # Validar que esté reabierta
        if apertura.estado != 'reabierta':
            return JsonResponse({
                'ok': False,
                'error': 'La caja no está reabierta'
            }, status=400)
        
        # Obtener saldo final (desde el POST o calcularlo)
        saldo_final = request.POST.get('saldo_final')
        
        if saldo_final:
            apertura.saldo_final = Decimal(saldo_final)
        
        # Cambiar estado a cerrada nuevamente
        ahora = timezone.now()
        apertura.estado = 'cerrada'
        apertura.fecha_cierre = ahora
        apertura.hora_cierre = ahora.time()
        apertura.save()
        
        # Actualizar auditoría
        reapertura = ReaperturaCaja.objects.filter(
            id_movimiento=apertura,
            estado='reabierta'
        ).order_by('-fecha_reapertura').first()
        
        if reapertura:
            reapertura.estado = 'cerrada_nuevamente'
            reapertura.fecha_cierre_reapertura = ahora
            reapertura.save()
        
        # Limpiar sesión
        request.session.pop('id_caja', None)
        
        print(f"✅ CAJA REABIERTA CERRADA NUEVAMENTE")
        print(f"   ID Movimiento: {apertura.id_movimiento}")
        
        return JsonResponse({
            'ok': True,
            'success': True,
            'message': 'Caja cerrada correctamente'
        })
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'ok': False,
            'error': f'Error al cerrar caja: {str(e)}'
        }, status=500)


def obtener_movimientos_caja(request, id_movimiento):
    """
    Retorna los movimientos asociados a una apertura específica en formato JSON,
    enriquecidos con datos detallados de pago del sistema.
    """
    idusuario = request.session.get('idusuario')
    id_tipo_usuario = request.session.get('idtipousuario')
    
    if not idusuario or not id_tipo_usuario:
        return JsonResponse({'ok': False, 'error': 'Sesión no iniciada'}, status=401)
        
    es_admin = id_tipo_usuario == 1
    
    # Obtener la apertura
    apertura = get_object_or_404(AperturaCierreCaja, id_movimiento=id_movimiento)
    
    # Validar permisos
    if not es_admin and apertura.idusuario_id != idusuario:
        return JsonResponse({'ok': False, 'error': 'No tiene permisos para ver los movimientos de esta apertura'}, status=403)
        
    from django.db.models import Sum
    from software.models.movimientoCajaModel import MovimientoCaja
    
    # Obtener movimientos activos con relaciones optimizadas
    movimientos = MovimientoCaja.objects.filter(
        id_movimiento=apertura,
        estado=1
    ).select_related(
        'idusuario',
        'idventa__idcliente',
        'idventa__id_forma_pago',
        'idventa__id_tipo_pago',
        'idcompra__idproveedor',
        'idcompra__id_forma_pago',
        'idcompra__id_tipo_pago'
    ).prefetch_related(
        'pagos_cuota__id_tipo_pago',
        'pagos_cuota__idcuotaventa__idcredito__idventa__idcliente'
    ).order_by('-fecha_movimiento')
    
    # Calcular totales usando monto_base_soles (equivalente en soles) cuando disponible
    total_ingresos = Decimal('0.00')
    total_ingresos += movimientos.filter(tipo_movimiento='ingreso', monto_base_soles__isnull=False).aggregate(total=Sum('monto_base_soles'))['total'] or Decimal('0.00')
    total_ingresos += movimientos.filter(tipo_movimiento='ingreso', monto_base_soles__isnull=True).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

    total_egresos = Decimal('0.00')
    total_egresos += movimientos.filter(tipo_movimiento='egreso', monto_base_soles__isnull=False).aggregate(total=Sum('monto_base_soles'))['total'] or Decimal('0.00')
    total_egresos += movimientos.filter(tipo_movimiento='egreso', monto_base_soles__isnull=True).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

    saldo_calculado = (apertura.saldo_inicial or Decimal('0.00')) + total_ingresos - total_egresos
    
    import re
    # PRE-FETCH MANUAL para evitar N+1 en Pre-Créditos
    pre_credito_ids = []
    for m in movimientos:
        if 'Pre-Crédito' in (m.descripcion or ''):
            m_pre = re.search(r'Pre-Crédito\s*#(\d+)', m.descripcion)
            if m_pre:
                pre_credito_ids.append(m_pre.group(1))
    
    detalles_por_precredito = {}
    if pre_credito_ids:
        try:
            from software.models.DetallePagoInicialModel import DetallePagoInicial
            dps = DetallePagoInicial.objects.filter(id_pre_credito_id__in=pre_credito_ids).select_related('id_tipo_pago')
            for p in dps:
                pid = str(p.id_pre_credito_id)
                if pid not in detalles_por_precredito:
                    detalles_por_precredito[pid] = []
                detalles_por_precredito[pid].append(p)
        except Exception:
            pass

    # Construir listado enriquecido
    movimientos_list = []
    for mov in movimientos:
        tercero = "N/A"
        forma_pago = "Contado"
        metodo_pago = "Efectivo"
        nro_operacion = "---"
        comprobante = None
        
        detalles_metodo = ""
        
        # 1. Evaluar si es Pago de Cuota de Crédito
        pagos_cuota_list = [p for p in mov.pagos_cuota.all() if p.estado == 1]
        
        if len(pagos_cuota_list) > 1:
            forma_pago = "Crédito"
            nro_operacion = "Múltiple"
            
            frac_detail = ""
            for p in pagos_cuota_list:
                if p.observaciones and '[FRACCIONADO:' in p.observaciones:
                    m_frac = re.search(r'\[FRACCIONADO:\s*(.*?)\]', p.observaciones)
                    if m_frac:
                        frac_detail = m_frac.group(1)
                        break
            if frac_detail:
                metodo_pago = "Múltiple"
                detalles_metodo = frac_detail
            else:
                # Check if all payments have the exact same method
                metodos_unicos = set(p.id_tipo_pago.nombre if p.id_tipo_pago else 'Efectivo' for p in pagos_cuota_list)
                if len(metodos_unicos) == 1:
                    metodo_pago = metodos_unicos.pop()
                    detalles_metodo = ""
                    ops = set(p.numero_operacion for p in pagos_cuota_list if p.numero_operacion and p.numero_operacion.lower() != 'múltiple')
                    if ops:
                        nro_operacion = " / ".join(ops)
                    else:
                        nro_operacion = "---"
                else:
                    metodo_pago = "Múltiple"
                    arr = []
                    for p in pagos_cuota_list:
                        n = p.id_tipo_pago.nombre if p.id_tipo_pago else 'Efectivo'
                        op = f' (Op:{p.numero_operacion})' if p.numero_operacion and p.numero_operacion.lower() != 'múltiple' else ''
                        arr.append(f"{n}: S/ {p.monto_pago}{op}")
                    detalles_metodo = " | ".join(arr)
                
            # Trazar cliente del crédito (usar el primero)
            try:
                cuota = pagos_cuota_list[0].idcuotaventa
                if cuota.idcredito and cuota.idcredito.idventa and cuota.idcredito.idventa.idcliente:
                    tercero = cuota.idcredito.idventa.idcliente.razonsocial
                elif cuota.idventa and cuota.idventa.idcliente:
                    tercero = cuota.idventa.idcliente.razonsocial
            except Exception:
                pass

        elif len(pagos_cuota_list) == 1:
            pago_cuota = pagos_cuota_list[0]
            forma_pago = "Crédito"
            if pago_cuota.id_tipo_pago:
                metodo_pago = pago_cuota.id_tipo_pago.nombre
                if pago_cuota.observaciones and '[FRACCIONADO:' in pago_cuota.observaciones:
                    m_frac = re.search(r'\[FRACCIONADO:\s*(.*?)\]', pago_cuota.observaciones)
                    if m_frac:
                        detalles_metodo = m_frac.group(1)
            nro_operacion = pago_cuota.numero_operacion or "---"
            
            # Trazar cliente del crédito
            try:
                cuota = pago_cuota.idcuotaventa
                if cuota.idcredito and cuota.idcredito.idventa and cuota.idcredito.idventa.idcliente:
                    tercero = cuota.idcredito.idventa.idcliente.razonsocial
                elif cuota.idventa and cuota.idventa.idcliente:
                    tercero = cuota.idventa.idcliente.razonsocial
            except Exception:
                pass
                
        # 2. Evaluar si proviene de una Venta Directa
        elif mov.idventa:
            if mov.idventa.idcliente:
                tercero = mov.idventa.idcliente.razonsocial
            if mov.idventa.id_forma_pago:
                forma_pago = mov.idventa.id_forma_pago.nombre
            if mov.idventa.id_tipo_pago:
                metodo_pago = mov.idventa.id_tipo_pago.nombre
                if mov.idventa.observaciones and '[FRACCIONADO:' in mov.idventa.observaciones:
                    m_frac = re.search(r'\[FRACCIONADO:\s*(.*?)\]', mov.idventa.observaciones)
                    if m_frac:
                        detalles_metodo = m_frac.group(1)
            comprobante = {
                'numero': mov.idventa.numero_comprobante,
                'url': f"/ventas/imprimir/{mov.idventa.idventa}/"
            }
            
        # 3. Evaluar si proviene de una Compra
        elif mov.idcompra:
            if mov.idcompra.idproveedor:
                tercero = mov.idcompra.idproveedor.razonsocial
            if mov.idcompra.id_forma_pago:
                forma_pago = mov.idcompra.id_forma_pago.nombre
            if mov.idcompra.id_tipo_pago:
                metodo_pago = mov.idcompra.id_tipo_pago.nombre
                if mov.idcompra.observaciones and '[FRACCIONADO:' in mov.idcompra.observaciones:
                    m_frac = re.search(r'\[FRACCIONADO:\s*(.*?)\]', mov.idcompra.observaciones)
                    if m_frac:
                        detalles_metodo = m_frac.group(1)
            # Mostrar info de moneda USD si aplica
            if mov.moneda == 'USD' and mov.tipo_cambio_aplicado:
                detalles_metodo = (detalles_metodo + " " if detalles_metodo else "") + f"[USD {mov.monto} a TC {mov.tipo_cambio_aplicado}]"
        
        # 4. Evaluar si es un Cobro Inicial Pre-Crédito
        elif 'Pre-Crédito' in (mov.descripcion or ''):
            m_pre = re.search(r'Pre-Crédito\s*#(\d+)', mov.descripcion)
            if m_pre:
                pid = m_pre.group(1)
                dp_list = detalles_por_precredito.get(pid, [])
                if len(dp_list) > 1:
                    metodo_pago = "Múltiple"
                    arr = []
                    for p in dp_list:
                        n = p.id_tipo_pago.nombre if p.id_tipo_pago else 'Efectivo'
                        op = f' (Op:{p.numero_operacion})' if p.numero_operacion else ''
                        arr.append(f"{n}: S/ {p.monto}{op}")
                    detalles_metodo = " | ".join(arr)
                elif len(dp_list) == 1:
                    metodo_pago = dp_list[0].id_tipo_pago.nombre if dp_list[0].id_tipo_pago else 'Efectivo'
                
        movimientos_list.append({
            'id': mov.id_movimiento_caja,
            'fecha': mov.fecha_movimiento.strftime('%d/%m/%Y %H:%M'),
            'tipo': mov.tipo_movimiento,
            'tercero': tercero,
            'forma_pago': forma_pago,
            'metodo_pago': metodo_pago,
            'detalles_metodo': detalles_metodo,
            'nro_operacion': nro_operacion,
            'descripcion': mov.descripcion or 'Sin descripción',
            'monto': float(mov.monto_base_soles if mov.monto_base_soles is not None else mov.monto),
            'monto_original': float(mov.monto),
            'moneda': mov.moneda or 'PEN',
            'tipo_cambio': float(mov.tipo_cambio_aplicado or 1),
            'usuario': mov.idusuario.nombrecompleto if mov.idusuario else 'N/A',
            'comprobante': comprobante
        })
        
    # Combinar fecha y hora para la información de la caja
    f_ap = apertura.fecha_apertura.strftime('%d/%m/%Y') if apertura.fecha_apertura else '---'
    h_ap = apertura.hora_apertura.strftime('%H:%M') if apertura.hora_apertura else ''
    f_ap_full = f"{f_ap} {h_ap}".strip() if f_ap != '---' else '---'
    
    f_ci = apertura.fecha_cierre.strftime('%d/%m/%Y') if apertura.fecha_cierre else '---'
    h_ci = apertura.hora_cierre.strftime('%H:%M') if apertura.hora_cierre else ''
    f_ci_full = f"{f_ci} {h_ci}".strip() if f_ci != '---' else '---'

    return JsonResponse({
        'ok': True,
        'info': {
            'caja': apertura.id_caja.nombre_caja if apertura.id_caja else 'N/A',
            'usuario': apertura.idusuario.nombrecompleto if apertura.idusuario else 'N/A',
            'estado': apertura.estado,
            'fecha_apertura': f_ap_full,
            'fecha_cierre': f_ci_full,
            'saldo_inicial': float(apertura.saldo_inicial or 0),
            'saldo_final': float(apertura.saldo_final or 0) if apertura.fecha_cierre else float(saldo_calculado),
        },
        'totales': {
            'ingresos': float(total_ingresos),
            'egresos': float(total_egresos),
            'saldo_neto': float(total_ingresos - total_egresos),
        },
        'movimientos': movimientos_list
    })

def exportar_caja_pdf(request, id_movimiento):
    """
    Exporta a PDF los movimientos de una caja específica
    """
    import json
    from django.http import HttpResponse
    
    # 1. Obtener datos usando la función existente
    response = obtener_movimientos_caja(request, id_movimiento)
    if response.status_code != 200:
        return HttpResponse('No autorizado', status=401)
        
    data = json.loads(response.content)
    if not data.get('ok'):
        return HttpResponse(data.get('error', 'Error desconocido'), status=400)
        
    info = data.get('info', {})
    
    # 2. Validar que esté cerrada
    if info.get('estado') != 'cerrada':
        return HttpResponse('Solo se puede exportar el historial de cajas cerradas.', status=400)
        
    # 3. Preparar datos para el PDF
    headers = ["Fecha y Hora", "Tipo", "Tercero", "Método", "Nro Op.", "Descripción", "Monto"]
    rows = []
    
    for mov in data.get('movimientos', []):
        metodo = mov['metodo_pago']
        if metodo == 'Múltiple' and mov.get('detalles_metodo'):
            # El PDF export maneja saltos de línea en celdas usando ReportLab Paragraphs si está configurado,
            # pero por si acaso, lo ponemos en una línea o con comas
            metodo = f"Múltiple: {mov['detalles_metodo']}"
            
        monto_val = float(mov['monto'])
        monto_str = f"+ S/ {monto_val:.2f}" if mov['tipo'] == 'ingreso' else f"- S/ {monto_val:.2f}"
            
        rows.append([
            mov['fecha'],
            mov['tipo'].capitalize(),
            mov['tercero'],
            metodo,
            mov['nro_operacion'],
            mov['descripcion'],
            monto_str
        ])
        
    total_monto = sum(float(mov['monto']) if str(mov['tipo']).lower() == 'ingreso' else -float(mov['monto']) for mov in data.get('movimientos', []))
    rows.append(["", "", "", "", "", '<b><font size="10">TOTAL RECAUDADO:</font></b>', f'<b><font size="10">S/ {total_monto:.2f}</font></b>'])
        
    # 4. Generar título y exportar
    caja_nombre = info.get('caja', '')
    usuario = info.get('usuario', '')
    fecha_apertura = info.get('fecha_apertura', '')
    fecha_cierre = info.get('fecha_cierre', '')
    
    title = f"Movimientos de Caja #{id_movimiento} - {caja_nombre}\nUsuario: {usuario} | Apertura: {fecha_apertura} | Cierre: {fecha_cierre}"
    
    return export_to_pdf(headers, rows, title, f'Historial_Caja_{id_movimiento}')