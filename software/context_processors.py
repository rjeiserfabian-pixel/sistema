from django.core.cache import cache
from django.http import JsonResponse
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos
from software.models.empresaModel import Empresa
from software.models.sucursalesModel import Sucursales
from software.models.cajaModel import Caja
from software.models.almacenesModel import Almacenes
from software.models.UsuarioModel import Usuario
from software.models.AperturaCierreCajaModel import AperturaCierreCaja


# Tiempo de vida de la caché para los context processors (en segundos)
_CTX_CACHE_TTL = 60


def modulos_sidebar(request):
    """
    Context processor para agregar módulos organizados a todas las plantillas.
    Resultado cacheado por tipo de usuario durante 60 segundos.
    """
    id_tipousuario = request.session.get('idtipousuario')

    if not id_tipousuario:
        return {'modulos_organizados': {}}

    cache_key = f'ctx_modulos_{id_tipousuario}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        # Obtener permisos del usuario
        permisos = Detalletipousuarioxmodulos.objects.filter(
            idtipousuario=id_tipousuario,
            idmodulo__estado=1
        ).select_related('idmodulo', 'idmodulo__idmodulo_padre')

        # Organizar módulos en estructura jerárquica
        modulos_organizados = {}

        # 🚀 INYECCIÓN MANUAL PARA LA OPCIÓN 2 (ACCESO A LOGÍSTICA)
        puede_gestionar_logistica = request.session.get('puede_gestionar_logistica', False)
        modulos_permitidos = list(permisos)

        if puede_gestionar_logistica:
            from software.models.ModulosModel import Modulos
            try:
                # Verificar si ya tiene el módulo de transferencias (ID 15)
                ya_tiene_transferencias = any(p.idmodulo.idmodulo == 15 for p in modulos_permitidos)
                if not ya_tiene_transferencias:
                    # Crear un objeto "permiso falso" para inyectarlo en la lista
                    class PermisoFalso:
                        pass
                    
                    modulo_transferencias = Modulos.objects.select_related('idmodulo_padre').get(idmodulo=15)
                    permiso_falso = PermisoFalso()
                    permiso_falso.idmodulo = modulo_transferencias
                    modulos_permitidos.append(permiso_falso)
                    
                    # También necesitamos asegurar que tenga el módulo padre (Almacén)
                    if modulo_transferencias.idmodulo_padre:
                        ya_tiene_padre = any(p.idmodulo.idmodulo == modulo_transferencias.idmodulo_padre.idmodulo for p in modulos_permitidos)
                        if not ya_tiene_padre:
                            permiso_falso_padre = PermisoFalso()
                            permiso_falso_padre.idmodulo = modulo_transferencias.idmodulo_padre
                            modulos_permitidos.append(permiso_falso_padre)
            except Exception as e:
                print(f"Error inyectando módulo de transferencias: {e}")

        for permiso in modulos_permitidos:
            modulo = permiso.idmodulo

            # Si el módulo tiene padre
            if modulo.idmodulo_padre:
                padre = modulo.idmodulo_padre
                padre_nombre = padre.nombremodulo

                if padre_nombre not in modulos_organizados:
                    modulos_organizados[padre_nombre] = {
                        'padre': padre,
                        'hijos': []
                    }
                modulos_organizados[padre_nombre]['hijos'].append(modulo)
            else:
                # Es módulo padre o independiente
                if modulo.nombremodulo not in modulos_organizados:
                    modulos_organizados[modulo.nombremodulo] = {
                        'padre': modulo,
                        'hijos': []
                    }

        # Ordenar hijos por orden
        for nombre, grupo in modulos_organizados.items():
            grupo['hijos'].sort(key=lambda x: x.orden if x.orden is not None else 0)

        # Ordenar el diccionario principal por el orden del padre
        modulos_organizados = dict(sorted(
            modulos_organizados.items(),
            key=lambda item: item[1]['padre'].orden if item[1]['padre'].orden is not None else 0
        ))

        result = {'modulos_organizados': modulos_organizados}
        cache.set(cache_key, result, timeout=_CTX_CACHE_TTL)
        return result

    except Exception as e:
        print(f"Error en context processor: {e}")
        return {'modulos_organizados': {}}


def empresa_context(request):
    """
    Agrega información de empresa, sucursal, caja, almacén y apertura actual.
    Resultado cacheado por usuario + combinación de sesión durante 60 segundos.
    La apertura de caja se consulta siempre (es estado operativo que cambia con frecuencia).
    """
    empresa = None
    sucursal = None
    caja = None
    almacen = None
    apertura_actual = None
    tiene_caja_abierta = False

    idusuario = request.session.get('idusuario')
    if not idusuario:
        return {
            'empresa': None,
            'sucursal': None,
            'caja': None,
            'almacen': None,
            'apertura_actual': None,
            'tiene_caja_abierta': False,
        }

    try:
        idempresa = request.session.get('idempresa')
        id_sucursal = request.session.get('id_sucursal')
        id_caja = request.session.get('id_caja')
        id_almacen = request.session.get('id_almacen')

        # ── Empresa, Sucursal, Caja y Almacén: datos estables → se cachean ──
        datos_cache_key = f'ctx_empresa_{idusuario}_{idempresa}_{id_sucursal}_{id_caja}_{id_almacen}'
        datos_cached = cache.get(datos_cache_key)

        if datos_cached is not None:
            empresa = datos_cached.get('empresa')
            sucursal = datos_cached.get('sucursal')
            caja = datos_cached.get('caja')
            almacen = datos_cached.get('almacen')
        else:
            if idempresa:
                empresa = Empresa.objects.get(idempresa=idempresa)
            if id_sucursal:
                sucursal = Sucursales.objects.get(id_sucursal=id_sucursal)
            if id_caja:
                caja = Caja.objects.get(id_caja=id_caja)
            if id_almacen:
                almacen = Almacenes.objects.get(id_almacen=id_almacen)

            cache.set(datos_cache_key, {
                'empresa': empresa,
                'sucursal': sucursal,
                'caja': caja,
                'almacen': almacen,
            }, timeout=_CTX_CACHE_TTL)

        # ── Apertura de caja: estado operativo → NO se cachea (cambia al abrir/cerrar) ──
        if id_caja:
            apertura_actual = AperturaCierreCaja.objects.filter(
                idusuario_id=idusuario,
                id_caja_id=id_caja,
                estado__in=['abierta', 'reabierta']
            ).select_related('id_caja').first()
        else:
            apertura_actual = None

        tiene_caja_abierta = apertura_actual is not None

    except Exception as e:
        print(f"❌ Error en context_processor: {e}")

    return {
        'empresa': empresa,
        'sucursal': sucursal,
        'caja': caja,
        'almacen': almacen,
        'apertura_actual': apertura_actual,
        'tiene_caja_abierta': tiene_caja_abierta,
    }


def cambiar_contexto(request):
    """
    Permite cambiar sucursal, caja y almacén (para todos los usuarios).
    Invalida la caché del empresa_context al cambiar de contexto.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    idusuario = request.session.get('idusuario')
    es_admin = request.session.get('es_admin', False)

    if not idusuario:
        return JsonResponse({'error': 'No autenticado'}, status=401)

    # Aceptar datos JSON o POST normales
    import json
    try:
        data = json.loads(request.body)
        id_sucursal = data.get('id_sucursal')
        id_caja = data.get('id_caja')
        id_almacen = data.get('id_almacen')
    except:
        id_sucursal = request.POST.get('id_sucursal')
        id_caja = request.POST.get('id_caja')
        id_almacen = request.POST.get('id_almacen')

    try:
        usuario = Usuario.objects.get(idusuario=idusuario)

        # Actualizar sucursal
        if id_sucursal:
            if es_admin:
                # Admin puede cambiar a cualquier sucursal de su empresa
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
                        'ok': False,
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
        else:
            request.session.pop('id_almacen', None)

        # ── Invalidar caché de empresa_context para este usuario ──
        # (el nuevo contexto se recalculará en el próximo request)
        idempresa = request.session.get('idempresa')
        # Limpiar todas las variantes posibles de clave para este usuario
        cache.delete_pattern(f'ctx_empresa_{idusuario}_*') if hasattr(cache, 'delete_pattern') else (
            cache.delete(
                f'ctx_empresa_{idusuario}_{idempresa}'
                f'_{request.session.get("id_sucursal")}'
                f'_{request.session.get("id_caja")}'
                f'_{request.session.get("id_almacen")}'
            )
        )

        return JsonResponse({
            'ok': True,
            'success': True,
            'mensaje': 'Configuración actualizada correctamente',
            'contexto': {
                'id_sucursal': request.session.get('id_sucursal'),
                'id_caja': request.session.get('id_caja'),
                'id_almacen': request.session.get('id_almacen')
            }
        })

    except (Sucursales.DoesNotExist, Caja.DoesNotExist, Almacenes.DoesNotExist):
        return JsonResponse({
            'ok': False,
            'error': 'Registro no encontrado'
        }, status=404)
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'ok': False,
            'error': 'Error al cambiar contexto'
        }, status=500)


def usuario_context(request):
    """
    Agrega el objeto usuario completo a todas las plantillas.
    Resultado cacheado por usuario durante 60 segundos.
    """
    idusuario = request.session.get('idusuario')
    if not idusuario:
        return {'user_obj': None}

    cache_key = f'ctx_usuario_{idusuario}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        usuario_obj = Usuario.objects.get(idusuario=idusuario)
        result = {'user_obj': usuario_obj}
        cache.set(cache_key, result, timeout=_CTX_CACHE_TTL)
        return result
    except Usuario.DoesNotExist:
        pass
    return {'user_obj': None}
