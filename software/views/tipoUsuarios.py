from django.http import JsonResponse
from django.shortcuts import render, HttpResponse
from software.models.TipousuarioModel import Tipousuario
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos


def _verificar_sesion(request):
    """Retorna el idtipousuario de sesión o None si no hay sesión activa."""
    return request.session.get('idtipousuario')


def tipoUsuarios(request):
    id2 = _verificar_sesion(request)
    if not id2:
        return HttpResponse("<h1>No tiene acceso. Por favor inicie sesión.</h1>")

    permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
    tipoUsuariosuarios = Tipousuario.objects.filter(estado=1)

    data = {
        "permisos": permisos,
        "tipoUsuariosuarios": tipoUsuariosuarios,
    }
    return render(request, 'tipousuarios/tipousuarios.html', data)


def tipousuariosAgregar(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)

    id2 = _verificar_sesion(request)
    if not id2:
        return JsonResponse({'ok': False, 'error': 'Sin sesión activa'}, status=401)

    nombre = request.POST.get('nombreTipo', '').strip()
    if not nombre:
        return JsonResponse({'ok': False, 'error': 'El nombre no puede estar vacío'}, status=400)

    try:
        Tipousuario.objects.create(nombretipousuario=nombre, estado=1)
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


def tipousuariosEditar(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)

    id2 = _verificar_sesion(request)
    if not id2:
        return JsonResponse({'ok': False, 'error': 'Sin sesión activa'}, status=401)

    id_tipo = request.POST.get('idtipousuario', '').strip()
    nombre = request.POST.get('nombreTipo', '').strip()

    if not id_tipo or not nombre:
        return JsonResponse({'ok': False, 'error': 'Datos incompletos'}, status=400)

    try:
        tipoUser = Tipousuario.objects.get(idtipousuario=id_tipo)
        tipoUser.nombretipousuario = nombre
        tipoUser.save()
        return JsonResponse({'ok': True})
    except Tipousuario.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Tipo de usuario no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


def tipousuariosEliminar(request, id):
    id2 = _verificar_sesion(request)
    if not id2:
        return JsonResponse({'ok': False, 'error': 'Sin sesión activa'}, status=401)

    try:
        actualizados = Tipousuario.objects.filter(idtipousuario=id).update(estado=0)
        if actualizados == 0:
            return JsonResponse({'ok': False, 'error': 'Registro no encontrado'}, status=404)
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

