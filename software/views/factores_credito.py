from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from software.models.FactorCreditoModel import FactorCredito
from software.models.ZonaCreditoModel import ZonaCredito
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos

def factores_credito(request):
    id2 = request.session.get('idtipousuario')
    if not id2:
        return HttpResponse("<h1>No tiene acceso. Por favor inicie sesión.</h1>")

    permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
    registros = FactorCredito.objects.filter(estado=1).select_related('id_zona')
    zonas = ZonaCredito.objects.filter(estado=1)

    data = {
        'registros': registros,
        'zonas': zonas,
        'permisos': permisos
    }
    return render(request, 'factores_credito/factores_credito.html', data)

def agregar(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)

    id_zona = request.POST.get('id_zona', '').strip()
    numero_cuotas = request.POST.get('numero_cuotas', '').strip()
    factor = request.POST.get('factor', '').strip()

    if not id_zona or not numero_cuotas or not factor:
        return JsonResponse({'ok': False, 'error': 'Datos incompletos'}, status=400)

    try:
        FactorCredito.objects.create(
            id_zona_id=id_zona,
            numero_cuotas=numero_cuotas,
            factor=factor,
            estado=1
        )
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

def editar(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)

    id = request.POST.get('id_factor', '').strip()
    id_zona = request.POST.get('id_zona', '').strip()
    numero_cuotas = request.POST.get('numero_cuotas', '').strip()
    factor = request.POST.get('factor', '').strip()

    if not id or not id_zona or not numero_cuotas or not factor:
        return JsonResponse({'ok': False, 'error': 'Datos incompletos'}, status=400)

    try:
        registro = FactorCredito.objects.get(id_factor=id)
        registro.id_zona_id = id_zona
        registro.numero_cuotas = numero_cuotas
        registro.factor = factor
        registro.save()
        return JsonResponse({'ok': True})
    except FactorCredito.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Registro no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

def eliminar(request, id):
    FactorCredito.objects.filter(id_factor=id).update(estado=0)
    return redirect('factores_credito')
