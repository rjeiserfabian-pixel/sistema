from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from software.models.ServicioModel import Servicio
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos


def servicios(request):
    id2 = request.session.get('idtipousuario')
    if id2:
        permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
        servicios_registros = Servicio.objects.filter(estado=1).order_by('nombre')
        data = {
            'servicios_registros': servicios_registros,
            'permisos': permisos,
        }
        return render(request, 'servicios/servicios.html', data)
    else:
        return HttpResponse("<h1>No tiene acceso</h1>")


def agregar(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido.'}, status=405)

    nombre = request.POST.get('nombre', '').strip().upper()
    precio = request.POST.get('precio_defecto', '').strip()
    descripcion = request.POST.get('descripcion', '').strip()

    if not nombre or not precio:
        return JsonResponse({'error': 'El nombre y el precio son obligatorios.'}, status=400)

    try:
        precio_decimal = float(precio)
        if precio_decimal < 0:
            return JsonResponse({'error': 'El precio no puede ser negativo.'}, status=400)
    except ValueError:
        return JsonResponse({'error': 'El precio ingresado no es válido.'}, status=400)

    if Servicio.objects.filter(nombre__iexact=nombre, estado=1).exists():
        return JsonResponse({'error': f'El servicio "{nombre}" ya existe.'}, status=400)

    nuevo = Servicio.objects.create(
        nombre=nombre,
        precio_defecto=precio_decimal,
        descripcion=descripcion if descripcion else None,
        estado=1,
    )
    return JsonResponse({'ok': True, 'id': nuevo.id_servicio, 'nombre': nuevo.nombre})


def editar(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido.'}, status=405)

    id_servicio = request.POST.get('id_servicio')
    nombre = request.POST.get('nombre', '').strip().upper()
    precio = request.POST.get('precio_defecto', '').strip()
    descripcion = request.POST.get('descripcion', '').strip()

    if not id_servicio or not nombre or not precio:
        return JsonResponse({'error': 'Datos incompletos.'}, status=400)

    try:
        servicio = Servicio.objects.get(id_servicio=id_servicio)
    except Servicio.DoesNotExist:
        return JsonResponse({'error': 'El servicio no existe.'}, status=404)

    try:
        precio_decimal = float(precio)
        if precio_decimal < 0:
            return JsonResponse({'error': 'El precio no puede ser negativo.'}, status=400)
    except ValueError:
        return JsonResponse({'error': 'El precio ingresado no es válido.'}, status=400)

    # Validar duplicados excluyendo el propio
    if Servicio.objects.filter(nombre__iexact=nombre, estado=1).exclude(id_servicio=id_servicio).exists():
        return JsonResponse({'error': f'Ya existe otro servicio llamado "{nombre}".'}, status=400)

    servicio.nombre = nombre
    servicio.precio_defecto = precio_decimal
    servicio.descripcion = descripcion if descripcion else None
    servicio.save()

    return JsonResponse({'ok': True})


def eliminar(request, id):
    Servicio.objects.filter(id_servicio=id).update(estado=0)
    return JsonResponse({'ok': True})


def listar_activos(request):
    """API: devuelve JSON con todos los servicios activos para usar en el modal de ventas."""
    servicios_activos = Servicio.objects.filter(estado=1).values(
        'id_servicio', 'nombre', 'precio_defecto', 'descripcion'
    )
    return JsonResponse({'servicios': list(servicios_activos)})
