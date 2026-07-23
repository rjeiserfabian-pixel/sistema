from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.db import IntegrityError
from software.models.cajaModel import Caja
from software.models.sucursalesModel import Sucursales
from software.models.empresaModel import Empresa
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos
import json

def cajas(request):
    # Obtención del id del tipo de usuario desde la sesión
    id2 = request.session.get('idtipousuario')
    if id2:
        permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
        cajas_registros = Caja.objects.filter(estado=1).select_related(
            'id_sucursal__idempresa'
        )
        sucursales_registros = Sucursales.objects.filter(estado=1).select_related('idempresa')
        empresas_registros = Empresa.objects.filter(activo=1)

        data = {
            'cajas_registros': cajas_registros,
            'sucursales_registros': sucursales_registros,
            'empresas_registros': empresas_registros,
            'permisos': permisos
        }
        
        return render(request, 'cajas/cajas.html', data)
    else:
        return HttpResponse("<h1>No tiene acceso señor</h1>")

def cajasEliminar(request, id):
    Caja.objects.filter(id_caja=id).update(estado=0)
    return redirect('cajas')

def agregarCajas(request):
    try:
        id_sucursal = request.POST.get('idSucursalAgregar')
        nombre_caja = request.POST.get('nameCajaAgregar')
        numero_caja = request.POST.get('numeroCajaAgregar')
        
        # Validaciones básicas
        if not nombre_caja or nombre_caja.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'El nombre de la caja es obligatorio'}),
                content_type='application/json',
                status=400
            )
        
        if not numero_caja or numero_caja.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'El número de caja es obligatorio'}),
                content_type='application/json',
                status=400
            )
        
        if not id_sucursal or id_sucursal.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'Debe seleccionar una sucursal'}),
                content_type='application/json',
                status=400
            )
        
        try:
            numero_caja_int = int(numero_caja)
            if numero_caja_int <= 0:
                return HttpResponse(
                    json.dumps({'error': 'El número de caja debe ser mayor a 0'}),
                    content_type='application/json',
                    status=400
                )
        except ValueError:
            return HttpResponse(
                json.dumps({'error': 'El número de caja debe ser un número válido'}),
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
        
        # La validación de una sola caja por sucursal ha sido eliminada para permitir múltiples cajas.
        
        # Verificar si el número de caja ya existe en esa sucursal
        numero_existente = Caja.objects.filter(
            numero_caja=numero_caja_int,
            id_sucursal=id_sucursal,
            estado=1
        ).exists()
        
        if numero_existente:
            return HttpResponse(
                json.dumps({
                    'error': f'El número de caja {numero_caja_int} ya está siendo usado en esta sucursal.'
                }),
                content_type='application/json',
                status=400
            )
        
        # Crear la caja
        Caja.objects.create(
            id_sucursal=sucursal,
            nombre_caja=nombre_caja.strip(),
            numero_caja=numero_caja_int,
            estado=1
        )
        
        return HttpResponse(
            json.dumps({'success': 'Caja creada correctamente'}),
            content_type='application/json',
            status=200
        )
        
    except IntegrityError as e:
        error_msg = str(e)
        print(f"DEBUG - IntegrityError en agregar: {error_msg}")
        
        # Detectar tipo de error
        if 'numero_caja' in error_msg or 'Duplicate entry' in error_msg:
            return HttpResponse(
                json.dumps({
                    'error': 'Ya existe una caja con ese número en esta sucursal.'
                }),
                content_type='application/json',
                status=400
            )
        else:
            return HttpResponse(
                json.dumps({
                    'error': 'Error de integridad en la base de datos. Verifique los datos ingresados.'
                }),
                content_type='application/json',
                status=400
            )
        
    except Exception as e:
        print(f"DEBUG - Error inesperado al agregar: {str(e)}")
        import traceback
        traceback.print_exc()
        return HttpResponse(
            json.dumps({'error': f'Error al guardar la caja: {str(e)}'}),
            content_type='application/json',
            status=500
        )

def editarCajas(request):
    try:
        id_caja = request.POST.get('idCaja')
        id_sucursal = request.POST.get('idSucursal')
        nombre_caja = request.POST.get('nameCaja')
        numero_caja = request.POST.get('numeroCaja')
        
        # Debug
        print(f"DEBUG - idCaja: {id_caja}")
        print(f"DEBUG - idSucursal: {id_sucursal}")
        print(f"DEBUG - nameCaja: {nombre_caja}")
        print(f"DEBUG - numeroCaja: {numero_caja}")
        print(f"DEBUG - POST completo: {request.POST}")
        
        # Validaciones básicas
        if not id_caja or id_caja.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'ID de caja inválido'}),
                content_type='application/json',
                status=400
            )
        
        if not nombre_caja or nombre_caja.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'El nombre de la caja es obligatorio'}),
                content_type='application/json',
                status=400
            )
        
        if not numero_caja or numero_caja.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'El número de caja es obligatorio'}),
                content_type='application/json',
                status=400
            )
        
        if not id_sucursal or id_sucursal.strip() == '':
            return HttpResponse(
                json.dumps({'error': 'Debe seleccionar una sucursal'}),
                content_type='application/json',
                status=400
            )
        
        try:
            numero_caja_int = int(numero_caja)
            if numero_caja_int <= 0:
                return HttpResponse(
                    json.dumps({'error': 'El número de caja debe ser mayor a 0'}),
                    content_type='application/json',
                    status=400
                )
        except ValueError:
            return HttpResponse(
                json.dumps({'error': 'El número de caja debe ser un número válido'}),
                content_type='application/json',
                status=400
            )
        
        # Obtener la caja
        try:
            caja = Caja.objects.get(id_caja=id_caja)
        except Caja.DoesNotExist:
            return HttpResponse(
                json.dumps({'error': 'La caja no existe'}),
                content_type='application/json',
                status=400
            )
        
        # Obtener la sucursal
        try:
            sucursal = Sucursales.objects.get(id_sucursal=id_sucursal)
        except Sucursales.DoesNotExist:
            return HttpResponse(
                json.dumps({'error': 'La sucursal seleccionada no existe'}),
                content_type='application/json',
                status=400
            )
        
        # La validación de una sola caja por sucursal ha sido eliminada.
        
        # Verificar si el número de caja ya está siendo usado en la misma sucursal
        numero_en_uso = Caja.objects.filter(
            numero_caja=numero_caja_int,
            id_sucursal=id_sucursal,
            estado=1
        ).exclude(id_caja=id_caja).exists()
        
        if numero_en_uso:
            return HttpResponse(
                json.dumps({
                    'error': f'El número de caja {numero_caja_int} ya está siendo usado en esta sucursal.'
                }),
                content_type='application/json',
                status=400
            )
        
        # Actualizar los campos
        caja.id_sucursal = sucursal
        caja.nombre_caja = nombre_caja.strip()
        caja.numero_caja = numero_caja_int
        caja.save()
        
        print(f"DEBUG - Caja actualizada exitosamente: {caja.id_caja}")
        
        return HttpResponse(
            json.dumps({'success': 'Caja actualizada correctamente'}),
            content_type='application/json',
            status=200
        )
        
    except IntegrityError as e:
        error_msg = str(e)
        print(f"DEBUG - IntegrityError: {error_msg}")
        
        # Detectar tipo de error
        if 'numero_caja' in error_msg or 'Duplicate entry' in error_msg:
            return HttpResponse(
                json.dumps({
                    'error': 'Ya existe una caja con ese número en esta sucursal.'
                }),
                content_type='application/json',
                status=400
            )
        else:
            return HttpResponse(
                json.dumps({
                    'error': 'Error de integridad en la base de datos. Verifique los datos ingresados.'
                }),
                content_type='application/json',
                status=400
            )
        
    except Exception as e:
        print(f"DEBUG - Error inesperado: {str(e)}")
        import traceback
        traceback.print_exc()
        return HttpResponse(
            json.dumps({'error': f'Error al editar la caja: {str(e)}'}),
            content_type='application/json',
            status=500
        )


# Vista AJAX para obtener sucursales por empresa
def obtenerSucursalesPorEmpresa(request):
    id_empresa = request.GET.get('id_empresa')
    sucursales = Sucursales.objects.filter(idempresa=id_empresa, estado=1).values('id_sucursal', 'nombre_sucursal')
    return JsonResponse(list(sucursales), safe=False)