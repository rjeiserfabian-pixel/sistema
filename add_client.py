import re
from pathlib import Path

ventas_path = Path("templates/ventas/ventas.html")
registrar_path = Path("templates/pre_financiamiento/registrar.html")

ventas_content = ventas_path.read_text(encoding="utf-8")
registrar_content = registrar_path.read_text(encoding="utf-8")

# Extract Modal HTML from ventas.html
modal_start = ventas_content.find("<!-- ⭐ MODAL AGREGAR CLIENTE (NUEVO)")
modal_end = ventas_content.find("<!-- ⭐ MODAL DETALLES DEL PRODUCTO")
modal_html = ventas_content[modal_start:modal_end]

# Rename IDs
modal_html = modal_html.replace("Venta", "PreCredito")
modal_html = modal_html.replace("modalAgregarClienteVenta", "modalAgregarClientePreCredito")
modal_html = modal_html.replace("formAgregarClienteVenta", "formAgregarClientePreCredito")
modal_html = modal_html.replace("alertCargandoVenta", "alertCargandoPreCredito")
modal_html = modal_html.replace("alertErrorVenta", "alertErrorPreCredito")
modal_html = modal_html.replace("alertExitoVenta", "alertExitoPreCredito")

# Extract the JS for the modal
js_start = ventas_content.find("// ⭐ FUNCIÓN PARA CERRAR MODAL DE CLIENTE")
js_end = ventas_content.find("  // ========================================  // ========================================", js_start) # There is no second one like this
# Wait, let's just search for `// ==================== LÓGICA DE UBICACIÓN` and go to before it
js_end = ventas_content.find("// ==================== LÓGICA DE UBICACIÓN", js_start)

js_code = ventas_content[js_start:js_end]
js_code = js_code.replace("Venta", "PreCredito")
js_code = js_code.replace("modalAgregarClienteVenta", "modalAgregarClientePreCredito")
js_code = js_code.replace("formAgregarClienteVenta", "formAgregarClientePreCredito")
js_code = js_code.replace("cerrarModalCliente", "cerrarModalClientePreCredito")
js_code = js_code.replace("consultarDocumentoTokenPeruVenta", "consultarDocumentoTokenPeruPreCredito")
js_code = js_code.replace("limpiarCamposCliente", "limpiarCamposClientePreCredito")
js_code = js_code.replace("$('#cliente_id').val(response.idcliente);", "$('#idcliente').val(response.idcliente);")

# Inject into registrar.html
injection_point_html = registrar_content.find('  <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>')
new_registrar_content = (
    registrar_content[:injection_point_html] +
    "\n\n" + modal_html + "\n\n" +
    registrar_content[injection_point_html:]
)

injection_point_js = new_registrar_content.find("// ── Listeners de Inputs ────────────────────────────────────────────────")
new_registrar_content = (
    new_registrar_content[:injection_point_js] +
    "\n\n" + js_code + "\n\n" +
    new_registrar_content[injection_point_js:]
)

registrar_path.write_text(new_registrar_content, encoding="utf-8")
print("Done")
