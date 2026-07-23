from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.db import IntegrityError
from django.core.paginator import Paginator
from django.db.models import Q
from software.models.GaranteModel import Garante
from software.models.ClienteModel import Cliente
from software.models.RegionModel import Region
from software.models.ProvinciaModel import Provincia
from software.models.DistritoModel import Distrito
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos

# Importar la función de TokenPeru
from software.tokenperu_api import consultar_documento

def garantes(request):
    """Vista principal que lista todos los garantes activos con su cliente asociado"""
    id2 = request.session.get('idtipousuario')
    if id2:
        permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
        # Obtenemos todos los clientes activos para los selectores de los modales
        clientes_activos = Cliente.objects.filter(estado=1).order_by('razonsocial')
        regiones = Region.objects.filter(estado=1)

        data = {
            'garantes_registros': [],
            'clientes_activos': clientes_activos,
            'regiones': regiones,
            'permisos': permisos
        }
        
        return render(request, 'garantes/garantes.html', data)
    else:
        return HttpResponse("<h1>No tiene acceso señor</h1>")


def api_listar_garantes(request):
    """API para listar garantes de forma paginada y con búsqueda AJAX"""
    id2 = request.session.get('idtipousuario')
    if not id2:
        return JsonResponse({'error': 'No autorizado'}, status=401)

    page = request.GET.get('page', 1)
    search = request.GET.get('search', '').strip()

    garantes = Garante.objects.filter(estado=1).select_related('idcliente', 'id_region', 'id_provincia', 'id_distrito').order_by('-id_garante')

    if search:
        garantes = garantes.filter(
            Q(numdoc__icontains=search) |
            Q(nombre__icontains=search) |
            Q(idcliente__razonsocial__icontains=search)
        )

    paginator = Paginator(garantes, 10)
    try:
        garantes_page = paginator.page(page)
    except Exception:
        garantes_page = paginator.page(1)

    data = []
    for g in garantes_page:
        data.append({
            'id_garante': g.id_garante,
            'numdoc': g.numdoc,
            'nombre': g.nombre,
            'cliente_nombre': g.idcliente.razonsocial if g.idcliente else '',
            'idcliente': g.idcliente.idcliente if g.idcliente else '',
            'telefono': g.telefono if g.telefono else '-',
            'direccion': g.direccion if g.direccion else '-',
            'conyuge_nombre': g.conyuge_nombre if g.conyuge_nombre else '',
            'conyuge_dni': g.conyuge_dni if g.conyuge_dni else '',
            'id_region': g.id_region.id_region if g.id_region else '',
            'id_provincia': g.id_provincia.id_provincia if g.id_provincia else '',
            'id_distrito': g.id_distrito.id_distrito if g.id_distrito else ''
        })

    pagination = {
        'current_page': garantes_page.number,
        'total_pages': paginator.num_pages,
        'has_previous': garantes_page.has_previous(),
        'has_next': garantes_page.has_next(),
    }

    return JsonResponse({'data': data, 'pagination': pagination})


def eliminar_garante(request, id):
    """Eliminación lógica del garante (cambia estado a 0)"""
    Garante.objects.filter(id_garante=id).update(estado=0)
    return redirect('garantes')


def agregar_garante(request):
    """Agregar un nuevo garante relacionado a un cliente con validaciones. Respuesta JSON."""
    try:
        numdoc = request.POST.get('numdocGarante', '').strip()
        nombre = request.POST.get('nombreGarante', '').strip()
        direccion = request.POST.get('direccionGarante', '').strip()
        telefono = request.POST.get('telefonoGarante', '').strip()
        idcliente = request.POST.get('idcliente', '').strip()
        
        id_region = request.POST.get('idRegion', '').strip()
        id_provincia = request.POST.get('idProvincia', '').strip()
        id_distrito = request.POST.get('idDistrito', '').strip()
        
        conyuge_nombre = request.POST.get('conyuge_nombre', '').strip()
        conyuge_dni = request.POST.get('conyuge_dni', '').strip()
        
        # 1. Validar cliente
        if not idcliente:
            return JsonResponse({'ok': False, 'error': 'Debe seleccionar un cliente'}, status=400)
        
        try:
            cliente = Cliente.objects.get(idcliente=idcliente, estado=1)
        except Cliente.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'El cliente seleccionado no es válido'}, status=400)

        # 2. Validar número de documento
        if not numdoc:
            return JsonResponse({'ok': False, 'error': 'El número de documento es obligatorio'}, status=400)
        if not numdoc.isdigit():
            return JsonResponse({'ok': False, 'error': 'El número de documento debe contener solo números'}, status=400)
        if len(numdoc) != 8:
            return JsonResponse({'ok': False, 'error': 'Para DNI el número debe tener exactamente 8 dígitos'}, status=400)
        
        # 3. Validar que el documento no esté duplicado
        if Garante.objects.filter(numdoc=numdoc, estado=1).exists():
            return JsonResponse({'ok': False, 'error': f'Ya existe un garante con el documento {numdoc}'}, status=400)
        
        # 4. Validar nombre
        if not nombre:
            return JsonResponse({'ok': False, 'error': 'El nombre completo es obligatorio'}, status=400)
        if len(nombre) < 3:
            return JsonResponse({'ok': False, 'error': 'El nombre debe tener al menos 3 caracteres'}, status=400)
        
        # 5. Validar teléfono (si se proporciona)
        if telefono:
            if not telefono.isdigit():
                return JsonResponse({'ok': False, 'error': 'El teléfono debe contener solo números'}, status=400)
            if len(telefono) < 7 or len(telefono) > 10:
                return JsonResponse({'ok': False, 'error': 'El teléfono debe tener entre 7 y 10 dígitos'}, status=400)
        
        # ========== CREAR GARANTE ==========
        garante = Garante.objects.create(
            idcliente=cliente,
            numdoc=numdoc,
            nombre=nombre,
            direccion=direccion if direccion else '',
            telefono=telefono if telefono else '',
            id_region_id=id_region if id_region else None,
            id_provincia_id=id_provincia if id_provincia else None,
            id_distrito_id=id_distrito if id_distrito else None,
            conyuge_nombre=conyuge_nombre if conyuge_nombre else None,
            conyuge_dni=conyuge_dni if conyuge_dni else None,
            estado=1
        )

        return JsonResponse({
            'ok': True,
            'success': 'Garante creado correctamente',
            'id_garante': garante.id_garante,
            'numdoc': garante.numdoc,
            'nombre': garante.nombre,
            'cliente': cliente.razonsocial,
            'direccion': garante.direccion or '',
            'telefono': garante.telefono or ''
        }, status=200)
        
    except IntegrityError:
        return JsonResponse({'ok': False, 'error': 'Error de integridad en la base de datos.'}, status=400)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': f'Error al guardar el garante: {str(e)}'}, status=500)


def editar_garante(request):
    """Editar un garante existente relacionado a un cliente. Respuesta JSON."""
    try:
        id = request.POST.get('idGarante', '').strip()
        numdoc = request.POST.get('numdocGarante', '').strip()
        nombre = request.POST.get('nombreGarante', '').strip()
        direccion = request.POST.get('direccionGarante', '').strip()
        telefono = request.POST.get('telefonoGarante', '').strip()
        idcliente = request.POST.get('idcliente', '').strip()

        id_region = request.POST.get('idRegion', '').strip()
        id_provincia = request.POST.get('idProvincia', '').strip()
        id_distrito = request.POST.get('idDistrito', '').strip()

        conyuge_nombre = request.POST.get('conyuge_nombre', '').strip()
        conyuge_dni = request.POST.get('conyuge_dni', '').strip()

        # ========== VALIDACIONES ==========
        
        if not id:
            return JsonResponse({'ok': False, 'error': 'ID de garante inválido'}, status=400)
        
        try:
            garante = Garante.objects.get(id_garante=id)
        except Garante.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'El garante no existe'}, status=400)
        
        # 1. Validar cliente
        if not idcliente:
            return JsonResponse({'ok': False, 'error': 'Debe seleccionar un cliente'}, status=400)
        
        try:
            cliente = Cliente.objects.get(idcliente=idcliente, estado=1)
        except Cliente.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'El cliente seleccionado no es válido'}, status=400)

        # 2. Validar número de documento
        if not numdoc:
            return JsonResponse({'ok': False, 'error': 'El número de documento es obligatorio'}, status=400)
        if not numdoc.isdigit():
            return JsonResponse({'ok': False, 'error': 'El número de documento debe contener solo números'}, status=400)
        if len(numdoc) != 8:
            return JsonResponse({'ok': False, 'error': 'Para DNI el número debe tener exactamente 8 dígitos'}, status=400)
        
        if Garante.objects.filter(numdoc=numdoc, estado=1).exclude(id_garante=id).exists():
            return JsonResponse({'ok': False, 'error': f'Ya existe otro garante con el documento {numdoc}'}, status=400)
        
        # 3. Validar nombre
        if not nombre:
            return JsonResponse({'ok': False, 'error': 'El nombre completo es obligatorio'}, status=400)
        if len(nombre) < 3:
            return JsonResponse({'ok': False, 'error': 'El nombre debe tener al menos 3 caracteres'}, status=400)
        
        if telefono:
            if not telefono.isdigit():
                return JsonResponse({'ok': False, 'error': 'El teléfono debe contener solo números'}, status=400)
            if len(telefono) < 7 or len(telefono) > 10:
                return JsonResponse({'ok': False, 'error': 'El teléfono debe tener entre 7 y 10 dígitos'}, status=400)
        
        # ========== ACTUALIZAR GARANTE ==========
        garante.idcliente = cliente
        garante.numdoc = numdoc
        garante.nombre = nombre
        garante.direccion = direccion if direccion else ''
        garante.telefono = telefono if telefono else ''
        
        garante.id_region_id = id_region if id_region else None
        garante.id_provincia_id = id_provincia if id_provincia else None
        garante.id_distrito_id = id_distrito if id_distrito else None
        
        garante.conyuge_nombre = conyuge_nombre if conyuge_nombre else None
        garante.conyuge_dni = conyuge_dni if conyuge_dni else None
        
        garante.save()

        return JsonResponse({'ok': True, 'success': 'Garante actualizado correctamente'}, status=200)
        
    except IntegrityError:
        return JsonResponse({'ok': False, 'error': 'Error de integridad en la base de datos.'}, status=400)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': f'Error al editar el garante: {str(e)}'}, status=500)


@csrf_exempt
def autocompletar_garante(request):
    """Vista AJAX para autocompletar datos de garante desde APIs.net.pe"""
    numero = request.GET.get('numero', '')
    
    if not numero:
        return JsonResponse({
            'success': False,
            'error': 'Se requiere el número de documento'
        })
    
    try:
        resultado = consultar_documento(numero)
        
        if resultado['tipo_documento'] == 'DNI':
            nombre_completo = resultado.get('nombre_completo', '')
            
            response_data = {
                'success': True,
                'numdoc': resultado.get('dni', numero),
                'nombre': nombre_completo,
                'direccion': resultado.get('direccion', ''),
                'telefono': ''
            }
            return JsonResponse(response_data)
        else:
            return JsonResponse({'success': False, 'error': 'Solo se permiten DNIs para garantes'})
        
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error: {str(e)}'})
