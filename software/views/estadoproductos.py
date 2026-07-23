from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from software.models.estadoproductoModel import EstadoProducto
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos


def estadoproductos(request):
    id2 = request.session.get('idtipousuario')
    if not id2:
        return HttpResponse("<h1>No tiene acceso. Por favor inicie sesión.</h1>")

    permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
    estadoproductos_registros = EstadoProducto.objects.filter(estado=1)

    data = {
        'estadoproductos_registros': estadoproductos_registros,
        'permisos': permisos
    }
    return render(request, 'estadoproductos/estadoproductos.html', data)


def eliminar(request, id):
    EstadoProducto.objects.filter(idestadoproducto=id).update(estado=0)
    return redirect('estadoproductos')


def agregar(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)

    nombre = request.POST.get('nameEstadoProductoAgregar', '').strip()
    if not nombre:
        return JsonResponse({'ok': False, 'error': 'El nombre no puede estar vacío'}, status=400)

    try:
        EstadoProducto.objects.create(nombreestadoproducto=nombre, estado=1)
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


def editar(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)

    id = request.POST.get('idEstadoProducto', '').strip()
    nombre = request.POST.get('nameEstadoProducto', '').strip()

    if not id or not nombre:
        return JsonResponse({'ok': False, 'error': 'Datos incompletos'}, status=400)

    try:
        estadoproducto = EstadoProducto.objects.get(idestadoproducto=id)
        estadoproducto.nombreestadoproducto = nombre
        estadoproducto.save()
        return JsonResponse({'ok': True})
    except EstadoProducto.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Registro no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)
