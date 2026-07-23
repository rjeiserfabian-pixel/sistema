from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from software.models.marcaModel import Marca
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos
from software.models.ProductoModel import Producto

def marcas(request):
    # Obtención del id del tipo de usuario desde la sesión
    id2 = request.session.get('idtipousuario')
    if id2:
        permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
        
        # Ya no enviamos las marcas, DataTables se encargará de pedirlas
        data = {
            'permisos': permisos
        }
        
        return render(request, 'marcas/marcas.html', data)
    else:
        return HttpResponse("<h1>No tiene acceso señor</h1>")

def api_listar_marcas(request):
    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '').strip()

    queryset = Marca.objects.filter(estado=1)
    
    if search_value:
        queryset = queryset.filter(nombremarca__icontains=search_value)

    records_total = Marca.objects.filter(estado=1).count()
    records_filtered = queryset.count()

    # Ordenamiento por nombremarca de forma predeterminada
    queryset = queryset.order_by('nombremarca')[start:start + length]

    data = []
    for index, marca in enumerate(queryset, start=start + 1):
        data.append({
            'index': index,
            'idmarca': marca.idmarca,
            'nombremarca': marca.nombremarca,
        })

    return JsonResponse({
        'draw': draw,
        'recordsTotal': records_total,
        'recordsFiltered': records_filtered,
        'data': data
    })

def eliminar(request, id):
    Marca.objects.filter(idmarca=id).update(estado=0)
    return JsonResponse({'ok': True})

def agregar(request):
    nombre = request.POST.get('nameMarcaAgregar', '').strip()

    if not nombre:
        return JsonResponse({'error': 'El nombre de la marca no puede estar vacío.'}, status=400)

    # Validar duplicado (sin distinguir mayúsculas/minúsculas)
    if Marca.objects.filter(nombremarca__iexact=nombre, estado=1).exists():
        return JsonResponse(
            {'error': f'La marca "{nombre}" ya existe. No se permiten marcas duplicadas.'},
            status=400
        )

    nueva_marca = Marca.objects.create(nombremarca=nombre, estado=1)
    return JsonResponse({'ok': True, 'id': nueva_marca.idmarca, 'nombre': nueva_marca.nombremarca})

def editar(request):
    id = request.POST.get('idMarca')
    nombre = request.POST.get('nameMarca', '').strip()

    if not id or not nombre:
        return JsonResponse({'error': 'Datos incompletos.'}, status=400)

    try:
        marca = Marca.objects.get(idmarca=id)
    except Marca.DoesNotExist:
        return JsonResponse({'error': 'La marca no existe.'}, status=404)

    # Validar duplicado solo si el nombre cambió (excluir la propia marca)
    if marca.nombremarca.lower() != nombre.lower():
        if Marca.objects.filter(nombremarca__iexact=nombre, estado=1).exclude(idmarca=id).exists():
            return JsonResponse(
                {'error': f'Ya existe otra marca llamada "{nombre}". No se permiten duplicados.'},
                status=400
            )
        marca.nombremarca = nombre
        marca.save()

        # Actualización en cascada
        productos = Producto.objects.filter(idmarca=marca).select_related(
            'idcategoria', 'idmarca', 'idmodelo', 'id_configuracion', 'idcolor'
        )
        Producto.actualizar_nombres_en_cascada(productos)

    return JsonResponse({'ok': True})

