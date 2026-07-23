from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from software.models.CategoriaRepuestoModel import CategoriaRepuesto
from software.models.MarcaRepuestoModel import MarcaRepuesto
from software.models.GarantiaRepuestoModel import GarantiaRepuesto
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos


def configuracion_repuestos(request):
    """Vista principal del submodulo Configuracion de Repuestos."""
    id2 = request.session.get('idtipousuario')
    if not id2:
        return redirect('login')

    permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
    return render(request, 'configuracion_repuestos/configuracion_repuestos.html', {
        'permisos': permisos,
    })


# ─────────────────────────────────────────────
# CRUD: CATEGORIA REPUESTO
# ─────────────────────────────────────────────

def listar_categorias_repuesto(request):
    """
    Retorna categorias de repuesto paginadas en JSON.
    """
    page = request.GET.get('page', 1)
    search = request.GET.get('search', '').strip()

    qs = CategoriaRepuesto.objects.values(
        'idcategoria_repuesto', 'nomcategoria', 'estado'
    ).order_by('nomcategoria')

    if search:
        qs = qs.filter(nomcategoria__icontains=search)

    paginator = Paginator(qs, 10)
    try:
        categorias = paginator.page(page)
    except PageNotAnInteger:
        categorias = paginator.page(1)
    except EmptyPage:
        categorias = paginator.page(paginator.num_pages)

    return JsonResponse({
        'ok': True,
        'data': list(categorias.object_list),
        'pagination': {
            'current_page': categorias.number,
            'total_pages': paginator.num_pages,
            'has_next': categorias.has_next(),
            'has_previous': categorias.has_previous()
        }
    })


def guardar_categoria_repuesto(request):
    """Crea o actualiza una CategoriaRepuesto (crea si no se envia id)."""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Metodo no permitido.'}, status=405)

    idcategoria = request.POST.get('idcategoria_repuesto', '').strip()
    nomcategoria = request.POST.get('nomcategoria', '').strip()
    estado_raw = request.POST.get('estado', 'true')
    estado = 1 if estado_raw == 'true' else 0

    if not nomcategoria:
        return JsonResponse({'ok': False, 'error': 'El nombre es obligatorio.'}, status=400)

    try:
        if idcategoria:
            # EDITAR — validar duplicado excluyendo el registro actual
            if CategoriaRepuesto.objects.filter(
                nomcategoria__iexact=nomcategoria, estado=1
            ).exclude(idcategoria_repuesto=idcategoria).exists():
                return JsonResponse(
                    {'ok': False, 'error': f'La categoría "{nomcategoria}" ya existe. No se permiten duplicados.'},
                    status=400
                )
            cat = CategoriaRepuesto.objects.get(idcategoria_repuesto=idcategoria)
            cat.nomcategoria = nomcategoria
            cat.estado = estado
            cat.save()
            return JsonResponse({'ok': True, 'mensaje': 'Categoria actualizada correctamente.'})
        else:
            # AGREGAR — validar duplicado
            if CategoriaRepuesto.objects.filter(nomcategoria__iexact=nomcategoria, estado=1).exists():
                return JsonResponse(
                    {'ok': False, 'error': f'La categoría "{nomcategoria}" ya existe. No se permiten duplicados.'},
                    status=400
                )
            nueva = CategoriaRepuesto.objects.create(nomcategoria=nomcategoria, estado=estado)
            return JsonResponse({
                'ok': True,
                'mensaje': 'Categoria creada correctamente.',
                'id': nueva.idcategoria_repuesto,
                'nombre': nueva.nomcategoria,
            })
    except CategoriaRepuesto.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'La categoria no existe.'}, status=404)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


def eliminar_categoria_repuesto(request):
    """Desactiva (estado=0) una CategoriaRepuesto. 1 sola query UPDATE, sin N+1."""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Metodo no permitido.'}, status=405)

    idcategoria = request.POST.get('idcategoria_repuesto')
    if not idcategoria:
        return JsonResponse({'ok': False, 'error': 'ID no proporcionado.'}, status=400)

    updated = CategoriaRepuesto.objects.filter(idcategoria_repuesto=idcategoria).update(estado=0)
    if updated == 0:
        return JsonResponse({'ok': False, 'error': 'La categoria no existe.'}, status=404)
    return JsonResponse({'ok': True, 'mensaje': 'Categoria desactivada correctamente.'})


# ─────────────────────────────────────────────
# CRUD: MARCA REPUESTO
# ─────────────────────────────────────────────

def listar_marcas_repuesto(request):
    """
    Retorna marcas de repuesto paginadas en JSON.
    """
    page = request.GET.get('page', 1)
    search = request.GET.get('search', '').strip()

    qs = MarcaRepuesto.objects.values(
        'idmarca_repuesto', 'nombremarca', 'estado'
    ).order_by('nombremarca')

    if search:
        qs = qs.filter(nombremarca__icontains=search)

    paginator = Paginator(qs, 10)
    try:
        marcas = paginator.page(page)
    except PageNotAnInteger:
        marcas = paginator.page(1)
    except EmptyPage:
        marcas = paginator.page(paginator.num_pages)

    return JsonResponse({
        'ok': True,
        'data': list(marcas.object_list),
        'pagination': {
            'current_page': marcas.number,
            'total_pages': paginator.num_pages,
            'has_next': marcas.has_next(),
            'has_previous': marcas.has_previous()
        }
    })


def guardar_marca_repuesto(request):
    """Crea o actualiza una MarcaRepuesto."""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Metodo no permitido.'}, status=405)

    idmarca = request.POST.get('idmarca_repuesto', '').strip()
    nombremarca = request.POST.get('nombremarca', '').strip()
    estado_raw = request.POST.get('estado', 'true')
    estado = 1 if estado_raw == 'true' else 0

    if not nombremarca:
        return JsonResponse({'ok': False, 'error': 'El nombre es obligatorio.'}, status=400)

    try:
        if idmarca:
            # EDITAR
            if MarcaRepuesto.objects.filter(
                nombremarca__iexact=nombremarca, estado=1
            ).exclude(idmarca_repuesto=idmarca).exists():
                return JsonResponse(
                    {'ok': False, 'error': f'La marca "{nombremarca}" ya existe. No se permiten duplicados.'},
                    status=400
                )
            marca = MarcaRepuesto.objects.get(idmarca_repuesto=idmarca)
            marca.nombremarca = nombremarca
            marca.estado = estado
            marca.save()
            return JsonResponse({'ok': True, 'mensaje': 'Marca actualizada correctamente.'})
        else:
            # AGREGAR
            if MarcaRepuesto.objects.filter(nombremarca__iexact=nombremarca, estado=1).exists():
                return JsonResponse(
                    {'ok': False, 'error': f'La marca "{nombremarca}" ya existe. No se permiten duplicados.'},
                    status=400
                )
            nueva = MarcaRepuesto.objects.create(nombremarca=nombremarca, estado=estado)
            return JsonResponse({
                'ok': True,
                'mensaje': 'Marca creada correctamente.',
                'id': nueva.idmarca_repuesto,
                'nombre': nueva.nombremarca,
            })
    except MarcaRepuesto.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'La marca no existe.'}, status=404)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


def eliminar_marca_repuesto(request):
    """Desactiva (estado=0) una MarcaRepuesto. 1 sola query UPDATE, sin N+1."""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Metodo no permitido.'}, status=405)

    idmarca = request.POST.get('idmarca_repuesto')
    if not idmarca:
        return JsonResponse({'ok': False, 'error': 'ID no proporcionado.'}, status=400)

    updated = MarcaRepuesto.objects.filter(idmarca_repuesto=idmarca).update(estado=0)
    if updated == 0:
        return JsonResponse({'ok': False, 'error': 'La marca no existe.'}, status=404)
    return JsonResponse({'ok': True, 'mensaje': 'Marca desactivada correctamente.'})


# ─────────────────────────────────────────────
# CRUD: GARANTIA REPUESTO
# ─────────────────────────────────────────────

def listar_garantias_repuesto(request):
    """
    Retorna garantias de repuesto paginadas en JSON.
    """
    page = request.GET.get('page', 1)
    search = request.GET.get('search', '').strip()

    qs = GarantiaRepuesto.objects.values(
        'id_garantia_repuesto', 'nombre', 'estado'
    ).order_by('nombre')

    if search:
        qs = qs.filter(nombre__icontains=search)

    paginator = Paginator(qs, 10)
    try:
        garantias = paginator.page(page)
    except PageNotAnInteger:
        garantias = paginator.page(1)
    except EmptyPage:
        garantias = paginator.page(paginator.num_pages)

    return JsonResponse({
        'ok': True,
        'data': list(garantias.object_list),
        'pagination': {
            'current_page': garantias.number,
            'total_pages': paginator.num_pages,
            'has_next': garantias.has_next(),
            'has_previous': garantias.has_previous()
        }
    })


def guardar_garantia_repuesto(request):
    """Crea o actualiza una GarantiaRepuesto."""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Metodo no permitido.'}, status=405)

    id_garantia = request.POST.get('id_garantia_repuesto', '').strip()
    nombre = request.POST.get('nombre', '').strip()
    estado_raw = request.POST.get('estado', 'true')
    estado = 1 if estado_raw == 'true' else 0

    if not nombre:
        return JsonResponse({'ok': False, 'error': 'El nombre es obligatorio.'}, status=400)

    try:
        if id_garantia:
            # EDITAR
            if GarantiaRepuesto.objects.filter(
                nombre__iexact=nombre, estado=1
            ).exclude(id_garantia_repuesto=id_garantia).exists():
                return JsonResponse(
                    {'ok': False, 'error': f'La garantía "{nombre}" ya existe. No se permiten duplicados.'},
                    status=400
                )
            garantia = GarantiaRepuesto.objects.get(id_garantia_repuesto=id_garantia)
            garantia.nombre = nombre
            garantia.estado = estado
            garantia.save()
            return JsonResponse({'ok': True, 'mensaje': 'Garantia actualizada correctamente.'})
        else:
            # AGREGAR
            if GarantiaRepuesto.objects.filter(nombre__iexact=nombre, estado=1).exists():
                return JsonResponse(
                    {'ok': False, 'error': f'La garantía "{nombre}" ya existe. No se permiten duplicados.'},
                    status=400
                )
            nueva = GarantiaRepuesto.objects.create(nombre=nombre, estado=estado)
            return JsonResponse({
                'ok': True,
                'mensaje': 'Garantia creada correctamente.',
                'id': nueva.id_garantia_repuesto,
                'nombre': nueva.nombre,
            })
    except GarantiaRepuesto.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'La garantia no existe.'}, status=404)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


def eliminar_garantia_repuesto(request):
    """Desactiva (estado=0) una GarantiaRepuesto."""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Metodo no permitido.'}, status=405)

    id_garantia = request.POST.get('id_garantia_repuesto')
    if not id_garantia:
        return JsonResponse({'ok': False, 'error': 'ID no proporcionado.'}, status=400)

    updated = GarantiaRepuesto.objects.filter(id_garantia_repuesto=id_garantia).update(estado=0)
    if updated == 0:
        return JsonResponse({'ok': False, 'error': 'La garantia no existe.'}, status=404)
    return JsonResponse({'ok': True, 'mensaje': 'Garantia desactivada correctamente.'})
