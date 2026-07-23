from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from software.models.modeloModel import Modelo
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos
from software.models.ProductoModel import Producto

def modelos(request):
    id2 = request.session.get('idtipousuario')
    if id2:
        permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
        # Se elimina la carga de todos los modelos para optimizar el Server-Side Processing
        data = {
            'permisos': permisos
        }

        return render(request, 'modelos/modelos.html', data)
    else:
        return HttpResponse("<h1>No tiene acceso</h1>")


def agregar(request):
    if request.method == 'POST':
        nombre = (request.POST.get('nameModeloAgregar') or '').strip()
        if not nombre:
            return JsonResponse({'ok': False, 'error': 'El nombre no puede estar vacío.'}, status=400)
        nuevo_modelo = Modelo.objects.create(nombremodelo=nombre, estado=1)
        return JsonResponse({'ok': True, 'id': nuevo_modelo.idmodelo, 'nombre': nuevo_modelo.nombremodelo})
    return JsonResponse({'ok': False, 'error': 'Método no permitido.'}, status=405)


def editar(request):
    if request.method == 'POST':
        id = request.POST.get('idModelo')
        nombre = (request.POST.get('nameModelo') or '').strip()
        if id and nombre:
            modelo = get_object_or_404(Modelo, idmodelo=id)
            if modelo.nombremodelo != nombre:
                modelo.nombremodelo = nombre
                modelo.save()
                
                # Actualización en cascada
                productos = Producto.objects.filter(idmodelo=modelo).select_related(
                    'idcategoria', 'idmarca', 'idmodelo', 'id_configuracion', 'idcolor'
                )
                Producto.actualizar_nombres_en_cascada(productos)
            return JsonResponse({'ok': True})
    return JsonResponse({'ok': False, 'error': 'Método no permitido.'}, status=405)


def eliminar(request, id):
    Modelo.objects.filter(idmodelo=id).update(estado=0)
    return JsonResponse({'ok': True})


def api_listar_modelos(request):
    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '').strip()

    modelos_qs = Modelo.objects.filter(estado=1)

    if search_value:
        modelos_qs = modelos_qs.filter(nombremodelo__icontains=search_value)

    records_total = Modelo.objects.filter(estado=1).count()
    records_filtered = modelos_qs.count()

    modelos_qs = modelos_qs.order_by('nombremodelo')[start:start + length]

    data = []
    for index, modelo in enumerate(modelos_qs):
        data.append({
            'index': start + index + 1,
            'idmodelo': modelo.idmodelo,
            'nombremodelo': modelo.nombremodelo,
        })

    return JsonResponse({
        'draw': draw,
        'recordsTotal': records_total,
        'recordsFiltered': records_filtered,
        'data': data
    })
