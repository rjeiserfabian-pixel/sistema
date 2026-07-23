from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.db import IntegrityError
from software.models.ProvinciaModel import Provincia
from software.models.RegionModel import Region
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos
import json


def provincias(request):
    # Obtención del id del tipo de usuario desde la sesión
    id2 = request.session.get('idtipousuario')
    if id2:
        permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
        provincias_registros = Provincia.objects.filter(estado=1).select_related('id_region')
        regiones_registros = Region.objects.filter(estado=1)

        data = {
            'provincias_registros': provincias_registros,
            'regiones_registros': regiones_registros,
            'permisos': permisos
        }
        
        return render(request, 'provincias/provincias.html', data)
    else:
        return HttpResponse("<h1>No tiene acceso señor</h1>")


def provinciasEliminar(request, id):
    Provincia.objects.filter(id_provincia=id).update(estado=0)
    return redirect('provincias')


def agregarProvincias(request):
    try:
        nombre = request.POST.get('nameProvinciaAgregar')
        id_region = request.POST.get('idRegionAgregar')

        # Validaciones básicas
        if not nombre or nombre.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'El nombre de la provincia es obligatorio'}),
                content_type='application/json',
                status=400
            )

        if not id_region or id_region.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'Debe seleccionar una región'}),
                content_type='application/json',
                status=400
            )

        # Verificar que la región existe
        try:
            region = Region.objects.get(id_region=id_region)
        except Region.DoesNotExist:
            return HttpResponse(
                json.dumps({'error': 'La región seleccionada no existe'}),
                content_type='application/json',
                status=400
            )

        nombre_limpio = nombre.strip()

        # Verificar que no exista otra provincia con el mismo nombre en la misma región
        provincia_duplicada = Provincia.objects.filter(
            nombre_provincia__iexact=nombre_limpio,
            id_region=region,
            estado=1
        ).exists()

        if provincia_duplicada:
            return HttpResponse(
                json.dumps({
                    'error': 'Ya existe una provincia con ese nombre en esta región.'
                }),
                content_type='application/json',
                status=400
            )

        # Crear la provincia
        Provincia.objects.create(
            nombre_provincia=nombre_limpio,
            id_region=region,
            estado=1
        )

        return HttpResponse(
            json.dumps({'success': 'Provincia creada correctamente'}),
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
            json.dumps({'error': f'Error al guardar la provincia: {str(e)}'}),
            content_type='application/json',
            status=500
        )


def editarProvincias(request):
    try:
        id_provincia = request.POST.get('idProvincia')
        nombre = request.POST.get('nameProvincia')
        id_region = request.POST.get('idRegion')

        # Validaciones básicas
        if not id_provincia or id_provincia.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'ID de provincia inválido'}),
                content_type='application/json',
                status=400
            )

        if not nombre or nombre.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'El nombre de la provincia es obligatorio'}),
                content_type='application/json',
                status=400
            )

        if not id_region or id_region.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'Debe seleccionar una región'}),
                content_type='application/json',
                status=400
            )

        # Obtener la provincia
        try:
            provincia = Provincia.objects.get(id_provincia=id_provincia)
        except Provincia.DoesNotExist:
            return HttpResponse(
                json.dumps({'error': 'La provincia no existe'}),
                content_type='application/json',
                status=400
            )

        # Obtener la región
        try:
            region = Region.objects.get(id_region=id_region)
        except Region.DoesNotExist:
            return HttpResponse(
                json.dumps({'error': 'La región seleccionada no existe'}),
                content_type='application/json',
                status=400
            )

        nombre_limpio = nombre.strip()

        # Verificar que no exista otra provincia con el mismo nombre en la misma región (excluyendo la actual)
        provincia_duplicada = Provincia.objects.filter(
            nombre_provincia__iexact=nombre_limpio,
            id_region=region,
            estado=1
        ).exclude(id_provincia=id_provincia).exists()

        if provincia_duplicada:
            return HttpResponse(
                json.dumps({
                    'error': 'Ya existe una provincia con ese nombre en esta región.'
                }),
                content_type='application/json',
                status=400
            )

        # Actualizar los campos
        provincia.nombre_provincia = nombre_limpio
        provincia.id_region = region
        provincia.save()

        return HttpResponse(
            json.dumps({'success': 'Provincia actualizada correctamente'}),
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
            json.dumps({'error': f'Error al editar la provincia: {str(e)}'}),
            content_type='application/json',
            status=500
        )
