import sys

file_path = r'c:\Users\JEISER\Desktop\PREMIUN\Sistemas-de-ventas\templates\productos\productos.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update the table row generation in renderizarTablaRepuestos
content = content.replace('<td class="fw-semibold text-success">S/ ${r.precio_sugerido || \'0.00\'}</td>',
                          '<td class="fw-semibold text-primary">S/ ${r.precio_por_mayor || \'0.00\'}</td>\n              <td class="fw-semibold text-success">S/ ${r.precio_minimo || \'0.00\'}</td>\n              <td class="fw-semibold text-purple" style="color: #6f42c1;">S/ ${r.precio_sugerido || \'0.00\'}</td>')

# 2. Update the edit button data attributes
content = content.replace('data-costo="${r.costo_unitario || 0}" data-pmin="${r.precio_minimo || 0}" data-psug="${r.precio_sugerido || 0}"',
                          'data-costo="${r.costo_unitario || 0}" data-pmayor="${r.precio_por_mayor || 0}" data-pmin="${r.precio_minimo || 0}" data-psug="${r.precio_sugerido || 0}"')


# 3. Update the click event handler for btn-editar-rep
content = content.replace('var costo = String($(this).data(\'costo\') || \'0\').replace(\',\', \'.\');',
                          'var costo = String($(this).data(\'costo\') || \'0\').replace(\',\', \'.\');\n      var pmayor = String($(this).data(\'pmayor\') || \'0\').replace(\',\', \'.\');')

content = content.replace('$(\'#edit_rep_costo\').val(parseFloat(costo));',
                          '$(\'#edit_rep_costo\').val(parseFloat(costo));\n      $(\'#edit_rep_pmayor\').val(parseFloat(pmayor));')


with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

# Now update repuestos_tab.html
tab_file = r'c:\Users\JEISER\Desktop\PREMIUN\Sistemas-de-ventas\templates\productos\componentes\repuestos_tab.html'
with open(tab_file, 'r', encoding='utf-8') as f:
    tab_content = f.read()

tab_content = tab_content.replace('<th style="width:8%;">Costo Unit.</th>\n                  <th style="width:8%;">Precio Lista</th>',
                                  '<th style="width:8%;">Costo Unit.</th>\n                  <th style="width:8%;">Precio Mayor</th>\n                  <th style="width:8%;">Precio Cash</th>\n                  <th style="width:8%;">Precio Lista</th>')
tab_content = tab_content.replace('colspan="11"', 'colspan="13"')

with open(tab_file, 'w', encoding='utf-8') as f:
    f.write(tab_content)

print("Done updating productos")
