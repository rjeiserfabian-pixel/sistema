from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from software.models.ProductoModel import Producto
from software.models.categoriaModel import Categoria
from software.models.UnidadesModel import Unidades
from software.models.marcaModel import Marca
from software.models.cilindradaModel import Cilindrada
from software.models.colorModel import Color
from software.models.modeloModel import Modelo
from software.models.ConfiguracionVehicularModel import ConfiguracionVehicular
from software.models.DetalleColorModel import DetalleColor
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos
from software.models.RepuestoModel import Repuesto
from software.models.CategoriaRepuestoModel import CategoriaRepuesto
from software.models.MarcaRepuestoModel import MarcaRepuesto
from software.models.GarantiaRepuestoModel import GarantiaRepuesto
from software.models.ServicioModel import Servicio
from software.models.AuditoriaProductosModel import AuditoriaProductos



def productos(request):
    id2 = request.session.get('idtipousuario')
    if not id2:
        return redirect('login')

    permisos   = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
    productos  = []
    categorias = Categoria.objects.filter(estado=1)
    unidades   = Unidades.objects.filter(estado=1)
    marcas     = Marca.objects.filter(estado=1)
    cilindrada = Cilindrada.objects.filter(estado=1)
    color      = Color.objects.filter(estado=1)

    modelos    = Modelo.objects.filter(estado=1).order_by('nombremodelo')
    configuraciones = ConfiguracionVehicular.objects.filter(estado=1)
    detalles_color  = DetalleColor.objects.filter(estado=1).values('iddetalle_color', 'nombre')

    # Repuestos para el tab 2 - Anti N+1: select_related en 1 query
    repuestos_qs = []
    categorias_rep = CategoriaRepuesto.objects.filter(estado=1).order_by('nomcategoria')
    marcas_rep     = MarcaRepuesto.objects.filter(estado=1).order_by('nombremarca')
    garantias_rep  = GarantiaRepuesto.objects.filter(estado=1).order_by('nombre')
    
    # Servicios / Trámites para el tab 3
    servicios_registros = []

    data = {
        'productos':  productos,
        'categorias': categorias,
        'unidades':   unidades,
        'marcas':     marcas,
        'modelos':    modelos,
        'cilindrada': cilindrada,
        'color':      color,
        'configuraciones': configuraciones,
        'detalles_color':  detalles_color,
        'permisos':   permisos,
        # datos para tab de Repuestos
        'repuestos':       repuestos_qs,
        'categorias_rep':  categorias_rep,
        'marcas_rep':      marcas_rep,
        'garantias_rep':   garantias_rep,
        # datos para tab de Servicios
        'servicios_registros': servicios_registros,
    }
    return render(request, 'productos/productos.html', data)



def agregar(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido.'}, status=405)

    nombreProducto = request.POST.get('nombreProducto', '').strip()
    categoria_id   = request.POST.get('categoria', '').strip()
    unidad_id      = request.POST.get('unidad', '').strip()
    marca_id       = request.POST.get('marca', '').strip()
    modelo_id      = request.POST.get('modelo', '').strip()
    cilindrada_id  = request.POST.get('cilindrada', '').strip()

    color_id       = request.POST.get('color', '').strip()
    detalle_color_id = request.POST.get('id_detalle_color', '').strip()
    configuracion_id = request.POST.get('id_configuracion', '').strip()
    imagenprod     = request.POST.get('imagenprod', '').strip()
    codigo_interno = request.POST.get('codigo_interno', '').strip()

    if not all([nombreProducto, categoria_id, unidad_id, marca_id, cilindrada_id, color_id]):

        return JsonResponse({'ok': False, 'error': 'Todos los campos marcados como obligatorios deben estar completos.'})

    try:
        categoria  = get_object_or_404(Categoria,  idcategoria=categoria_id)
        unidad     = get_object_or_404(Unidades,   idunidad=unidad_id)
        marca      = get_object_or_404(Marca,      idmarca=marca_id)
        modelo_obj = Modelo.objects.filter(idmodelo=modelo_id).first() if modelo_id else None
        cilindrada = get_object_or_404(Cilindrada, idcilindrada=cilindrada_id)
        color      = get_object_or_404(Color,      idcolor=color_id)
        config_obj = ConfiguracionVehicular.objects.filter(id_configuracion=configuracion_id).first() if configuracion_id else None
        detalle_color_obj = DetalleColor.objects.filter(iddetalle_color=detalle_color_id).first() if detalle_color_id else None

        Producto.objects.create(
            idcategoria=categoria,
            idunidad=unidad,
            idmarca=marca,
            idmodelo=modelo_obj,
            idcilindrada=cilindrada,
            idcolor=color,
            id_configuracion=config_obj,
            id_detalle_color=detalle_color_obj,
            nomproducto=nombreProducto,
            imagenprod=imagenprod,
            codigo_interno=codigo_interno,
            estado=1,
        )

        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': f'Error al guardar el vehículo: {str(e)}'})


def editado(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido.'}, status=405)

    idproducto    = request.POST.get('idproducto2', '').strip()
    categoria_id  = request.POST.get('categoria2', '').strip()
    unidad_id     = request.POST.get('unidad2', '').strip()
    marca_id      = request.POST.get('marca2', '').strip()
    modelo_id     = request.POST.get('modelo2', '').strip()
    cilindrada_id = request.POST.get('cilindrada2', '').strip()

    color_id      = request.POST.get('color2', '').strip()
    detalle_color_id = request.POST.get('id_detalle_color2', '').strip()
    configuracion_id = request.POST.get('id_configuracion2', '').strip()
    nombre        = request.POST.get('nombreProducto2', '').strip()
    imagenprod    = request.POST.get('imagenprod2', '').strip()
    codigo_interno = request.POST.get('codigo_interno2', '').strip()
    if not all([idproducto, nombre, categoria_id, unidad_id, marca_id, cilindrada_id, color_id]):
        return JsonResponse({'ok': False, 'error': 'Todos los campos marcados como obligatorios deben estar completos.'})

    try:
        categoria  = get_object_or_404(Categoria,  idcategoria=categoria_id)
        unidad     = get_object_or_404(Unidades,   idunidad=unidad_id)
        marca      = get_object_or_404(Marca,      idmarca=marca_id)
        modelo_obj = Modelo.objects.filter(idmodelo=modelo_id).first() if modelo_id else None
        cilindrada = get_object_or_404(Cilindrada, idcilindrada=cilindrada_id)
        color      = get_object_or_404(Color,      idcolor=color_id)
        config_obj = ConfiguracionVehicular.objects.filter(id_configuracion=configuracion_id).first() if configuracion_id else None
        detalle_color_obj = DetalleColor.objects.filter(iddetalle_color=detalle_color_id).first() if detalle_color_id else None

        # Capturar datos anteriores ANTES de actualizar (para auditoría)
        producto_anterior = Producto.objects.filter(idproducto=idproducto).select_related(
            'idmarca', 'idmodelo', 'idcilindrada', 'idcolor'
        ).first()
        datos_anteriores = None
        if producto_anterior:
            datos_anteriores = {
                'nomproducto': producto_anterior.nomproducto,
                'codigo_interno': producto_anterior.codigo_interno or '',
                'marca': producto_anterior.idmarca.nombremarca if producto_anterior.idmarca else '',
                'modelo': producto_anterior.idmodelo.nombremodelo if producto_anterior.idmodelo else '',
                'cilindrada': str(producto_anterior.idcilindrada.cilindrada_cc) if producto_anterior.idcilindrada else '',
                'color': producto_anterior.idcolor.nombrecolor if producto_anterior.idcolor else '',
            }

        Producto.objects.filter(idproducto=idproducto).update(
            idcategoria=categoria,
            idunidad=unidad,
            idmarca=marca,
            idmodelo=modelo_obj,
            idcilindrada=cilindrada,
            idcolor=color,
            id_configuracion=config_obj,
            id_detalle_color=detalle_color_obj,
            nomproducto=nombre,
            imagenprod=imagenprod,
            codigo_interno=codigo_interno,
            estado=1,
        )

        # Registrar en auditoría (sin interrumpir si falla)
        try:
            idusuario = request.session.get('idusuario')
            if idusuario and producto_anterior:
                AuditoriaProductos.objects.create(
                    idproducto=producto_anterior,
                    accion='EDICION',
                    motivo='Producto/Vehículo actualizado',
                    idusuario_id=idusuario,
                    datos_anteriores=datos_anteriores,
                    datos_nuevos={
                        'nomproducto': nombre,
                        'codigo_interno': codigo_interno,
                        'marca': marca.nombremarca if marca else '',
                        'modelo': modelo_obj.nombremodelo if modelo_obj else '',
                        'cilindrada': str(cilindrada.cilindrada_cc) if cilindrada else '',
                        'color': color.nombrecolor if color else '',
                    }
                )
        except Exception as e_aud:
            print(f'⚠️ Auditoría productos (editado) falló silenciosamente: {e_aud}')

        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': f'Error al actualizar el vehículo: {str(e)}'})


def eliminar(request, idproducto):
    try:
        producto = get_object_or_404(Producto, idproducto=idproducto)

        # Guardar datos antes de eliminar (para auditoría)
        datos_producto = {
            'nomproducto': producto.nomproducto,
            'codigo_interno': producto.codigo_interno or '',
            'marca': producto.idmarca.nombremarca if producto.idmarca else '',
            'modelo': producto.idmodelo.nombremodelo if producto.idmodelo else '',
            'color': producto.idcolor.nombrecolor if producto.idcolor else '',
        }

        producto.estado = 0
        producto.save()

        # Registrar en auditoría (sin interrumpir si falla)
        try:
            idusuario = request.session.get('idusuario')
            if idusuario:
                AuditoriaProductos.objects.create(
                    idproducto=producto,
                    accion='ELIMINACION',
                    motivo='Producto/Vehículo eliminado del catálogo',
                    idusuario_id=idusuario,
                    datos_anteriores=datos_producto,
                )
        except Exception as e_aud:
            print(f'⚠️ Auditoría productos (eliminar) falló silenciosamente: {e_aud}')

        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})


def api_listar_vehiculos(request):
    from django.db.models import Q
    from django.core.paginator import Paginator
    
    idusuario = request.session.get('idusuario')
    if not idusuario:
        return JsonResponse({'ok': False, 'error': 'No autorizado'}, status=401)
        
    page_number = request.GET.get('page', 1)
    busqueda = request.GET.get('busqueda', '').strip()
    
    vehiculos = Producto.objects.filter(estado=1).select_related(
        'idcategoria', 'idunidad', 'idmarca', 'idmodelo', 'idcilindrada', 'idcolor', 'id_configuracion', 'id_detalle_color'
    ).order_by('-idproducto')
    
    if busqueda:
        vehiculos = vehiculos.filter(
            Q(nomproducto__icontains=busqueda) |
            Q(codigo_interno__icontains=busqueda) |
            Q(idmarca__nombremarca__icontains=busqueda) |
            Q(idmodelo__nombremodelo__icontains=busqueda)
        )
        
    total_registros = vehiculos.count()
    
    paginator = Paginator(vehiculos, 10)
    page_obj = paginator.get_page(page_number)
    
    data = []
    for v in page_obj:
        data.append({
            'idproducto': v.idproducto,
            'codigo_interno': v.codigo_interno or '',
            'nomproducto': v.nomproducto or '',
            'marca': v.idmarca.nombremarca if v.idmarca else '',
            'idmarca': v.idmarca.idmarca if v.idmarca else '',
            'modelo': v.idmodelo.nombremodelo if v.idmodelo else '',
            'idmodelo': v.idmodelo.idmodelo if v.idmodelo else '',
            'cilindrada': v.idcilindrada.cilindrada_cc if v.idcilindrada else '',
            'idcilindrada': v.idcilindrada.idcilindrada if v.idcilindrada else '',
            'color': v.idcolor.nombrecolor if v.idcolor else '',
            'idcolor': v.idcolor.idcolor if v.idcolor else '',
            'detalle_color': v.id_detalle_color.nombre if getattr(v, 'id_detalle_color', None) else '',
            'id_detalle_color': v.id_detalle_color.iddetalle_color if getattr(v, 'id_detalle_color', None) else '',
            'unidad': v.idunidad.abrunidad if v.idunidad else '',
            'idunidad': v.idunidad.idunidad if v.idunidad else '',
            'categoria': v.idcategoria.nomcategoria if getattr(v, 'idcategoria', None) else '',
            'idcategoria': v.idcategoria.idcategoria if getattr(v, 'idcategoria', None) else '',
            'configuracion': v.id_configuracion.nombre if getattr(v, 'id_configuracion', None) else '',
            'id_configuracion': v.id_configuracion.id_configuracion if getattr(v, 'id_configuracion', None) else '',
            'imagenprod': v.imagenprod if v.imagenprod else ''
        })
        
    return JsonResponse({
        'ok': True,
        'vehiculos': data,
        'stats': {'total_registros': total_registros},
        'pagination': {
            'has_previous': page_obj.has_previous(),
            'has_next': page_obj.has_next(),
            'current_page': page_obj.number,
            'num_pages': paginator.num_pages,
            'previous_page_number': page_obj.previous_page_number() if page_obj.has_previous() else None,
            'next_page_number': page_obj.next_page_number() if page_obj.has_next() else None,
            'start_index': page_obj.start_index() if total_registros > 0 else 0,
            'end_index': page_obj.end_index() if total_registros > 0 else 0
        }
    })

def api_listar_repuestos(request):
    from django.db.models import Q
    from django.core.paginator import Paginator
    
    idusuario = request.session.get('idusuario')
    if not idusuario:
        return JsonResponse({'ok': False, 'error': 'No autorizado'}, status=401)
        
    page_number = request.GET.get('page', 1)
    busqueda = request.GET.get('busqueda', '').strip()
    
    repuestos = Repuesto.objects.filter(estado=1).select_related(
        'id_categoria_repuesto', 'idmarca', 'idunidad', 'id_garantia_repuesto'
    ).order_by('nombre')
    
    if busqueda:
        repuestos = repuestos.filter(
            Q(nombre__icontains=busqueda) |
            Q(codigo_barras__icontains=busqueda) |
            Q(idmarca__nombremarca__icontains=busqueda)
        )
        
    total_registros = repuestos.count()
    paginator = Paginator(repuestos, 10)
    page_obj = paginator.get_page(page_number)
    
    data = []
    for r in page_obj:
        data.append({
            'id_repuesto': r.id_repuesto,
            'codigo_barras': r.codigo_barras or '',
            'nombre': r.nombre or '',
            'marca': r.idmarca.nombremarca if getattr(r, 'idmarca', None) else 'S/M',
            'idmarca': r.idmarca.idmarca_repuesto if getattr(r, 'idmarca', None) else '',
            'categoria': r.id_categoria_repuesto.nomcategoria if getattr(r, 'id_categoria_repuesto', None) else 'S/C',
            'id_categoria': r.id_categoria_repuesto.idcategoria_repuesto if getattr(r, 'id_categoria_repuesto', None) else '',
            'garantia': r.id_garantia_repuesto.nombre if getattr(r, 'id_garantia_repuesto', None) else 'S/G',
            'id_garantia': r.id_garantia_repuesto.id_garantia_repuesto if getattr(r, 'id_garantia_repuesto', None) else '',
            'unidad': r.idunidad.abrunidad if getattr(r, 'idunidad', None) else 'S/U',
            'idunidad': r.idunidad.idunidad if getattr(r, 'idunidad', None) else '',
            'codigo_interno': r.codigo_interno or '',
            'modelo_referencia': r.modelo_referencia or '',
            'descripcion': r.descripcion or '',
            'compatibilidad': r.compatibilidad or '',
            'stock_minimo': r.stock_minimo,
            'stock_maximo': r.stock_maximo,
            'costo_unitario': str(r.costo_unitario),
            'precio_por_mayor': str(r.precio_por_mayor),
            'precio_minimo': str(r.precio_minimo),
            'precio_sugerido': str(r.precio_sugerido),
            'observaciones': r.observaciones or '',
            'imagen': ''
        })
        
    return JsonResponse({
        'ok': True,
        'repuestos': data,
        'stats': {'total_registros': total_registros},
        'pagination': {
            'has_previous': page_obj.has_previous(),
            'has_next': page_obj.has_next(),
            'current_page': page_obj.number,
            'num_pages': paginator.num_pages,
            'previous_page_number': page_obj.previous_page_number() if page_obj.has_previous() else None,
            'next_page_number': page_obj.next_page_number() if page_obj.has_next() else None,
            'start_index': page_obj.start_index() if total_registros > 0 else 0,
            'end_index': page_obj.end_index() if total_registros > 0 else 0
        }
    })

def api_listar_servicios(request):
    from django.db.models import Q
    from django.core.paginator import Paginator
    
    idusuario = request.session.get('idusuario')
    if not idusuario:
        return JsonResponse({'ok': False, 'error': 'No autorizado'}, status=401)
        
    page_number = request.GET.get('page', 1)
    busqueda = request.GET.get('busqueda', '').strip()
    
    servicios = Servicio.objects.filter(estado=1).order_by('nombre')
    
    if busqueda:
        servicios = servicios.filter(nombre__icontains=busqueda)
        
    total_registros = servicios.count()
    paginator = Paginator(servicios, 10)
    page_obj = paginator.get_page(page_number)
    
    data = []
    for s in page_obj:
        data.append({
            'id_servicio': s.id_servicio,
            'nombre': s.nombre or '',
            'precio': str(s.precio_defecto) if getattr(s, 'precio_defecto', None) else '0.00',
            'descripcion': s.descripcion or '',
        })
        
    return JsonResponse({
        'ok': True,
        'servicios': data,
        'stats': {'total_registros': total_registros},
        'pagination': {
            'has_previous': page_obj.has_previous(),
            'has_next': page_obj.has_next(),
            'current_page': page_obj.number,
            'num_pages': paginator.num_pages,
            'previous_page_number': page_obj.previous_page_number() if page_obj.has_previous() else None,
            'next_page_number': page_obj.next_page_number() if page_obj.has_next() else None,
            'start_index': page_obj.start_index() if total_registros > 0 else 0,
            'end_index': page_obj.end_index() if total_registros > 0 else 0
        }
    })
