from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from software.models.SeriecomprobanteModel import Seriecomprobante
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


def serie_comprobante(request):
    """Vista principal que lista todas las series de comprobante activas"""
    id2 = request.session.get('idtipousuario')
    if id2:
        permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
        series_comprobante = Seriecomprobante.objects.filter(estado=1).select_related('idtipocomprobante').order_by('idtipocomprobante__codigo', 'serie')
        tipos_comprobante = Tipocomprobante.objects.filter(estado=1).order_by('codigo')

        data = {
            'series_comprobante': series_comprobante,
            'tipos_comprobante': tipos_comprobante,
            'permisos': permisos
        }
        
        return render(request, 'serie_comprobante/serie_comprobante.html', data)
    else:
        return HttpResponse("<h1>No tiene acceso</h1>")


def eliminar_serie_comprobante(request, id):
    """Eliminación lógica de la serie de comprobante (cambia estado a 0)"""
    try:
        serie_comprobante = Seriecomprobante.objects.get(idseriecomprobante=id)
        serie_comprobante.estado = 0
        serie_comprobante.save()
        return redirect('serie_comprobante')
    except Seriecomprobante.DoesNotExist:
        return HttpResponse("La serie de comprobante no existe", status=404)
    except Exception as e:
        return HttpResponse(f"Error al eliminar: {str(e)}", status=500)


def agregar_serie_comprobante(request):
    """Agregar una nueva serie de comprobante con validaciones. Siempre responde JSON."""
    try:
        idtipocomprobante = request.POST.get('tipoComprobanteSerieComprobante', '').strip()
        serie = request.POST.get('serieSerieComprobante', '').strip().upper()
        numero_actual = request.POST.get('numeroActualSerieComprobante', '').strip()

        if not idtipocomprobante:
            return JsonResponse({'error': 'Debe seleccionar un tipo de comprobante'}, status=400)
        try:
            tipo_comprobante = Tipocomprobante.objects.get(idtipocomprobante=idtipocomprobante, estado=1)
        except Tipocomprobante.DoesNotExist:
            return JsonResponse({'error': 'El tipo de comprobante seleccionado no existe'}, status=400)

        if not serie:
            return JsonResponse({'error': 'La serie es obligatoria'}, status=400)
        if len(serie) != 4:
            return JsonResponse({'error': 'La serie debe tener exactamente 4 caracteres'}, status=400)
        if not serie.isalnum():
            return JsonResponse({'error': 'La serie solo puede contener letras y números (sin espacios ni caracteres especiales)'}, status=400)
        if Seriecomprobante.objects.filter(idtipocomprobante=tipo_comprobante, serie=serie, estado=1).exists():
            return JsonResponse({'error': f'Ya existe una serie {serie} para el tipo de comprobante {tipo_comprobante.nombre}'}, status=400)

        if not numero_actual:
            return JsonResponse({'error': 'El número actual es obligatorio'}, status=400)
        try:
            numero_actual_int = int(numero_actual)
        except ValueError:
            return JsonResponse({'error': 'El número actual debe ser un número entero'}, status=400)
        if numero_actual_int < 0:
            return JsonResponse({'error': 'El número actual debe ser mayor o igual a 0'}, status=400)
        if numero_actual_int > 99999999:
            return JsonResponse({'error': 'El número actual no puede exceder 99999999 (8 dígitos)'}, status=400)

        Seriecomprobante.objects.create(
            idtipocomprobante=tipo_comprobante,
            serie=serie,
            numero_actual=numero_actual_int,
            estado=1
        )
        return JsonResponse({'success': 'Serie de comprobante creada correctamente'}, status=200)

    except IntegrityError:
        return JsonResponse({'error': 'Error de integridad. La serie podría estar duplicada para este tipo de comprobante.'}, status=400)
    except ValidationError as e:
        error_msg = _mensaje_validacion(e)
        return JsonResponse({'error': error_msg}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Error al guardar la serie de comprobante: {str(e)}'}, status=500)


def editar_serie_comprobante(request):
    """Editar una serie de comprobante existente con validaciones. Siempre responde JSON."""
    try:
        id = request.POST.get('idSerieComprobante', '').strip()
        idtipocomprobante = request.POST.get('tipoComprobanteSerieComprobante', '').strip()
        serie = request.POST.get('serieSerieComprobante', '').strip().upper()
        numero_actual = request.POST.get('numeroActualSerieComprobante', '').strip()

        if not id:
            return JsonResponse({'error': 'ID de serie de comprobante inválido'}, status=400)
        try:
            serie_comprobante = Seriecomprobante.objects.get(idseriecomprobante=id)
        except Seriecomprobante.DoesNotExist:
            return JsonResponse({'error': 'La serie de comprobante no existe'}, status=404)

        if not idtipocomprobante:
            return JsonResponse({'error': 'Debe seleccionar un tipo de comprobante'}, status=400)
        try:
            tipo_comprobante = Tipocomprobante.objects.get(idtipocomprobante=idtipocomprobante, estado=1)
        except Tipocomprobante.DoesNotExist:
            return JsonResponse({'error': 'El tipo de comprobante seleccionado no existe'}, status=400)

        if not serie:
            return JsonResponse({'error': 'La serie es obligatoria'}, status=400)
        if len(serie) != 4:
            return JsonResponse({'error': 'La serie debe tener exactamente 4 caracteres'}, status=400)
        if not serie.isalnum():
            return JsonResponse({'error': 'La serie solo puede contener letras y números (sin espacios ni caracteres especiales)'}, status=400)
        if Seriecomprobante.objects.filter(
            idtipocomprobante=tipo_comprobante,
            serie=serie,
            estado=1
        ).exclude(idseriecomprobante=id).exists():
            return JsonResponse({'error': f'Ya existe otra serie {serie} para el tipo de comprobante {tipo_comprobante.nombre}'}, status=400)

        if not numero_actual:
            return JsonResponse({'error': 'El número actual es obligatorio'}, status=400)
        try:
            numero_actual_int = int(numero_actual)
        except ValueError:
            return JsonResponse({'error': 'El número actual debe ser un número entero'}, status=400)
        if numero_actual_int < 0:
            return JsonResponse({'error': 'El número actual debe ser mayor o igual a 0'}, status=400)
        if numero_actual_int > 99999999:
            return JsonResponse({'error': 'El número actual no puede exceder 99999999 (8 dígitos)'}, status=400)

        serie_comprobante.idtipocomprobante = tipo_comprobante
        serie_comprobante.serie = serie
        serie_comprobante.numero_actual = numero_actual_int
        serie_comprobante.save()
        return JsonResponse({'success': 'Serie de comprobante actualizada correctamente'}, status=200)

    except IntegrityError:
        return JsonResponse({'error': 'Error de integridad. La serie podría estar duplicada para este tipo de comprobante.'}, status=400)
    except ValidationError as e:
        error_msg = _mensaje_validacion(e)
        return JsonResponse({'error': error_msg}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Error al editar la serie de comprobante: {str(e)}'}, status=500)