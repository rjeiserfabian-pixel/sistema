from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.db import transaction
from django.db.models import Q, Max, Sum
from software.models.compradetalleModel import CompraDetalle
from software.models.comprasModel import Compras
from software.models.VehiculosModel import Vehiculo
from software.models.ProductoModel import Producto
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos
from software.models.RepuestoModel import Repuesto
from software.models.RespuestoCompModel import RepuestoComp
from software.models.stockModel import Stock
from software.models.sucursalesModel import Sucursales
from software.models.estadoproductoModel import EstadoProducto
from software.models.SituacionVehiculoModel import SituacionVehiculo
from software.models.almacenesModel import Almacenes
from software.models.ProveedoresModel import Proveedor
from software.models.Tipo_entidadModel import TipoEntidad
from software.models.transferenciaModel import Transferencia
from software.models.detalleTransferenciaModel import DetalleTransferencia


def stock(request):
    id2 = request.session.get('idtipousuario')

    if not id2:
        return HttpResponse("<h1>No tiene acceso señor</h1>")

    es_admin = (id2 == 1)
    permisos = Detalletipousuarioxmodulos.objects.filter(idtipousuario=id2)
    id_sucursal_activa = request.session.get('id_sucursal')
    id_almacen_activo = request.session.get('id_almacen')

    if not id_sucursal_activa:
        return HttpResponse("<h1>No hay sucursal seleccionada</h1>")

    try:
        sucursal_usuario = Sucursales.objects.get(id_sucursal=id_sucursal_activa)
    except Sucursales.DoesNotExist:
        return HttpResponse("<h1>Sucursal no encontrada</h1>")

    # ── Exportar PDF (consulta propia, independiente de la carga principal) ──
    export_fmt = request.GET.get('export')
    if export_fmt == 'pdf':
        from software.views.report_exports import export_to_pdf_stock
        from software.models.PreCreditoModel import PreCredito

        filtro_base_pdf = {'estado': 1, 'cantidad_disponible__gt': 0}
        if id_almacen_activo:
            filtro_base_pdf['id_almacen_id'] = id_almacen_activo
        else:
            filtro_base_pdf['id_almacen__id_sucursal'] = sucursal_usuario

        vehiculos_reservados_pdf = set(PreCredito.objects.filter(
            estado__in=['pendiente', 'aprobado']
        ).values_list('detalles_vehiculos__id_vehiculo_id', flat=True))

        # Vehículos
        filtro_v_pdf = filtro_base_pdf.copy()
        filtro_v_pdf.update({
            'id_vehiculo__estado': 1,
            'id_vehiculo__isnull': False,
            'id_vehiculo__idproducto__estado': 1,
        })
        stocks_v_pdf = Stock.objects.filter(**filtro_v_pdf).select_related(
            'id_vehiculo__idestadoproducto',
            'id_vehiculo__id_situacion',
            'id_vehiculo__idproducto',
            'id_almacen',
            'idcompradetalle'
        )
        vehiculos_sin_det_pdf = [s.id_vehiculo.id_vehiculo for s in stocks_v_pdf if not s.idcompradetalle and s.id_vehiculo]
        fallback_v_pdf = {}
        if vehiculos_sin_det_pdf:
            for d in CompraDetalle.objects.filter(id_vehiculo__in=vehiculos_sin_det_pdf).order_by('id_vehiculo', '-idcompradetalle'):
                if d.id_vehiculo_id not in fallback_v_pdf:
                    fallback_v_pdf[d.id_vehiculo_id] = d

        vehiculos_stock_pdf = {}
        for s in stocks_v_pdf:
            veh = s.id_vehiculo
            if not veh:
                continue
            det = s.idcompradetalle or fallback_v_pdf.get(veh.id_vehiculo)
            if det:
                nom = veh.idproducto.nomproducto
                vehiculos_stock_pdf.setdefault(nom, []).append({
                    'serie_chasis': veh.serie_chasis,
                    'serie_motor': veh.serie_motor,
                    'cantidad': s.cantidad_disponible,
                    'precio_compra': det.precio_compra,
                    'precio_maximo': det.precio_maximo,
                })

        # Repuestos
        filtro_r_pdf = filtro_base_pdf.copy()
        filtro_r_pdf.update({
            'id_repuesto_comprado__estado': 1,
            'id_repuesto_comprado__isnull': False,
            'id_repuesto_comprado__id_repuesto__estado': 1,
        })
        stocks_r_pdf = Stock.objects.filter(**filtro_r_pdf).select_related(
            'id_repuesto_comprado__id_repuesto',
            'id_almacen',
            'idcompradetalle'
        )
        repuestos_sin_det_pdf = [s.id_repuesto_comprado.id_repuesto_comprado for s in stocks_r_pdf if not s.idcompradetalle and s.id_repuesto_comprado]
        fallback_r_pdf = {}
        if repuestos_sin_det_pdf:
            for d in CompraDetalle.objects.filter(id_repuesto_comprado__in=repuestos_sin_det_pdf).order_by('id_repuesto_comprado', '-idcompradetalle'):
                if d.id_repuesto_comprado_id not in fallback_r_pdf:
                    fallback_r_pdf[d.id_repuesto_comprado_id] = d

        repuestos_stock_pdf = {}
        for s in stocks_r_pdf:
            rc = s.id_repuesto_comprado
            if not rc:
                continue
            det = s.idcompradetalle or fallback_r_pdf.get(rc.id_repuesto_comprado)
            p_compra = det.precio_compra if det else rc.id_repuesto.costo_unitario
            p_maximo = rc.id_repuesto.precio_sugerido or (det.precio_maximo if det else 0)
            nom = rc.id_repuesto.nombre
            repuestos_stock_pdf.setdefault(nom, []).append({
                'codigo_barras': rc.id_repuesto.codigo_barras or 'N/A',
                'ubicacion': rc.ubicacion or 'Sin ubicación',
                'cantidad': s.cantidad_disponible,
                'precio_compra': p_compra,
                'precio_maximo': p_maximo,
            })

        vehiculos_headers = ['Producto/Repuesto', 'Identificador', 'Stock', 'Costo Unit.', 'Venta Unit. (P. Máx)', 'Inversión', 'Ganancia Est.']
        vehiculos_data = []
        for nom, detalles in vehiculos_stock_pdf.items():
            for det in detalles:
                cant = int(det['cantidad'])
                costo = float(det['precio_compra']) if det['precio_compra'] else 0.0
                venta = float(det['precio_maximo']) if det['precio_maximo'] else 0.0
                vehiculos_data.append([
                    nom,
                    f"CH: {det.get('serie_chasis', '')}\nMOT: {det.get('serie_motor', '')}",
                    str(cant), f"{costo:.2f}", f"{venta:.2f}",
                    f"{cant * costo:.2f}", f"{(cant * venta) - (cant * costo):.2f}"
                ])

        repuestos_headers = ['Producto/Repuesto', 'Identificador', 'Ubicación', 'Stock', 'Costo Unit.', 'Venta Unit. (P. Máx)', 'Inversión', 'Ganancia Est.']
        repuestos_data = []
        for nom, detalles in repuestos_stock_pdf.items():
            for det in detalles:
                cant = int(det['cantidad'])
                costo = float(det['precio_compra']) if det['precio_compra'] else 0.0
                venta = float(det['precio_maximo']) if det['precio_maximo'] else 0.0
                repuestos_data.append([
                    nom, f"COD: {det.get('codigo_barras', '')}",
                    det.get('ubicacion', 'Sin ubicación'),
                    str(cant), f"{costo:.2f}", f"{venta:.2f}",
                    f"{cant * costo:.2f}", f"{(cant * venta) - (cant * costo):.2f}"
                ])

        return export_to_pdf_stock(
            vehiculos_headers, vehiculos_data,
            repuestos_headers, repuestos_data,
            'REPORTE DE INVERSIÓN Y GANANCIAS - STOCK', 'Reporte_Stock'
        )

    # ── Carga normal de la página (liviana, sin consultar el inventario) ──
    productos = Producto.objects.filter(estado=1)
    catalogo_repuestos = Repuesto.objects.filter(estado=1).select_related('idmarca', 'id_categoria_repuesto', 'idunidad')

    data = {
        'permisos': permisos,
        'sucursal': sucursal_usuario,
        'es_admin': es_admin,
        'estado_producto': EstadoProducto.objects.filter(estado=1),
        'productos_catalogo': productos,
        'catalogo_repuestos': catalogo_repuestos,
    }

    return render(request, 'stock/stock.html', data)

@transaction.atomic
def agregar_vehiculo_stock_directo(request):
    if request.method == "POST":
        try:
            id_sucursal_activa = request.session.get('id_sucursal')
            id_almacen_activo = request.session.get('id_almacen')
            if not id_almacen_activo:
                return JsonResponse({'success': False, 'error': 'Debe tener un almacén activo en sesión.'})

            almacen = Almacenes.objects.get(id_almacen=id_almacen_activo)

            idproducto = request.POST.get('idproducto')
            serie_motor = request.POST.get('serie_motor', '').strip()
            serie_chasis = request.POST.get('serie_chasis', '').strip()
            anio = request.POST.get('anio', '').strip()
            idestadoproducto = request.POST.get('idestadoproducto')
            placas = request.POST.get('placas', '').strip()
            imperfecciones = request.POST.get('imperfecciones', '').strip()
            cantidad = int(request.POST.get('cantidad', '1'))
            precio_compra = float(request.POST.get('precio_compra', '0.0'))
            precio_por_mayor = float(request.POST.get('precio_por_mayor', '0.0'))
            precio_minimo = float(request.POST.get('precio_minimo', '0.0'))
            precio_maximo = float(request.POST.get('precio_maximo', '0.0'))

            if not idproducto or not idestadoproducto:
                return JsonResponse({'success': False, 'error': 'Faltan datos requeridos.'})

            # Obtener el producto si es necesario (ya no se usa para id_configuracion aquí)
            # producto = get_object_or_404(Producto, idproducto=idproducto)
            situacion_disponible, _ = SituacionVehiculo.objects.get_or_create(nombre_situacion='DISPONIBLE', defaults={'estado': 1})

            if serie_motor or serie_chasis:
                query = Q()
                if serie_motor:
                    query |= Q(serie_motor=serie_motor)
                if serie_chasis:
                    query |= Q(serie_chasis=serie_chasis)
                
                if Vehiculo.objects.filter(query).exists():
                    return JsonResponse({'success': False, 'error': 'La Serie Motor o Serie Chasis ya se encuentra registrada en el sistema.'})

            vehiculo = Vehiculo.objects.create(
                id_situacion=situacion_disponible,
                idproducto_id=int(idproducto),
                serie_motor=serie_motor,
                serie_chasis=serie_chasis,
                anio=int(anio) if anio else None,
                idestadoproducto_id=int(idestadoproducto),
                imperfecciones=imperfecciones,
                placas=placas,
                estado=1
            )

            # Crear proveedor y entidad maestra interna para saltar restricción de base de datos
            tipo_entidad, _ = TipoEntidad.objects.get_or_create(
                tipo_entidad='INTERNO', 
                defaults={
                    'codigo': 'INT',
                    'descripcion': 'INTERNO',
                    'abreviatura': 'INT',
                    'estado': 1
                }
            )
            proveedor_interno, _ = Proveedor.objects.get_or_create(
                numdoc='00000000',
                defaults={
                    'razonsocial': 'INGRESO STOCK DIRECTO',
                    'nombre_comercial': 'INTERNO',
                    'direccion': 'INTERNO',
                    'telefono': '000000000',
                    'email': 'interno@stock.com',
                    'departamento': 'N/A',
                    'provincia': 'N/A',
                    'distrito': 'N/A',
                    'estado': 1,
                    'id_tipo_entidad': tipo_entidad
                }
            )

            compra_stock, _ = Compras.objects.get_or_create(
                numcorrelativo='STOCKDIR',
                defaults={
                    'idproveedor': proveedor_interno,
                    'id_sucursal_id': id_sucursal_activa,
                    'estado': 1,
                    'total_compra': 0.00
                }
            )

            tipo_entidad, _ = TipoEntidad.objects.get_or_create(
                tipo_entidad='INTERNO', 
                defaults={
                    'codigo': 'INT',
                    'descripcion': 'INTERNO',
                    'abreviatura': 'INT',
                    'estado': 1
                }
            )
            proveedor_interno, _ = Proveedor.objects.get_or_create(
                numdoc='00000000',
                defaults={
                    'razonsocial': 'INGRESO STOCK DIRECTO',
                    'nombre_comercial': 'INTERNO',
                    'direccion': 'INTERNO',
                    'telefono': '000000000',
                    'email': 'interno@stock.com',
                    'departamento': 'N/A',
                    'provincia': 'N/A',
                    'distrito': 'N/A',
                    'estado': 1,
                    'id_tipo_entidad': tipo_entidad
                }
            )

            compra_stock, _ = Compras.objects.get_or_create(
                numcorrelativo='STOCKDIR',
                defaults={
                    'idproveedor': proveedor_interno,
                    'id_sucursal_id': id_sucursal_activa,
                    'estado': 1,
                    'total_compra': 0.00
                }
            )

            compra_detalle = CompraDetalle.objects.create(
                idcompra=compra_stock,
                id_vehiculo=vehiculo,
                id_repuesto_comprado=None,
                cantidad=cantidad,
                precio_compra=precio_compra,
                precio_por_mayor=precio_por_mayor,
                precio_minimo=precio_minimo,
                precio_maximo=precio_maximo,
                margen_minimo=0,
                margen_maximo=0,
                subtotal=0.00
            )

            stock_obj, created = Stock.objects.get_or_create(
                id_almacen=almacen,
                id_vehiculo=vehiculo,
                defaults={
                    'idcompradetalle': compra_detalle,
                    'cantidad_disponible': cantidad,
                    'estado': 1
                }
            )
            if not created:
                stock_obj.cantidad_disponible += cantidad
                stock_obj.idcompradetalle = compra_detalle
                stock_obj.save()

            return JsonResponse({'success': True, 'message': 'Vehículo agregado al stock correctamente.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

@transaction.atomic
def agregar_repuesto_stock_directo(request):
    if request.method == "POST":
        try:
            id_sucursal_activa = request.session.get('id_sucursal')
            id_almacen_activo = request.session.get('id_almacen')
            if not id_almacen_activo:
                return JsonResponse({'success': False, 'error': 'Debe tener un almacén activo en sesión.'})

            almacen = Almacenes.objects.get(id_almacen=id_almacen_activo)

            id_repuesto = request.POST.get('id_repuesto')
            ubicacion = request.POST.get('ubicacion', '').strip()
            if not ubicacion or ubicacion.lower() == 'sin ubicacion':
                ubicacion = 'Sin ubicacion'
            cantidad = int(request.POST.get('cantidad', '1'))
            precio_compra = float(request.POST.get('precio_compra', '0.0'))
            precio_por_mayor = float(request.POST.get('precio_por_mayor', '0.0'))
            precio_minimo = float(request.POST.get('precio_minimo', '0.0'))
            precio_maximo = float(request.POST.get('precio_maximo', '0.0'))

            if not id_repuesto:
                return JsonResponse({'success': False, 'error': 'Faltan datos requeridos.'})

            # Si no se ingresó un costo de compra, traer el costo_unitario del catálogo
            if precio_compra == 0:
                costo_catalogo = Repuesto.objects.filter(
                    id_repuesto=int(id_repuesto)
                ).values('costo_unitario').first()
                if costo_catalogo and costo_catalogo['costo_unitario']:
                    precio_compra = float(costo_catalogo['costo_unitario'])

            repuesto_comp, created = RepuestoComp.objects.get_or_create(
                id_repuesto_id=int(id_repuesto),
                ubicacion=ubicacion,
                defaults={
                    'estado': 1
                }
            )
            if not created:
                repuesto_comp.estado = 1
                repuesto_comp.save()

            tipo_entidad, _ = TipoEntidad.objects.get_or_create(
                tipo_entidad='INTERNO', 
                defaults={
                    'codigo': 'INT',
                    'descripcion': 'INTERNO',
                    'abreviatura': 'INT',
                    'estado': 1
                }
            )
            proveedor_interno, _ = Proveedor.objects.get_or_create(
                numdoc='00000000',
                defaults={
                    'razonsocial': 'INGRESO STOCK DIRECTO',
                    'nombre_comercial': 'INTERNO',
                    'direccion': 'INTERNO',
                    'telefono': '000000000',
                    'email': 'interno@stock.com',
                    'departamento': 'N/A',
                    'provincia': 'N/A',
                    'distrito': 'N/A',
                    'estado': 1,
                    'id_tipo_entidad': tipo_entidad
                }
            )

            compra_stock, _ = Compras.objects.get_or_create(
                numcorrelativo='STOCKDIR',
                defaults={
                    'idproveedor': proveedor_interno,
                    'id_sucursal_id': id_sucursal_activa,
                    'estado': 1,
                    'total_compra': 0.00
                }
            )

            compra_detalle = CompraDetalle.objects.create(
                idcompra=compra_stock,
                id_repuesto_comprado=repuesto_comp,
                id_vehiculo=None,
                cantidad=cantidad,
                precio_compra=precio_compra,
                precio_por_mayor=precio_por_mayor,
                precio_minimo=precio_minimo,
                precio_maximo=precio_maximo,
                margen_minimo=0,
                margen_maximo=0,
                subtotal=0.00
            )

            # --- CÁLCULO DEL PRECIO PROMEDIO PONDERADO (PPP) ---
            # Calcular ANTES de sumar el nuevo stock
            stock_actual_agregado = Stock.objects.filter(
                id_repuesto_comprado__id_repuesto_id=int(id_repuesto),
                estado=1
            ).aggregate(total=Sum('cantidad_disponible'))['total'] or 0

            costo_actual = Repuesto.objects.filter(id_repuesto=int(id_repuesto)).values_list('costo_unitario', flat=True).first() or 0.0

            nuevo_ppp = precio_compra
            if stock_actual_agregado > 0:
                valor_inventario_actual = float(stock_actual_agregado) * float(costo_actual)
                valor_nueva_compra = cantidad * precio_compra
                total_unidades = float(stock_actual_agregado) + cantidad
                nuevo_ppp = (valor_inventario_actual + valor_nueva_compra) / total_unidades
                nuevo_ppp = round(nuevo_ppp, 4)
            # ---------------------------------------------------

            stock_obj, created = Stock.objects.get_or_create(
                id_almacen=almacen,
                id_repuesto_comprado=repuesto_comp,
                defaults={
                    'idcompradetalle': compra_detalle,
                    'cantidad_disponible': cantidad,
                    'estado': 1
                }
            )
            if not created:
                stock_obj.cantidad_disponible += cantidad
                stock_obj.idcompradetalle = compra_detalle
                stock_obj.save()

            # --- SINCRONIZAR PRECIOS DEL CATÁLOGO ---
            # El ingreso directo siempre usa la fecha actual, por lo que siempre
            # es el más reciente. Se actualiza el catálogo con una sola consulta.
            Repuesto.objects.filter(id_repuesto=int(id_repuesto)).update(
                costo_unitario=nuevo_ppp,
                precio_por_mayor=precio_por_mayor,
                precio_minimo=precio_minimo,
                precio_sugerido=precio_maximo,
            )
            # -----------------------------------------

            return JsonResponse({'success': True, 'message': 'Repuesto agregado al stock correctamente.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

@transaction.atomic
def editar_vehiculo_stock(request):
    if request.method == "POST":
        try:
            id_vehiculo = request.POST.get('id_vehiculo')
            idcompradetalle = request.POST.get('idcompradetalle')
            
            if not id_vehiculo or not idcompradetalle:
                return JsonResponse({'success': False, 'error': 'Faltan identificadores del vehículo o detalle de compra.'})
                
            vehiculo = Vehiculo.objects.get(id_vehiculo=id_vehiculo)
            detalle_compra = CompraDetalle.objects.get(idcompradetalle=idcompradetalle)
            
            # Datos del vehículo
            serie_motor = request.POST.get('serie_motor', '').strip()
            serie_chasis = request.POST.get('serie_chasis', '').strip()
            anio = request.POST.get('anio', '').strip()
            idestadoproducto = request.POST.get('idestadoproducto')
            placas = request.POST.get('placas', '').strip()
            imperfecciones = request.POST.get('imperfecciones', '').strip()
            
            # Datos de la compra (precios)
            precio_compra = float(request.POST.get('precio_compra', '0.0'))
            precio_por_mayor = float(request.POST.get('precio_por_mayor', '0.0'))
            precio_minimo = float(request.POST.get('precio_minimo', '0.0'))
            precio_maximo = float(request.POST.get('precio_maximo', '0.0'))
            
            if precio_minimo > precio_maximo:
                return JsonResponse({'success': False, 'error': 'El Precio Mínimo no puede ser mayor al Precio Máximo.'})
                
            # Actualizar Vehículo
            vehiculo.serie_motor = serie_motor
            vehiculo.serie_chasis = serie_chasis
            vehiculo.anio = int(anio) if anio else None
            vehiculo.idestadoproducto_id = int(idestadoproducto) if idestadoproducto else None
            vehiculo.placas = placas
            vehiculo.imperfecciones = imperfecciones
            vehiculo.save()
            
            # Actualizar CompraDetalle
            detalle_compra.precio_compra = precio_compra
            detalle_compra.precio_por_mayor = precio_por_mayor
            detalle_compra.precio_minimo = precio_minimo
            detalle_compra.precio_maximo = precio_maximo
            detalle_compra.save()
            
            return JsonResponse({'success': True, 'message': 'Vehículo actualizado correctamente.'})
            
        except Vehiculo.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Vehículo no encontrado.'})
        except CompraDetalle.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Detalle de compra no encontrado.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

@transaction.atomic
def editar_repuesto_stock(request):
    if request.method == "POST":
        try:
            id_stock = request.POST.get('id_stock')
            id_repuesto_comprado = request.POST.get('id_repuesto_comprado')
            idcompradetalle = request.POST.get('idcompradetalle')
            
            if not id_repuesto_comprado or not id_stock:
                return JsonResponse({'success': False, 'error': 'Faltan identificadores del repuesto o stock.'})
                
            stock = Stock.objects.get(id_stock=id_stock)
            # select_related evita una consulta extra cuando accedemos a repuesto.id_repuesto
            repuesto = RepuestoComp.objects.select_related('id_repuesto').get(id_repuesto_comprado=id_repuesto_comprado)
            
            detalle_compra = None
            if idcompradetalle:
                try:
                    detalle_compra = CompraDetalle.objects.select_related('idcompra').get(idcompradetalle=idcompradetalle)
                except CompraDetalle.DoesNotExist:
                    pass

            # Determinar si este detalle corresponde a la compra más reciente del repuesto.
            # Una única consulta con Max evita el problema N+1.
            id_repuesto_base = repuesto.id_repuesto_id
            fecha_ultima_compra = CompraDetalle.objects.filter(
                id_repuesto_comprado__id_repuesto_id=id_repuesto_base,
                idcompra__estado=1
            ).aggregate(ultima=Max('idcompra__fechacompra'))['ultima']

            fecha_detalle_actual = detalle_compra.idcompra.fechacompra if detalle_compra else None
            # Solo actualizar el catálogo si el lote editado proviene de la compra más reciente
            es_el_mas_reciente = (
                fecha_ultima_compra is None or
                (fecha_detalle_actual is not None and fecha_detalle_actual >= fecha_ultima_compra)
            )
            
            # Datos del repuesto
            ubicacion = request.POST.get('ubicacion', '').strip()
            
            # Datos de la compra (precios) y cantidad
            cantidad = int(request.POST.get('cantidad', stock.cantidad_disponible))
            precio_compra = float(request.POST.get('precio_compra', '0.0'))
            precio_por_mayor = float(request.POST.get('precio_por_mayor', '0.0'))
            precio_minimo = float(request.POST.get('precio_minimo', '0.0'))
            precio_maximo = float(request.POST.get('precio_maximo', '0.0'))
            
            if precio_minimo > precio_maximo:
                return JsonResponse({'success': False, 'error': 'El Precio Mínimo no puede ser mayor al Precio Máximo.'})
                
            if cantidad < 0:
                return JsonResponse({'success': False, 'error': 'La cantidad no puede ser negativa.'})
                
            # Lógica de Agrupación (Fusión)
            if repuesto.ubicacion != ubicacion:
                # Buscar otro lote idéntico. Se verifica en memoria para asegurar case-sensitive
                otro_repuesto = None
                for r_cand in RepuestoComp.objects.filter(id_repuesto=repuesto.id_repuesto, estado=1).exclude(id_repuesto_comprado=repuesto.id_repuesto_comprado):
                    if r_cand.ubicacion == ubicacion:
                        otro_repuesto = r_cand
                        break
                        
                if otro_repuesto:
                    from django.db import transaction
                    with transaction.atomic():
                        # Trasladar detalles de compra
                        CompraDetalle.objects.filter(id_repuesto_comprado=repuesto).update(id_repuesto_comprado=otro_repuesto)
                        
                        # Actualizar stock del lote destino
                        otro_stock = Stock.objects.filter(id_repuesto_comprado=otro_repuesto, id_almacen=stock.id_almacen).first()
                        if otro_stock:
                            otro_stock.cantidad_disponible += cantidad
                            otro_stock.save()
                        else:
                            stock.id_repuesto_comprado = otro_repuesto
                            stock.cantidad_disponible = cantidad
                            stock.save()
                            
                        # Actualizar detalle_compra modificado con los nuevos precios
                        if detalle_compra:
                            detalle_compra.id_repuesto_comprado = otro_repuesto
                            detalle_compra.precio_compra = precio_compra
                            detalle_compra.precio_por_mayor = precio_por_mayor
                            detalle_compra.precio_minimo = precio_minimo
                            detalle_compra.precio_maximo = precio_maximo
                            detalle_compra.save()
                        
                        # Actualizar catálogo base (Repuesto) solo si es el más reciente
                        if es_el_mas_reciente and id_repuesto_base:
                            Repuesto.objects.filter(id_repuesto=id_repuesto_base).update(
                                precio_por_mayor=precio_por_mayor,
                precio_minimo=precio_minimo,
                                precio_sugerido=precio_maximo,
                            )

                        # Eliminar el lote antiguo
                        repuesto.delete()
                        
                    return JsonResponse({'success': True, 'message': 'Repuesto actualizado y agrupado correctamente.'})

            # Flujo normal si no hay agrupación
            stock.cantidad_disponible = cantidad
            stock.save()
                
            repuesto.ubicacion = ubicacion
            repuesto.save()
            
            if detalle_compra:
                detalle_compra.precio_compra = precio_compra
                detalle_compra.precio_por_mayor = precio_por_mayor
                detalle_compra.precio_minimo = precio_minimo
                detalle_compra.precio_maximo = precio_maximo
                detalle_compra.save()

            # Actualizar catálogo base (Repuesto) solo si es el lote más reciente
            if es_el_mas_reciente and id_repuesto_base:
                Repuesto.objects.filter(id_repuesto=id_repuesto_base).update(
                    precio_por_mayor=precio_por_mayor,
                precio_minimo=precio_minimo,
                    precio_sugerido=precio_maximo,
                )
            
            return JsonResponse({'success': True, 'message': 'Repuesto actualizado correctamente.'})
            
        except Stock.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Stock no encontrado.'})
        except RepuestoComp.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Repuesto no encontrado.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

def mover_repuesto_stock(request):
    if request.method == "POST":
        try:
            id_stock = request.POST.get('id_stock')
            cantidad_mover = int(request.POST.get('cantidad_mover', '0'))
            nueva_ubicacion = request.POST.get('nueva_ubicacion', '').strip()
            
            if not id_stock or cantidad_mover <= 0 or not nueva_ubicacion:
                return JsonResponse({'success': False, 'error': 'Datos inválidos para mover el repuesto.'})
                
            stock = Stock.objects.get(id_stock=id_stock)
            repuesto = stock.id_repuesto_comprado
            
            if not repuesto:
                return JsonResponse({'success': False, 'error': 'El stock no tiene un repuesto asociado.'})
                
            if cantidad_mover >= stock.cantidad_disponible:
                return JsonResponse({'success': False, 'error': 'Para mover todo el lote, utilice el botón de Editar en lugar de Dividir.'})
                
            if repuesto.ubicacion == nueva_ubicacion:
                return JsonResponse({'success': False, 'error': 'La nueva ubicación debe ser diferente a la actual.'})
                
            # Buscar si ya existe la ubicación destino (Fusionar)
            otro_repuesto = None
            for r_cand in RepuestoComp.objects.filter(id_repuesto=repuesto.id_repuesto, estado=1).exclude(id_repuesto_comprado=repuesto.id_repuesto_comprado):
                if r_cand.ubicacion == nueva_ubicacion:
                    otro_repuesto = r_cand
                    break
                    
            from django.db import transaction
            with transaction.atomic():
                # Restar la cantidad del lote original
                stock.cantidad_disponible -= cantidad_mover
                stock.save()
                
                if otro_repuesto:
                    # Sumar a lote existente
                    otro_stock, _ = Stock.objects.get_or_create(
                        id_repuesto_comprado=otro_repuesto,
                        id_almacen=stock.id_almacen,
                        defaults={'cantidad_disponible': 0, 'estado': 1}
                    )
                    otro_stock.cantidad_disponible += cantidad_mover
                    otro_stock.save()
                else:
                    # Crear nuevo lote
                    nuevo_repuesto = RepuestoComp.objects.create(
                        id_repuesto=repuesto.id_repuesto,
                        ubicacion=nueva_ubicacion,
                        estado=1
                    )
                    # Crear nuevo stock
                    Stock.objects.create(
                        id_repuesto_comprado=nuevo_repuesto,
                        id_almacen=stock.id_almacen,
                        cantidad_disponible=cantidad_mover,
                        estado=1
                    )

                    # Se eliminó la creación del clon de CompraDetalle para mantener
                    # la independencia de los lotes internos y no ensuciar la boleta de compra.

            return JsonResponse({'success': True, 'message': 'Lote dividido y movido correctamente.'})

        except Stock.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Stock no encontrado.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


# ─────────────────────────────────────────────────────────────────────────────
# API: Vehículos paginados (Server-Side Processing)
# ─────────────────────────────────────────────────────────────────────────────
def api_listar_vehiculos_stock(request):
    """Devuelve grupos de vehículos paginados para el frontend AJAX."""
    id2 = request.session.get('idtipousuario')
    if not id2:
        return JsonResponse({'error': 'No autorizado'}, status=401)

    id_sucursal_activa = request.session.get('id_sucursal')
    id_almacen_activo = request.session.get('id_almacen')
    if not id_sucursal_activa:
        return JsonResponse({'error': 'Sin sucursal activa'}, status=400)

    try:
        sucursal_usuario = Sucursales.objects.get(id_sucursal=id_sucursal_activa)
    except Sucursales.DoesNotExist:
        return JsonResponse({'error': 'Sucursal no encontrada'}, status=400)

    page = int(request.GET.get('page', 1))
    page_size = 10
    search = request.GET.get('search', '').strip()

    # Filtro base
    filtro_base = {'estado': 1, 'cantidad_disponible__gt': 0}
    if id_almacen_activo:
        filtro_base['id_almacen_id'] = id_almacen_activo
    else:
        filtro_base['id_almacen__id_sucursal'] = sucursal_usuario

    # Vehículos reservados en pre-financiamiento
    from software.models.PreCreditoModel import PreCredito
    vehiculos_reservados = set(PreCredito.objects.filter(
        estado__in=['pendiente', 'aprobado']
    ).values_list('detalles_vehiculos__id_vehiculo_id', flat=True))

    filtro_v = filtro_base.copy()
    filtro_v.update({
        'id_vehiculo__estado': 1,
        'id_vehiculo__isnull': False,
        'id_vehiculo__idproducto__estado': 1,
    })

    # Búsqueda en servidor
    if search:
        filtro_v['id_vehiculo__idproducto__nomproducto__icontains'] = search
        # Para búsqueda en series/año usamos Q adicional sobre el queryset
        qs_base = Stock.objects.filter(**filtro_v)
        qs_extra = Stock.objects.filter(
            estado=1,
            cantidad_disponible__gt=0,
            id_vehiculo__estado=1,
            id_vehiculo__isnull=False,
            id_vehiculo__idproducto__estado=1,
            **(
                {'id_almacen_id': id_almacen_activo}
                if id_almacen_activo
                else {'id_almacen__id_sucursal': sucursal_usuario}
            ),
        ).filter(
            Q(id_vehiculo__serie_motor__icontains=search) |
            Q(id_vehiculo__serie_chasis__icontains=search) |
            Q(id_vehiculo__anio__icontains=search)
        )
        stocks_vehiculos = (qs_base | qs_extra).distinct().order_by('-fecha_ultima_actualizacion')
    else:
        stocks_vehiculos = Stock.objects.filter(**filtro_v).order_by('-fecha_ultima_actualizacion')

    stocks_vehiculos = stocks_vehiculos.select_related(
        'id_vehiculo__idestadoproducto',
        'id_vehiculo__id_situacion',
        'id_vehiculo__idproducto__idmarca',
        'id_vehiculo__idproducto__idcolor',
        'id_vehiculo__idproducto__idcategoria',
        'id_vehiculo__idproducto__idmodelo',
        'id_vehiculo__idproducto__idcilindrada',
        'id_vehiculo__idproducto__idunidad',
        'id_vehiculo__idproducto__id_configuracion',
        'id_almacen',
        'idcompradetalle',
    )

    # Fallback para stocks sin idcompradetalle
    vehiculos_sin_detalle = [
        s.id_vehiculo.id_vehiculo for s in stocks_vehiculos if not s.idcompradetalle and s.id_vehiculo
    ]
    fallback_v = {}
    if vehiculos_sin_detalle:
        for d in CompraDetalle.objects.filter(
            id_vehiculo__in=vehiculos_sin_detalle
        ).order_by('id_vehiculo', '-idcompradetalle'):
            if d.id_vehiculo_id not in fallback_v:
                fallback_v[d.id_vehiculo_id] = d

    # Agrupar por nombre de producto
    vehiculos_stock_dict = {}
    for s in stocks_vehiculos:
        veh = s.id_vehiculo
        if not veh:
            continue
        det = s.idcompradetalle or fallback_v.get(veh.id_vehiculo)
        if not det:
            continue

        nom = veh.idproducto.nomproducto
        if nom not in vehiculos_stock_dict:
            vehiculos_stock_dict[nom] = {'detalles': [], 'cantidad_total': 0}

        situacion_label = veh.id_situacion.nombre_situacion if veh.id_situacion else 'DISPONIBLE'
        if veh.id_vehiculo in vehiculos_reservados:
            situacion_label = 'RESERVADO (PRE-FINANC.)'

        vehiculos_stock_dict[nom]['detalles'].append({
            'id_vehiculo': veh.id_vehiculo,
            'idcompradetalle': det.idcompradetalle,
            'idestadoproducto': veh.idestadoproducto_id or '',
            'placas': veh.placas or '',
            'serie_motor': veh.serie_motor or '',
            'serie_chasis': veh.serie_chasis or '',
            'anio': veh.anio or '',
            'estado': veh.idestadoproducto.nombreestadoproducto if veh.idestadoproducto else 'Sin estado',
            'imperfecciones': veh.imperfecciones or 'Ninguna',
            'precio_compra': str(det.precio_compra),
            'precio_por_mayor': str(det.precio_por_mayor) if hasattr(det, 'precio_por_mayor') else '0.00',
            'precio_minimo': str(det.precio_minimo),
            'precio_maximo': str(det.precio_maximo),
            'cantidad': s.cantidad_disponible,
            'situacion': situacion_label,
            'almacen': s.id_almacen.nombre_almacen,
        })
        vehiculos_stock_dict[nom]['cantidad_total'] += s.cantidad_disponible

    grupos_lista = [
        {'nombre': k, 'detalles': v['detalles'], 'cantidad_total': v['cantidad_total']}
        for k, v in vehiculos_stock_dict.items()
    ]

    total_grupos = len(grupos_lista)
    total_unidades = sum(g['cantidad_total'] for g in grupos_lista)

    # Paginación de grupos
    start = (page - 1) * page_size
    grupos_pagina = grupos_lista[start:start + page_size]
    total_paginas = max(1, -(-total_grupos // page_size))  # ceil division

    return JsonResponse({
        'grupos': grupos_pagina,
        'total_grupos': total_grupos,
        'total_unidades': total_unidades,
        'pagina_actual': page,
        'total_paginas': total_paginas,
    })


# ─────────────────────────────────────────────────────────────────────────────
# API: Repuestos paginados (Server-Side Processing)
# ─────────────────────────────────────────────────────────────────────────────
def api_listar_repuestos_stock(request):
    """Devuelve grupos de repuestos paginados para el frontend AJAX."""
    id2 = request.session.get('idtipousuario')
    if not id2:
        return JsonResponse({'error': 'No autorizado'}, status=401)

    id_sucursal_activa = request.session.get('id_sucursal')
    id_almacen_activo = request.session.get('id_almacen')
    if not id_sucursal_activa:
        return JsonResponse({'error': 'Sin sucursal activa'}, status=400)

    try:
        sucursal_usuario = Sucursales.objects.get(id_sucursal=id_sucursal_activa)
    except Sucursales.DoesNotExist:
        return JsonResponse({'error': 'Sucursal no encontrada'}, status=400)

    page = int(request.GET.get('page', 1))
    page_size = 10
    search = request.GET.get('search', '').strip()

    filtro_base = {'estado': 1, 'cantidad_disponible__gt': 0}
    if id_almacen_activo:
        filtro_base['id_almacen_id'] = id_almacen_activo
    else:
        filtro_base['id_almacen__id_sucursal'] = sucursal_usuario

    filtro_r = filtro_base.copy()
    filtro_r.update({
        'id_repuesto_comprado__estado': 1,
        'id_repuesto_comprado__isnull': False,
        'id_repuesto_comprado__id_repuesto__estado': 1,
    })

    stocks_repuestos = Stock.objects.filter(**filtro_r).select_related(
        'id_repuesto_comprado__id_repuesto__idmarca',
        'id_repuesto_comprado__id_repuesto__id_categoria_repuesto',
        'id_repuesto_comprado__id_repuesto__idunidad',
        'id_almacen',
        'idcompradetalle',
    ).order_by('-fecha_ultima_actualizacion')

    # Búsqueda en servidor
    if search:
        stocks_repuestos = stocks_repuestos.filter(
            Q(id_repuesto_comprado__id_repuesto__nombre__icontains=search) |
            Q(id_repuesto_comprado__id_repuesto__codigo_barras__icontains=search) |
            Q(id_repuesto_comprado__id_repuesto__idmarca__nombremarca__icontains=search) |
            Q(id_repuesto_comprado__id_repuesto__modelo_referencia__icontains=search) |
            Q(id_repuesto_comprado__ubicacion__icontains=search)
        )

    # Fallback para stocks sin idcompradetalle
    repuestos_sin_detalle = [
        s.id_repuesto_comprado.id_repuesto_comprado
        for s in stocks_repuestos if not s.idcompradetalle and s.id_repuesto_comprado
    ]
    fallback_r = {}
    if repuestos_sin_detalle:
        for d in CompraDetalle.objects.filter(
            id_repuesto_comprado__in=repuestos_sin_detalle
        ).order_by('id_repuesto_comprado', '-idcompradetalle'):
            if d.id_repuesto_comprado_id not in fallback_r:
                fallback_r[d.id_repuesto_comprado_id] = d

    # Agrupar por nombre de repuesto
    repuestos_stock_dict = {}
    for s in stocks_repuestos:
        rc = s.id_repuesto_comprado
        if not rc:
            continue

        det = s.idcompradetalle or fallback_r.get(rc.id_repuesto_comprado)
        rep = rc.id_repuesto

        p_compra = rep.costo_unitario or (det.precio_compra if det else 0)
        p_por_mayor = getattr(rep, 'precio_por_mayor', 0) or (getattr(det, 'precio_por_mayor', 0) if det else 0)
        p_minimo = rep.precio_minimo or (det.precio_minimo if det else 0)
        p_maximo = rep.precio_sugerido or (det.precio_maximo if det else 0)

        nom = rep.nombre
        if nom not in repuestos_stock_dict:
            repuestos_stock_dict[nom] = {
                'detalles': [],
                'cantidad_total': 0,
                'stock_minimo': rep.stock_minimo or 0,
                'stock_maximo': rep.stock_maximo or 0,
            }

        repuestos_stock_dict[nom]['detalles'].append({
            'id_stock': s.id_stock,
            'id_repuesto_comprado': rc.id_repuesto_comprado,
            'idcompradetalle': det.idcompradetalle if det else '',
            'codigo_barras': rep.codigo_barras or 'N/A',
            'marca': rep.idmarca.nombremarca if rep.idmarca else 'N/A',
            'modelo': rep.modelo_referencia or 'N/A',
            'categoria': rep.id_categoria_repuesto.nomcategoria if rep.id_categoria_repuesto else 'N/A',
            'ubicacion': rc.ubicacion or 'Sin ubicacion',
            'precio_compra': str(p_compra),
            'precio_por_mayor': str(p_por_mayor),
            'precio_minimo': str(p_minimo),
            'precio_maximo': str(p_maximo),
            'cantidad': s.cantidad_disponible,
            'almacen': s.id_almacen.nombre_almacen,
        })
        repuestos_stock_dict[nom]['cantidad_total'] += s.cantidad_disponible

    # Construir lista con estado de salud
    grupos_lista = []
    for nom, v in repuestos_stock_dict.items():
        pct = 0
        if v['stock_maximo'] > 0:
            pct = min(100, int((v['cantidad_total'] / v['stock_maximo']) * 100))
        elif v['stock_minimo'] > 0 and v['cantidad_total'] >= v['stock_minimo']:
            pct = 100

        estado_salud = 'optimo'
        if v['cantidad_total'] <= v['stock_minimo']:
            estado_salud = 'critico'
        elif v['stock_maximo'] > 0 and v['cantidad_total'] > v['stock_maximo']:
            estado_salud = 'exceso'

        grupos_lista.append({
            'nombre': nom,
            'detalles': v['detalles'],
            'cantidad_total': v['cantidad_total'],
            'stock_minimo': v['stock_minimo'],
            'stock_maximo': v['stock_maximo'],
            'porcentaje_stock': pct,
            'estado_salud': estado_salud,
        })

    total_grupos = len(grupos_lista)
    total_unidades = sum(g['cantidad_total'] for g in grupos_lista)

    start = (page - 1) * page_size
    grupos_pagina = grupos_lista[start:start + page_size]
    total_paginas = max(1, -(-total_grupos // page_size))

    return JsonResponse({
        'grupos': grupos_pagina,
        'total_grupos': total_grupos,
        'total_unidades': total_unidades,
        'pagina_actual': page,
        'total_paginas': total_paginas,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Vista: Exportar Excel completo desde el backend
# ─────────────────────────────────────────────────────────────────────────────
def exportar_excel_stock(request):
    """Genera y descarga el archivo Excel de todo el inventario."""
    id2 = request.session.get('idtipousuario')
    if not id2:
        return HttpResponse('No autorizado', status=401)

    id_sucursal_activa = request.session.get('id_sucursal')
    id_almacen_activo = request.session.get('id_almacen')
    if not id_sucursal_activa:
        return HttpResponse('Sin sucursal activa', status=400)

    try:
        sucursal_usuario = Sucursales.objects.get(id_sucursal=id_sucursal_activa)
    except Sucursales.DoesNotExist:
        return HttpResponse('Sucursal no encontrada', status=400)

    filtro_base = {'estado': 1, 'cantidad_disponible__gt': 0}
    if id_almacen_activo:
        filtro_base['id_almacen_id'] = id_almacen_activo
    else:
        filtro_base['id_almacen__id_sucursal'] = sucursal_usuario

    # ── Vehículos ──
    filtro_v = filtro_base.copy()
    filtro_v.update({
        'id_vehiculo__estado': 1, 'id_vehiculo__isnull': False,
        'id_vehiculo__idproducto__estado': 1,
    })
    stocks_v = Stock.objects.filter(**filtro_v).select_related(
        'id_vehiculo__idproducto__idmarca', 'id_vehiculo__idproducto__idcolor',
        'id_vehiculo__idproducto__idcategoria', 'id_vehiculo__idproducto__idmodelo',
        'id_vehiculo__idproducto__idcilindrada', 'id_vehiculo__idproducto__idunidad',
        'id_vehiculo__idproducto__id_configuracion',
        'id_vehiculo__idestadoproducto', 'id_vehiculo__id_situacion',
        'id_almacen', 'idcompradetalle',
    )
    fallback_v_xls = {}
    vids = [s.id_vehiculo.id_vehiculo for s in stocks_v if not s.idcompradetalle and s.id_vehiculo]
    if vids:
        for d in CompraDetalle.objects.filter(id_vehiculo__in=vids).order_by('id_vehiculo', '-idcompradetalle'):
            if d.id_vehiculo_id not in fallback_v_xls:
                fallback_v_xls[d.id_vehiculo_id] = d

    from software.models.PreCreditoModel import PreCredito
    vehiculos_reservados = set(PreCredito.objects.filter(
        estado__in=['pendiente', 'aprobado']
    ).values_list('detalles_vehiculos__id_vehiculo_id', flat=True))

    filas_v = []
    for s in stocks_v:
        veh = s.id_vehiculo
        if not veh:
            continue
        det = s.idcompradetalle or fallback_v_xls.get(veh.id_vehiculo)
        if not det:
            continue
        situacion = veh.id_situacion.nombre_situacion if veh.id_situacion else 'DISPONIBLE'
        if veh.id_vehiculo in vehiculos_reservados:
            situacion = 'RESERVADO (PRE-FINANC.)'
        filas_v.append({
            'nombre': veh.idproducto.nomproducto,
            'marca': veh.idproducto.idmarca.nombremarca if veh.idproducto.idmarca else '',
            'serie_chasis': veh.serie_chasis or '',
            'serie_motor': veh.serie_motor or '',
            'color': veh.idproducto.idcolor.nombrecolor if veh.idproducto.idcolor else '',
            'anio': veh.anio or '',
            'tipo_vehiculo': veh.idproducto.idcategoria.nomcategoria if veh.idproducto.idcategoria else '',
            'modelos': veh.idproducto.idmodelo.nombremodelo if veh.idproducto.idmodelo else '',
            'cilindrada': veh.idproducto.idcilindrada.cilindrada_cc if veh.idproducto.idcilindrada else '',
            'unidades': veh.idproducto.idunidad.abrunidad if veh.idproducto.idunidad else '',
            'config': veh.idproducto.id_configuracion.nombre if veh.idproducto.id_configuracion else '',
            'estado': veh.idestadoproducto.nombreestadoproducto if veh.idestadoproducto else '',
            'situacion': situacion,
            'imperfecciones': veh.imperfecciones or 'Ninguna',
            'p_compra': float(det.precio_compra) if det.precio_compra else 0,
            'p_mayor': float(det.precio_minimo) if det.precio_minimo else 0,
            'p_por_mayor': float(det.precio_por_mayor) if hasattr(det, 'precio_por_mayor') and det.precio_por_mayor else 0,
            'p_menor': float(det.precio_maximo) if det.precio_maximo else 0,
            'cantidad': s.cantidad_disponible,
        })

    # ── Repuestos ──
    filtro_r = filtro_base.copy()
    filtro_r.update({
        'id_repuesto_comprado__estado': 1, 'id_repuesto_comprado__isnull': False,
        'id_repuesto_comprado__id_repuesto__estado': 1,
    })
    stocks_r = Stock.objects.filter(**filtro_r).select_related(
        'id_repuesto_comprado__id_repuesto__idmarca',
        'id_repuesto_comprado__id_repuesto__id_categoria_repuesto',
        'id_almacen', 'idcompradetalle',
    )
    fallback_r_xls = {}
    rids = [s.id_repuesto_comprado.id_repuesto_comprado for s in stocks_r if not s.idcompradetalle and s.id_repuesto_comprado]
    if rids:
        for d in CompraDetalle.objects.filter(id_repuesto_comprado__in=rids).order_by('id_repuesto_comprado', '-idcompradetalle'):
            if d.id_repuesto_comprado_id not in fallback_r_xls:
                fallback_r_xls[d.id_repuesto_comprado_id] = d

    filas_r = []
    for s in stocks_r:
        rc = s.id_repuesto_comprado
        if not rc:
            continue
        rep = rc.id_repuesto
        det = s.idcompradetalle or fallback_r_xls.get(rc.id_repuesto_comprado)
        p_compra = float(det.precio_compra) if det and det.precio_compra else (float(rep.costo_unitario) if rep.costo_unitario else 0)
        p_por_mayor = float(rep.precio_por_mayor) if getattr(rep, 'precio_por_mayor', None) else (float(det.precio_por_mayor) if det and getattr(det, 'precio_por_mayor', None) else 0)
        p_mayor = float(rep.precio_minimo) if rep.precio_minimo else (float(det.precio_minimo) if det and det.precio_minimo else 0)
        p_menor = float(rep.precio_sugerido) if rep.precio_sugerido else (float(det.precio_maximo) if det and det.precio_maximo else 0)
        filas_r.append({
            'nombre': rep.nombre,
            'categoria': rep.id_categoria_repuesto.nomcategoria if rep.id_categoria_repuesto else '',
            'marca': rep.idmarca.nombremarca if rep.idmarca else '',
            'modelo': rep.modelo_referencia or '',
            'codigo': rep.codigo_barras or '',
            'ubicacion': rc.ubicacion or '',
            'p_compra': p_compra,
            'p_mayor': p_mayor,
            'p_menor': p_menor,
            'cantidad': s.cantidad_disponible,
        })

    # ── Construir HTML del Excel ──
    tabla_html = """
<html xmlns:x="urn:schemas-microsoft-com:office:excel">
<head><meta charset="utf-8">
<style>
  table { border-collapse: collapse; font-family: Calibri, Arial, sans-serif; }
  th.vehiculo { background-color: #FFFF00; color: black; font-weight: bold; border: 1px solid black; padding: 5px; text-align: left; }
  th.repuesto { background-color: #00B0F0; color: white; font-weight: bold; border: 1px solid black; padding: 5px; text-align: left; }
  td { border: 1px solid black; padding: 5px; text-align: left; }
</style></head><body>
<h3>STOCK DE VEHÍCULOS</h3>
<table><thead><tr>
  <th class="vehiculo">Marca</th><th class="vehiculo">SERIE CHASIS</th>
  <th class="vehiculo">SERIE MOTOR</th><th class="vehiculo">Color</th>
  <th class="vehiculo">AÑO</th><th class="vehiculo">Tipo Vehículo</th>
  <th class="vehiculo">Modelo</th><th class="vehiculo">Cilindrada</th>
  <th class="vehiculo">Unidades</th><th class="vehiculo">Config</th>
  <th class="vehiculo">Estado</th><th class="vehiculo">Situación</th>
  <th class="vehiculo">Imperfecciones</th>
  <th class="vehiculo">P. Compra</th><th class="vehiculo">P. Mayor</th><th class="vehiculo">P. Menor</th>
</tr></thead><tbody>
"""
    for f in filas_v:
        tabla_html += f"""<tr>
  <td>{f['marca']}</td><td>{f['serie_chasis']}</td><td>{f['serie_motor']}</td>
  <td>{f['color']}</td><td>{f['anio']}</td><td>{f['tipo_vehiculo']}</td>
  <td>{f['modelos']}</td><td>{f['cilindrada']}</td><td>{f['unidades']}</td>
  <td>{f['config']}</td><td>{f['estado']}</td><td>{f['situacion']}</td>
  <td>{f['imperfecciones']}</td>
  <td>S/ {f['p_compra']:.2f}</td><td>S/ {f['p_mayor']:.2f}</td><td>S/ {f['p_menor']:.2f}</td>
</tr>"""

    tabla_html += """</tbody></table><br><br>
<h3>STOCK DE REPUESTOS</h3>
<table><thead><tr>
  <th class="repuesto">Repuesto</th><th class="repuesto">Categoría</th>
  <th class="repuesto">Marca</th><th class="repuesto">Modelo/Ref</th>
  <th class="repuesto">Cód. Barras</th><th class="repuesto">Ubicación</th>
  <th class="repuesto">P. Compra</th><th class="repuesto">P. Mayor</th>
  <th class="repuesto">P. Menor</th><th class="repuesto">Cantidad</th>
</tr></thead><tbody>
"""
    for f in filas_r:
        tabla_html += f"""<tr>
  <td>{f['nombre']}</td><td>{f['categoria']}</td><td>{f['marca']}</td>
  <td>{f['modelo']}</td><td>{f['codigo']}</td><td>{f['ubicacion']}</td>
  <td>S/ {f['p_compra']:.2f}</td><td>S/ {f['p_mayor']:.2f}</td><td>S/ {f['p_menor']:.2f}</td>
  <td style="font-weight:bold;color:green;">{f['cantidad']}</td>
</tr>"""

    tabla_html += "</tbody></table></body></html>"

    response = HttpResponse(
        tabla_html,
        content_type='application/vnd.ms-excel; charset=utf-8',
    )
    response['Content-Disposition'] = 'attachment; filename="Reporte_General_Inventario.xls"'
    return response


# ─────────────────────────────────────────────────────────────────────────────
# API: Búsqueda Global de Stock (Todas las Sucursales)
# ─────────────────────────────────────────────────────────────────────────────
def api_buscar_stock_global(request):
    """
    Busca stock disponible en TODAS las sucursales y almacenes activos.
    Una sola query con select_related + .only() — sin N+1.
    Solo se ejecuta al presionar "Buscar": no afecta la carga del módulo.
    """
    id2 = request.session.get('idtipousuario')
    if not id2:
        return JsonResponse({'error': 'No autorizado'}, status=401)

    search = request.GET.get('search', '').strip()
    if len(search) < 3:
        return JsonResponse({'error': 'Mínimo 3 caracteres para buscar'}, status=400)

    id_sucursal_sesion = request.session.get('id_sucursal')

    # UNA SOLA QUERY — select_related elimina N+1 completamente
    qs = Stock.objects.filter(
        estado=1,
        cantidad_disponible__gt=0,
    ).filter(
        Q(id_vehiculo__idproducto__nomproducto__icontains=search)
        | Q(id_vehiculo__serie_motor__icontains=search)
        | Q(id_vehiculo__serie_chasis__icontains=search)
        | Q(id_repuesto_comprado__id_repuesto__nombre__icontains=search)
        | Q(id_repuesto_comprado__id_repuesto__codigo_barras__icontains=search)
    ).select_related(
        'id_almacen__id_sucursal',
        'id_vehiculo__idproducto',
        'id_repuesto_comprado__id_repuesto',
    ).only(
        'id_stock', 'cantidad_disponible',
        'id_almacen__nombre_almacen',
        'id_almacen__id_sucursal__id_sucursal',
        'id_almacen__id_sucursal__nombre_sucursal',
        'id_vehiculo__id_vehiculo',
        'id_vehiculo__idproducto__nomproducto',
        'id_vehiculo__serie_motor',
        'id_vehiculo__serie_chasis',
        'id_repuesto_comprado__id_repuesto_comprado',
        'id_repuesto_comprado__id_repuesto__nombre',
        'id_repuesto_comprado__id_repuesto__codigo_barras',
    )

    # Agrupar en Python — sin queries adicionales
    grupos = {}
    total_items = 0

    for s in qs:
        alm = s.id_almacen
        suc = alm.id_sucursal
        es_propia = (str(suc.id_sucursal) == str(id_sucursal_sesion))

        if s.id_vehiculo:
            veh = s.id_vehiculo
            item = {
                'tipo': 'vehiculo',
                'id_stock': s.id_stock,
                'id_item': veh.id_vehiculo,
                'nombre': veh.idproducto.nomproducto,
                'detalle': 'Motor: {} | Chasis: {}'.format(
                    veh.serie_motor or '—', veh.serie_chasis or '—'
                ),
                'cantidad': s.cantidad_disponible,
                'almacen': alm.nombre_almacen,
                'sucursal': suc.nombre_sucursal,
                'id_almacen': alm.id_almacen,
                'es_propia': es_propia,
            }
        elif s.id_repuesto_comprado:
            rc = s.id_repuesto_comprado
            rep = rc.id_repuesto
            item = {
                'tipo': 'repuesto',
                'id_stock': s.id_stock,
                'id_item': rc.id_repuesto_comprado,
                'nombre': rep.nombre,
                'detalle': 'Código: {}'.format(rep.codigo_barras or 'S/N'),
                'cantidad': s.cantidad_disponible,
                'almacen': alm.nombre_almacen,
                'sucursal': suc.nombre_sucursal,
                'id_almacen': alm.id_almacen,
                'es_propia': es_propia,
            }
        else:
            continue

        key = suc.nombre_sucursal
        if key not in grupos:
            grupos[key] = {
                'sucursal': suc.nombre_sucursal,
                'es_propia': es_propia,
                'items': [],
            }
        grupos[key]['items'].append(item)
        total_items += 1

    # La sucursal propia aparece primero
    grupos_lista = sorted(
        grupos.values(),
        key=lambda g: (0 if g['es_propia'] else 1, g['sucursal'])
    )

    return JsonResponse({
        'grupos': grupos_lista,
        'total': total_items,
    })


# ─────────────────────────────────────────────────────────────────────────────
# API: Solicitar Traslado desde el módulo de Stock
# ─────────────────────────────────────────────────────────────────────────────
@transaction.atomic
def api_solicitar_traslado_desde_stock(request):
    """
    Crea una Transferencia en estado 'pendiente' desde la búsqueda global de stock.
    Reutiliza el mismo patrón de nueva_transferencia() en transferencias.py.
    NO descuenta stock: el descuento ocurre cuando el admin confirma el despacho.
    """
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)

    id2 = request.session.get('idtipousuario')
    if not id2:
        return JsonResponse({'ok': False, 'error': 'No autorizado'}, status=401)

    id_stock_origen = request.POST.get('id_stock')
    cantidad_raw = request.POST.get('cantidad', '1')
    id_almacen_destino = request.session.get('id_almacen')
    idusuario = request.session.get('idusuario')

    if not id_almacen_destino:
        return JsonResponse({
            'ok': False,
            'error': 'Sin almacén activo en sesión. Configure su almacén antes de solicitar traslados.'
        }, status=400)

    if not id_stock_origen:
        return JsonResponse({'ok': False, 'error': 'Stock de origen no especificado'}, status=400)

    try:
        cantidad = int(cantidad_raw)
        if cantidad < 1:
            raise ValueError()
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'Cantidad inválida'}, status=400)

    try:
        stock_origen = Stock.objects.select_related(
            'id_almacen',
            'id_vehiculo__idproducto',
            'id_repuesto_comprado__id_repuesto',
        ).get(id_stock=id_stock_origen, estado=1)
    except Stock.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Registro de stock no encontrado'}, status=404)

    # Validar que no sea el mismo almacén
    if str(stock_origen.id_almacen_id) == str(id_almacen_destino):
        return JsonResponse({'ok': False, 'error': 'El origen y destino son el mismo almacén'}, status=400)

    # Validar disponibilidad suficiente
    if stock_origen.cantidad_disponible < cantidad:
        return JsonResponse({
            'ok': False,
            'error': 'Stock insuficiente en el origen. Disponible: {}'.format(stock_origen.cantidad_disponible)
        }, status=400)

    from django.utils import timezone

    # Crear la Transferencia (mismo patrón que nueva_transferencia en transferencias.py)
    transferencia = Transferencia.objects.create(
        id_almacen_origen=stock_origen.id_almacen,
        id_almacen_destino_id=id_almacen_destino,
        idusuario_solicita_id=idusuario,
        fecha_transferencia=timezone.now().date(),
        observaciones='Solicitud generada desde módulo Stock (búsqueda multi-sucursal).',
        tipo_transferencia='sucursal_a_sucursal',
        estado='pendiente',
    )

    # bulk_create — 1 INSERT en lugar de N (mismo patrón que nueva_transferencia)
    if stock_origen.id_vehiculo:
        nuevos_detalles = [DetalleTransferencia(
            id_transferencia=transferencia,
            id_vehiculo=stock_origen.id_vehiculo,
            cantidad=1,
            estado=1,
        )]
        nombre_item = stock_origen.id_vehiculo.idproducto.nomproducto
    else:
        nuevos_detalles = [DetalleTransferencia(
            id_transferencia=transferencia,
            id_repuesto_comprado=stock_origen.id_repuesto_comprado,
            cantidad=cantidad,
            estado=1,
        )]
        nombre_item = stock_origen.id_repuesto_comprado.id_repuesto.nombre

    DetalleTransferencia.objects.bulk_create(nuevos_detalles)

    return JsonResponse({
        'ok': True,
        'id_transferencia': transferencia.id_transferencia,
        'nombre_item': nombre_item,
        'message': 'Solicitud #{} creada correctamente. Pendiente de aprobación del administrador.'.format(
            transferencia.id_transferencia
        ),
    })
