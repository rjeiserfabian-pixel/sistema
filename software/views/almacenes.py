from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.db import IntegrityError
from software.models.almacenesModel import Almacenes
from software.models.sucursalesModel import Sucursales
from software.models.empresaModel import Empresa
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos
import json

def almacenes(request):
    # Obtención del id del tipo de usuario desde la sesión
    id2 = request.session.get('idtipousuario')
    if id2:
        permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
        almacenes_registros = Almacenes.objects.filter(estado=1).select_related(
            'id_sucursal__idempresa'
        )
        sucursales_registros = Sucursales.objects.filter(estado=1).select_related('idempresa')
        empresas_registros = Empresa.objects.filter(activo=1)

        data = {
            'almacenes_registros': almacenes_registros,
            'sucursales_registros': sucursales_registros,
            'empresas_registros': empresas_registros,
            'permisos': permisos
        }
        
        return render(request, 'almacenes/almacenes.html', data)
    else:
        return HttpResponse("<h1>No tiene acceso señor</h1>")

def almacenesEliminar(request, id):
    Almacenes.objects.filter(id_almacen=id).update(estado=0)
    return redirect('almacenes')

def agregarAlmacenes(request):
    try:
        id_sucursal = request.POST.get('idSucursalAgregar')
        nombre_almacen = request.POST.get('nameAlmacenAgregar')
        codigo_almacen = request.POST.get('codigoAlmacenAgregar')
        descripcion = request.POST.get('descripcionAgregar')
        capacidad_maxima = request.POST.get('capacidadMaximaAgregar')

        if not nombre_almacen or nombre_almacen.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'El nombre del almacén es obligatorio'}),
                content_type='application/json',
                status=400
            )

        if not codigo_almacen or codigo_almacen.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'El código del almacén es obligatorio'}),
                content_type='application/json',
                status=400
            )

        if not id_sucursal or id_sucursal.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'Debe seleccionar una sucursal'}),
                content_type='application/json',
                status=400
            )

        # Verificar que la sucursal existe
        try:
            sucursal = Sucursales.objects.get(id_sucursal=id_sucursal)
        except Sucursales.DoesNotExist:
            return HttpResponse(
                json.dumps({'error': 'La sucursal seleccionada no existe'}),
                content_type='application/json',
                status=400
            )

        nombre_limpio = nombre_almacen.strip()
        codigo_limpio = codigo_almacen.strip()

        # Reglas: únicos por sucursal (entre activos)
        codigo_duplicado = Almacenes.objects.filter(
            id_sucursal=sucursal,
            codigo_almacen__iexact=codigo_limpio,
            estado=1
        ).exists()
        if codigo_duplicado:
            return HttpResponse(
                json.dumps({'error': 'Ya existe un almacén con ese código en esta sucursal.'}),
                content_type='application/json',
                status=400
            )

        nombre_duplicado = Almacenes.objects.filter(
            id_sucursal=sucursal,
            nombre_almacen__iexact=nombre_limpio,
            estado=1
        ).exists()
        if nombre_duplicado:
            return HttpResponse(
                json.dumps({'error': 'Ya existe un almacén con ese nombre en esta sucursal.'}),
                content_type='application/json',
                status=400
            )

        capacidad_int = None
        if capacidad_maxima is not None and str(capacidad_maxima).strip() != '':
            try:
                capacidad_int = int(capacidad_maxima)
            except ValueError:
                return HttpResponse(
                    json.dumps({'error': 'La capacidad máxima debe ser un número entero válido'}),
                    content_type='application/json',
                    status=400
                )
            if capacidad_int < 0:
                return HttpResponse(
                    json.dumps({'error': 'La capacidad máxima debe ser mayor o igual a 0'}),
                    content_type='application/json',
                    status=400
                )

        Almacenes.objects.create(
            id_sucursal=sucursal,
            nombre_almacen=nombre_limpio,
            codigo_almacen=codigo_limpio,
            descripcion=descripcion.strip() if descripcion and descripcion.strip() != '' else None,
            capacidad_maxima=capacidad_int,
            estado=1
        )

        return HttpResponse(
            json.dumps({'success': 'Almacén creado correctamente'}),
            content_type='application/json',
            status=200
        )

    except IntegrityError:
        return HttpResponse(
            json.dumps({'error': 'Error de integridad en la base de datos. Verifique los datos ingresados.'}),
            content_type='application/json',
            status=400
        )
    except Exception as e:
        return HttpResponse(
            json.dumps({'error': f'Error al guardar el almacén: {str(e)}'}),
            content_type='application/json',
            status=500
        )

def editarAlmacenes(request):
    try:
        id_almacen = request.POST.get('idAlmacen')
        id_sucursal = request.POST.get('idSucursal')
        nombre_almacen = request.POST.get('nameAlmacen')
        codigo_almacen = request.POST.get('codigoAlmacen')
        descripcion = request.POST.get('descripcion')
        capacidad_maxima = request.POST.get('capacidadMaxima')

        if not id_almacen or str(id_almacen).strip() == '':
            return HttpResponse(
                json.dumps({'error': 'ID de almacén inválido'}),
                content_type='application/json',
                status=400
            )

        if not nombre_almacen or nombre_almacen.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'El nombre del almacén es obligatorio'}),
                content_type='application/json',
                status=400
            )

        if not codigo_almacen or codigo_almacen.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'El código del almacén es obligatorio'}),
                content_type='application/json',
                status=400
            )

        if not id_sucursal or id_sucursal.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'Debe seleccionar una sucursal'}),
                content_type='application/json',
                status=400
            )

        # Obtener el almacén
        try:
            almacen = Almacenes.objects.get(id_almacen=id_almacen)
        except Almacenes.DoesNotExist:
            return HttpResponse(
                json.dumps({'error': 'El almacén no existe'}),
                content_type='application/json',
                status=400
            )

        # Verificar que la sucursal existe
        try:
            sucursal = Sucursales.objects.get(id_sucursal=id_sucursal)
        except Sucursales.DoesNotExist:
            return HttpResponse(
                json.dumps({'error': 'La sucursal seleccionada no existe'}),
                content_type='application/json',
                status=400
            )

        nombre_limpio = nombre_almacen.strip()
        codigo_limpio = codigo_almacen.strip()

        # Reglas: únicos por sucursal (entre activos), excluyendo el actual
        codigo_duplicado = Almacenes.objects.filter(
            id_sucursal=sucursal,
            codigo_almacen__iexact=codigo_limpio,
            estado=1
        ).exclude(id_almacen=id_almacen).exists()
        if codigo_duplicado:
            return HttpResponse(
                json.dumps({'error': 'Ya existe un almacén con ese código en esta sucursal.'}),
                content_type='application/json',
                status=400
            )

        nombre_duplicado = Almacenes.objects.filter(
            id_sucursal=sucursal,
            nombre_almacen__iexact=nombre_limpio,
            estado=1
        ).exclude(id_almacen=id_almacen).exists()
        if nombre_duplicado:
            return HttpResponse(
                json.dumps({'error': 'Ya existe un almacén con ese nombre en esta sucursal.'}),
                content_type='application/json',
                status=400
            )

        capacidad_int = None
        if capacidad_maxima is not None and str(capacidad_maxima).strip() != '':
            try:
                capacidad_int = int(capacidad_maxima)
            except ValueError:
                return HttpResponse(
                    json.dumps({'error': 'La capacidad máxima debe ser un número entero válido'}),
                    content_type='application/json',
                    status=400
                )
            if capacidad_int < 0:
                return HttpResponse(
                    json.dumps({'error': 'La capacidad máxima debe ser mayor o igual a 0'}),
                    content_type='application/json',
                    status=400
                )

        almacen.id_sucursal = sucursal
        almacen.nombre_almacen = nombre_limpio
        almacen.codigo_almacen = codigo_limpio
        almacen.descripcion = descripcion.strip() if descripcion and descripcion.strip() != '' else None
        almacen.capacidad_maxima = capacidad_int
        almacen.save()

        return HttpResponse(
            json.dumps({'success': 'Almacén actualizado correctamente'}),
            content_type='application/json',
            status=200
        )

    except IntegrityError:
        return HttpResponse(
            json.dumps({'error': 'Error de integridad en la base de datos. Verifique los datos ingresados.'}),
            content_type='application/json',
            status=400
        )
    except Exception as e:
        return HttpResponse(
            json.dumps({'error': f'Error al editar el almacén: {str(e)}'}),
            content_type='application/json',
            status=500
        )

# Vista AJAX para obtener sucursales por empresa
def obtenerSucursalesPorEmpresa(request):
    id_empresa = request.GET.get('id_empresa')
    sucursales = Sucursales.objects.filter(idempresa=id_empresa, estado=1).values('id_sucursal', 'nombre_sucursal')
    return JsonResponse(list(sucursales), safe=False)