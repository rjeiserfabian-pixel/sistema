from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.db import IntegrityError
from software.models.DistritoModel import Distrito
from software.models.ProvinciaModel import Provincia
from software.models.RegionModel import Region
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos
import json

def distritos(request):
    # Obtención del id del tipo de usuario desde la sesión
    id2 = request.session.get('idtipousuario')
    if id2:
        permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
        distritos_registros = Distrito.objects.filter(estado=1).select_related('id_provincia__id_region')
        provincias_registros = Provincia.objects.filter(estado=1).select_related('id_region')
        regiones_registros = Region.objects.filter(estado=1)

        data = {
            'distritos_registros': distritos_registros,
            'provincias_registros': provincias_registros,
            'regiones_registros': regiones_registros,
            'permisos': permisos
        }
        
        return render(request, 'distritos/distritos.html', data)
    else:
        return HttpResponse("<h1>No tiene acceso señor</h1>")

def distritosEliminar(request, id):
    Distrito.objects.filter(id_distrito=id).update(estado=0)
    return redirect('distritos')

def agregarDistritos(request):
    try:
        nombre = request.POST.get('nameDistritoAgregar')
        id_provincia = request.POST.get('idProvinciaAgregar')

        # Validaciones básicas
        if not nombre or nombre.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'El nombre del distrito es obligatorio'}),
                content_type='application/json',
                status=400
            )

        if not id_provincia or id_provincia.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'Debe seleccionar una provincia'}),
                content_type='application/json',
                status=400
            )

        # Verificar que la provincia existe
        try:
            provincia = Provincia.objects.get(id_provincia=id_provincia)
        except Provincia.DoesNotExist:
            return HttpResponse(
                json.dumps({'error': 'La provincia seleccionada no existe'}),
                content_type='application/json',
                status=400
            )

        nombre_limpio = nombre.strip()

        # Verificar que no exista otro distrito con el mismo nombre en la misma provincia
        distrito_duplicado = Distrito.objects.filter(
            nombre_distrito__iexact=nombre_limpio,
            id_provincia=provincia,
            estado=1
        ).exists()

        if distrito_duplicado:
            return HttpResponse(
                json.dumps({
                    'error': 'Ya existe un distrito con ese nombre en esta provincia.'
                }),
                content_type='application/json',
                status=400
            )

        # Crear el distrito
        Distrito.objects.create(
            nombre_distrito=nombre_limpio,
            id_provincia=provincia,
            estado=1
        )

        return HttpResponse(
            json.dumps({'success': 'Distrito creado correctamente'}),
            content_type='application/json',
            status=200
        )

    except IntegrityError as e:
        return HttpResponse(
            json.dumps({
                'error': 'Error de integridad en la base de datos. Verifique los datos ingresados.'
            }),
            content_type='application/json',
            status=400
        )
    except Exception as e:
        return HttpResponse(
            json.dumps({'error': f'Error al guardar el distrito: {str(e)}'}),
            content_type='application/json',
            status=500
        )


def editarDistritos(request):
    try:
        id_distrito = request.POST.get('idDistrito')
        nombre = request.POST.get('nameDistrito')
        id_provincia = request.POST.get('idProvincia')

        # Validaciones básicas
        if not id_distrito or id_distrito.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'ID de distrito inválido'}),
                content_type='application/json',
                status=400
            )

        if not nombre or nombre.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'El nombre del distrito es obligatorio'}),
                content_type='application/json',
                status=400
            )

        if not id_provincia or id_provincia.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'Debe seleccionar una provincia'}),
                content_type='application/json',
                status=400
            )

        # Obtener el distrito
        try:
            distrito = Distrito.objects.get(id_distrito=id_distrito)
        except Distrito.DoesNotExist:
            return HttpResponse(
                json.dumps({'error': 'El distrito no existe'}),
                content_type='application/json',
                status=400
            )

        # Obtener la provincia
        try:
            provincia = Provincia.objects.get(id_provincia=id_provincia)
        except Provincia.DoesNotExist:
            return HttpResponse(
                json.dumps({'error': 'La provincia seleccionada no existe'}),
                content_type='application/json',
                status=400
            )

        nombre_limpio = nombre.strip()

        # Verificar que no exista otro distrito con el mismo nombre en la misma provincia (excluyendo el actual)
        distrito_duplicado = Distrito.objects.filter(
            nombre_distrito__iexact=nombre_limpio,
            id_provincia=provincia,
            estado=1
        ).exclude(id_distrito=id_distrito).exists()

        if distrito_duplicado:
            return HttpResponse(
                json.dumps({
                    'error': 'Ya existe un distrito con ese nombre en esta provincia.'
                }),
                content_type='application/json',
                status=400
            )

        # Actualizar los campos
        distrito.nombre_distrito = nombre_limpio
        distrito.id_provincia = provincia
        distrito.save()

        return HttpResponse(
            json.dumps({'success': 'Distrito actualizado correctamente'}),
            content_type='application/json',
            status=200
        )

    except IntegrityError as e:
        return HttpResponse(
            json.dumps({
                'error': 'Error de integridad en la base de datos. Verifique los datos ingresados.'
            }),
            content_type='application/json',
            status=400
        )
    except Exception as e:
        return HttpResponse(
            json.dumps({'error': f'Error al editar el distrito: {str(e)}'}),
            content_type='application/json',
            status=500
        )

# Vista AJAX para obtener provincias por región
def obtenerProvinciasPorRegion(request):
    id_region = request.GET.get('id_region')
    provincias = Provincia.objects.filter(id_region=id_region, estado=1).values('id_provincia', 'nombre_provincia')
    return JsonResponse(list(provincias), safe=False)