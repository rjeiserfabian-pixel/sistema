from django.shortcuts import redirect, render, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
from decimal import Decimal
import os
import cloudinary.uploader
from software.models.empresaModel import Empresa
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos
from software.models.RegionModel import Region
from software.models.ProvinciaModel import Provincia
from software.models.DistritoModel import Distrito


def configuracion(request):
    """
    Vista principal de configuración de empresa.
    Muestra la información de todas las empresas registradas.
    """
    id_tipo_usuario = request.session.get('idtipousuario')
    
    if not id_tipo_usuario:
        return render(request, 'error.html', {
            'mensaje': 'No tiene acceso. Por favor, inicie sesión.'
        })
    
    try:
        # Obtener permisos del usuario
        permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id_tipo_usuario)
        
        # Obtener datos de empresa
        empresas = Empresa.objects.all()
        
        # Obtener regiones para los selectores de ubicación (solo activas)
        regiones = Region.objects.filter(estado=1).order_by('nombre_region')
        
        # Obtener modo de desarrollo de la primera empresa
        modo = empresas.first().mododev if empresas.exists() else 0
        
        context = {
            'empresas': empresas,
            'regiones': regiones,
            'modo': modo,
            'permisos': permisos
        }
        
        return render(request, 'configuracion/configuracion.html', context)
    
    except Exception as e:
        messages.error(request, f'Error al cargar la configuración: {str(e)}')
        return render(request, 'configuracion/configuracion.html', {
            'empresas': [],
            'modo': 0,
            'permisos': []
        })


def editarEmpresa(request):
    """
    Edita la información de una empresa.
    Método: POST
    Incluye manejo de archivo de logo, slogan y publicidad.
    """
    if request.method != 'POST':
        messages.warning(request, 'Método no permitido')
        return redirect('configuracion')
    
    try:
        # Obtener datos del formulario
        idempresa = request.POST.get('idempresa')
        ruc = request.POST.get('ruc', '').strip()
        razon_social = request.POST.get('razonSocial', '').strip()
        nombre_comercial = request.POST.get('nombreComercia', '').strip()
        direccion = request.POST.get('Direccion', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        user_sec = request.POST.get('user', '').strip()
        password_sec = request.POST.get('password', '').strip()
        ubigueo_value = request.POST.get('ubigueo', '').strip()
        
        # Nuevos campos
        slogan = request.POST.get('slogan', '').strip()
        pagina = request.POST.get('pagina', '').strip()
        publicidad = request.POST.get('publicidad', '').strip()
        
        gerente_general = request.POST.get('gerenteGeneral', '').strip()
        dni_gerente = request.POST.get('dniGerente', '').strip()
        celular_gerente = request.POST.get('celularGerente', '').strip()
        
        # UltraMsg (WhatsApp)
        ultramsg_instance = request.POST.get('ultramsg_instance', '').strip()
        ultramsg_token = request.POST.get('ultramsg_token', '').strip()
        
        # Validaciones básicas
        if not idempresa:
            messages.error(request, 'ID de empresa no proporcionado')
            return redirect('configuracion')
        
        if not ruc or len(ruc) != 11 or not ruc.isdigit():
            messages.error(request, 'El RUC debe tener 11 dígitos numéricos')
            return redirect('configuracion')
        
        if not razon_social:
            messages.error(request, 'La razón social es obligatoria')
            return redirect('configuracion')
        
        if not nombre_comercial:
            messages.error(request, 'El nombre comercial es obligatorio')
            return redirect('configuracion')
        
        if not direccion:
            messages.error(request, 'La dirección es obligatoria')
            return redirect('configuracion')
        
        # Usar transacción para asegurar integridad de datos
        with transaction.atomic():
            # Obtener la empresa
            empresa = get_object_or_404(Empresa, idempresa=idempresa)
            
            # Actualizar campos básicos
            empresa.ruc = ruc
            empresa.razonsocial = razon_social.upper()
            empresa.nombrecomercial = nombre_comercial
            empresa.direccion = direccion
            empresa.telefono = telefono if telefono else None
            empresa.usersec = user_sec if user_sec else None
            empresa.passwordsec = password_sec if password_sec else None
            empresa.ubigueo = ubigueo_value if ubigueo_value else None
            
            # Actualizar campos nuevos
            empresa.slogan = slogan if slogan else None
            empresa.pagina = pagina if pagina else None
            empresa.publicidad = publicidad if publicidad else None
            empresa.gerente_general = gerente_general if gerente_general else None
            empresa.dni_gerente = dni_gerente if dni_gerente else None
            empresa.celular_gerente = celular_gerente if celular_gerente else None
            
            # UltraMsg
            empresa.ultramsg_instance = ultramsg_instance if ultramsg_instance else None
            empresa.ultramsg_token = ultramsg_token if ultramsg_token else None
            empresa.agradecimiento = request.POST.get('agradecimiento', '').strip() or None
            
            condiciones_comerciales = request.POST.get('condiciones_comerciales', '').strip()
            empresa.condiciones_comerciales = condiciones_comerciales if condiciones_comerciales else None
            
            # Gmails
            gmail_1 = request.POST.get('gmail_1', '').strip()
            gmail_2 = request.POST.get('gmail_2', '').strip()
            empresa.gmail_1 = gmail_1 if gmail_1 else None
            empresa.gmail_2 = gmail_2 if gmail_2 else None
            
            # Ubicación del Gerente
            direccion_gerente = request.POST.get('direccionGerente', '').strip()
            id_region_gerente = request.POST.get('idRegionGerente')
            id_provincia_gerente = request.POST.get('idProvinciaGerente')
            id_distrito_gerente = request.POST.get('idDistritoGerente')
            
            empresa.direccion_gerente = direccion_gerente if direccion_gerente else None
            
            if id_region_gerente:
                empresa.id_region_gerente = Region.objects.get(id_region=id_region_gerente)
            else:
                empresa.id_region_gerente = None
                
            if id_provincia_gerente:
                empresa.id_provincia_gerente = Provincia.objects.get(id_provincia=id_provincia_gerente)
            else:
                empresa.id_provincia_gerente = None
                
            if id_distrito_gerente:
                empresa.id_distrito_gerente = Distrito.objects.get(id_distrito=id_distrito_gerente)
            else:
                empresa.id_distrito_gerente = None
            
            # Actualizar Parámetros Tributarios
            igv = request.POST.get('igv')
            if igv:
                empresa.igv = Decimal(igv)
            
            icbper = request.POST.get('icbper')
            if icbper:
                empresa.icbper = Decimal(icbper)
            
            isc = request.POST.get('isc')
            if isc:
                empresa.isc = Decimal(isc)
            
            afectacion = request.POST.get('afectacion_sunat')
            if afectacion:
                empresa.afectacion_sunat = int(afectacion)
            
            # Actualizar Interés Mora
            empresa.cobrar_mora = (request.POST.get('cobrarMora') == 'on')
            
            interes_mora_base = request.POST.get('interesMoraBase')
            if interes_mora_base:
                empresa.interes_mora_base = Decimal(interes_mora_base)
            
            dias_mora_inicio = request.POST.get('diasMoraInicio')
            if dias_mora_inicio:
                empresa.dias_mora_inicio = int(dias_mora_inicio)
                
            limite_dias_verde = request.POST.get('limiteDiasVerde')
            if limite_dias_verde:
                empresa.limite_dias_verde = int(limite_dias_verde)
                
            limite_dias_amarillo = request.POST.get('limiteDiasAmarillo')
            if limite_dias_amarillo:
                empresa.limite_dias_amarillo = int(limite_dias_amarillo)
            
            # Manejo de archivo de logo
            if 'logo' in request.FILES:
                logo_file = request.FILES['logo']
                
                # Validar extensión
                valid_extensions = ['.jpg', '.jpeg', '.png']
                file_extension = os.path.splitext(logo_file.name)[1].lower()
                
                if file_extension not in valid_extensions:
                    messages.error(request, 'El logo debe ser una imagen (JPG, JPEG o PNG).')
                    return redirect('configuracion')
                
                if logo_file.size > 2 * 1024 * 1024:  # 2MB en bytes
                    messages.error(request, 'El logo no debe superar los 2MB.')
                    return redirect('configuracion')
                
                # Subir a Cloudinary con public_id estático
                upload_result = cloudinary.uploader.upload(
                    logo_file,
                    folder='logos_empresa',
                    public_id=f'logo_{ruc}',
                    overwrite=True
                )
                empresa.logo = upload_result['secure_url']

            # Manejo de archivo de logo_ticket
            if 'logo_ticket' in request.FILES:
                logo_ticket_file = request.FILES['logo_ticket']
                
                # Validar extensión
                valid_extensions = ['.jpg', '.jpeg', '.png']
                file_extension = os.path.splitext(logo_ticket_file.name)[1].lower()
                
                if file_extension not in valid_extensions:
                    messages.error(request, 'El logo para ticket debe ser una imagen (JPG, JPEG o PNG).')
                    return redirect('configuracion')
                
                if logo_ticket_file.size > 2 * 1024 * 1024:  # 2MB en bytes
                    messages.error(request, 'El logo para ticket no debe superar los 2MB.')
                    return redirect('configuracion')
                
                # Subir a Cloudinary con public_id estático
                upload_result_ticket = cloudinary.uploader.upload(
                    logo_ticket_file,
                    folder='logos_empresa',
                    public_id=f'logo_ticket_{ruc}',
                    overwrite=True
                )
                empresa.logo_ticket = upload_result_ticket['secure_url']
            
            # Guardar cambios
            empresa.save()
            
            # Limpiar caché de configuración para que se reflejen los cambios instantáneamente
            from django.core.cache import cache
            cache.delete('config_empresa_mora')
            
            messages.success(request, 'Información de la empresa actualizada correctamente.')
            
            # Si es AJAX, retornar JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'ok': True,
                    'message': 'Información de empresa actualizada correctamente'
                })
    
    except Empresa.DoesNotExist:
        messages.error(request, 'Empresa no encontrada')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'ok': False,
                'error': 'Empresa no encontrada'
            }, status=404)
    
    except Exception as e:
        messages.error(request, f'Error al actualizar la empresa: {str(e)}')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'ok': False,
                'error': str(e)
            }, status=500)
    
    return redirect('configuracion')


def produccion(request, id):
    """
    Cambia el modo de la empresa a producción.
    """
    try:
        empresa = get_object_or_404(Empresa, idempresa=id)
        empresa.mododev = 1  # 1 = Producción
        empresa.save()
        messages.success(request, f'La empresa "{empresa.nombrecomercial}" está ahora en modo PRODUCCIÓN')
    
    except Empresa.DoesNotExist:
        messages.error(request, 'Empresa no encontrada')
    
    except Exception as e:
        messages.error(request, f'Error al cambiar modo: {str(e)}')
    
    return redirect('configuracion')


def desarrollo(request, id):
    """
    Cambia el modo de la empresa a desarrollo.
    """
    try:
        empresa = get_object_or_404(Empresa, idempresa=id)
        empresa.mododev = 0  # 0 = Desarrollo
        empresa.save()
        messages.success(request, f'La empresa "{empresa.nombrecomercial}" está ahora en modo DESARROLLO')
    
    except Empresa.DoesNotExist:
        messages.error(request, 'Empresa no encontrada')
    
    except Exception as e:
        messages.error(request, f'Error al cambiar modo: {str(e)}')
    
    return redirect('configuracion')


# Funciones auxiliares adicionales

def validar_ruc(ruc):
    """
    Valida el formato del RUC peruano.
    Retorna True si es válido, False en caso contrario.
    """
    if not ruc or len(ruc) != 11:
        return False
    
    if not ruc.isdigit():
        return False
    
    # El primer dígito debe ser 1 (persona natural) o 2 (persona jurídica)
    primer_digito = ruc[0]
    if primer_digito not in ['1', '2']:
        return False
    
    return True


def obtener_datos_empresa_por_ruc(request):
    """
    Endpoint AJAX para obtener datos de una empresa por RUC.
    Útil para autocompletar datos desde SUNAT API (implementación futura).
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    ruc = request.GET.get('ruc', '').strip()
    
    if not validar_ruc(ruc):
        return JsonResponse({
            'ok': False,
            'error': 'RUC inválido'
        }, status=400)
    
    try:
        # Buscar en base de datos local
        empresa = Empresa.objects.filter(ruc=ruc).first()
        
        if empresa:
            return JsonResponse({
                'ok': True,
                'exists': True,
                'data': {
                    'ruc': empresa.ruc,
                    'razon_social': empresa.razonsocial,
                    'nombre_comercial': empresa.nombrecomercial,
                    'direccion': empresa.direccion,
                    'slogan': empresa.slogan,
                    'publicidad': empresa.publicidad,
                }
            })
        else:
            # Aquí podrías integrar con API de SUNAT en el futuro
            return JsonResponse({
                'ok': True,
                'exists': False,
                'message': 'RUC no encontrado en la base de datos'
            })
    
    except Exception as e:
        return JsonResponse({
            'ok': False,
            'error': str(e)
        }, status=500)