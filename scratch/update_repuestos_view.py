import sys

file_path = r'c:\Users\JEISER\Desktop\PREMIUN\Sistemas-de-ventas\software\views\repuestos.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add precio_por_mayor to agregar_repuesto
content = content.replace('precio_minimo  = float(request.POST.get(\'precio_minimo\', 0) or 0)',
                          'precio_por_mayor = float(request.POST.get(\'precio_por_mayor\', 0) or 0)\n        precio_minimo  = float(request.POST.get(\'precio_minimo\', 0) or 0)')

content = content.replace('costo_unitario=costo_unitario,\n            precio_minimo=precio_minimo,',
                          'costo_unitario=costo_unitario,\n            precio_por_mayor=precio_por_mayor,\n            precio_minimo=precio_minimo,')

# 2. Add precio_por_mayor to editar_repuesto
content = content.replace('precio_minimo  = float(request.POST.get(\'precio_minimo2\', 0) or 0)',
                          'precio_por_mayor = float(request.POST.get(\'precio_por_mayor2\', 0) or 0)\n        precio_minimo  = float(request.POST.get(\'precio_minimo2\', 0) or 0)')

content = content.replace('repuesto.costo_unitario    = costo_unitario\n        repuesto.precio_minimo     = precio_minimo',
                          'repuesto.costo_unitario    = costo_unitario\n        repuesto.precio_por_mayor  = precio_por_mayor\n        repuesto.precio_minimo     = precio_minimo')


with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

# 3. Update software/views/productos.py for api_listar_repuestos to include precio_por_mayor
prod_file = r'c:\Users\JEISER\Desktop\PREMIUN\Sistemas-de-ventas\software\views\productos.py'
with open(prod_file, 'r', encoding='utf-8') as f:
    prod_content = f.read()

prod_content = prod_content.replace('\'costo_unitario\': str(r.costo_unitario),\n            \'precio_minimo\': str(r.precio_minimo),',
                                    '\'costo_unitario\': str(r.costo_unitario),\n            \'precio_por_mayor\': str(r.precio_por_mayor),\n            \'precio_minimo\': str(r.precio_minimo),')

with open(prod_file, 'w', encoding='utf-8') as f:
    f.write(prod_content)


print("Done updating repuestos and productos views")
