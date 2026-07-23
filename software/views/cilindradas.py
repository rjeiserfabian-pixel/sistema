from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from software.models.cilindradaModel import Cilindrada
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos


def cilindradas(request):
    id2 = request.session.get('idtipousuario')
    if not id2:
        return HttpResponse("<h1>No tiene acceso. Por favor inicie sesión.</h1>")

    permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
    cilindradas_registros = Cilindrada.objects.filter(estado=1)

    data = {
        'cilindradas_registros': cilindradas_registros,
        'permisos': permisos
    }
    return render(request, 'cilindradas/cilindradas.html', data)


def eliminar(request, id):
    Cilindrada.objects.filter(idcilindrada=id).update(estado=0)
    return redirect('cilindradas')


def agregar(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)

    nombre = request.POST.get('nameCilindradaAgregar', '').strip()
    if not nombre:
        return JsonResponse({'ok': False, 'error': 'El nombre no puede estar vacío'}, status=400)

    # Validar duplicado
    if Cilindrada.objects.filter(cilindrada_cc__iexact=nombre, estado=1).exists():
        return JsonResponse({'ok': False, 'error': f'La cilindrada "{nombre}" ya existe. No se permiten duplicados.'}, status=400)

    try:
        nueva = Cilindrada.objects.create(cilindrada_cc=nombre, estado=1)
        return JsonResponse({'ok': True, 'id': nueva.idcilindrada, 'nombre': nueva.cilindrada_cc})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


def editar(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)

    id = request.POST.get('idCilindrada', '').strip()
    nombre = request.POST.get('nameCilindrada', '').strip()

    if not id or not nombre:
        return JsonResponse({'ok': False, 'error': 'Datos incompletos'}, status=400)

    try:
        cilindrada = Cilindrada.objects.get(idcilindrada=id)
        
        # Validar duplicado si el nombre cambió
        if cilindrada.cilindrada_cc.lower() != nombre.lower():
            if Cilindrada.objects.filter(cilindrada_cc__iexact=nombre, estado=1).exclude(idcilindrada=id).exists():
                return JsonResponse({'ok': False, 'error': f'La cilindrada "{nombre}" ya existe. No se permiten duplicados.'}, status=400)
        
        cilindrada.cilindrada_cc = nombre
        cilindrada.save()
        return JsonResponse({'ok': True})
    except Cilindrada.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Registro no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)
