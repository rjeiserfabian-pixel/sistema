
from django.urls import path



from .views import login
from .views import categorias
from .views import marcas
from .views import colores
from .views import cilindradas
from .views import estadoproductos
from .views import configuracion
from .views import compras
from .views import productos
from .views import repuestos
from .views import unidades
from .views import usuarios
from .views import ventas
from .views import permisos
from .views import cpanel
from .views import tipoUsuarios
from .views import registroCaja
from .views import stock
from .views import password_reset
from .views import transferencias
from .views import movimientosCaja
from .views import creditos
from .views import clientes
from .views import proveedores
from .views import imposicionPlacas
from .views import transporte
from .views import regiones
from .views import provincias
from .views import distritos
from .views import sucursales
from .views import almacenes
from .views import cajas
from .views import historialCajas
from .views import tipo_comprobante
from .views import serie_comprobante
from .views import proforma
from .views import reportes
from .views import sunat
from .views import cuentas_por_pagar
from .views import vistas_retencion
from .views import pre_financiamiento
from .views import modelos
from .views import garantes
from .views import situacionVehiculo
from .views import configuracion_vehicular
from .views import zonas_credito
from .views import factores_credito
from .views import gestion_igv
from .views import canales_pago
from .views import autorizaciones
from .views import bonificaciones
from .views import servicios
from .views import configuracion_repuestos
from .views import trazabilidad
from .views import cuentas_por_cobrar
from .views.sunat import api_tipo_cambio
from .views import facturacion_comprobantes

urlpatterns = [


    #login
    path('', login.index, name="index"),
    path('api/tipo-cambio/', api_tipo_cambio, name='api_tipo_cambio'),
    path('login', login.login, name="login"),
    path('logout', login.logout, name="logout"),

    # Autorizaciones vía WhatsApp
    path('autorizaciones/solicitar/', autorizaciones.solicitar_codigo_view, name='solicitar_codigo_auth'),
    path('autorizaciones/validar/', autorizaciones.validar_codigo_view, name='validar_codigo_auth'),

    # Cuentas por Cobrar (App Móvil)
    path('cuentas-por-cobrar/', cuentas_por_cobrar.index, name='cuentas_por_cobrar'),
    path('cuentas-por-cobrar/api/listar/', cuentas_por_cobrar.api_listar_clientes_cobrar, name='api_listar_clientes_cobrar'),
    path('cuentas-por-cobrar/cliente/<int:idcliente>/', cuentas_por_cobrar.detalle_cobro, name='cobro_cliente'),
    path('cuentas-por-cobrar/procesar/', cuentas_por_cobrar.procesar_cobro, name='procesar_cobro_cliente'),

    # Recuperación de contraseña
    path('recuperar-contrasena/', password_reset.solicitar_recuperacion, name="solicitar_recuperacion"),
    path('restablecer-contrasena/<str:token>/', password_reset.restablecer_contrasena, name="restablecer_contrasena"),

    # Nuevas rutas para manejo de caja
    path('api/obtener-datos-apertura/', login.obtener_datos_apertura, name="obtener_datos_apertura"),
    path('api/obtener-cajas-almacenes/', login.obtener_cajas_almacenes, name="obtener_cajas_almacenes"),
    path('api/cambiar-contexto/', login.cambiar_contexto, name="cambiar_contexto"),
    path('api/abrir-caja/', login.abrir_caja, name="abrir_caja"),
    path('api/cerrar-caja/', login.cerrar_caja, name="cerrar_caja"),
    path('api/obtener-saldo-actual/', login.obtener_saldo_actual, name='obtener_saldo_actual'),

    # Unidades
    path('unidades/', unidades.unidades, name='unidades'),
    path('unidades/agregar/', unidades.agregar, name='unidadesAgregar'),
    path('unidades/editar/', unidades.editar, name='unidadesEditar'),
    path('unidades/activo/<int:id>/', unidades.activo, name='unidadesActivo'),
    path('unidades/desactivo/<int:id>/', unidades.desactivo, name='unidadesDesactivo'),
        
    #Usuarios
    path('usuarios', usuarios.usuarios, name="usuarios"),
    path('usuarios/agregar', usuarios.agregar, name="usuarioAgregar"),
    path('usuarios/editar', usuarios.editar, name="usuarioEditar"),
    path('usuarios/eliminar/<int:id>', usuarios.eliminar, name="usuarioEliminar"),

    # Perfil de Usuario
    path('mi-cuenta/', usuarios.mi_perfil, name='mi_perfil'),
    path('mi-cuenta/actualizar/', usuarios.actualizar_perfil, name='actualizar_perfil'),
    path('mi-cuenta/cambiar-contrasena/', usuarios.cambiar_contrasena, name='cambiar_contrasena'),
    
    # compras
    path('compras/', compras.compras, name="compras"),
    path('compras/api/listar/', compras.api_listar_compras, name='api_listar_compras'),
    path('compras/agregar/', compras.nueva_compra, name="agregarCompras"), 
    path('api/obtener-compra/<int:id>/', compras.obtener_compra, name='obtener_compra'),
    path('compras/actualizar/<int:id>/', compras.actualizar_compra, name='actualizar_compra'),
    path('compras/eliminar/<int:id>/', compras.eliminar_compra, name='eliminar_compra'),
    path('compras/obtener-detalle/<int:id>/', compras.api_obtener_detalle_compra, name='api_obtener_detalle_compra'),
    path('compras/pdf/<int:idcompra>/', compras.compra_pdf, name='compra_pdf'),
    path('api/compras/crear-producto/', compras.api_crear_producto_compra, name='api_crear_producto_compra'),
    path('api/compras/crear-repuesto/', compras.api_crear_repuesto_compra, name='api_crear_repuesto_compra'),
    path('api/compras/validar-series/', compras.api_validar_series_vehiculo, name='api_validar_series_vehiculo'),
    path('stock/', stock.stock, name='stock'),
     
    # ventas
    path('ventas/', ventas.ventas, name="ventas"),
    path('ventas/api/listar/', ventas.api_listar_ventas, name='api_listar_ventas'),
    path('ventas/cobrar-pendiente/', ventas.cobrar_venta_pendiente, name='cobrar_venta_pendiente'),
    path('ventas/nueva/', ventas.nueva_venta, name="nuevaVenta"),
    path('ventas/obtener-series/', ventas.obtener_series, name="obtenerSeries"),
    path('ventas/imprimir/<int:idventa>/', ventas.imprimir_comprobante, name="imprimir_comprobante"),
    path('ventas/obtener-factor/', ventas.obtener_factor_credito, name='obtener_factor_credito'),
    path('ventas/obtener-cuotas/', ventas.obtener_cuotas_por_zona, name='obtener_cuotas_por_zona'),
    path('ventas/obtener/<int:id>/', ventas.obtener_venta, name='obtener_venta'),
    path('ventas/obtener-detalle/<int:id>/', ventas.obtener_detalle_venta, name='obtener_detalle_venta'),
    path('ventas/actualizar/<int:id>/', ventas.actualizar_venta, name='actualizar_venta'),
    path('ventas/eliminar/<int:id>/', ventas.eliminar_venta, name='eliminar_venta'),

    #categorias
    path('categorias', categorias.categorias, name="categorias"),
    path('categorias/agregar', categorias.agregar, name="agregarCategorias"),
    path('categorias/editar', categorias.editar, name="editarCategorias"),
    path('categorias/eliminarCategoria/<int:id>', categorias.eliminar, name="categoriasEliminar"),
    
    # Marcas
    path('marcas', marcas.marcas, name="marcas"),
    path('marcas/api/listar/', marcas.api_listar_marcas, name='api_listar_marcas'),
    path('marcas/agregar', marcas.agregar, name="agregarMarcas"),
    path('marcas/editar', marcas.editar, name="editarMarcas"),
    path('marcas/eliminarMarca/<int:id>', marcas.eliminar, name="marcasEliminar"),

    # Modelos
    path('modelos', modelos.modelos, name="modelos"),
    path('modelos/api/listar/', modelos.api_listar_modelos, name='api_listar_modelos'),
    path('modelos/agregar', modelos.agregar, name="agregarModelos"),
    path('modelos/editar', modelos.editar, name="editarModelos"),
    path('modelos/eliminar/<int:id>', modelos.eliminar, name="eliminarModelos"),


    # Colores
    path('colores', colores.colores, name="colores"),
    path('colores/agregar', colores.agregar, name="agregarColores"),
    path('colores/editar', colores.editar, name="editarColores"),
    path('colores/eliminarColor/<int:id>', colores.eliminar, name="coloresEliminar"),

    # Detalle de Color
    path('colores/detalle/listar/', colores.listar_detalle_color, name='listarDetalleColor'),
    path('colores/detalle/guardar/', colores.guardar_detalle_color, name='guardarDetalleColor'),
    path('colores/detalle/eliminar/', colores.eliminar_detalle_color, name='eliminarDetalleColor'),

    # Cilindradas
    path('cilindradas', cilindradas.cilindradas, name="cilindradas"),
    path('cilindradas/agregar', cilindradas.agregar, name="agregarCilindradas"),
    path('cilindradas/editar', cilindradas.editar, name="editarCilindradas"),
    path('cilindradas/eliminarCilindrada/<int:id>', cilindradas.eliminar, name="cilindradasEliminar"),
    
    # Estado Producto
    path('estadoproductos', estadoproductos.estadoproductos, name="estadoproductos"),
    path('estadoproductos/agregar', estadoproductos.agregar, name="agregarEstadoProductos"),
    path('estadoproductos/editar', estadoproductos.editar, name="editarEstadoProductos"),
    path('estadoproductos/eliminarEstadoProducto/<int:id>', estadoproductos.eliminar, name="estadoproductosEliminar"),

    #Permisos
    path('permisos', permisos.permisos, name="permisos"),
    path('permisos/agregaPermiso', permisos.agregaPermiso, name="agregaPermiso"),
    path('editarPermiso/', permisos.editarPermiso, name='editarPermiso'),
    path('permisos/eliminarPermiso/<int:id>', permisos.eliminarPermiso, name="eliminarPermiso"),
     
    #productos
    path('productos', productos.productos, name="productos"),
    path('productos/agregar', productos.agregar, name="productosAgregar"),
    path('productos/editar', productos.editado, name="productosEditado"),
    path('productos/eliminarProducto/<int:idproducto>', productos.eliminar, name="eliminarProducto"),
    path('productos/api/vehiculos/', productos.api_listar_vehiculos, name="api_listar_vehiculos"),
    path('productos/api/repuestos/', productos.api_listar_repuestos, name="api_listar_repuestos"),
    path('productos/api/servicios/', productos.api_listar_servicios, name="api_listar_servicios"),

    #Repuestos (catalogo)
    path('repuestos/agregar', repuestos.agregar_repuesto, name="agregarRepuesto"),
    path('repuestos/editar', repuestos.editar_repuesto, name="editarRepuesto"),
    path('repuestos/eliminar/<int:id_repuesto>', repuestos.eliminar_repuesto, name="eliminarRepuesto"),

    # Configuracion de Repuestos (nuevo submodulo)
    path('configuracion-repuestos/', configuracion_repuestos.configuracion_repuestos, name='configuracion_repuestos'),
    # API Categorias Repuesto
    path('api/repuestos/categorias/', configuracion_repuestos.listar_categorias_repuesto, name='listar_categorias_repuesto'),
    path('api/repuestos/categorias/guardar/', configuracion_repuestos.guardar_categoria_repuesto, name='guardar_categoria_repuesto'),
    path('api/repuestos/categorias/eliminar/', configuracion_repuestos.eliminar_categoria_repuesto, name='eliminar_categoria_repuesto'),
    # API Marcas Repuesto
    path('api/repuestos/marcas/', configuracion_repuestos.listar_marcas_repuesto, name='listar_marcas_repuesto'),
    path('api/repuestos/marcas/guardar/', configuracion_repuestos.guardar_marca_repuesto, name='guardar_marca_repuesto'),
    path('api/repuestos/marcas/eliminar/', configuracion_repuestos.eliminar_marca_repuesto, name='eliminar_marca_repuesto'),
    # API Garantias Repuesto
    path('api/repuestos/garantias/', configuracion_repuestos.listar_garantias_repuesto, name='listar_garantias_repuesto'),
    path('api/repuestos/garantias/guardar/', configuracion_repuestos.guardar_garantia_repuesto, name='guardar_garantia_repuesto'),
    path('api/repuestos/garantias/eliminar/', configuracion_repuestos.eliminar_garantia_repuesto, name='eliminar_garantia_repuesto'),
    
    #configuracion
    path('configuracion', configuracion.configuracion, name="configuracion"),
    path('configuracion/editarEmpresa', configuracion.editarEmpresa, name="editarEmpresa"),
    path('configuracion/produccion/<int:id>', configuracion.produccion, name="produccion"),
    path('configuracion/desarrollo/<int:id>', configuracion.desarrollo, name="desarrollo"),
    path('obtener-empresa-ruc/', configuracion.obtener_datos_empresa_por_ruc, name='obtener_empresa_ruc'),

    #cpanel
    path('cpanel', cpanel.cpanel, name="cpanel"),

    #Tipo usuarios
    path('tipousuarios/', tipoUsuarios.tipoUsuarios, name="tipoUsuarios"),
    path('tipousuarios/agregar/', tipoUsuarios.tipousuariosAgregar, name="tipousuariosAgregar"),
    path('tipousuarios/editar/', tipoUsuarios.tipousuariosEditar, name="tipousuariosEditar"),
    path('tipousuarios/eliminar/<int:id>/', tipoUsuarios.tipousuariosEliminar, name="tipousuariosEliminar"),

    # TRANSFERENCIAS
    path('transferencias/', transferencias.transferencias, name='transferencias'),
    path('transferencias/api/listar/', transferencias.api_listar_transferencias, name='api_listar_transferencias'),
    path('transferencias/nueva/', transferencias.nueva_transferencia, name='nueva_transferencia'),
    path('transferencias/registrar-salida/<int:id>/', transferencias.registrar_salida_transferencia, name='registrar_salida_transferencia'),
    path('transferencias/confirmar-recepcion/<int:id>/', transferencias.confirmar_recepcion_transferencia, name='confirmar_recepcion_transferencia'),
    path('transferencias/iniciar-retorno/<int:id>/', transferencias.iniciar_retorno_transferencia, name='iniciar_retorno_transferencia'),
    path('transferencias/modal-detalle/<int:id>/', transferencias.render_modal_detalle_transferencia, name='modal_detalle_transferencia'),
    path('transferencias/rechazar/<int:id>/', transferencias.rechazar_transferencia, name='rechazar_transferencia'),
    path('api/transferencia/detalle/<int:id>/', transferencias.obtener_detalle_transferencia, name='api_detalle_transferencia'),
    path('transferencias/guia-pdf/<int:id>/', transferencias.descargar_guia_pdf, name='descargar_guia_pdf'),
   
    # API para obtener stock y búsqueda
    path('api/obtener-stock-almacen/', transferencias.obtener_stock_almacen, name='obtener_stock_almacen'),
    path('api/buscar-vehiculos-transporte/', transferencias.buscar_vehiculos_transporte, name='buscar_vehiculos_transporte'),
    path('api/buscar-conductores-transporte/', transferencias.buscar_conductores_transporte, name='buscar_conductores_transporte'),
    
    # TRANSPORTE Y LOGÍSTICA
    path('transporte/vehiculos/', transporte.lista_vehiculos_transporte, name='lista_vehiculos_transporte'),
    path('transporte/vehiculos/agregar/', transporte.agregar_vehiculo_transporte, name='agregar_vehiculo_transporte'),
    path('transporte/vehiculos/editar/', transporte.editar_vehiculo_transporte, name='editar_vehiculo_transporte'),
    path('transporte/vehiculos/eliminar/<int:id>/', transporte.eliminar_vehiculo_transporte, name='eliminar_vehiculo_transporte'),
    
    path('transporte/conductores/', transporte.lista_conductores, name='lista_conductores'),
    path('transporte/conductores/agregar/', transporte.agregar_conductor, name='agregar_conductor'),
    path('transporte/conductores/editar/', transporte.editar_conductor, name='editar_conductor'),
    path('transporte/conductores/eliminar/<int:id>/', transporte.eliminar_conductor, name='eliminar_conductor'),

    path('stock/', stock.stock, name='stock'),
    path('stock/api/vehiculos/', stock.api_listar_vehiculos_stock, name='api_listar_vehiculos_stock'),
    path('stock/api/repuestos/', stock.api_listar_repuestos_stock, name='api_listar_repuestos_stock'),
    path('stock/api/buscar-global/', stock.api_buscar_stock_global, name='api_buscar_stock_global'),
    path('stock/api/solicitar-traslado/', stock.api_solicitar_traslado_desde_stock, name='api_solicitar_traslado_desde_stock'),
    path('stock/exportar-excel/', stock.exportar_excel_stock, name='exportar_excel_stock'),
    path('api/agregar-vehiculo-stock/', stock.agregar_vehiculo_stock_directo, name='agregar_vehiculo_stock_directo'),
    path('api/editar-vehiculo-stock/', stock.editar_vehiculo_stock, name='editar_vehiculo_stock'),
    path('api/editar-repuesto-stock/', stock.editar_repuesto_stock, name='editar_repuesto_stock'),
    path('api/mover-repuesto-stock/', stock.mover_repuesto_stock, name='mover_repuesto_stock'),
    path('api/agregar-repuesto-stock/', stock.agregar_repuesto_stock_directo, name='agregar_repuesto_stock_directo'),
    
    #REGISTROS DE CAJA
    path('cajas/', cajas.cajas, name='cajas'),
    path('cajas/eliminar/<int:id>/', cajas.cajasEliminar, name='cajasEliminar'),
    path('cajas/agregar/', cajas.agregarCajas, name='agregarCajas'),
    path('cajas/editar/', cajas.editarCajas, name='editarCajas'),
    path('cajas/obtener-sucursales/', cajas.obtenerSucursalesPorEmpresa, name='obtenerSucursalesPorEmpresaCajas'),
    


    # MOVIMIENTOS DE CAJA
    path('movimientos-caja/', movimientosCaja.movimientos_caja, name='movimientos_caja'),
    path('movimientos-caja/api/listar/', movimientosCaja.api_listar_movimientos, name='api_listar_movimientos_caja'),
    path('movimientos-caja/registrar-egreso/', movimientosCaja.registrar_egreso, name='registrar_egreso'),
    path('movimientos-caja/reporte/', movimientosCaja.reporte_caja, name='reporte_caja'),
    path('movimientos-caja/buscar-compra/', movimientosCaja.buscar_compra_por_numero, name='buscar_compra_egreso'),

    
    # MÓDULO DE CRÉDITOS
    path('creditos/', creditos.creditos, name='creditos'),
    path('creditos/api/listar/', creditos.api_listar_creditos, name='api_listar_creditos'),
    path('creditos/detalle/<int:idcredito>/', creditos.detalle_credito, name='detalle_credito'),
    path('creditos/pagar-cuota/<int:idcuotaventa>/', creditos.pagar_cuota, name='pagar_cuota'),
    path('creditos/editar-pago/<int:idpagocuota>/', creditos.editar_pago, name='editar_pago'),
    path('creditos/fraccionar-pago/<int:idpagocuota>/', creditos.fraccionar_pago, name='fraccionar_pago'),
    path('creditos/anular-pago/<int:idpagocuota>/', creditos.anular_pago, name='anular_pago'),
    path('creditos/reportes/', creditos.reportes_creditos, name='reportes_creditos'),
    path('creditos/buscar-cuotas-cliente/', creditos.buscar_cuotas_cliente, name='buscar_cuotas_cliente'),
    path('creditos/historial-anulados/', creditos.historial_creditos_anulados, name='historial_creditos_anulados'),
    path('creditos/registrar-directo/', creditos.registrar_credito_directo, name='registrar_credito_directo'),
    path('creditos/api/obtener-stock-almacen/', creditos.obtener_stock_almacen_credito, name='obtener_stock_almacen_credito'),
    path('creditos/api/editar-mora/<int:idcuotaventa>/', creditos.ajax_editar_mora, name='ajax_editar_mora'),
    path('creditos/cuota/editar-fecha/', creditos.editar_fecha_cuota, name='editar_fecha_cuota'),
    
    # APIs DE NOTIFICACIONES
    path('api/notificaciones/vencidas/', creditos.obtener_notificaciones_vencidas, name='obtener_notificaciones_vencidas'),
    path('api/notificaciones/compras_vencidas/', compras.obtener_notificaciones_compras_vencidas, name='obtener_notificaciones_compras_vencidas'),
    path('api/notificaciones/cumpleanos/', clientes.obtener_notificaciones_cumpleanos, name='obtener_notificaciones_cumpleanos'),
    path('api/notificaciones/config-sonido/', creditos.actualizar_preferencia_sonido, name='actualizar_preferencia_sonido'),
    path('api/notificaciones/subir-sonido/', creditos.subir_sonido_notificacion, name='subir_sonido_notificacion'),

    # IMPRIMIR CRONOGRAMA
    path('ventas/imprimir-cronograma/<int:idventa>/', creditos.imprimir_cronograma_credito, name='imprimir_cronograma'),
    path('creditos/imprimir-cronograma-directo/<int:idcredito>/', creditos.imprimir_cronograma_credito_directo, name='imprimir_cronograma_directo'),

    path('creditos/recibo-pago/<int:idpagocuota>/', creditos.imprimir_recibo_pago, name='imprimir_recibo_pago'),

    # PAGO MÚLTIPLE DE CUOTAS
    path('creditos/pagar-multiples/', creditos.pagar_cuotas_multiples, name='pagar_cuotas_multiples'),
    path('creditos/pagar-total/', creditos.pagar_total_credito, name='pagar_total_credito'),
    path('creditos/recibo-pago-total/<int:idmovimiento>/', creditos.imprimir_recibo_pago_total, name='imprimir_recibo_pago_total'),
    path('creditos/recibo-pago-multiple/<str:pago_ids>/', creditos.imprimir_recibo_pago_multiple, name='imprimir_recibo_pago_multiple'),

    # MÓDULO DE RETENCIÓN DE VEHÍCULOS
    path('creditos/retener-vehiculo/<int:idcredito>/', vistas_retencion.retener_vehiculo, name='retener_vehiculo'),
    path('creditos/liberar-vehiculo/<int:idcredito>/', vistas_retencion.liberar_vehiculo, name='liberar_vehiculo'),
    path('creditos/ejecutar-incumplimiento/<int:idcredito>/', vistas_retencion.ejecutar_incumplimiento, name='ejecutar_incumplimiento'),
    path('creditos/registrar-reparacion/<int:idcredito>/', vistas_retencion.registrar_reparacion, name='registrar_reparacion'),
    path('creditos/reingresar-stock-recuperado/<int:idcredito>/', vistas_retencion.reingresar_stock_recuperado, name='reingresar_stock_recuperado'),

    # CUENTAS POR PAGAR (COMPRAS AL CRÉDITO)
    path('cuentas-por-pagar/', cuentas_por_pagar.cuentas_por_pagar, name='cuentas_por_pagar'),
    path('cuentas-por-pagar/api/listar/', cuentas_por_pagar.api_listar_cuentas_por_pagar, name='api_listar_cuentas_por_pagar'),
    path('cuentas-por-pagar/detalle/<int:idcompra>/', cuentas_por_pagar.detalle_cuenta_pagar, name='detalle_cuenta_pagar'),
    path('cuentas-por-pagar/pagar-cuota/', cuentas_por_pagar.registrar_pago_cuota, name='registrar_pago_cuota_compra'),
    path('cuentas-por-pagar/ticket-pago/<int:idpago>/', cuentas_por_pagar.imprimir_ticket_pago, name='imprimir_ticket_pago_compra'),


    # Clientes
    path('clientes/', clientes.clientes, name='clientes'),
    path('clientes/agregar/', clientes.agregar_cliente, name='agregar_cliente'),
    path('clientes/editar/', clientes.editar_cliente, name='editar_cliente'),
    path('clientes/eliminar/<int:id>/', clientes.eliminar_cliente, name='eliminar_cliente'),
    path('clientes/api/listar/', clientes.api_listar_clientes, name='api_listar_clientes'),
    path('api/autocompletar-cliente/', clientes.autocompletar_cliente, name='autocompletar_cliente'),

    # Garantes
    path('garantes/', garantes.garantes, name='garantes'),
    path('garantes/api/listar/', garantes.api_listar_garantes, name='api_listar_garantes'),
    path('garantes/agregar/', garantes.agregar_garante, name='agregar_garante'),
    path('garantes/editar/', garantes.editar_garante, name='editar_garante'),
    path('garantes/eliminar/<int:id>/', garantes.eliminar_garante, name='eliminar_garante'),
    path('api/autocompletar-garante/', garantes.autocompletar_garante, name='autocompletar_garante'),

    # Proveedores
    path('proveedores/', proveedores.proveedores, name='proveedores'),
    path('proveedores/agregar/', proveedores.agregar_proveedor, name='agregar_proveedor'),
    path('proveedores/editar/', proveedores.editar_proveedor, name='editar_proveedor'),
    path('proveedores/eliminar/<int:id>/', proveedores.eliminar_proveedor, name='eliminar_proveedor'),
    path('proveedores/api/listar/', proveedores.api_listar_proveedores, name='api_listar_proveedores'),
    path('api/autocompletar-proveedor/', proveedores.autocompletar_proveedor, name='autocompletar_proveedor'),
    path('api/obtener-ultimo-proveedor/', proveedores.obtener_ultimo_proveedor, name='obtener_ultimo_proveedor'),


    # Imposición de Placas
    path('imposicion-placas/', imposicionPlacas.imposicion_placas, name='imposicion_placas'),
    path('imposicion-placas/api/listar/', imposicionPlacas.api_listar_imposiciones, name='api_listar_imposiciones'),
    path('imposicion-placas/nueva/', imposicionPlacas.nueva_imposicion, name='nueva_imposicion'),
    path('imposicion-placas/editar/<int:id>/', imposicionPlacas.editar_imposicion, name='editar_imposicion'),
    path('imposicion-placas/cambiar-estado/<int:id>/', imposicionPlacas.cambiar_estado_imposicion, name='cambiar_estado_imposicion'),
    path('imposicion-placas/eliminar/<int:id>/', imposicionPlacas.eliminar_imposicion, name='eliminar_imposicion'),
    path('imposicion-placas/detalle/<int:id>/', imposicionPlacas.detalle_imposicion, name='detalle_imposicion'),
    path('imposicion-placas/vehiculos-venta/', imposicionPlacas.obtener_vehiculos_venta, name='obtener_vehiculos_venta'),
    path('imposicion-placas/imprimir/<int:id>/', imposicionPlacas.imprimir_constancia, name='imprimir_constancia_placa'),
    path('imposicion-placas/acta-entrega/<int:id>/', imposicionPlacas.imprimir_acta_entrega, name='imprimir_acta_entrega_placa'),

    #Regiones
    path('regiones/', regiones.regiones, name='regiones'),
    path('regiones/eliminar/<int:id>/', regiones.regionesEliminar, name='regionesEliminar'),
    path('regiones/agregar/', regiones.agregarRegiones, name='agregarRegiones'),
    path('regiones/editar/', regiones.editarRegiones, name='editarRegiones'),

    #Provincias
    path('provincias/', provincias.provincias, name='provincias'),
    path('provincias/eliminar/<int:id>/', provincias.provinciasEliminar, name='provinciasEliminar'),
    path('provincias/agregar/', provincias.agregarProvincias, name='agregarProvincias'),
    path('provincias/editar/', provincias.editarProvincias, name='editarProvincias'),

    #Distritos
    path('distritos/', distritos.distritos, name='distritos'),
    path('distritos/eliminar/<int:id>/', distritos.distritosEliminar, name='distritosEliminar'),
    path('distritos/agregar/', distritos.agregarDistritos, name='agregarDistritos'),
    path('distritos/editar/', distritos.editarDistritos, name='editarDistritos'),
    path('distritos/obtener-provincias/', distritos.obtenerProvinciasPorRegion, name='obtenerProvinciasPorRegion'),

    #Sucursales
    path('sucursales/', sucursales.sucursales, name='sucursales'),
    path('sucursales/eliminar/<int:id>/', sucursales.sucursalesEliminar, name='sucursalesEliminar'),
    path('sucursales/agregar/', sucursales.agregarSucursales, name='agregarSucursales'),
    path('sucursales/editar/', sucursales.editarSucursales, name='editarSucursales'),
    path('sucursales/obtener-provincias/', sucursales.obtenerProvinciasPorRegion, name='obtenerProvinciasPorRegionSucursales'),
    path('sucursales/obtener-distritos/', sucursales.obtenerDistritosPorProvincia, name='obtenerDistritosPorProvincia'),

    #Almacenes
    path('almacenes/', almacenes.almacenes, name='almacenes'),
    path('almacenes/eliminar/<int:id>/', almacenes.almacenesEliminar, name='almacenesEliminar'),
    path('almacenes/agregar/', almacenes.agregarAlmacenes, name='agregarAlmacenes'),
    path('almacenes/editar/', almacenes.editarAlmacenes, name='editarAlmacenes'),
    path('almacenes/obtener-sucursales/', almacenes.obtenerSucursalesPorEmpresa, name='obtenerSucursalesPorEmpresa'),


    # Historial de Cajas
    path('historial-cajas/', historialCajas.historial_cajas, name='historial_cajas'),
    path('historial-cajas/api/listar/', historialCajas.api_listar_historial, name='api_listar_historial_cajas'),
    path('historial-cajas/solicitar-reapertura/<int:id_movimiento>/', historialCajas.solicitar_reapertura, name='solicitar_reapertura'),
    path('historial-cajas/verificar-codigo/', historialCajas.verificar_codigo_reapertura, name='verificar_codigo_reapertura'),
    path('historial-cajas/cerrar-reabierta/<int:id_movimiento>/', historialCajas.cerrar_caja_reabierta, name='cerrar_caja_reabierta'),
    path('historial-cajas/movimientos/<int:id_movimiento>/', historialCajas.obtener_movimientos_caja, name='api_movimientos_caja'),
    path('historial-cajas/exportar/<int:id_movimiento>/', historialCajas.exportar_caja_pdf, name='exportar_caja_pdf'),


    # Tipo Compprobante
    path('tipo-comprobante/', tipo_comprobante.tipo_comprobante, name='tipo_comprobante'),
    path('agregar-tipo-comprobante/', tipo_comprobante.agregar_tipo_comprobante, name='agregar_tipo_comprobante'),
    path('editar-tipo-comprobante/', tipo_comprobante.editar_tipo_comprobante, name='editar_tipo_comprobante'),
    path('eliminar-tipo-comprobante/<int:id>/', tipo_comprobante.eliminar_tipo_comprobante, name='eliminar_tipo_comprobante'),

    # Series de Comprobante
    path('serie-comprobante/', serie_comprobante.serie_comprobante, name='serie_comprobante'),
    path('agregar-serie-comprobante/', serie_comprobante.agregar_serie_comprobante, name='agregar_serie_comprobante'),
    path('editar-serie-comprobante/', serie_comprobante.editar_serie_comprobante, name='editar_serie_comprobante'),
    path('eliminar-serie-comprobante/<int:id>/', serie_comprobante.eliminar_serie_comprobante, name='eliminar_serie_comprobante'),

    # Proformas 
    path('proformas/', proforma.proformas, name='proformas'),
    path('proformas/api/listar/', proforma.api_listar_proformas, name='api_listar_proformas'),
    path('proformas/nueva/', proforma.nueva_proforma, name='nueva_proforma'),
    path('proformas/pdf/<int:idproforma>/', proforma.proforma_pdf, name='proforma_pdf'),
    path('proformas/anular/<int:idproforma>/', proforma.eliminar_proforma, name='anular_proforma'),
    path('proformas/editar/<int:idproforma>/', proforma.editar_proforma, name='editar_proforma'),

    # Reportes
    path('reportes/ventas/',   reportes.reporte_ventas,   name='reporte_ventas'),
    path('reportes/ventas/api/listar/', reportes.api_listar_reporte_ventas, name='api_listar_reporte_ventas'),
    path('reportes/compras/',  reportes.reporte_compras,  name='reporte_compras'),
    path('reportes/compras/api/listar/', reportes.api_listar_reporte_compras, name='api_listar_reporte_compras'),
    path('reportes/almacen/',  reportes.reporte_almacen,  name='reporte_almacen'),
    path('reportes/almacen/api/vehiculos/', reportes.api_listar_almacen_vehiculos, name='api_listar_almacen_vehiculos'),
    path('reportes/almacen/api/repuestos/', reportes.api_listar_almacen_repuestos, name='api_listar_almacen_repuestos'),
    path('reportes/inventario/', reportes.reporte_inventario, name='reporte_inventario'),
    path('reportes/inventario/api/vehiculos/', reportes.api_listar_inventario_vehiculos, name='api_listar_inventario_vehiculos'),
    path('reportes/inventario/api/repuestos/', reportes.api_listar_inventario_repuestos, name='api_listar_inventario_repuestos'),
    path('reportes/caja/',     reportes.reporte_caja,     name='reporte_caja'),
    path('reportes/caja/api/listar/', reportes.api_listar_reporte_caja, name='api_listar_reporte_caja'),
    path('reportes/creditos/', reportes.reporte_creditos, name='reporte_creditos'),
    path('reportes/creditos/api/listar/', reportes.api_listar_reporte_creditos, name='api_listar_reporte_creditos'),
    path('reportes/creditos/api/moras/', reportes.api_listar_reporte_moras, name='api_listar_reporte_moras'),
    path('reportes/contactos/', reportes.reporte_contactos, name='reporte_contactos'),
    path('reportes/contactos/api/clientes/', reportes.api_listar_contactos_clientes, name='api_listar_contactos_clientes'),
    path('reportes/contactos/api/proveedores/', reportes.api_listar_contactos_proveedores, name='api_listar_contactos_proveedores'),
    path('reportes/pre-financiamiento/', reportes.reporte_pre_financiamiento, name='reporte_pre_financiamiento'),
    path('reportes/pre-financiamiento/api/listar/', reportes.api_listar_reporte_pre_financiamiento, name='api_listar_reporte_pre_financiamiento'),
    # SUNAT Integración (módulo existente)
    path('sunat/', sunat.lista_sunat, name='lista_sunat'),
    path('sunat/enviar/<int:idventa>/', sunat.enviar_sunat_manual, name='enviar_sunat_manual'),

    # ── Facturación Electrónica → Comprobantes de Venta (submódulo nuevo) ──
    path('facturacion/comprobantes/', facturacion_comprobantes.comprobantes_venta, name='comprobantes_venta'),
    path('facturacion/comprobantes/api/facturas/', facturacion_comprobantes.api_listar_facturas, name='api_listar_facturas_sunat'),
    path('facturacion/comprobantes/api/boletas/', facturacion_comprobantes.api_listar_boletas, name='api_listar_boletas_sunat'),
    path('facturacion/comprobantes/api/liquidaciones/', facturacion_comprobantes.api_listar_liquidaciones, name='api_listar_liquidaciones_sunat'),
    path('facturacion/comprobantes/enviar/<int:idventa>/', facturacion_comprobantes.enviar_comprobante_sunat, name='enviar_comprobante_sunat'),

    # PRE-FINANCIAMIENTO
    path('pre-financiamiento/', pre_financiamiento.index_pre_financiamiento, name='index_pre_financiamiento'),
    path('pre-financiamiento/registrar/', pre_financiamiento.registrar_pre_financiamiento, name='registrar_pre_financiamiento'),
    path('pre-financiamiento/api/listar/', pre_financiamiento.api_listar_pre_financiamiento, name='api_listar_pre_financiamiento'),
    path('pre-financiamiento/evaluar/<int:id_pre_credito>/', pre_financiamiento.evaluar_pre_financiamiento, name='evaluar_pre_financiamiento'),
    path('pre-financiamiento/cobrar/<int:id_pre_credito>/', pre_financiamiento.cobrar_pre_financiamiento, name='cobrar_pre_financiamiento'),
    path('pre-financiamiento/recibo/<int:id_pre_credito>/', pre_financiamiento.imprimir_recibo_pre_financiamiento, name='imprimir_recibo_pre_financiamiento'),
    path('pre-financiamiento/recibo-devolucion/<int:id_pre_credito>/', pre_financiamiento.imprimir_recibo_devolucion_pre_financiamiento, name='imprimir_recibo_devolucion_pre_financiamiento'),
    path('pre-financiamiento/api/get-data/<int:id_pre_credito>/', pre_financiamiento.get_pre_credito_data, name='get_pre_credito_data'),

    path('creditos/descargar-contrato/<int:idcredito>/', creditos.descargar_contrato_pdf, name='descargar_contrato_pdf'),
    path('creditos/descargar-pagare/<int:idcredito>/', creditos.descargar_pagare_pdf, name='descargar_pagare_pdf'),
    path('creditos/descargar-contrato-especial/<int:idcredito>/', creditos.descargar_contrato_especial_pdf, name='descargar_contrato_especial_pdf'),
    path('creditos/guardar-garante/', creditos.guardar_garante_credito, name='guardar_garante_credito'),
    path('creditos/buscar-garantes/', creditos.buscar_garantes, name='buscar_garantes'),

    # Situación de Vehículo
    path('situacion-vehiculos/', situacionVehiculo.situacion_vehiculos, name='situacion_vehiculos'),
    path('situacion-vehiculos/agregar/', situacionVehiculo.agregar_situacion, name='agregar_situacion'),
    path('situacion-vehiculos/editar/', situacionVehiculo.editar_situacion, name='editar_situacion'),
    path('situacion-vehiculos/eliminar/<int:id>/', situacionVehiculo.eliminar_situacion, name='eliminar_situacion'),

    # Configuración Vehicular
    path('configuracion_vehicular/', configuracion_vehicular.configuracion_vehicular, name='configuracion_vehicular'),
    path('configuracion_vehicular/agregar', configuracion_vehicular.agregar_configuracion, name='agregar_configuracion'),
    path('configuracion_vehicular/editar', configuracion_vehicular.editar_configuracion, name='editar_configuracion'),
    path('configuracion_vehicular/eliminar/<int:id>', configuracion_vehicular.eliminar_configuracion, name='eliminar_configuracion'),

    # ZONAS DE CRÉDITO
    path('zonas-credito/', zonas_credito.zonas_credito, name='zonas_credito'),
    path('zonas-credito/agregar/', zonas_credito.agregar, name='zonas_credito_agregar'),
    path('zonas-credito/editar/', zonas_credito.editar, name='zonas_credito_editar'),
    path('zonas-credito/eliminar/<int:id>/', zonas_credito.eliminar, name='zonas_credito_eliminar'),

    # FACTORES DE CRÉDITO
    path('factores-credito/', factores_credito.factores_credito, name='factores_credito'),
    path('factores-credito/agregar/', factores_credito.agregar, name='factores_credito_agregar'),
    path('factores-credito/editar/', factores_credito.editar, name='factores_credito_editar'),
    path('factores-credito/eliminar/<int:id>/', factores_credito.eliminar, name='factores_credito_eliminar'),

    # GESTIÓN IGV
    path('gestion/igv/', gestion_igv.gestion_igv, name='gestion_igv'),
    path('gestion/igv/agregar/', gestion_igv.agregar_igv, name='agregar_igv'),
    path('gestion/igv/editar/', gestion_igv.editar_igv, name='editar_igv'),
    path('gestion/igv/eliminar/<int:id>/', gestion_igv.eliminar_igv, name='eliminar_igv'),

    # CANALES DE PAGO
    path('gestion/canales-pago/', canales_pago.canales_pago_view, name='canales_pago'),
    path('gestion/canales-pago/tipos/listar/', canales_pago.listar_tipos_cuenta, name='listar_tipos_cuenta'),
    path('gestion/canales-pago/tipos/guardar/', canales_pago.guardar_tipo_cuenta, name='guardar_tipo_cuenta'),
    path('gestion/canales-pago/tipos/eliminar/', canales_pago.eliminar_tipo_cuenta, name='eliminar_tipo_cuenta'),
    path('gestion/canales-pago/canales/listar/', canales_pago.listar_canales_pago, name='listar_canales_pago'),
    path('gestion/canales-pago/canales/guardar/', canales_pago.guardar_canal_pago, name='guardar_canal_pago'),
    path('gestion/canales-pago/canales/eliminar/', canales_pago.eliminar_canal_pago, name='eliminar_canal_pago'),

    # BONIFICACIONES
    path('bonificaciones/reglas/', bonificaciones.listar_reglas, name='listar_reglas_bonificacion'),
    path('bonificaciones/reglas/guardar/', bonificaciones.guardar_regla, name='guardar_regla_bonificacion'),
    path('bonificaciones/reglas/eliminar/<int:id>/', bonificaciones.eliminar_regla, name='eliminar_regla_bonificacion'),
    path('bonificaciones/reglas/editar/', bonificaciones.editar_regla, name='editar_regla_bonificacion'),
    path('bonificaciones/metas/', bonificaciones.listar_metas, name='listar_metas_bonificacion'),
    path('bonificaciones/metas/guardar/', bonificaciones.guardar_meta, name='guardar_meta_bonificacion'),
    path('bonificaciones/metas/eliminar/<int:id>/', bonificaciones.eliminar_meta, name='eliminar_meta_bonificacion'),
    path('bonificaciones/metas/editar/', bonificaciones.editar_meta, name='editar_meta_bonificacion'),
    path('bonificaciones/api/buscar-vendedores/', bonificaciones.buscar_vendedores, name='buscar_vendedores_bonificacion'),
    path('bonificaciones/calculos/', bonificaciones.motor_calculo, name='motor_calculo_bonificacion'),
    path('bonificaciones/api/listar_calculos/', bonificaciones.api_listar_calculos, name='api_listar_calculos'),
    path('bonificaciones/calculos/ejecutar/', bonificaciones.ejecutar_calculo, name='ejecutar_calculo_bonificacion'),
    path('bonificaciones/calculos/detalle/<int:id_calculo>/', bonificaciones.detalle_calculo, name='detalle_calculo_bonificacion'),
    path('bonificaciones/calculos/estado/<int:id_calculo>/<str:estado>/', bonificaciones.cambiar_estado_calculo, name='cambiar_estado_calculo_bonificacion'),
    path('bonificaciones/calculos/eliminar/<int:id_calculo>/', bonificaciones.eliminar_calculo, name='eliminar_calculo_bonificacion'),
    path('bonificaciones/reportes/', bonificaciones.reportes, name='reportes_bonificacion'),
    path('bonificaciones/api/reportes/listar/', bonificaciones.api_listar_reportes, name='api_listar_reportes_bonificaciones'),
    path('bonificaciones/calculos/pdf/<int:id_calculo>/', bonificaciones.pdf_calculo, name='pdf_calculo_bonificacion'),

    # SERVICIOS / TRÁMITES
    path('gestion/servicios/', servicios.servicios, name='servicios'),
    path('gestion/servicios/agregar/', servicios.agregar, name='servicios_agregar'),
    path('gestion/servicios/editar/', servicios.editar, name='servicios_editar'),
    path('gestion/servicios/eliminar/<int:id>/', servicios.eliminar, name='servicios_eliminar'),
    path('gestion/servicios/listar/', servicios.listar_activos, name='servicios_listar_activos'),

    # TRAZABILIDAD
    path('trazabilidad/', trazabilidad.trazabilidad, name='trazabilidad'),
    path('trazabilidad/buscar-vehiculo/', trazabilidad.buscar_vehiculo, name='trazabilidad_buscar_vehiculo'),
    path('trazabilidad/buscar-repuesto/', trazabilidad.buscar_repuesto, name='trazabilidad_buscar_repuesto'),
    path('trazabilidad/vehiculo/<str:serie>/pdf/', trazabilidad.pdf_trazabilidad_vehiculo, name='pdf_trazabilidad_vehiculo'),
    path('trazabilidad/repuesto/<str:codigo>/pdf/', trazabilidad.pdf_trazabilidad_repuesto, name='pdf_trazabilidad_repuesto'),

]
