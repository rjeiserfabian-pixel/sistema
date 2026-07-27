import re
from pathlib import Path

ventas_path = Path("templates/ventas/ventas.html")
registrar_path = Path("templates/pre_financiamiento/registrar.html")

ventas_content = ventas_path.read_text(encoding="utf-8")
registrar_content = registrar_path.read_text(encoding="utf-8")

# --- Update HTML button ---
button_html = """
              <div class="d-flex align-items-center gap-2">
                <div class="autocomplete-wrapper flex-grow-1">
                  <input type="text" id="cliente_search" class="form-control autocomplete-input" 
                         placeholder="Buscar por nombre o documento..." autocomplete="off">
                  <button type="button" class="autocomplete-arrow" onclick="toggleAutocomplete('cliente_search', 'cliente_results')">
                    <i class="fa-solid fa-chevron-down"></i>
                  </button>
                  <input type="hidden" name="idcliente" id="idcliente">
                  <div class="autocomplete-results" id="cliente_results"></div>
                </div>
                <button type="button" class="btn btn-success btn-add-cliente" data-bs-toggle="modal"
                  data-bs-target="#modalAgregarClientePreCredito" title="Agregar nuevo cliente">
                  <i class="fa-solid fa-user-plus"></i>
                </button>
              </div>"""
old_button_html = """
              <div class="autocomplete-wrapper">
                <input type="text" id="cliente_search" class="form-control autocomplete-input" 
                       placeholder="Buscar por nombre o documento..." autocomplete="off">
                <button type="button" class="autocomplete-arrow" onclick="toggleAutocomplete('cliente_search', 'cliente_results')">
                  <i class="fa-solid fa-chevron-down"></i>
                </button>
                <input type="hidden" name="idcliente" id="idcliente">
                <div class="autocomplete-results" id="cliente_results"></div>
              </div>"""
registrar_content = registrar_content.replace(old_button_html.strip(), button_html.strip())


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
js_end = ventas_content.find("// ⭐ CONTROL DE FORMA DE PAGO", js_start)

if js_end == -1:
    raise Exception("Could not find js_end")

js_code = ventas_content[js_start:js_end]

# Strip the re-open modal block BEFORE renaming anything
js_code = re.sub(r"\s*// Reabrir modal de venta.*?setTimeout\(\(\) => \{.*?modalVenta\.show\(\);\s*\}, 300\);", "", js_code, flags=re.DOTALL)

# Rename IDs
js_code = js_code.replace("Venta", "PreCredito")
js_code = js_code.replace("modalAgregarClienteVenta", "modalAgregarClientePreCredito")
js_code = js_code.replace("formAgregarClienteVenta", "formAgregarClientePreCredito")
js_code = js_code.replace("cerrarModalCliente", "cerrarModalClientePreCredito")
js_code = js_code.replace("consultarDocumentoTokenPeruVenta", "consultarDocumentoTokenPeruPreCredito")
js_code = js_code.replace("limpiarCamposCliente", "limpiarCamposClientePreCredito")
js_code = js_code.replace("$('#cliente_id').val(response.idcliente);", "$('#idcliente').val(response.idcliente);")


# Inject into registrar.html
# HTML insertion right before {% endblock %} at the end of the content block
html_target = '\n{% endblock %}'
injection_point_html = registrar_content.find(html_target)
if injection_point_html == -1:
    raise Exception("Could not find HTML insertion point")

registrar_content = (
    registrar_content[:injection_point_html] +
    "\n\n" + modal_html + "\n\n" +
    registrar_content[injection_point_html:]
)

# JS insertion right after let pagoCount = 1;
js_target = 'let pagoCount = 1;\n'
injection_point_js = registrar_content.find(js_target)
if injection_point_js == -1:
    raise Exception("Could not find JS insertion point")

injection_point_js += len(js_target)
registrar_content = (
    registrar_content[:injection_point_js] +
    "\n" + js_code + "\n" +
    registrar_content[injection_point_js:]
)

registrar_path.write_text(registrar_content, encoding="utf-8")
print("Done fixing 2")
