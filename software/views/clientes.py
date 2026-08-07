from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils.html import escape
from django.views.decorators.csrf import csrf_exempt
from django.db import IntegrityError
from software.models.ClienteModel import Cliente
from software.models.Tipo_entidadModel import TipoEntidad
from software.models.RegionModel import Region
from software.models.ProvinciaModel import Provincia
from software.models.DistritoModel import Distrito
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos

# Importar la función de TokenPeru
from software.tokenperu_api import consultar_documento


from django.db.models import Q

def clientes(request):
    """Vista principal que lista todos los clientes activos (sin traer todos los datos)"""
    id2 = request.session.get('idtipousuario')
    if id2:
        permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
        tipos_entidad = TipoEntidad.objects.filter(estado=1)
        regiones = Region.objects.filter(estado=1)

        data = {
            'tipos_entidad': tipos_entidad,
            'regiones': regiones,
            'permisos': permisos
        }
        
        return render(request, 'clientes/clientes.html', data)
    else:
        return HttpResponse("<h1>No tiene acceso señor</h1>")

def api_listar_clientes(request):
    """API para proveer datos a DataTables mediante Server-Side Processing"""
    id2 = request.session.get('idtipousuario')
    if not id2:
        return JsonResponse({'error': 'No autorizado'}, status=401)

    # Parámetros de DataTables
    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '').strip()

    # Consulta base
    queryset = Cliente.objects.filter(estado=1).select_related('id_tipo_entidad', 'id_region', 'id_provincia', 'id_distrito')
    
    total_records = queryset.count()

    # Búsqueda
    if search_value:
        queryset = queryset.filter(
            Q(numdoc__icontains=search_value) |
            Q(razonsocial__icontains=search_value) |
            Q(nombre_comercial_cliente__icontains=search_value) |
            Q(telefono__icontains=search_value) |
            Q(id_tipo_entidad__tipo_entidad__icontains=search_value)
        )
    
    filtered_records = queryset.count()

    # Ordenamiento (DataTables envía order[0][column] y order[0][dir])
    # Mapeo de columnas según el frontend (índices)
    # 0: index (no se ordena en db usualmente), 1: tipo doc, 2: num doc, 3: razon social, 4: nombre comercial, 5: telefono, 6: direccion, 7: tipo entidad
    order_column_index = request.GET.get('order[0][column]')
    order_dir = request.GET.get('order[0][dir]', 'asc')
    
    if order_column_index:
        order_columns_map = {
            '2': 'numdoc',
            '3': 'razonsocial',
            '4': 'nombre_comercial_cliente',
            '5': 'telefono',
            '6': 'direccion',
            '7': 'id_tipo_entidad__tipo_entidad'
        }
        order_field = order_columns_map.get(order_column_index, 'idcliente')
        if order_dir == 'desc':
            order_field = '-' + order_field
        queryset = queryset.order_by(order_field)
    else:
        # Orden predeterminado (más recientes primero o id)
        queryset = queryset.order_by('-idcliente')

    # Paginación
    if length != -1:
        clientes_page = queryset[start:start + length]
    else:
        clientes_page = queryset

    # Construir data
    data = []
    # Usaremos start para calcular el índice real
    for idx, cliente in enumerate(clientes_page, start=start+1):
        # Determinar badge para tipo de entidad
        if cliente.id_tipo_entidad.id_tipo_entidad == 6:
            badge_tipo = '<span class="badge bg-info text-dark">RUC</span>'
        elif cliente.id_tipo_entidad.id_tipo_entidad == 1:
            badge_tipo = '<span class="badge bg-secondary text-dark">DNI</span>'
        else:
            badge_tipo = '<span class="badge bg-secondary text-dark">OTRO</span>'
        
        acciones = f"""
            <a type="button" class="btn btn-sm btn-outline-primary me-1 btn-abrir-editar" data-bs-toggle="modal"
                data-bs-target="#myModalEditar" title="Editar"
                data-id="{cliente.idcliente}"
                data-tipo-entidad="{cliente.id_tipo_entidad.id_tipo_entidad}"
                data-numdoc="{cliente.numdoc}"
                data-razonsocial="{escape(cliente.razonsocial)}"
                data-nombre-comercial="{escape(cliente.nombre_comercial_cliente or '')}"
                data-telefono="{escape(cliente.telefono or '')}"
                data-email="{escape(cliente.email or '')}"
                data-fecha-nacimiento="{cliente.fecha_nacimiento.strftime('%Y-%m-%d') if cliente.fecha_nacimiento else ''}"
                data-direccion="{escape(cliente.direccion or '')}"
                data-region="{cliente.id_region_id or ''}"
                data-provincia="{cliente.id_provincia_id or ''}"
                data-distrito="{cliente.id_distrito_id or ''}"
                data-conyuge-nombre="{escape(cliente.conyuge_nombre or '')}"
                data-conyuge-dni="{cliente.conyuge_dni or ''}">
                <i class="fa-solid fa-pen-to-square"></i>
            </a>
            <a href="/clientes/eliminar/{cliente.idcliente}" class="btn btn-sm btn-outline-danger eliminar"
                onclick="return confirmarEliminar('{cliente.idcliente}', this)" title="Eliminar">
                <i class="fa-solid fa-trash"></i>
            </a>
        """

        data.append({
            'DT_RowId': f'row-cliente-{cliente.idcliente}',
            'index': idx,
            'tipo_doc': badge_tipo,
            'numdoc': cliente.numdoc,
            'razonsocial': cliente.razonsocial,
            'nombrecomercial': cliente.nombre_comercial_cliente or '-',
            'telefono': cliente.telefono or '-',
            'direccion': cliente.direccion or '-',
            'tipoentidad': f'<span class="badge bg-secondary">{cliente.id_tipo_entidad.tipo_entidad}</span>',
            'acciones': acciones
        })

    return JsonResponse({
        'draw': draw,
        'recordsTotal': total_records,
        'recordsFiltered': filtered_records,
        'data': data
    })


def eliminar_cliente(request, id):
    """Eliminación lógica del cliente (cambia estado a 0)"""
    Cliente.objects.filter(idcliente=id).update(estado=0)
    return redirect('clientes')


def agregar_cliente(request):
    """Agregar un nuevo cliente con validaciones. Respuesta JSON."""
    try:
        numdoc = request.POST.get('numdocCliente', '').strip()
        razonsocial = request.POST.get('razonsocialCliente', '').strip()
        direccion = request.POST.get('direccionCliente', '').strip()
        telefono = request.POST.get('telefonoCliente', '').strip()
        nombre_comercial = request.POST.get('nombreComercialCliente', '').strip()
        email = request.POST.get('emailCliente', '').strip()
        fecha_nacimiento = request.POST.get('fechaNacimiento', '').strip()
        id_tipo_entidad = request.POST.get('tipoEntidadCliente', '').strip()
        
        conyuge_nombre = request.POST.get('conyugeNombre', '').strip()
        conyuge_dni = request.POST.get('conyugeDni', '').strip()

        id_region = request.POST.get('idRegion', '').strip()
        id_provincia = request.POST.get('idProvincia', '').strip()
        id_distrito = request.POST.get('idDistrito', '').strip()

        # 1. Validar tipo de entidad
        if not id_tipo_entidad:
            return JsonResponse({'ok': False, 'error': 'Debe seleccionar un tipo de entidad'}, status=400)
        
        try:
            tipo_entidad = TipoEntidad.objects.get(id_tipo_entidad=id_tipo_entidad, estado=1)
        except TipoEntidad.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'El tipo de entidad seleccionado no existe'}, status=400)
        
        # 2. Validar número de documento
        if not numdoc:
            return JsonResponse({'ok': False, 'error': 'El número de documento es obligatorio'}, status=400)
        if not numdoc.isdigit():
            return JsonResponse({'ok': False, 'error': 'El número de documento debe contener solo números'}, status=400)

        # Validación estricta por tipo (según TokenPeru en este proyecto)
        if str(id_tipo_entidad) == '1' and len(numdoc) not in (7, 8):
            return JsonResponse({'ok': False, 'error': 'Para DNI el número debe tener 7 u 8 dígitos'}, status=400)
        if str(id_tipo_entidad) == '6' and len(numdoc) != 11:
            return JsonResponse({'ok': False, 'error': 'Para RUC el número debe tener exactamente 11 dígitos'}, status=400)
        if str(id_tipo_entidad) not in ('1', '6') and (len(numdoc) < 7 or len(numdoc) > 11):
            return JsonResponse({'ok': False, 'error': 'El número de documento debe tener entre 7 y 11 dígitos'}, status=400)
        
        # 3. Validar que el documento no esté duplicado
        if Cliente.objects.filter(numdoc=numdoc, estado=1).exists():
            return JsonResponse({'ok': False, 'error': f'Ya existe un cliente con el documento {numdoc}'}, status=400)
        
        # 4. Validar razón social
        if not razonsocial:
            return JsonResponse({'ok': False, 'error': 'La razón social / nombre completo es obligatorio'}, status=400)
        
        if len(razonsocial) < 3:
            return JsonResponse({'ok': False, 'error': 'La razón social debe tener al menos 3 caracteres'}, status=400)
        
        # 5. Validar teléfono (si se proporciona)
        if telefono:
            if len(telefono) > 150:
                return JsonResponse({'ok': False, 'error': 'El teléfono no puede exceder los 150 caracteres'}, status=400)
        
        # 6. Validar longitudes máximas
        if len(razonsocial) > 255:
            return JsonResponse({'ok': False, 'error': 'La razón social no puede exceder 255 caracteres'}, status=400)
        
        if nombre_comercial and len(nombre_comercial) > 255:
            return JsonResponse({'ok': False, 'error': 'El nombre comercial no puede exceder 255 caracteres'}, status=400)
        
        if direccion and len(direccion) > 255:
            return JsonResponse({'ok': False, 'error': 'La dirección no puede exceder 255 caracteres'}, status=400)
        
        # ========== CREAR CLIENTE ==========
        cliente = Cliente.objects.create(
            numdoc=numdoc,
            razonsocial=razonsocial,
            direccion=direccion if direccion else '',
            telefono=telefono if telefono else '',
            email=email if email else None,
            fecha_nacimiento=fecha_nacimiento if fecha_nacimiento else None,
            nombre_comercial_cliente=nombre_comercial if nombre_comercial else '',
            conyuge_nombre=conyuge_nombre if conyuge_nombre else None,
            conyuge_dni=conyuge_dni if conyuge_dni else None,
            id_region_id=id_region if id_region else None,
            id_provincia_id=id_provincia if id_provincia else None,
            id_distrito_id=id_distrito if id_distrito else None,
            id_tipo_entidad=tipo_entidad,
            estado=1
        )

        # Mantener compatibilidad (ventas) devolviendo datos del cliente creado
        return JsonResponse({
            'ok': True,
            'success': 'Cliente creado correctamente',
            'idcliente': cliente.idcliente,
            'numdoc': cliente.numdoc,
            'razonsocial': cliente.razonsocial,
            'nombre_comercial': cliente.nombre_comercial_cliente or '',
            'direccion': cliente.direccion or '',
            'telefono': cliente.telefono or '',
            'email': cliente.email or '',
            'fecha_nacimiento': fecha_nacimiento if fecha_nacimiento else '',
            'tipo_entidad_nombre': tipo_entidad.tipo_entidad,
            'id_tipo_entidad': tipo_entidad.id_tipo_entidad,
            'id_region': cliente.id_region_id or '',
            'id_provincia': cliente.id_provincia_id or '',
            'id_distrito': cliente.id_distrito_id or '',
            'conyuge_nombre': cliente.conyuge_nombre or '',
            'conyuge_dni': cliente.conyuge_dni or ''
        }, status=200)
    except IntegrityError:
        return JsonResponse({'ok': False, 'error': 'Error de integridad en la base de datos. Verifique los datos ingresados.'}, status=400)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': f'Error al guardar el cliente: {str(e)}'}, status=500)


def editar_cliente(request):
    """Editar un cliente existente con validaciones. Respuesta JSON."""
    try:
        id = request.POST.get('idCliente', '').strip()
        numdoc = request.POST.get('numdocCliente', '').strip()
        razonsocial = request.POST.get('razonsocialCliente', '').strip()
        direccion = request.POST.get('direccionCliente', '').strip()
        telefono = request.POST.get('telefonoCliente', '').strip()
        email = request.POST.get('emailCliente', '').strip()
        fecha_nacimiento = request.POST.get('fechaNacimiento', '').strip()
        nombre_comercial = request.POST.get('nombreComercialCliente', '').strip()
        id_tipo_entidad = request.POST.get('tipoEntidadCliente', '').strip()
        
        conyuge_nombre = request.POST.get('conyugeNombre', '').strip()
        conyuge_dni = request.POST.get('conyugeDni', '').strip()

        id_region = request.POST.get('idRegion', '').strip()
        id_provincia = request.POST.get('idProvincia', '').strip()
        id_distrito = request.POST.get('idDistrito', '').strip()

        # ========== VALIDACIONES ==========
        
        # 1. Validar ID del cliente
        if not id:
            return JsonResponse({'ok': False, 'error': 'ID de cliente inválido'}, status=400)
        
        try:
            cliente = Cliente.objects.get(idcliente=id)
        except Cliente.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'El cliente no existe'}, status=400)
        
        # 2. Validar tipo de entidad
        if not id_tipo_entidad:
            return JsonResponse({'ok': False, 'error': 'Debe seleccionar un tipo de entidad'}, status=400)
        
        try:
            tipo_entidad = TipoEntidad.objects.get(id_tipo_entidad=id_tipo_entidad, estado=1)
        except TipoEntidad.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'El tipo de entidad seleccionado no existe'}, status=400)
        
        # 3. Validar número de documento
        if not numdoc:
            return JsonResponse({'ok': False, 'error': 'El número de documento es obligatorio'}, status=400)
        
        if not numdoc.isdigit():
            return JsonResponse({'ok': False, 'error': 'El número de documento debe contener solo números'}, status=400)

        if str(id_tipo_entidad) == '1' and len(numdoc) not in (7, 8):
            return JsonResponse({'ok': False, 'error': 'Para DNI el número debe tener 7 u 8 dígitos'}, status=400)
        if str(id_tipo_entidad) == '6' and len(numdoc) != 11:
            return JsonResponse({'ok': False, 'error': 'Para RUC el número debe tener exactamente 11 dígitos'}, status=400)
        if str(id_tipo_entidad) not in ('1', '6') and (len(numdoc) < 7 or len(numdoc) > 11):
            return JsonResponse({'ok': False, 'error': 'El número de documento debe tener entre 7 y 11 dígitos'}, status=400)
        
        # 4. Validar que el documento no esté duplicado (excepto el cliente actual)
        if Cliente.objects.filter(numdoc=numdoc, estado=1).exclude(idcliente=id).exists():
            return JsonResponse({'ok': False, 'error': f'Ya existe otro cliente con el documento {numdoc}'}, status=400)
        
        # 5. Validar razón social
        if not razonsocial:
            return JsonResponse({'ok': False, 'error': 'La razón social / nombre completo es obligatorio'}, status=400)
        
        if len(razonsocial) < 3:
            return JsonResponse({'ok': False, 'error': 'La razón social debe tener al menos 3 caracteres'}, status=400)
        
        # 6. Validar teléfono (si se proporciona)
        if telefono:
            if len(telefono) > 150:
                return JsonResponse({'ok': False, 'error': 'El teléfono no puede exceder los 150 caracteres'}, status=400)
        
        # 7. Validar longitudes máximas
        if len(razonsocial) > 255:
            return JsonResponse({'ok': False, 'error': 'La razón social no puede exceder 255 caracteres'}, status=400)
        
        if nombre_comercial and len(nombre_comercial) > 255:
            return JsonResponse({'ok': False, 'error': 'El nombre comercial no puede exceder 255 caracteres'}, status=400)
        
        if direccion and len(direccion) > 255:
            return JsonResponse({'ok': False, 'error': 'La dirección no puede exceder 255 caracteres'}, status=400)
        
        # ========== ACTUALIZAR CLIENTE ==========
        cliente.numdoc = numdoc
        cliente.razonsocial = razonsocial
        cliente.direccion = direccion if direccion else ''
        cliente.telefono = telefono if telefono else ''
        cliente.email = email if email else None
        cliente.fecha_nacimiento = fecha_nacimiento if fecha_nacimiento else None
        cliente.nombre_comercial_cliente = nombre_comercial if nombre_comercial else ''
        cliente.conyuge_nombre = conyuge_nombre if conyuge_nombre else None
        cliente.conyuge_dni = conyuge_dni if conyuge_dni else None
        
        cliente.id_region_id = id_region if id_region else None
        cliente.id_provincia_id = id_provincia if id_provincia else None
        cliente.id_distrito_id = id_distrito if id_distrito else None
        
        cliente.id_tipo_entidad = tipo_entidad
        
        cliente.save()

        return JsonResponse({
            'ok': True, 
            'success': 'Cliente actualizado correctamente',
            'idcliente': cliente.idcliente,
            'numdoc': cliente.numdoc,
            'razonsocial': cliente.razonsocial,
            'nombre_comercial': cliente.nombre_comercial_cliente or '',
            'direccion': cliente.direccion or '',
            'telefono': cliente.telefono or '',
            'email': cliente.email or '',
            'tipo_entidad_nombre': tipo_entidad.tipo_entidad,
            'id_tipo_entidad': tipo_entidad.id_tipo_entidad,
            'id_region': cliente.id_region_id or '',
            'id_provincia': cliente.id_provincia_id or '',
            'id_distrito': cliente.id_distrito_id or '',
            'conyuge_nombre': cliente.conyuge_nombre or '',
            'conyuge_dni': cliente.conyuge_dni or ''
        }, status=200)
        
    except IntegrityError:
        return JsonResponse({'ok': False, 'error': 'Error de integridad en la base de datos. Verifique los datos ingresados.'}, status=400)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': f'Error al editar el cliente: {str(e)}'}, status=500)


# ==================== NUEVA FUNCIÓN TOKENPERU ====================
@csrf_exempt
def autocompletar_cliente(request):
    """Vista AJAX para autocompletar datos de cliente desde APIs.net.pe"""
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
                'telefono': ''
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
                'telefono': ''
            }
        
        return JsonResponse(response_data)
        
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error: {str(e)}'})