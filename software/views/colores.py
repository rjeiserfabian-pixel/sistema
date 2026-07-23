from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from software.models.colorModel import Color
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos
from software.models.ProductoModel import Producto
from software.models.DetalleColorModel import DetalleColor

def colores(request):
    # Obtención del id del tipo de usuario desde la sesión
    id2 = request.session.get('idtipousuario')
    if id2:
        permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
        colores_registros = Color.objects.filter(estado=1)

        data = {
            'colores_registros': colores_registros,
            'permisos': permisos
        }
        
        return render(request, 'colores/colores.html', data)
    else:
        return HttpResponse("<h1>No tiene acceso señor</h1>")

def eliminar(request, id):
    try:
        Color.objects.filter(idcolor=id).update(estado=0)
        return redirect('colores')
    except Exception as e:
        return HttpResponse(f"Error al eliminar: {str(e)}", status=500)

def agregar(request):
    if request.method == 'POST':
        nombre = request.POST.get('nameColorAgregar', '').strip()
        
        if not nombre:
            return JsonResponse({'ok': False, 'error': 'El nombre del color es obligatorio.'}, status=400)
            
        # Validar duplicado
        if Color.objects.filter(nombrecolor__iexact=nombre, estado=1).exists():
            return JsonResponse({'ok': False, 'error': f'El color "{nombre}" ya existe. No se permiten duplicados.'}, status=400)
            
        try:
            nuevo = Color.objects.create(nombrecolor=nombre, estado=1)
            return JsonResponse({'ok': True, 'id': nuevo.idcolor, 'nombre': nuevo.nombrecolor})
        except Exception as e:
            return JsonResponse({'ok': False, 'error': f'Error al guardar: {str(e)}'}, status=500)
    
    return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)

def editar(request):
    if request.method == 'POST':
        id = request.POST.get('idColor')
        nombre = request.POST.get('nameColor', '').strip()

        if not id or not nombre:
            return JsonResponse({'ok': False, 'error': 'Datos incompletos para la edición.'}, status=400)

        try:
            color = Color.objects.get(idcolor=id)
            if color.nombrecolor.lower() != nombre.lower():
                # Validar duplicado si el nombre cambió
                if Color.objects.filter(nombrecolor__iexact=nombre, estado=1).exclude(idcolor=id).exists():
                    return JsonResponse({'ok': False, 'error': f'El color "{nombre}" ya existe. No se permiten duplicados.'}, status=400)
                
                color.nombrecolor = nombre
                color.save()
                
                # Actualización en cascada
                productos = Producto.objects.filter(idcolor=color).select_related(
                    'idcategoria', 'idmarca', 'idmodelo', 'id_configuracion', 'idcolor'
                )
                Producto.actualizar_nombres_en_cascada(productos)
                
            return JsonResponse({'ok': True})
        except Color.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'El color no existe.'}, status=404)
        except Exception as e:
            return JsonResponse({'ok': False, 'error': f'Error al actualizar: {str(e)}'}, status=500)

    return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)


# ==========================================
# CRUD DETALLE DE COLOR
# ==========================================

def listar_detalle_color(request):
    """
    Retorna todos los detalles de color en formato JSON.
    Usa .values() para evitar instanciar objetos ORM y prevenir consultas N+1.
    """
    detalles = DetalleColor.objects.values(
        'iddetalle_color', 'nombre', 'estado'
    ).order_by('nombre')
    return JsonResponse({'data': list(detalles)})


def guardar_detalle_color(request):
    """
    Crea o actualiza un Detalle de Color según si se recibe iddetalle_color.
    Valida duplicados con .exists() (sin traer el objeto completo).
    """
    if request.method == 'POST':
        try:
            iddetalle_color = request.POST.get('iddetalle_color', '').strip()
            nombre = request.POST.get('nombre', '').strip()
            estado_raw = request.POST.get('estado', 'true')
            estado = 1 if estado_raw == 'true' else 0

            if not nombre:
                return JsonResponse({'ok': False, 'error': 'El nombre es obligatorio.'}, status=400)

            if iddetalle_color:
                # ── EDITAR ──────────────────────────────────────────────────
                # Validar duplicado excluyendo el registro actual
                if DetalleColor.objects.filter(
                    nombre__iexact=nombre, estado=1
                ).exclude(iddetalle_color=iddetalle_color).exists():
                    return JsonResponse(
                        {'ok': False, 'error': f'El detalle "{nombre}" ya existe.'},
                        status=400
                    )
                detalle = DetalleColor.objects.get(iddetalle_color=iddetalle_color)
                detalle.nombre = nombre
                detalle.estado = estado
                detalle.save()
                return JsonResponse({'ok': True, 'mensaje': 'Detalle actualizado correctamente.'})
            else:
                # ── AGREGAR ─────────────────────────────────────────────────
                if DetalleColor.objects.filter(nombre__iexact=nombre, estado=1).exists():
                    return JsonResponse(
                        {'ok': False, 'error': f'El detalle "{nombre}" ya existe.'},
                        status=400
                    )
                nuevo = DetalleColor.objects.create(nombre=nombre, estado=estado)
                return JsonResponse({
                    'ok': True,
                    'mensaje': 'Detalle creado correctamente.',
                    'id': nuevo.iddetalle_color,
                    'nombre': nuevo.nombre
                })

        except DetalleColor.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'El detalle no existe.'}, status=404)
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)}, status=500)

    return JsonResponse({'ok': False, 'error': 'Método no permitido.'}, status=405)


def eliminar_detalle_color(request):
    """
    Desactiva un Detalle de Color (estado=0).
    Usa .filter().update() — 1 sola query UPDATE, sin N+1.
    """
    if request.method == 'POST':
        try:
            iddetalle_color = request.POST.get('iddetalle_color')
            if not iddetalle_color:
                return JsonResponse({'ok': False, 'error': 'ID no proporcionado.'}, status=400)

            updated = DetalleColor.objects.filter(
                iddetalle_color=iddetalle_color
            ).update(estado=0)

            if updated == 0:
                return JsonResponse({'ok': False, 'error': 'El detalle no existe.'}, status=404)

            return JsonResponse({'ok': True, 'mensaje': 'Detalle desactivado correctamente.'})
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)}, status=500)

    return JsonResponse({'ok': False, 'error': 'Método no permitido.'}, status=405)
