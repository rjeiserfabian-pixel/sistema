import sys

file_path = r'c:\Users\JEISER\Desktop\PREMIUN\Sistemas-de-ventas\templates\productos\componentes\repuestos_modales.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace col-md-4 with col-md-3 for Costo Unitario (Add form)
content = content.replace('<div class="col-md-4">\n              <label class="form-label fw-semibold">Costo Unitario (S/)</label>\n              <input type="number" name="costo_unitario" class="form-control" value="0.00" min="0" step="0.01">\n            </div>',
                          '<div class="col-md-3">\n              <label class="form-label fw-semibold">Costo Unitario (S/)</label>\n              <input type="number" name="costo_unitario" class="form-control" value="0.00" min="0" step="0.01">\n            </div>\n            <div class="col-md-3">\n              <label class="form-label fw-semibold">Precio Mayor (S/)</label>\n              <input type="number" name="precio_por_mayor" class="form-control" value="0.00" min="0" step="0.01">\n            </div>')

content = content.replace('<div class="col-md-4">\n              <label class="form-label fw-semibold">Precio Cash (S/)</label>\n              <input type="number" name="precio_minimo" class="form-control" value="0.00" min="0" step="0.01">\n            </div>',
                          '<div class="col-md-3">\n              <label class="form-label fw-semibold">Precio Cash (S/)</label>\n              <input type="number" name="precio_minimo" class="form-control" value="0.00" min="0" step="0.01">\n            </div>')

content = content.replace('<div class="col-md-4">\n              <label class="form-label fw-semibold">Precio Lista (S/)</label>\n              <input type="number" name="precio_sugerido" class="form-control" value="0.00" min="0" step="0.01">\n            </div>',
                          '<div class="col-md-3">\n              <label class="form-label fw-semibold">Precio Lista (S/)</label>\n              <input type="number" name="precio_sugerido" class="form-control" value="0.00" min="0" step="0.01">\n            </div>')

# Edit form
content = content.replace('<div class="col-md-4">\n              <label class="form-label fw-semibold">Costo Unitario (S/)</label>\n              <input type="number" name="costo_unitario2" id="edit_rep_costo" class="form-control" min="0" step="0.01">\n            </div>',
                          '<div class="col-md-3">\n              <label class="form-label fw-semibold">Costo Unitario (S/)</label>\n              <input type="number" name="costo_unitario2" id="edit_rep_costo" class="form-control" min="0" step="0.01">\n            </div>\n            <div class="col-md-3">\n              <label class="form-label fw-semibold">Precio Mayor (S/)</label>\n              <input type="number" name="precio_por_mayor2" id="edit_rep_pmayor" class="form-control" min="0" step="0.01">\n            </div>')

content = content.replace('<div class="col-md-4">\n              <label class="form-label fw-semibold">Precio Cash (S/)</label>\n              <input type="number" name="precio_minimo2" id="edit_rep_pmin" class="form-control" min="0" step="0.01">\n            </div>',
                          '<div class="col-md-3">\n              <label class="form-label fw-semibold">Precio Cash (S/)</label>\n              <input type="number" name="precio_minimo2" id="edit_rep_pmin" class="form-control" min="0" step="0.01">\n            </div>')

content = content.replace('<div class="col-md-4">\n              <label class="form-label fw-semibold">Precio Lista (S/)</label>\n              <input type="number" name="precio_sugerido2" id="edit_rep_psug" class="form-control" min="0" step="0.01">\n            </div>',
                          '<div class="col-md-3">\n              <label class="form-label fw-semibold">Precio Lista (S/)</label>\n              <input type="number" name="precio_sugerido2" id="edit_rep_psug" class="form-control" min="0" step="0.01">\n            </div>')


with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")
