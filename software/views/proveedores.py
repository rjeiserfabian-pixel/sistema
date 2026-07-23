
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.db import IntegrityError
from django.db.models import Q
from software.models.ProveedoresModel import Proveedor
from software.models.Tipo_entidadModel import TipoEntidad
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos

# Importar la función de TokenPeru
from software.tokenperu_api import consultar_documento


def proveedores(request):
    """Vista principal — carga instantánea sin traer registros (Server-Side Processing)"""
    id2 = request.session.get('idtipousuario')
    if id2:
        permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
        tipos_entidad = TipoEntidad.objects.filter(estado=1)

        data = {
            'tipos_entidad': tipos_entidad,
            'permisos': permisos
        }
        
        return render(request, 'proveedores/proveedores.html', data)
    else:
        return HttpResponse("<h1>No tiene acceso señor</h1>")


def api_listar_proveedores(request):
    """API para proveer datos a DataTables mediante Server-Side Processing"""
    id2 = request.session.get('idtipousuario')
    if not id2:
        return JsonResponse({'error': 'No autorizado'}, status=401)

    # Parámetros de DataTables
    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '').strip()

    # Consulta base — más recientes primero
    queryset = Proveedor.objects.filter(estado=1).select_related('id_tipo_entidad')

    total_records = queryset.count()

    # Búsqueda
    if search_value:
        queryset = queryset.filter(
            Q(numdoc__icontains=search_value) |
            Q(razonsocial__icontains=search_value) |
            Q(nombre_comercial__icontains=search_value) |
            Q(telefono__icontains=search_value) |
            Q(email__icontains=search_value) |
            Q(id_tipo_entidad__tipo_entidad__icontains=search_value)
        )

    filtered_records = queryset.count()

    # Ordenamiento
    order_column_index = request.GET.get('order[0][column]')
    order_dir = request.GET.get('order[0][dir]', 'asc')

    order_columns_map = {
        '2': 'numdoc',
        '3': 'razonsocial',
        '4': 'nombre_comercial',
        '5': 'telefono',
        '6': 'email',
        '7': 'direccion',
        '9': 'id_tipo_entidad__tipo_entidad',
    }

    if order_column_index and order_column_index in order_columns_map:
        order_field = order_columns_map[order_column_index]
        if order_dir == 'desc':
            order_field = '-' + order_field
        queryset = queryset.order_by(order_field)
    else:
        # Orden predeterminado: más recientes primero
        queryset = queryset.order_by('-idproveedor')

    # Paginación
    if length != -1:
        proveedores_page = queryset[start:start + length]
    else:
        proveedores_page = queryset

    # Construir data
    data = []
    for idx, proveedor in enumerate(proveedores_page, start=start + 1):
        # Badge tipo documento
        tipo_doc = proveedor.tipo_documento
        if proveedor.id_tipo_entidad.id_tipo_entidad == 6:
            badge_tipo = f'<span class="badge bg-info text-dark">{tipo_doc}</span>'
        elif proveedor.id_tipo_entidad.id_tipo_entidad == 1:
            badge_tipo = f'<span class="badge bg-secondary text-dark">{tipo_doc}</span>'
        else:
            badge_tipo = f'<span class="badge bg-secondary text-dark">{tipo_doc}</span>'

        acciones = f"""
            <button type="button" class="btn btn-sm btn-outline-primary me-1 btn-editar"
                data-id="{proveedor.idproveedor}"
                data-numdoc="{proveedor.numdoc}"
                data-razonsocial="{proveedor.razonsocial}"
                data-nombrecomercial="{proveedor.nombre_comercial or ''}"
                data-telefono="{proveedor.telefono or ''}"
                data-email="{proveedor.email or ''}"
                data-direccion="{proveedor.direccion or ''}"
                data-departamento="{proveedor.departamento or ''}"
                data-provincia="{proveedor.provincia or ''}"
                data-distrito="{proveedor.distrito or ''}"
                data-idtipoentidad="{proveedor.id_tipo_entidad.id_tipo_entidad}"
                title="Editar">
                <i class="fa-solid fa-pen-to-square"></i>
            </button>
            <a href="/proveedores/eliminar/{proveedor.idproveedor}/" class="btn btn-sm btn-outline-danger eliminar"
                onclick="return confirmarEliminar('{proveedor.idproveedor}', this)" title="Eliminar">
                <i class="fa-solid fa-trash"></i>
            </a>
        """

        data.append({
            'DT_RowId': f'row-proveedor-{proveedor.idproveedor}',
            'index': idx,
            'tipo_doc': badge_tipo,
            'numdoc': proveedor.numdoc,
            'razonsocial': proveedor.razonsocial,
            'nombrecomercial': proveedor.nombre_comercial or '-',
            'telefono': proveedor.telefono or '-',
            'email': proveedor.email or '-',
            'direccion': proveedor.direccion or '-',
            'ubicacion': proveedor.ubicacion_completa or '-',
            'tipoentidad': f'<span class="badge bg-secondary">{proveedor.id_tipo_entidad.tipo_entidad}</span>',
            'acciones': acciones
        })

    return JsonResponse({
        'draw': draw,
        'recordsTotal': total_records,
        'recordsFiltered': filtered_records,
        'data': data
    })


def eliminar_proveedor(request, id):
    """Eliminación lógica del proveedor (cambia estado a 0)"""
    Proveedor.objects.filter(idproveedor=id).update(estado=0)
    return redirect('proveedores')


def agregar_proveedor(request):
    """Agregar un nuevo proveedor. Validaciones estilo Clientes. Respuesta JSON."""
    try:
        numdoc = (request.POST.get('numdocProveedor') or '').strip()
        razonsocial = (request.POST.get('razonsocialProveedor') or '').strip()
        direccion = (request.POST.get('direccionProveedor') or '').strip()
        telefono = (request.POST.get('telefonoProveedor') or '').strip()
        email = (request.POST.get('emailProveedor') or '').strip()
        nombre_comercial = (request.POST.get('nombreComercialProveedor') or '').strip()
        departamento = (request.POST.get('departamentoProveedor') or '').strip()
        provincia = (request.POST.get('provinciaProveedor') or '').strip()
        distrito = (request.POST.get('distritoProveedor') or '').strip()
        id_tipo_entidad = (request.POST.get('tipoEntidadProveedor') or '').strip()

        if not id_tipo_entidad:
            return JsonResponse({'ok': False, 'error': 'Debe seleccionar un tipo de entidad'}, status=400)
        try:
            tipo_entidad = TipoEntidad.objects.get(id_tipo_entidad=id_tipo_entidad, estado=1)
        except TipoEntidad.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'El tipo de entidad seleccionado no existe'}, status=400)

        if not numdoc:
            return JsonResponse({'ok': False, 'error': 'El número de documento es obligatorio'}, status=400)
        if not numdoc.isdigit():
            return JsonResponse({'ok': False, 'error': 'El número de documento debe contener solo números'}, status=400)

        if str(id_tipo_entidad) == '1' and len(numdoc) != 8:
            return JsonResponse({'ok': False, 'error': 'Para DNI el número debe tener exactamente 8 dígitos'}, status=400)
        if str(id_tipo_entidad) == '6' and len(numdoc) != 11:
            return JsonResponse({'ok': False, 'error': 'Para RUC el número debe tener exactamente 11 dígitos'}, status=400)
        if str(id_tipo_entidad) not in ('1', '6') and (len(numdoc) < 8 or len(numdoc) > 11):
            return JsonResponse({'ok': False, 'error': 'El número de documento debe tener entre 8 y 11 dígitos'}, status=400)

        # Unicidad solo entre activos
        if Proveedor.objects.filter(numdoc=numdoc, estado=1).exists():
            return JsonResponse({'ok': False, 'error': f'Ya existe un proveedor con el documento {numdoc}'}, status=400)

        if not razonsocial:
            return JsonResponse({'ok': False, 'error': 'La razón social / nombre completo es obligatorio'}, status=400)
        if len(razonsocial) < 3:
            return JsonResponse({'ok': False, 'error': 'La razón social debe tener al menos 3 caracteres'}, status=400)
        if len(razonsocial) > 255:
            return JsonResponse({'ok': False, 'error': 'La razón social no puede exceder 255 caracteres'}, status=400)

        # Teléfono estilo Clientes
        if telefono:
            if len(telefono) > 150:
                return JsonResponse({'ok': False, 'error': 'El teléfono no puede exceder los 150 caracteres'}, status=400)

        if nombre_comercial and len(nombre_comercial) > 255:
            return JsonResponse({'ok': False, 'error': 'El nombre comercial no puede exceder 255 caracteres'}, status=400)
        if direccion and len(direccion) > 255:
            return JsonResponse({'ok': False, 'error': 'La dirección no puede exceder 255 caracteres'}, status=400)
        if email and len(email) > 255:
            return JsonResponse({'ok': False, 'error': 'El correo electrónico no puede exceder 255 caracteres'}, status=400)
        if departamento and len(departamento) > 100:
            return JsonResponse({'ok': False, 'error': 'El departamento no puede exceder 100 caracteres'}, status=400)
        if provincia and len(provincia) > 100:
            return JsonResponse({'ok': False, 'error': 'La provincia no puede exceder 100 caracteres'}, status=400)
        if distrito and len(distrito) > 100:
            return JsonResponse({'ok': False, 'error': 'El distrito no puede exceder 100 caracteres'}, status=400)

        proveedor = Proveedor.objects.create(
            numdoc=numdoc,
            razonsocial=razonsocial,
            direccion=direccion,
            telefono=telefono if telefono else None,
            email=email if email else None,
            nombre_comercial=nombre_comercial if nombre_comercial else None,
            departamento=departamento if departamento else None,
            provincia=provincia if provincia else None,
            distrito=distrito if distrito else None,
            id_tipo_entidad=tipo_entidad,
            estado=1
        )
        
        # Compatibilidad (compras) + éxito
        return JsonResponse({
            'ok': True,
            'success': 'Proveedor creado correctamente',
            'id': proveedor.idproveedor,
            'numdoc': proveedor.numdoc,
            'razonsocial': proveedor.razonsocial,
            'tipo_documento': proveedor.tipo_documento,
            'nombre_comercial': proveedor.nombre_comercial or '',
            'telefono': proveedor.telefono or '',
            'email': proveedor.email or '',
            'direccion': proveedor.direccion or '',
            'departamento': proveedor.departamento or '',
            'provincia': proveedor.provincia or '',
            'distrito': proveedor.distrito or '',
            'id_tipo_entidad': proveedor.id_tipo_entidad.id_tipo_entidad,
            'tipo_entidad_nombre': proveedor.id_tipo_entidad.tipo_entidad,
            'ubicacion_completa': proveedor.ubicacion_completa
        }, status=200)
        
    except IntegrityError as e:
        print(f"IntegrityError en agregar_proveedor: {e}")
        return JsonResponse({'ok': False, 'error': f'Error de integridad en la base de datos: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': f'Error al guardar el proveedor: {str(e)}'}, status=500)


def editar_proveedor(request):
    """Editar un proveedor existente. Validaciones estilo Clientes. Respuesta JSON."""
    try:
        id = (request.POST.get('idProveedor') or '').strip()
        numdoc = (request.POST.get('numdocProveedor') or '').strip()
        razonsocial = (request.POST.get('razonsocialProveedor') or '').strip()
        direccion = (request.POST.get('direccionProveedor') or '').strip()
        telefono = (request.POST.get('telefonoProveedor') or '').strip()
        email = (request.POST.get('emailProveedor') or '').strip()
        nombre_comercial = (request.POST.get('nombreComercialProveedor') or '').strip()
        departamento = (request.POST.get('departamentoProveedor') or '').strip()
        provincia = (request.POST.get('provinciaProveedor') or '').strip()
        distrito = (request.POST.get('distritoProveedor') or '').strip()
        id_tipo_entidad = (request.POST.get('tipoEntidadProveedor') or '').strip()

        if not id:
            return JsonResponse({'ok': False, 'error': 'ID de proveedor inválido'}, status=400)
        try:
            proveedor = Proveedor.objects.get(idproveedor=id)
        except Proveedor.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'El proveedor no existe'}, status=400)

        if not id_tipo_entidad:
            return JsonResponse({'ok': False, 'error': 'Debe seleccionar un tipo de entidad'}, status=400)
        try:
            tipo_entidad = TipoEntidad.objects.get(id_tipo_entidad=id_tipo_entidad, estado=1)
        except TipoEntidad.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'El tipo de entidad seleccionado no existe'}, status=400)

        if not numdoc:
            return JsonResponse({'ok': False, 'error': 'El número de documento es obligatorio'}, status=400)
        if not numdoc.isdigit():
            return JsonResponse({'ok': False, 'error': 'El número de documento debe contener solo números'}, status=400)

        if str(id_tipo_entidad) == '1' and len(numdoc) != 8:
            return JsonResponse({'ok': False, 'error': 'Para DNI el número debe tener exactamente 8 dígitos'}, status=400)
        if str(id_tipo_entidad) == '6' and len(numdoc) != 11:
            return JsonResponse({'ok': False, 'error': 'Para RUC el número debe tener exactamente 11 dígitos'}, status=400)
        if str(id_tipo_entidad) not in ('1', '6') and (len(numdoc) < 8 or len(numdoc) > 11):
            return JsonResponse({'ok': False, 'error': 'El número de documento debe tener entre 8 y 11 dígitos'}, status=400)

        if Proveedor.objects.filter(numdoc=numdoc, estado=1).exclude(idproveedor=id).exists():
            return JsonResponse({'ok': False, 'error': f'Ya existe otro proveedor con el documento {numdoc}'}, status=400)

        if not razonsocial:
            return JsonResponse({'ok': False, 'error': 'La razón social / nombre completo es obligatorio'}, status=400)
        if len(razonsocial) < 3:
            return JsonResponse({'ok': False, 'error': 'La razón social debe tener al menos 3 caracteres'}, status=400)
        if len(razonsocial) > 255:
            return JsonResponse({'ok': False, 'error': 'La razón social no puede exceder 255 caracteres'}, status=400)

        if telefono:
            if len(telefono) > 150:
                return JsonResponse({'ok': False, 'error': 'El teléfono no puede exceder los 150 caracteres'}, status=400)

        if nombre_comercial and len(nombre_comercial) > 255:
            return JsonResponse({'ok': False, 'error': 'El nombre comercial no puede exceder 255 caracteres'}, status=400)
        if direccion and len(direccion) > 255:
            return JsonResponse({'ok': False, 'error': 'La dirección no puede exceder 255 caracteres'}, status=400)
        if email and len(email) > 255:
            return JsonResponse({'ok': False, 'error': 'El correo electrónico no puede exceder 255 caracteres'}, status=400)
        if departamento and len(departamento) > 100:
            return JsonResponse({'ok': False, 'error': 'El departamento no puede exceder 100 caracteres'}, status=400)
        if provincia and len(provincia) > 100:
            return JsonResponse({'ok': False, 'error': 'La provincia no puede exceder 100 caracteres'}, status=400)
        if distrito and len(distrito) > 100:
            return JsonResponse({'ok': False, 'error': 'El distrito no puede exceder 100 caracteres'}, status=400)

        proveedor.numdoc = numdoc
        proveedor.razonsocial = razonsocial
        proveedor.direccion = direccion
        proveedor.telefono = telefono if telefono else None
        proveedor.email = email if email else None
        proveedor.nombre_comercial = nombre_comercial if nombre_comercial else None
        proveedor.departamento = departamento if departamento else None
        proveedor.provincia = provincia if provincia else None
        proveedor.distrito = distrito if distrito else None
        proveedor.id_tipo_entidad = tipo_entidad
        proveedor.save()

        return JsonResponse({
            'ok': True, 
            'success': 'Proveedor actualizado correctamente',
            'id': proveedor.idproveedor,
            'numdoc': proveedor.numdoc,
            'razonsocial': proveedor.razonsocial,
            'tipo_documento': proveedor.tipo_documento,
            'nombre_comercial': proveedor.nombre_comercial or '',
            'telefono': proveedor.telefono or '',
            'email': proveedor.email or '',
            'direccion': proveedor.direccion or '',
            'departamento': proveedor.departamento or '',
            'provincia': proveedor.provincia or '',
            'distrito': proveedor.distrito or '',
            'id_tipo_entidad': proveedor.id_tipo_entidad.id_tipo_entidad,
            'tipo_entidad_nombre': proveedor.id_tipo_entidad.tipo_entidad,
            'ubicacion_completa': proveedor.ubicacion_completa
        }, status=200)

    except IntegrityError:
        return JsonResponse({'ok': False, 'error': 'Error de integridad en la base de datos. Verifique los datos ingresados.'}, status=400)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': f'Error al editar el proveedor: {str(e)}'}, status=500)


# ==================== FUNCIÓN TOKENPERU ====================
@csrf_exempt
def autocompletar_proveedor(request):
    """Vista AJAX para autocompletar datos de proveedor desde APIs.net.pe"""
    numero = request.GET.get('numero', '')
    
    if not numero:
        return JsonResponse({
            'success': False,
            'error': 'Se requiere el número de documento'
        })
    
    try:
        # Consultar APIs.net.pe
        resultado = consultar_documento(numero)
        
        # Formatear respuesta según tipo de documento
        if resultado['tipo_documento'] == 'DNI':
            # Para DNI: Razón Social y Nombre Comercial son iguales
            nombre_completo = resultado.get('nombre_completo', '')
            
            response_data = {
                'success': True,
                'tipo': 'DNI',
                'id_tipo_entidad': 1,
                'numdoc': resultado.get('dni', numero),
                'razonsocial': nombre_completo,
                'nombre_comercial': nombre_completo,
                'direccion': resultado.get('direccion', ''),
                'telefono': '',
                'email': '',
                'departamento': '',
                'provincia': '',
                'distrito': ''
            }
        else:  # RUC
            # Para RUC: Razón Social y Nombre Comercial son diferentes
            response_data = {
                'success': True,
                'tipo': 'RUC',
                'id_tipo_entidad': 6,
                'numdoc': resultado.get('ruc', numero),
                'razonsocial': resultado.get('razon_social', ''),
                'nombre_comercial': resultado.get('nombre_comercial', ''),
                'direccion': resultado.get('direccion', ''),
                'departamento': resultado.get('departamento', ''),
                'provincia': resultado.get('provincia', ''),
                'distrito': resultado.get('distrito', ''),
                'ubigeo': resultado.get('ubigeo', ''),
                'estado': resultado.get('estado', ''),
                'condicion': resultado.get('condicion', ''),
                'telefono': '',
                'email': ''
            }
        
        return JsonResponse(response_data)
        
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error: {str(e)}'})
    

def obtener_ultimo_proveedor(request):
    """Obtiene el último proveedor registrado para selección automática"""
    try:
        ultimo_proveedor = Proveedor.objects.filter(estado=1).order_by('-idproveedor').first()
        
        if ultimo_proveedor:
            return JsonResponse({
                'success': True,
                'id': ultimo_proveedor.idproveedor,
                'razonsocial': ultimo_proveedor.razonsocial,
                'numdoc': ultimo_proveedor.numdoc
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'No se encontró el proveedor'
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


