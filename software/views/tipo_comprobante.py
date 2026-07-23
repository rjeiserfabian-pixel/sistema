import re
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from software.models.TipocomprobanteModel import Tipocomprobante
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos


def _mensaje_validacion(e):
    """Convierte ValidationError (dict o mensaje) en un texto para mostrar al usuario."""
    if getattr(e, 'message_dict', None):
        partes = []
        for campo, mensajes in e.message_dict.items():
            if isinstance(mensajes, (list, tuple)):
                partes.extend(mensajes)
            else:
                partes.append(str(mensajes))
        return ' '.join(partes) if partes else str(e)
    return str(e)


def tipo_comprobante(request):
    """Vista principal que lista todos los tipos de comprobante activos"""
    id2 = request.session.get('idtipousuario')
    if id2:
        permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
        tipos_comprobante = Tipocomprobante.objects.filter(estado=1).order_by('codigo')

        data = {
            'tipos_comprobante': tipos_comprobante,
            'permisos': permisos
        }
        
        return render(request, 'tipo_comprobante/tipo_comprobante.html', data)
    else:
        return HttpResponse("<h1>No tiene acceso</h1>")


def eliminar_tipo_comprobante(request, id):
    """Eliminación lógica del tipo de comprobante (cambia estado a 0)"""
    try:
        tipo_comprobante = Tipocomprobante.objects.get(idtipocomprobante=id)
        tipo_comprobante.estado = 0
        tipo_comprobante.save()
        return redirect('tipo_comprobante')
    except Tipocomprobante.DoesNotExist:
        return HttpResponse("El tipo de comprobante no existe", status=404)
    except Exception as e:
        return HttpResponse(f"Error al eliminar: {str(e)}", status=500)


def agregar_tipo_comprobante(request):
    """Agregar un nuevo tipo de comprobante con validaciones. Siempre responde JSON."""
    try:
        codigo = request.POST.get('codigoTipoComprobante', '').strip().upper()
        nombre = request.POST.get('nombreTipoComprobante', '').strip()
        abreviatura = request.POST.get('abreviaturaTipoComprobante', '').strip().upper()

        # 1. Validar código
        if not codigo:
            return JsonResponse({'error': 'El código es obligatorio'}, status=400)
        if len(codigo) < 2:
            return JsonResponse({'error': 'El código debe tener al menos 2 caracteres'}, status=400)
        if len(codigo) > 10:
            return JsonResponse({'error': 'El código no puede exceder 10 caracteres'}, status=400)
        if not re.match(r'^[0-9A-Z\-]+$', codigo):
            return JsonResponse({'error': 'El código solo puede contener números, letras mayúsculas y guiones'}, status=400)
        if Tipocomprobante.objects.filter(codigo=codigo, estado=1).exists():
            return JsonResponse({'error': f'Ya existe un tipo de comprobante con el código {codigo}'}, status=400)

        # 2. Validar nombre
        if not nombre:
            return JsonResponse({'error': 'El nombre es obligatorio'}, status=400)
        if len(nombre) < 3:
            return JsonResponse({'error': 'El nombre debe tener al menos 3 caracteres'}, status=400)
        if len(nombre) > 255:
            return JsonResponse({'error': 'El nombre no puede exceder 255 caracteres'}, status=400)

        # 3. Validar abreviatura
        if not abreviatura:
            return JsonResponse({'error': 'La abreviatura es obligatoria'}, status=400)
        if len(abreviatura) < 2:
            return JsonResponse({'error': 'La abreviatura debe tener al menos 2 caracteres'}, status=400)
        if len(abreviatura) > 50:
            return JsonResponse({'error': 'La abreviatura no puede exceder 50 caracteres'}, status=400)

        tipo_comprobante = Tipocomprobante.objects.create(
            codigo=codigo,
            nombre=nombre,
            abreviatura=abreviatura,
            estado=1
        )
        return JsonResponse({'success': 'Tipo de comprobante creado correctamente'}, status=200)

    except IntegrityError:
        return JsonResponse({'error': 'Error de integridad. El código podría estar duplicado.'}, status=400)
    except ValidationError as e:
        error_msg = _mensaje_validacion(e)
        return JsonResponse({'error': error_msg}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Error al guardar el tipo de comprobante: {str(e)}'}, status=500)


def editar_tipo_comprobante(request):
    """Editar un tipo de comprobante existente con validaciones. Siempre responde JSON."""
    try:
        id = request.POST.get('idTipoComprobante', '').strip()
        codigo = request.POST.get('codigoTipoComprobante', '').strip().upper()
        nombre = request.POST.get('nombreTipoComprobante', '').strip()
        abreviatura = request.POST.get('abreviaturaTipoComprobante', '').strip().upper()

        if not id:
            return JsonResponse({'error': 'ID de tipo de comprobante inválido'}, status=400)
        try:
            tipo_comprobante = Tipocomprobante.objects.get(idtipocomprobante=id)
        except Tipocomprobante.DoesNotExist:
            return JsonResponse({'error': 'El tipo de comprobante no existe'}, status=404)

        if not codigo:
            return JsonResponse({'error': 'El código es obligatorio'}, status=400)
        if len(codigo) < 2:
            return JsonResponse({'error': 'El código debe tener al menos 2 caracteres'}, status=400)
        if len(codigo) > 10:
            return JsonResponse({'error': 'El código no puede exceder 10 caracteres'}, status=400)
        if not re.match(r'^[0-9A-Z\-]+$', codigo):
            return JsonResponse({'error': 'El código solo puede contener números, letras mayúsculas y guiones'}, status=400)
        if Tipocomprobante.objects.filter(codigo=codigo, estado=1).exclude(idtipocomprobante=id).exists():
            return JsonResponse({'error': f'Ya existe otro tipo de comprobante con el código {codigo}'}, status=400)

        if not nombre:
            return JsonResponse({'error': 'El nombre es obligatorio'}, status=400)
        if len(nombre) < 3:
            return JsonResponse({'error': 'El nombre debe tener al menos 3 caracteres'}, status=400)
        if len(nombre) > 255:
            return JsonResponse({'error': 'El nombre no puede exceder 255 caracteres'}, status=400)

        if not abreviatura:
            return JsonResponse({'error': 'La abreviatura es obligatoria'}, status=400)
        if len(abreviatura) < 2:
            return JsonResponse({'error': 'La abreviatura debe tener al menos 2 caracteres'}, status=400)
        if len(abreviatura) > 50:
            return JsonResponse({'error': 'La abreviatura no puede exceder 50 caracteres'}, status=400)

        tipo_comprobante.codigo = codigo
        tipo_comprobante.nombre = nombre
        tipo_comprobante.abreviatura = abreviatura
        tipo_comprobante.save()
        return JsonResponse({'success': 'Tipo de comprobante actualizado correctamente'}, status=200)

    except IntegrityError:
        return JsonResponse({'error': 'Error de integridad. El código podría estar duplicado.'}, status=400)
    except ValidationError as e:
        error_msg = _mensaje_validacion(e)
        return JsonResponse({'error': error_msg}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Error al editar el tipo de comprobante: {str(e)}'}, status=500)