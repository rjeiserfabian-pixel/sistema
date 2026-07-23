from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from software.models.ConfiguracionVehicularModel import ConfiguracionVehicular
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos
from software.models.ProductoModel import Producto

def configuracion_vehicular(request):
    id_tipo_usuario = request.session.get('idtipousuario')
    if not id_tipo_usuario:
        return redirect('login')

    permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id_tipo_usuario)
    registros = ConfiguracionVehicular.objects.filter(estado=1)

    data = {
        'registros': registros,
        'permisos': permisos
    }
    return render(request, 'configuracionvehicular/configuracionvehicular.html', data)

def agregar_configuracion(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)

    nombre = request.POST.get('nombre', '').strip()
    if not nombre:
        return JsonResponse({'ok': False, 'error': 'El nombre no puede estar vacío'}, status=400)

    try:
        nueva = ConfiguracionVehicular.objects.create(nombre=nombre, estado=1)
        return JsonResponse({'ok': True, 'id': nueva.id_configuracion, 'nombre': nueva.nombre})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

def editar_configuracion(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)

    id_conf = request.POST.get('id', '').strip()
    nombre = request.POST.get('nombre', '').strip()

    if not id_conf or not nombre:
        return JsonResponse({'ok': False, 'error': 'Datos incompletos'}, status=400)

    try:
        configuracion = ConfiguracionVehicular.objects.get(pk=id_conf)
        if configuracion.nombre != nombre:
            configuracion.nombre = nombre
            configuracion.save()
            
            # Actualización en cascada
            productos = Producto.objects.filter(id_configuracion=configuracion).select_related(
                'idcategoria', 'idmarca', 'idmodelo', 'id_configuracion', 'idcolor'
            )
            Producto.actualizar_nombres_en_cascada(productos)
            
        return JsonResponse({'ok': True})
    except ConfiguracionVehicular.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Registro no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

def eliminar_configuracion(request, id):
    ConfiguracionVehicular.objects.filter(pk=id).update(estado=0)
    return redirect('configuracion_vehicular')
