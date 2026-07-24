# software/views.py
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from software.models.UsuarioModel import Usuario
from software.models.sucursalesModel import Sucursales
from software.models.cajaModel import Caja
from software.models.almacenesModel import Almacenes
from software.models.AperturaCierreCajaModel import AperturaCierreCaja


def index(request):
    return render(request, 'index.html')


def login(request):
    from software.utils.encryption_utils import EncryptionManager, PasswordManager
    
    email_raw = request.POST.get('email_1')
    email = email_raw.strip() if email_raw else None
    contrasena2 = request.POST.get('contrasena')
    
    if email and contrasena2:
        # Buscar usuario por correo cifrado
        usuarios_todos = Usuario.objects.select_related(
            'idempresa', 'id_sucursal', 'idtipousuario'
        ).filter(estado=1)  # Solo usuarios activos
        
        usuario_encontrado = None
        usuario_existe = False
        
        # Buscar y validar el usuario
        for usuario in usuarios_todos:
            try:
                # Intentar descifrar el correo (flujo normal del sistema)
                usuario_identificador = EncryptionManager.decrypt_data(usuario.correo)
                if usuario_identificador is None:
                    # Fallback: el correo está en texto plano (agregado manualmente a la BD)
                    usuario_identificador = usuario.correo
            except Exception as e:
                print(f"Error al descifrar datos: {e}")
                # Fallback: comparar directamente en texto plano
                usuario_identificador = usuario.correo

            if usuario_identificador == email:
                usuario_existe = True
                # Verificar contraseña: primero intentar hash de Django
                try:
                    password_ok = PasswordManager.verify_password(contrasena2, usuario.contrasena)
                except Exception:
                    password_ok = False
                
                # Fallback: comparar en texto plano (contraseña ingresada directamente en BD)
                if not password_ok:
                    password_ok = (contrasena2 == usuario.contrasena)
                
                if password_ok:
                    usuario_encontrado = usuario
                    break

        if usuario_encontrado:
            # ✅ Login exitoso - Sin 2FA
            es_admin = usuario_encontrado.idtipousuario.idtipousuario == 1
            
            # Guardar datos en sesión
            request.session['idtipousuario'] = usuario_encontrado.idtipousuario.idtipousuario
            request.session['nombrecompleto'] = usuario_encontrado.nombrecompleto
            request.session['idusuario'] = usuario_encontrado.idusuario
            request.session['es_admin'] = es_admin
            request.session['puede_gestionar_logistica'] = usuario_encontrado.puede_gestionar_logistica
            
            if usuario_encontrado.idempresa:
                request.session['idempresa'] = usuario_encontrado.idempresa.idempresa
            
            # Asignar sucursal del usuario
            if usuario_encontrado.id_sucursal:
                request.session['id_sucursal'] = usuario_encontrado.id_sucursal.id_sucursal
            elif es_admin:
                # Admin sin sucursal: usar la primera de su empresa
                primera_sucursal = Sucursales.objects.filter(
                    idempresa=usuario_encontrado.idempresa
                ).first()
                if primera_sucursal:
                    request.session['id_sucursal'] = primera_sucursal.id_sucursal
            
            # Verificar si tiene caja abierta de sesiones anteriores
            apertura_abierta = AperturaCierreCaja.objects.filter(
                idusuario=usuario_encontrado,
                estado__in=['abierta', 'reabierta']
            ).select_related('id_caja__id_sucursal', 'id_almacen').first()
            
            if apertura_abierta:
                # Restaurar contexto de caja abierta
                request.session['id_caja'] = apertura_abierta.id_caja.id_caja
                if apertura_abierta.id_caja.id_sucursal:
                    request.session['id_sucursal'] = apertura_abierta.id_caja.id_sucursal.id_sucursal
                # ✅ Restaurar almacén guardado en la apertura
                if apertura_abierta.id_almacen_id:
                    request.session['id_almacen'] = apertura_abierta.id_almacen_id
                    print(f"✅ Almacén restaurado: {apertura_abierta.id_almacen}")
                print(f"✅ Caja abierta restaurada: {apertura_abierta.id_caja.nombre_caja}")
            
            print(f"✅ Login exitoso: {usuario_encontrado.nombrecompleto} ({'Admin' if es_admin else 'Usuario'})")
            print(f"   Sucursal: {request.session.get('id_sucursal')}")
            print(f"   Caja: {request.session.get('id_caja', 'Sin caja')}")
            
            # Redirigir al dashboard o página principal
            return redirect('cpanel')  # Cambia esto por tu vista
        else:
            if usuario_existe:
                error = "La contraseña es incorrecta"
            else:
                error = "El usuario no existe"
            data = {"error": error}
            return render(request, 'index.html', data)
    else:
        return HttpResponse("<h1>No tiene acceso señor</h1>")


def logout(request):
    request.session.flush()
    return redirect('index')


def cambiar_contexto(request):
    """
    Permite cambiar sucursal, caja y almacén (para todos los usuarios)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    idusuario = request.session.get('idusuario')
    es_admin = request.session.get('es_admin', False)
    
    if not idusuario:
        return JsonResponse({'error': 'No autenticado'}, status=401)
    
    id_sucursal = request.POST.get('id_sucursal')
    id_caja = request.POST.get('id_caja')
    id_almacen = request.POST.get('id_almacen')
    
    try:
        usuario = Usuario.objects.get(idusuario=idusuario)
        
        # Actualizar sucursal
        if id_sucursal:
            puede_cambiar_sucursal = usuario.idtipousuario.idtipousuario in [1, 5, 6]
            if puede_cambiar_sucursal:
                # Admin, Gerente o Analista pueden cambiar a cualquier sucursal de su empresa
                sucursal = Sucursales.objects.get(
                    id_sucursal=id_sucursal,
                    idempresa=usuario.idempresa
                )
            else:
                # Usuario normal: verificar que sea su sucursal
                if usuario.id_sucursal and usuario.id_sucursal.id_sucursal == int(id_sucursal):
                    sucursal = usuario.id_sucursal
                else:
                    return JsonResponse({
                        'error': 'No tienes permiso para cambiar a esta sucursal'
                    }, status=403)
            
            request.session['id_sucursal'] = sucursal.id_sucursal
            print(f"✅ Sucursal cambiada a: {sucursal.nombre_sucursal}")
        
        # Actualizar caja (sin aperturar)
        if id_caja:
            caja = Caja.objects.get(id_caja=id_caja)
            request.session['id_caja'] = caja.id_caja
            print(f"✅ Caja seleccionada: {caja.nombre_caja}")
        else:
            request.session.pop('id_caja', None)
        
        # Actualizar almacén
        if id_almacen:
            almacen = Almacenes.objects.get(id_almacen=id_almacen)
            request.session['id_almacen'] = almacen.id_almacen
            print(f"✅ Almacén seleccionado: {almacen.nombre_almacen}")
            
            # ✅ Persistir almacén en la apertura activa para restaurarlo al re-iniciar sesión
            apertura_activa = AperturaCierreCaja.objects.filter(
                idusuario_id=idusuario,
                estado__in=['abierta', 'reabierta']
            ).first()
            if apertura_activa:
                apertura_activa.id_almacen = almacen
                apertura_activa.save(update_fields=['id_almacen'])
                print(f"✅ Almacén guardado en apertura: {almacen.nombre_almacen}")
        else:
            request.session.pop('id_almacen', None)
            # También limpiar de la apertura activa
            AperturaCierreCaja.objects.filter(
                idusuario_id=idusuario,
                estado__in=['abierta', 'reabierta']
            ).update(id_almacen=None)
        
        return JsonResponse({
            'success': True,
            'mensaje': 'Contexto actualizado correctamente'
        })
        
    except (Sucursales.DoesNotExist, Caja.DoesNotExist, Almacenes.DoesNotExist):
        return JsonResponse({
            'error': 'Registro no encontrado'
        }, status=404)
    except Exception as e:
        print(f"Error: {str(e)}")
        return JsonResponse({
            'error': 'Error al cambiar contexto'
        }, status=500)


def obtener_datos_apertura(request):
    """
    Devuelve las opciones disponibles según el tipo de usuario
    """
    idusuario = request.session.get('idusuario')
    idtipousuario = request.session.get('idtipousuario')
    
    if not idusuario:
        return JsonResponse({'error': 'No autenticado'}, status=401)
    
    usuario = Usuario.objects.get(idusuario=idusuario)
    es_admin = idtipousuario == 1
    puede_cambiar_sucursal = idtipousuario in [1, 5, 6]
    
    data = {
        'es_admin': es_admin,
        'sucursales': [],
        'cajas': [],
        'almacenes': []
    }
    
    if puede_cambiar_sucursal:
        # Puede ver todas las sucursales de su empresa
        sucursales = Sucursales.objects.filter(idempresa=usuario.idempresa)
        data['sucursales'] = [
            {'id': s.id_sucursal, 'nombre': s.nombre_sucursal} 
            for s in sucursales
        ]
    else:
        # Usuario normal: solo su sucursal
        if usuario.id_sucursal:
            data['sucursales'] = [{
                'id': usuario.id_sucursal.id_sucursal,
                'nombre': usuario.id_sucursal.nombre_sucursal
            }]
            
            # Cargar cajas y almacenes de su sucursal
            cajas = Caja.objects.filter(
                id_sucursal=usuario.id_sucursal,
                estado=1
            )
            
            # Filtrar cajas disponibles (sin apertura activa de otro usuario)
            cajas_disponibles = []
            for caja in cajas:
                apertura_activa = AperturaCierreCaja.objects.filter(
                    id_caja=caja,
                    estado__in=['abierta', 'reabierta']
                ).exclude(idusuario=usuario).exists()  # Excluir aperturas propias
                
                if not apertura_activa:
                    cajas_disponibles.append({
                        'id': caja.id_caja,
                        'nombre': caja.nombre_caja,
                        'numero': caja.numero_caja
                    })
            
            data['cajas'] = cajas_disponibles
            
            # Almacenes
            almacenes = Almacenes.objects.filter(
                id_sucursal=usuario.id_sucursal,
                estado=1
            )
            data['almacenes'] = [
                {'id': a.id_almacen, 'nombre': a.nombre_almacen}
                for a in almacenes
            ]
    
    # ✅ AGREGAR VALORES ACTUALES DE SESIÓN PARA PRE-SELECCIÓN
    data['id_sucursal_actual'] = request.session.get('id_sucursal')
    data['id_caja_actual'] = request.session.get('id_caja')
    data['id_almacen_actual'] = request.session.get('id_almacen')
    
    return JsonResponse(data)


def obtener_cajas_almacenes(request):
    """
    Obtiene cajas y almacenes de una sucursal específica
    """
    id_sucursal = request.GET.get('id_sucursal')
    idusuario = request.session.get('idusuario')
    
    print(f"🔍 DEBUG obtener_cajas_almacenes:")
    print(f"   id_sucursal recibido: {id_sucursal}")
    print(f"   idusuario: {idusuario}")
    
    if not id_sucursal:
        return JsonResponse({'error': 'Sucursal no especificada'}, status=400)
    
    try:
        # Obtener cajas activas de la sucursal
        cajas = Caja.objects.filter(
            id_sucursal_id=id_sucursal,
            estado=1
        )
        
        print(f"   Total cajas encontradas: {cajas.count()}")
        for caja in cajas:
            print(f"   - Caja: {caja.nombre_caja} (ID: {caja.id_caja})")
        
        # Filtrar cajas disponibles
        cajas_disponibles = []
        for caja in cajas:
            apertura_activa = AperturaCierreCaja.objects.filter(
                id_caja=caja,
                estado__in=['abierta', 'reabierta']
            ).exclude(idusuario_id=idusuario).exists()
            
            print(f"   - Caja {caja.nombre_caja}: apertura_activa={apertura_activa}")
            
            if not apertura_activa:
                cajas_disponibles.append({
                    'id': caja.id_caja,
                    'nombre': caja.nombre_caja,
                    'numero': caja.numero_caja
                })
        
        print(f"   Cajas disponibles: {len(cajas_disponibles)}")
        
        # Almacenes activos
        almacenes = Almacenes.objects.filter(
            id_sucursal_id=id_sucursal,
            estado=1
        )
        
        print(f"   Total almacenes encontrados: {almacenes.count()}")
        
        data = {
            'cajas': cajas_disponibles,
            'almacenes': [
                {'id': a.id_almacen, 'nombre': a.nombre_almacen}
                for a in almacenes
            ],
            'id_sucursal_actual': request.session.get('id_sucursal'),
            'id_caja_actual': request.session.get('id_caja'),
            'id_almacen_actual': request.session.get('id_almacen')
        }
        return JsonResponse(data)
        
        print(f"   ✅ Respuesta: {data}")
        
        return JsonResponse(data)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': 'Error al obtener datos'}, status=500)


def abrir_caja(request):
    """
    Apertura una caja (se llama cuando el usuario va a vender)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    # Aceptar datos JSON o POST normales
    import json
    try:
        data = json.loads(request.body)
        monto = data.get('monto')
        id_caja = data.get('id_caja')
        id_almacen = data.get('id_almacen')
        id_sucursal = data.get('id_sucursal')
    except:
        monto = request.POST.get('monto')
        id_caja = request.POST.get('id_caja')
        id_almacen = request.POST.get('id_almacen')
        id_sucursal = request.POST.get('id_sucursal')
    
    idusuario = request.session.get('idusuario')
    es_admin = request.session.get('es_admin', False)
    
    if not idusuario:
        return JsonResponse({'ok': False, 'error': 'No autenticado'}, status=401)
    
    if not id_caja or not monto:
        return JsonResponse({'ok': False, 'error': 'Datos incompletos'}, status=400)
    
    try:
        usuario = Usuario.objects.get(idusuario=idusuario)
        caja = Caja.objects.get(id_caja=id_caja)
        
        # Verificar que no tenga otra caja abierta
        apertura_propia = AperturaCierreCaja.objects.filter(
            idusuario=usuario,
            estado__in=['abierta', 'reabierta']
        ).first()
        
        if apertura_propia:
            return JsonResponse({
                'ok': False,
                'error': f'Ya tienes la caja "{apertura_propia.id_caja.nombre_caja}" abierta. Ciérrala primero.'
            }, status=400)
        
        # Verificar que la caja no esté abierta por otro usuario
        apertura_otra = AperturaCierreCaja.objects.filter(
            id_caja=caja,
            estado__in=['abierta', 'reabierta']
        ).first()
        
        if apertura_otra:
            return JsonResponse({
                'ok': False,
                'error': f'La caja está siendo usada por {apertura_otra.idusuario.nombrecompleto}'
            }, status=400)
        
        # Actualizar contexto si es admin y cambió sucursal
        if es_admin and id_sucursal:
            request.session['id_sucursal'] = int(id_sucursal)
        
        ahora = timezone.now()
        
        # Crear apertura
        apertura = AperturaCierreCaja.objects.create(
            id_caja=caja,
            idusuario=usuario,
            saldo_inicial=monto,
            fecha_apertura=ahora,
            hora_apertura=ahora.time(),
            estado='abierta'
        )
        
        # Guardar en sesión
        request.session['id_caja'] = caja.id_caja
        if id_almacen:
            request.session['id_almacen'] = int(id_almacen)
            # ✅ Persistir almacén en la apertura para restaurarlo al re-iniciar sesión
            try:
                from software.models.almacenesModel import Almacenes
                almacen_obj = Almacenes.objects.get(id_almacen=id_almacen)
                apertura.id_almacen = almacen_obj
                apertura.save(update_fields=['id_almacen'])
            except Almacenes.DoesNotExist:
                pass
        if caja.id_sucursal:
            request.session['id_sucursal'] = caja.id_sucursal.id_sucursal
        
        print(f"✅ Caja aperturada: {caja.nombre_caja}")
        print(f"   Usuario: {usuario.nombrecompleto}")
        print(f"   Saldo inicial: S/ {monto}")
        
        return JsonResponse({
            'ok': True,
            'success': True,
            'mensaje': f'Caja {caja.nombre_caja} aperturada correctamente',
            'id_movimiento': apertura.id_movimiento,
            'datos': {
                'caja': caja.nombre_caja,
                'saldo_inicial': float(monto),
                'fecha_apertura': ahora.strftime('%d/%m/%Y %H:%M')
            }
        })
        
    except Caja.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Caja no encontrada'}, status=404)
    except Usuario.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Usuario no encontrado'}, status=404)
    except Exception as e:
        print(f"❌ Error al aperturar caja: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'ok': False,
            'error': f'Error al aperturar caja: {str(e)}'
        }, status=500)


def cerrar_caja(request):
    """
    Cierra la caja actual del usuario
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    idusuario = request.session.get('idusuario')
    
    # Aceptar datos JSON o POST normales
    import json
    try:
        data = json.loads(request.body)
        saldo_final = data.get('saldo_final')
    except:
        saldo_final = request.POST.get('saldo_final')
    
    if not idusuario:
        return JsonResponse({'error': 'No autenticado'}, status=401)
    
    try:
        # Buscar apertura activa del usuario
        apertura_abierta = AperturaCierreCaja.objects.filter(
            idusuario_id=idusuario,
            estado__in=['abierta', 'reabierta']
        ).first()
        
        if not apertura_abierta:
            return JsonResponse({
                'ok': False,
                'error': 'No tienes una caja abierta'
            }, status=400)
        
        ahora = timezone.now()
        
        # Cerrar caja
        apertura_abierta.saldo_final = saldo_final if saldo_final else apertura_abierta.saldo_inicial
        apertura_abierta.fecha_cierre = ahora
        apertura_abierta.hora_cierre = ahora.time()
        apertura_abierta.estado = 'cerrada'
        apertura_abierta.save()
        
        # Limpiar sesión
        request.session.pop('id_caja', None)
        
        print(f"✅ Caja cerrada: {apertura_abierta.id_caja.nombre_caja}")
        print(f"   Saldo inicial: {apertura_abierta.saldo_inicial}")
        print(f"   Saldo final: {apertura_abierta.saldo_final}")
        
        return JsonResponse({
            'ok': True,
            'success': True,
            'mensaje': 'Caja cerrada correctamente',
            'datos': {
                'caja': apertura_abierta.id_caja.nombre_caja,
                'saldo_inicial': float(apertura_abierta.saldo_inicial),
                'saldo_final': float(apertura_abierta.saldo_final)
            }
        })
        
    except Exception as e:
        print(f"❌ Error al cerrar caja: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'ok': False,
            'error': f'Error al cerrar caja: {str(e)}'
        }, status=500)


def obtener_saldo_actual(request):
    """
    Devuelve el saldo actual de la caja abierta O reabierta del usuario
    """
    idusuario = request.session.get('idusuario')
    
    if not idusuario:
        return JsonResponse({'error': 'No autenticado'}, status=401)
    
    try:
        # Buscar apertura activa O reabierta
        apertura = AperturaCierreCaja.objects.filter(
            idusuario_id=idusuario,
            estado__in=['abierta', 'reabierta']
        ).first()
        
        if not apertura:
            return JsonResponse({
                'ok': False,
                'error': 'No hay caja abierta'
            }, status=400)
        
        from software.models.movimientoCajaModel import MovimientoCaja
        from django.db.models import Sum
        
        # Filtrar movimientos de esta apertura
        movimientos = MovimientoCaja.objects.filter(
            id_movimiento=apertura,
            estado=1
        )
        
        print("=" * 60)
        print("🔍 DEBUG SALDO ACTUAL")
        print(f"   Caja: {apertura.id_caja.nombre_caja}")
        print(f"   ID Apertura (id_movimiento): {apertura.id_movimiento}")
        print(f"   Estado: {apertura.estado}")
        print(f"   Saldo inicial: S/ {apertura.saldo_inicial}")
        print(f"   Total movimientos: {movimientos.count()}")
        
        # Calcular ingresos y egresos
        total_ingresos = movimientos.filter(
            tipo_movimiento='ingreso'
        ).aggregate(total=Sum('monto'))['total'] or 0
        
        total_egresos = movimientos.filter(
            tipo_movimiento='egreso'
        ).aggregate(total=Sum('monto'))['total'] or 0
        
        print(f"   Total ingresos: S/ {total_ingresos}")
        print(f"   Total egresos: S/ {total_egresos}")
        
        # Saldo actual = Saldo inicial + Ingresos - Egresos
        saldo_actual = float(apertura.saldo_inicial) + float(total_ingresos) - float(total_egresos)
        
        print(f"   ✅ SALDO ACTUAL: S/ {saldo_actual}")
        print("=" * 60)
        
        return JsonResponse({
            'ok': True,
            'saldo_actual': saldo_actual,
            'saldo_inicial': float(apertura.saldo_inicial),
            'total_ingresos': float(total_ingresos),
            'total_egresos': float(total_egresos),
            'caja': apertura.id_caja.nombre_caja,
            'fecha_apertura': apertura.fecha_apertura.strftime('%d/%m/%Y %H:%M'),
            'es_reabierta': apertura.estado == 'reabierta'
        })
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'ok': False,
            'error': 'Error al obtener saldo'
        }, status=500)