from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from software.models.RegionModel import Region
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos

def regiones(request):
    # Obtención del id del tipo de usuario desde la sesión
    id2 = request.session.get('idtipousuario')
    if id2:
        permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
        regiones_registros = Region.objects.filter(estado=1)

        data = {
            'regiones_registros': regiones_registros,
            'permisos': permisos
        }
        
        return render(request, 'regiones/regiones.html', data)
    else:
        return HttpResponse("<h1>No tiene acceso señor</h1>")

def regionesEliminar(request, id):
    try:
        Region.objects.filter(id_region=id).update(estado=0)
        return redirect('regiones')
    except Exception as e:
        return HttpResponse(f"Error al eliminar: {str(e)}", status=500)

def agregarRegiones(request):
    if request.method == 'POST':
        nombre = request.POST.get('nameRegionAgregar', '').strip()
        
        if not nombre:
            return JsonResponse({'ok': False, 'error': 'El nombre de la región es obligatorio.'}, status=400)
            
        try:
            Region.objects.create(nombre_region=nombre, estado=1)
            return JsonResponse({'ok': True})
        except Exception as e:
            return JsonResponse({'ok': False, 'error': f'Error al guardar: {str(e)}'}, status=500)
    
    return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)

def editarRegiones(request):
    if request.method == 'POST':
        id = request.POST.get('idRegion')
        nombre = request.POST.get('nameRegion', '').strip()

        if not id or not nombre:
            return JsonResponse({'ok': False, 'error': 'Datos incompletos para la edición.'}, status=400)

        try:
            region = Region.objects.get(id_region=id)
            region.nombre_region = nombre
            region.save()
            return JsonResponse({'ok': True})
        except Region.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'La región no existe.'}, status=404)
        except Exception as e:
            return JsonResponse({'ok': False, 'error': f'Error al actualizar: {str(e)}'}, status=500)

    return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)