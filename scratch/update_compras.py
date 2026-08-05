import re
import sys

file_path = r'c:\Users\JEISER\Desktop\PREMIUN\Sistemas-de-ventas\templates\compras\compras.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update the layout: change col-md-6 to col-md-4 for the price config sections
content = content.replace('<div class="col-md-6 mb-3">\n                <h6 class="text-success fw-bold mb-2">\n                  <i class="fa-solid fa-circle text-success"\n                     style="font-size: 0.5rem;\n                            vertical-align: middle"></i> CONFIGURACIÓN PRECIO AL POR MAYOR',
                          '<div class="col-md-4 mb-3">\n                <h6 class="text-success fw-bold mb-2">\n                  <i class="fa-solid fa-circle text-success"\n                     style="font-size: 0.5rem;\n                            vertical-align: middle"></i> PRECIO CASH')
content = content.replace('<div class="col-md-6 mb-3">\n                <h6 class="text-purple fw-bold mb-2" style="color: #6f42c1;">\n                  <i class="fa-solid fa-circle"\n                     style="font-size: 0.5rem;\n                            vertical-align: middle;\n                            color: #6f42c1"></i> CONFIGURACIÓN PRECIO AL POR MENOR',
                          '<div class="col-md-4 mb-3">\n                <h6 class="text-purple fw-bold mb-2" style="color: #6f42c1;">\n                  <i class="fa-solid fa-circle"\n                     style="font-size: 0.5rem;\n                            vertical-align: middle;\n                            color: #6f42c1"></i> PRECIO LISTA')

# Insert the new column block before "PRECIO CASH" block
new_block = """              <div class="col-md-4 mb-3">
                <h6 class="text-primary fw-bold mb-2">
                  <i class="fa-solid fa-circle text-primary"
                     style="font-size: 0.5rem;
                            vertical-align: middle"></i> PRECIO AL POR MAYOR
                </h6>
                <div class="row">
                  <div class="col-md-6">
                    <label class="form-label text-muted">Margen Mayor</label>
                    <div class="input-group">
                      <input type="number"
                             id="margen_por_mayor"
                             class="form-control"
                             step="0.01"
                             oninput="calcularPrecioDesdeMargen('por_mayor')">
                      <span class="input-group-text">%</span>
                    </div>
                  </div>
                  <div class="col-md-6">
                    <label class="form-label text-muted">Precio Mayor</label>
                    <div class="input-group">
                      <span class="input-group-text bg-primary text-white">S/</span>
                      <input type="number"
                             id="precio_por_mayor"
                             class="form-control bg-light text-primary fw-bold"
                             step="0.01"
                             oninput="calcularMargenDesdePrecio('por_mayor')">
                    </div>
                  </div>
                </div>
              </div>
"""
content = content.replace('              <div class="col-md-4 mb-3">\n                <h6 class="text-success fw-bold mb-2">',
                          new_block + '              <div class="col-md-4 mb-3">\n                <h6 class="text-success fw-bold mb-2">')


# 2. Update table headers
content = content.replace('<th>Precio al por mayor</th>\n                    <th>Precio al por menor</th>',
                          '<th>Precio al por mayor</th>\n                    <th>Precio Cash</th>\n                    <th>Precio Lista</th>')

# 3. Update JS 'actualizarTotalesMargenes'
content = content.replace("calcularPrecioDesdeMargen('minimo');\n    calcularPrecioDesdeMargen('maximo');",
                          "calcularPrecioDesdeMargen('por_mayor');\n    calcularPrecioDesdeMargen('minimo');\n    calcularPrecioDesdeMargen('maximo');")

# 4. Update JS variables in 'agregarDetalle'
content = content.replace('const precioMinimo = parseFloat(document.getElementById("precio_minimo").value) || 0;',
                          'const precioPorMayor = parseFloat(document.getElementById("precio_por_mayor").value) || 0;\n    const precioMinimo = parseFloat(document.getElementById("precio_minimo").value) || 0;')
content = content.replace('const margenMinimo = parseFloat(document.getElementById("margen_minimo").value) || 0;',
                          'const margenPorMayor = parseFloat(document.getElementById("margen_por_mayor").value) || 0;\n    const margenMinimo = parseFloat(document.getElementById("margen_minimo").value) || 0;')

# 5. Add to the object array push
content = content.replace('precio_minimo: precioMinimo,', 'precio_por_mayor: precioPorMayor,\n      precio_minimo: precioMinimo,')
content = content.replace('margen_minimo: margenMinimo,', 'margen_por_mayor: margenPorMayor,\n      margen_minimo: margenMinimo,')

# 6. HTML generation for the table row
# We need to find the string where the table row is constructed: `<td>${detalle.precio_minimo.toFixed(2)}</td>`
content = content.replace('<td>${detalle.precio_minimo.toFixed(2)}</td>',
                          '<td>${detalle.precio_por_mayor.toFixed(2)}</td>\n            <td>${detalle.precio_minimo.toFixed(2)}</td>')

# 7. Form clearing logic
content = content.replace('document.getElementById("precio_minimo").value = "";',
                          'document.getElementById("precio_por_mayor").value = "";\n    document.getElementById("precio_minimo").value = "";')
content = content.replace('document.getElementById("margen_minimo").value = "";',
                          'document.getElementById("margen_por_mayor").value = "";\n    document.getElementById("margen_minimo").value = "";')

# Fill initial edit form logic if present
content = content.replace('$("#precio_minimo").val(detalle.precio_minimo);',
                          '$("#precio_por_mayor").val(detalle.precio_por_mayor);\n        $("#precio_minimo").val(detalle.precio_minimo);')
content = content.replace('$("#margen_minimo").val(detalle.margen_minimo);',
                          '$("#margen_por_mayor").val(detalle.margen_por_mayor);\n        $("#margen_minimo").val(detalle.margen_minimo);')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done updating compras.html")
