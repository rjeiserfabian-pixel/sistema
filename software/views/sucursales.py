from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.db import IntegrityError
from software.models.sucursalesModel import Sucursales
from software.models.empresaModel import Empresa
from software.models.DistritoModel import Distrito
from software.models.ProvinciaModel import Provincia
from software.models.RegionModel import Region
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos
import json

def sucursales(request):
    # Obtención del id del tipo de usuario desde la sesión
    id2 = request.session.get('idtipousuario')
    if id2:
        permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
        sucursales_registros = Sucursales.objects.filter(estado=1).select_related(
            'idempresa', 
            'id_distrito__id_provincia__id_region'
        )
        empresas_registros = Empresa.objects.filter(activo=1)
        distritos_registros = Distrito.objects.filter(estado=1).select_related('id_provincia__id_region')
        provincias_registros = Provincia.objects.filter(estado=1).select_related('id_region')
        regiones_registros = Region.objects.filter(estado=1)

        data = {
            'sucursales_registros': sucursales_registros,
            'empresas_registros': empresas_registros,
            'distritos_registros': distritos_registros,
            'provincias_registros': provincias_registros,
            'regiones_registros': regiones_registros,
            'permisos': permisos
        }
        
        return render(request, 'sucursales/sucursales.html', data)
    else:
        return HttpResponse("<h1>No tiene acceso señor</h1>")

def sucursalesEliminar(request, id):
    Sucursales.objects.filter(id_sucursal=id).update(estado=0)
    return redirect('sucursales')

def agregarSucursales(request):
    try:
        idempresa = request.POST.get('idEmpresaAgregar')
        id_distrito = request.POST.get('idDistritoAgregar')
        nombre_sucursal = request.POST.get('nameSucursalAgregar')
        codigo_sucursal = request.POST.get('codigoSucursalAgregar')
        direccion = request.POST.get('direccionAgregar')
        telefono = request.POST.get('telefonoAgregar')
        fecha_apertura = request.POST.get('fechaAperturaAgregar')
        es_principal = request.POST.get('esPrincipalAgregar') == 'on'

        # Validaciones básicas
        if not nombre_sucursal or nombre_sucursal.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'El nombre de la sucursal es obligatorio'}),
                content_type='application/json',
                status=400
            )
        if not codigo_sucursal or codigo_sucursal.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'El código de sucursal es obligatorio'}),
                content_type='application/json',
                status=400
            )
        if not idempresa or idempresa.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'Debe seleccionar una empresa'}),
                content_type='application/json',
                status=400
            )
        if not id_distrito or id_distrito.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'Debe seleccionar un distrito'}),
                content_type='application/json',
                status=400
            )
        if not direccion or direccion.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'La dirección es obligatoria'}),
                content_type='application/json',
                status=400
            )
        if not telefono or telefono.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'El teléfono es obligatorio'}),
                content_type='application/json',
                status=400
            )
        if not fecha_apertura or fecha_apertura.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'La fecha de apertura es obligatoria'}),
                content_type='application/json',
                status=400
            )

        # Verificar que la empresa existe
        try:
            empresa = Empresa.objects.get(idempresa=idempresa)
        except Empresa.DoesNotExist:
            return HttpResponse(
                json.dumps({'error': 'La empresa seleccionada no existe'}),
                content_type='application/json',
                status=400
            )

        # Verificar que el distrito existe
        try:
            distrito = Distrito.objects.get(id_distrito=id_distrito)
        except Distrito.DoesNotExist:
            return HttpResponse(
                json.dumps({'error': 'El distrito seleccionado no existe'}),
                content_type='application/json',
                status=400
            )

        nombre_limpio = nombre_sucursal.strip()
        codigo_limpio = codigo_sucursal.strip()

        # Código único por empresa
        codigo_duplicado = Sucursales.objects.filter(
            idempresa=empresa,
            codigo_sucursal__iexact=codigo_limpio,
            estado=1
        ).exists()
        if codigo_duplicado:
            return HttpResponse(
                json.dumps({
                    'error': 'Ya existe una sucursal con ese código en esta empresa.'
                }),
                content_type='application/json',
                status=400
            )

        Sucursales.objects.create(
            idempresa=empresa,
            id_distrito=distrito,
            nombre_sucursal=nombre_limpio,
            codigo_sucursal=codigo_limpio,
            direccion=direccion.strip(),
            telefono=telefono.strip(),
            fecha_apertura=fecha_apertura.strip(),
            es_principal=es_principal,
            estado=1
        )

        return HttpResponse(
            json.dumps({'success': 'Sucursal creada correctamente'}),
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
            json.dumps({'error': f'Error al guardar la sucursal: {str(e)}'}),
            content_type='application/json',
            status=500
        )


def editarSucursales(request):
    try:
        id_sucursal = request.POST.get('idSucursal')
        idempresa = request.POST.get('idEmpresa')
        id_distrito = request.POST.get('idDistrito')
        nombre_sucursal = request.POST.get('nameSucursal')
        codigo_sucursal = request.POST.get('codigoSucursal')
        direccion = request.POST.get('direccion')
        telefono = request.POST.get('telefono')
        fecha_apertura = request.POST.get('fechaApertura')
        es_principal = request.POST.get('esPrincipal') == 'on'

        # Validaciones básicas
        if not id_sucursal or id_sucursal.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'ID de sucursal inválido'}),
                content_type='application/json',
                status=400
            )
        if not nombre_sucursal or nombre_sucursal.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'El nombre de la sucursal es obligatorio'}),
                content_type='application/json',
                status=400
            )
        if not codigo_sucursal or codigo_sucursal.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'El código de sucursal es obligatorio'}),
                content_type='application/json',
                status=400
            )
        if not idempresa or idempresa.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'Debe seleccionar una empresa'}),
                content_type='application/json',
                status=400
            )
        if not id_distrito or id_distrito.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'Debe seleccionar un distrito'}),
                content_type='application/json',
                status=400
            )
        if not direccion or direccion.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'La dirección es obligatoria'}),
                content_type='application/json',
                status=400
            )
        if not telefono or telefono.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'El teléfono es obligatorio'}),
                content_type='application/json',
                status=400
            )
        if not fecha_apertura or fecha_apertura.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'La fecha de apertura es obligatoria'}),
                content_type='application/json',
                status=400
            )

        # Obtener la sucursal
        try:
            sucursal = Sucursales.objects.get(id_sucursal=id_sucursal)
        except Sucursales.DoesNotExist:
            return HttpResponse(
                json.dumps({'error': 'La sucursal no existe'}),
                content_type='application/json',
                status=400
            )

        # Obtener empresa y distrito
        try:
            empresa = Empresa.objects.get(idempresa=idempresa)
        except Empresa.DoesNotExist:
            return HttpResponse(
                json.dumps({'error': 'La empresa seleccionada no existe'}),
                content_type='application/json',
                status=400
            )
        try:
            distrito = Distrito.objects.get(id_distrito=id_distrito)
        except Distrito.DoesNotExist:
            return HttpResponse(
                json.dumps({'error': 'El distrito seleccionado no existe'}),
                content_type='application/json',
                status=400
            )

        nombre_limpio = nombre_sucursal.strip()
        codigo_limpio = codigo_sucursal.strip()

        # Código único por empresa (excluyendo la sucursal actual)
        codigo_duplicado = Sucursales.objects.filter(
            idempresa=empresa,
            codigo_sucursal__iexact=codigo_limpio,
            estado=1
        ).exclude(id_sucursal=id_sucursal).exists()
        if codigo_duplicado:
            return HttpResponse(
                json.dumps({
                    'error': 'Ya existe una sucursal con ese código en esta empresa.'
                }),
                content_type='application/json',
                status=400
            )

        sucursal.idempresa = empresa
        sucursal.id_distrito = distrito
        sucursal.nombre_sucursal = nombre_limpio
        sucursal.codigo_sucursal = codigo_limpio
        sucursal.direccion = direccion.strip()
        sucursal.telefono = telefono.strip()
        sucursal.fecha_apertura = fecha_apertura.strip()
        sucursal.es_principal = es_principal
        sucursal.save()

        return HttpResponse(
            json.dumps({'success': 'Sucursal actualizada correctamente'}),
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
            json.dumps({'error': f'Error al editar la sucursal: {str(e)}'}),
            content_type='application/json',
            status=500
        )

# Vista AJAX para obtener provincias por región
def obtenerProvinciasPorRegion(request):
    id_region = request.GET.get('id_region')
    provincias = Provincia.objects.filter(id_region=id_region, estado=1).values('id_provincia', 'nombre_provincia')
    return JsonResponse(list(provincias), safe=False)

# Vista AJAX para obtener distritos por provincia
def obtenerDistritosPorProvincia(request):
    id_provincia = request.GET.get('id_provincia')
    distritos = Distrito.objects.filter(id_provincia=id_provincia, estado=1).values('id_distrito', 'nombre_distrito')
    return JsonResponse(list(distritos), safe=False)