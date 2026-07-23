from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from software.models.SituacionVehiculoModel import SituacionVehiculo
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos


def situacion_vehiculos(request):
    id2 = request.session.get('idtipousuario')
    if not id2:
        return HttpResponse("<h1>No tiene acceso. Por favor inicie sesión.</h1>")

    permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
    situaciones = SituacionVehiculo.objects.filter(estado=1)

    data = {
        'situaciones': situaciones,
        'permisos': permisos
    }
    return render(request, 'situacion_vehiculo/situacion_vehiculo.html', data)


def eliminar_situacion(request, id):
    SituacionVehiculo.objects.filter(id_situacion=id).update(estado=0)
    return redirect('situacion_vehiculos')


def agregar_situacion(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)

    nombre = request.POST.get('nombre_situacion', '').strip()
    if not nombre:
        return JsonResponse({'ok': False, 'error': 'El nombre no puede estar vacío'}, status=400)

    try:
        SituacionVehiculo.objects.create(nombre_situacion=nombre, estado=1)
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


def editar_situacion(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)

    id = request.POST.get('id_situacion', '').strip()
    nombre = request.POST.get('nombre_situacion', '').strip()

    if not id or not nombre:
        return JsonResponse({'ok': False, 'error': 'Datos incompletos'}, status=400)

    try:
        situacion = SituacionVehiculo.objects.get(id_situacion=id)
        situacion.nombre_situacion = nombre
        situacion.save()
        return JsonResponse({'ok': True})
    except SituacionVehiculo.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Registro no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)
