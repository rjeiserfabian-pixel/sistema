from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from software.models.RepuestoModel import Repuesto
from software.models.UnidadesModel import Unidades
from software.models.CategoriaRepuestoModel import CategoriaRepuesto
from software.models.MarcaRepuestoModel import MarcaRepuesto
from software.models.GarantiaRepuestoModel import GarantiaRepuesto
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos





def agregar_repuesto(request):
    """Crea un nuevo repuesto en el catalogo."""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Metodo no permitido.'}, status=405)

    nombre       = request.POST.get('nombre', '').strip()
    unidad_id    = request.POST.get('unidad', '').strip()
    marca_id     = request.POST.get('marca', '').strip()
    categoria_id = request.POST.get('categoria', '').strip()

    # Campos opcionales
    codigo_interno   = request.POST.get('codigo_interno', '').strip()
    modelo_referencia = request.POST.get('modelo_referencia', '').strip()
    codigo_barras    = request.POST.get('codigo_barras', '').strip()
    descripcion      = request.POST.get('descripcion', '').strip()
    compatibilidad   = request.POST.get('compatibilidad', '').strip()
    garantia         = request.POST.get('garantia', '').strip()
    observaciones    = request.POST.get('observaciones', '').strip()

    # Campos numericos con valores por defecto seguros
    try:
        stock_minimo   = int(request.POST.get('stock_minimo', 0) or 0)
        stock_maximo   = int(request.POST.get('stock_maximo', 0) or 0)
        costo_unitario = float(request.POST.get('costo_unitario', 0) or 0)
        precio_por_mayor = float(request.POST.get('precio_por_mayor', 0) or 0)
        precio_minimo  = float(request.POST.get('precio_minimo', 0) or 0)
        precio_sugerido = float(request.POST.get('precio_sugerido', 0) or 0)
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'Los campos numericos tienen valores invalidos.'})

    if not nombre or not unidad_id:
        return JsonResponse({'ok': False, 'error': 'El nombre y la unidad son obligatorios.'})

    try:
        unidad    = get_object_or_404(Unidades, idunidad=unidad_id)
        marca_obj = MarcaRepuesto.objects.filter(idmarca_repuesto=marca_id).first() if marca_id else None
        cat_obj   = CategoriaRepuesto.objects.filter(idcategoria_repuesto=categoria_id).first() if categoria_id else None
        garantia_obj = GarantiaRepuesto.objects.filter(id_garantia_repuesto=garantia).first() if garantia else None

        Repuesto.objects.create(
            nombre=nombre,
            idunidad=unidad,
            idmarca=marca_obj,
            id_categoria_repuesto=cat_obj,
            codigo_interno=codigo_interno or None,
            modelo_referencia=modelo_referencia or None,
            codigo_barras=codigo_barras or None,
            descripcion=descripcion or None,
            compatibilidad=compatibilidad or None,
            id_garantia_repuesto=garantia_obj,
            observaciones=observaciones or None,
            stock_minimo=stock_minimo,
            stock_maximo=stock_maximo,
            costo_unitario=costo_unitario,
            precio_por_mayor=precio_por_mayor,
            precio_minimo=precio_minimo,
            precio_sugerido=precio_sugerido,
            estado=1,
        )
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': f'Error al guardar: {str(e)}'})


def editar_repuesto(request):
    """Actualiza un repuesto del catalogo."""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Metodo no permitido.'}, status=405)

    id_repuesto  = request.POST.get('id_repuesto', '').strip()
    nombre       = request.POST.get('nombre2', '').strip()
    unidad_id    = request.POST.get('unidad2', '').strip()
    marca_id     = request.POST.get('marca2', '').strip()
    categoria_id = request.POST.get('categoria2', '').strip()

    # Campos opcionales
    codigo_interno    = request.POST.get('codigo_interno2', '').strip()
    modelo_referencia = request.POST.get('modelo_referencia2', '').strip()
    codigo_barras     = request.POST.get('codigo_barras2', '').strip()
    descripcion       = request.POST.get('descripcion2', '').strip()
    compatibilidad    = request.POST.get('compatibilidad2', '').strip()
    garantia          = request.POST.get('garantia2', '').strip()
    observaciones     = request.POST.get('observaciones2', '').strip()

    try:
        stock_minimo   = int(request.POST.get('stock_minimo2', 0) or 0)
        stock_maximo   = int(request.POST.get('stock_maximo2', 0) or 0)
        costo_unitario = float(request.POST.get('costo_unitario2', 0) or 0)
        precio_por_mayor = float(request.POST.get('precio_por_mayor2', 0) or 0)
        precio_minimo  = float(request.POST.get('precio_minimo2', 0) or 0)
        precio_sugerido = float(request.POST.get('precio_sugerido2', 0) or 0)
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'Los campos numericos tienen valores invalidos.'})

    if not id_repuesto or not nombre or not unidad_id:
        return JsonResponse({'ok': False, 'error': 'El nombre y la unidad son obligatorios.'})

    try:
        repuesto = get_object_or_404(Repuesto, id_repuesto=id_repuesto)

        repuesto.nombre            = nombre
        repuesto.idunidad          = get_object_or_404(Unidades, idunidad=unidad_id)
        repuesto.idmarca           = MarcaRepuesto.objects.filter(idmarca_repuesto=marca_id).first() if marca_id else None
        repuesto.id_categoria_repuesto = CategoriaRepuesto.objects.filter(idcategoria_repuesto=categoria_id).first() if categoria_id else None
        repuesto.codigo_interno    = codigo_interno or None
        repuesto.modelo_referencia = modelo_referencia or None
        repuesto.codigo_barras     = codigo_barras or None
        repuesto.descripcion       = descripcion or None
        repuesto.compatibilidad    = compatibilidad or None
        repuesto.id_garantia_repuesto = GarantiaRepuesto.objects.filter(id_garantia_repuesto=garantia).first() if garantia else None
        repuesto.observaciones     = observaciones or None
        repuesto.stock_minimo      = stock_minimo
        repuesto.stock_maximo      = stock_maximo
        repuesto.costo_unitario    = costo_unitario
        repuesto.precio_por_mayor  = precio_por_mayor
        repuesto.precio_minimo     = precio_minimo
        repuesto.precio_sugerido   = precio_sugerido
        repuesto.save()
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': f'Error al actualizar: {str(e)}'})


def eliminar_repuesto(request, id_repuesto):
    """Desactiva un repuesto (estado=0). Sin cambios de firma para no romper URLs."""
    try:
        repuesto = get_object_or_404(Repuesto, id_repuesto=id_repuesto)
        repuesto.estado = 0
        repuesto.save()
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})
