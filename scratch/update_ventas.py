import sys

file_path = r'c:\Users\JEISER\Desktop\PREMIUN\Sistemas-de-ventas\templates\ventas\ventas.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update the table header
content = content.replace('<th style="width: 10%;" class="bg-info bg-opacity-10">PRECIO CASH</th>',
                          '<th style="width: 10%;" class="bg-primary bg-opacity-10">PRECIO MAYOR</th>\n                        <th style="width: 10%;" class="bg-info bg-opacity-10">PRECIO CASH</th>')

# 2. Update row generation logic 1
content = content.replace('<td class="bg-info bg-opacity-10">\n        <input type="number" name="precio_venta_contado_${itemCounter}"',
                          '<td class="bg-primary bg-opacity-10">\n        <input type="number" name="precio_venta_mayor_${itemCounter}" id="precio_venta_mayor_${itemCounter}" class="form-control form-control-sm" value="" step="0.01" readonly style="background-color: #e9ecef;">\n      </td>\n      <td class="bg-info bg-opacity-10">\n        <input type="number" name="precio_venta_contado_${itemCounter}"')

# 3. Update row generation logic 2
content = content.replace('<td class="bg-info bg-opacity-10">\n                  <input type="number" name="precio_venta_contado_${itemCounter}" id="precio_venta_contado_${itemCounter}" class="form-control form-control-sm" value="${precioVenta}" step="0.01" readonly style="background-color: #e9ecef;">',
                          '<td class="bg-primary bg-opacity-10">\n                  <input type="number" name="precio_venta_mayor_${itemCounter}" id="precio_venta_mayor_${itemCounter}" class="form-control form-control-sm" value="${precioMayor || 0}" step="0.01" readonly style="background-color: #e9ecef;">\n                </td>\n                <td class="bg-info bg-opacity-10">\n                  <input type="number" name="precio_venta_contado_${itemCounter}" id="precio_venta_contado_${itemCounter}" class="form-control form-control-sm" value="${precioVenta}" step="0.01" readonly style="background-color: #e9ecef;">')


with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done updating ventas.html")
