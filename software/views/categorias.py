from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from software.models.categoriaModel import Categoria
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos
from software.models.ProductoModel import Producto

def categorias(request):
    id2 = request.session.get('idtipousuario')
    if not id2:
        return HttpResponse("<h1>No tiene acceso. Por favor inicie sesión.</h1>")

    permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
    cateogiras_registros = Categoria.objects.filter(estado=1)

    data = {
        'cateogiras_registros': cateogiras_registros,
        'permisos': permisos
    }
    return render(request, 'categorias/categorias.html', data)


def eliminar(request, id):
    Categoria.objects.filter(idcategoria=id).update(estado=0)
    return redirect('categorias')


def agregar(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)

    nombre = request.POST.get('nameCategoriaAgregar', '').strip()
    if not nombre:
        return JsonResponse({'ok': False, 'error': 'El nombre no puede estar vacío'}, status=400)

    try:
        Categoria.objects.create(nomcategoria=nombre, estado=1)
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


def editar(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)

    id = request.POST.get('idCategoria', '').strip()
    nombre = request.POST.get('nameCategoria', '').strip()

    if not id or not nombre:
        return JsonResponse({'ok': False, 'error': 'Datos incompletos'}, status=400)

    try:
        categoria = Categoria.objects.get(idcategoria=id)
        if categoria.nomcategoria != nombre:
            categoria.nomcategoria = nombre
            categoria.save()
            
            # Actualización en cascada
            productos = Producto.objects.filter(idcategoria=categoria).select_related(
                'idcategoria', 'idmarca', 'idmodelo', 'id_configuracion', 'idcolor'
            )
            Producto.actualizar_nombres_en_cascada(productos)
            
        return JsonResponse({'ok': True})
    except Categoria.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Registro no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)