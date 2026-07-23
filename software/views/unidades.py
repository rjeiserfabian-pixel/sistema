from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from software.models.UnidadesModel import Unidades
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos


def unidades(request):
    id2 = request.session.get('idtipousuario')
    if not id2:
        return HttpResponse("<h1>No tiene acceso señor</h1>")

    permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
    lista    = Unidades.objects.all()

    data = {
        'unidades': lista,
        'permisos': permisos,
    }
    return render(request, 'unidades/unidades.html', data)


@require_POST
def agregar(request):
    codigo = request.POST.get('codigo_sunat', '').strip()
    nombre = request.POST.get('abrunidad', '').strip()

    if not codigo or not nombre:
        return JsonResponse({'ok': False, 'error': 'El código y el nombre son obligatorios.'})

    # Validar duplicado
    if Unidades.objects.filter(abrunidad__iexact=nombre, estado=1).exists():
        return JsonResponse({'ok': False, 'error': f'La unidad "{nombre}" ya existe. No se permiten duplicados.'}, status=400)

    try:
        nueva = Unidades.objects.create(codigo_sunat=codigo, abrunidad=nombre, estado=1)
        return JsonResponse({'ok': True, 'id': nueva.idunidad, 'nombre': nueva.abrunidad})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': f'Error al guardar: {str(e)}'})


@require_POST
def editar(request):
    idunidad = request.POST.get('idunidad', '').strip()
    codigo   = request.POST.get('codigo_sunat2', '').strip()
    nombre   = request.POST.get('abrunidad2', '').strip()

    if not all([idunidad, codigo, nombre]):
        return JsonResponse({'ok': False, 'error': 'Todos los campos son obligatorios.'})

    try:
        unidad = get_object_or_404(Unidades, idunidad=idunidad)
        
        # Validar duplicado si el nombre cambió
        if unidad.abrunidad.lower() != nombre.lower():
            if Unidades.objects.filter(abrunidad__iexact=nombre, estado=1).exclude(idunidad=idunidad).exists():
                return JsonResponse({'ok': False, 'error': f'La unidad "{nombre}" ya existe. No se permiten duplicados.'}, status=400)
        
        unidad.codigo_sunat = codigo
        unidad.abrunidad    = nombre
        unidad.save()
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': f'Error al actualizar: {str(e)}'})


def activo(request, id):
    unidad = get_object_or_404(Unidades, idunidad=id)
    unidad.estado = 1
    unidad.save()
    return JsonResponse({'status': 'success', 'new_state': 'activo'})


def desactivo(request, id):
    unidad = get_object_or_404(Unidades, idunidad=id)
    unidad.estado = 0
    unidad.save()
    return JsonResponse({'status': 'success', 'new_state': 'desactivado'})
