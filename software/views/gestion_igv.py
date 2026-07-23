from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from software.models.TipoIgvModel import TipoIgv
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos

def gestion_igv(request):
    id2 = request.session.get('idtipousuario')
    if not id2:
        return HttpResponse("<h1>No tiene acceso. Por favor inicie sesión.</h1>")

    permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
    registros = TipoIgv.objects.filter(estado=1).order_by('id_tipo_igv')

    data = {
        'registros': registros,
        'permisos': permisos
    }
    return render(request, 'gestion/igv.html', data)

def agregar_igv(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)

    codigo = request.POST.get('codigo', '').strip()
    tipo_igv = request.POST.get('tipo_igv', '').strip()
    codigo_de_tributo = request.POST.get('codigo_de_tributo', '').strip()

    if not codigo or not tipo_igv or not codigo_de_tributo:
        return JsonResponse({'ok': False, 'error': 'Datos incompletos'}, status=400)

    try:
        TipoIgv.objects.create(
            codigo=codigo,
            tipo_igv=tipo_igv,
            codigo_de_tributo=int(codigo_de_tributo),
            estado=1
        )
        return JsonResponse({'ok': True})
    except ValueError:
        return JsonResponse({'ok': False, 'error': 'El código de tributo debe ser un número'}, status=400)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

def editar_igv(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)

    id = request.POST.get('id_tipo_igv', '').strip()
    codigo = request.POST.get('codigo', '').strip()
    tipo_igv = request.POST.get('tipo_igv', '').strip()
    codigo_de_tributo = request.POST.get('codigo_de_tributo', '').strip()

    if not id or not codigo or not tipo_igv or not codigo_de_tributo:
        return JsonResponse({'ok': False, 'error': 'Datos incompletos'}, status=400)

    try:
        registro = TipoIgv.objects.get(id_tipo_igv=id)
        registro.codigo = codigo
        registro.tipo_igv = tipo_igv
        registro.codigo_de_tributo = int(codigo_de_tributo)
        registro.save()
        return JsonResponse({'ok': True})
    except TipoIgv.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Registro no encontrado'}, status=404)
    except ValueError:
        return JsonResponse({'ok': False, 'error': 'El código de tributo debe ser un número'}, status=400)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

def eliminar_igv(request, id):
    TipoIgv.objects.filter(id_tipo_igv=id).update(estado=0)
    return redirect('gestion_igv')
