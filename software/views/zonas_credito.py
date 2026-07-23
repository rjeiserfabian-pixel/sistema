from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from software.models.ZonaCreditoModel import ZonaCredito
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos

def zonas_credito(request):
    id2 = request.session.get('idtipousuario')
    if not id2:
        return HttpResponse("<h1>No tiene acceso. Por favor inicie sesión.</h1>")

    permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
    registros = ZonaCredito.objects.filter(estado=1)

    data = {
        'registros': registros,
        'permisos': permisos
    }
    return render(request, 'zonas_credito/zonas_credito.html', data)

def agregar(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)

    nombre = request.POST.get('nombre', '').strip()
    if not nombre:
        return JsonResponse({'ok': False, 'error': 'El nombre no puede estar vacío'}, status=400)

    try:
        ZonaCredito.objects.create(nombre=nombre, estado=1)
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

def editar(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)

    id = request.POST.get('id_zona', '').strip()
    nombre = request.POST.get('nombre', '').strip()

    if not id or not nombre:
        return JsonResponse({'ok': False, 'error': 'Datos incompletos'}, status=400)

    try:
        registro = ZonaCredito.objects.get(id_zona=id)
        registro.nombre = nombre
        registro.save()
        return JsonResponse({'ok': True})
    except ZonaCredito.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Registro no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

def eliminar(request, id):
    ZonaCredito.objects.filter(id_zona=id).update(estado=0)
    return redirect('zonas_credito')
