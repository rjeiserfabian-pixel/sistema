import sys

file_path = r'c:\Users\JEISER\Desktop\PREMIUN\Sistemas-de-ventas\templates\stock\stock.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update headers in the repuestos table (line 741 approx)
# We don't have the exact line for table headers. Let's just find "P. Cash" and replace with "P. Mayor</th> <th>P. Cash" for the th.
content = content.replace('<th style="width: 8%;">P. Cash</th>',
                          '<th style="width: 8%;">P. Mayor</th>\n                        <th style="width: 8%;">P. Cash</th>')

content = content.replace('<th class="bg-light text-dark" style="width: 8%;">P. Cash</th>',
                          '<th class="bg-light text-dark" style="width: 8%;">P. Mayor</th>\n                        <th class="bg-light text-dark" style="width: 8%;">P. Cash</th>')


# 2. Update render functions
content = content.replace('var pm = parseFloat(det.precio_minimo || 0).toFixed(2);',
                          'var pmayor = parseFloat(det.precio_por_mayor || 0).toFixed(2);\n    var pm = parseFloat(det.precio_minimo || 0).toFixed(2);')

content = content.replace('\'<td class="text-center align-middle"><span class="badge bg-success bg-opacity-10 text-success border border-success fw-bold">S/ \' + pm + \'</span></td>\' +',
                          '\'<td class="text-center align-middle"><span class="badge bg-primary bg-opacity-10 text-primary border border-primary fw-bold">S/ \' + pmayor + \'</span></td>\' +\n      \'<td class="text-center align-middle"><span class="badge bg-success bg-opacity-10 text-success border border-success fw-bold">S/ \' + pm + \'</span></td>\' +')

content = content.replace('\'<td class="text-center"><span class="badge bg-success bg-opacity-10 text-success border border-success fw-bold">S/ \' + pm + \'</span></td>\' +',
                          '\'<td class="text-center"><span class="badge bg-primary bg-opacity-10 text-primary border border-primary fw-bold">S/ \' + pmayor + \'</span></td>\' +\n      \'<td class="text-center"><span class="badge bg-success bg-opacity-10 text-success border border-success fw-bold">S/ \' + pm + \'</span></td>\' +')


# 3. Increase colspan where necessary
content = content.replace('colspan="12"', 'colspan="13"')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done updating stock.html")
