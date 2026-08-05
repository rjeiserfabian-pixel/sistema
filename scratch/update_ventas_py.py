import sys

file_path = r'c:\Users\JEISER\Desktop\PREMIUN\Sistemas-de-ventas\software\views\ventas.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update vehiculos stock (around line 149)
content = content.replace('                    \'precio_minimo\': float(detalle_compra.precio_minimo),',
                          '                    \'precio_por_mayor\': float(detalle_compra.precio_por_mayor) if hasattr(detalle_compra, \'precio_por_mayor\') else 0,\n                    \'precio_minimo\': float(detalle_compra.precio_minimo),')

# 2. Update repuestos logic (around line 235)
content = content.replace('            p_mayor = float(rep_cat.precio_minimo) if rep_cat and rep_cat.precio_minimo else (float(detalle_compra.precio_minimo) if detalle_compra and detalle_compra.precio_minimo else 0)',
                          '            p_por_mayor = float(rep_cat.precio_por_mayor) if rep_cat and getattr(rep_cat, \'precio_por_mayor\', None) else (float(detalle_compra.precio_por_mayor) if detalle_compra and getattr(detalle_compra, \'precio_por_mayor\', None) else 0)\n            p_mayor = float(rep_cat.precio_minimo) if rep_cat and rep_cat.precio_minimo else (float(detalle_compra.precio_minimo) if detalle_compra and detalle_compra.precio_minimo else 0)')

content = content.replace('            precio_minimo_val = p_mayor',
                          '            precio_por_mayor_val = p_por_mayor\n            precio_minimo_val = p_mayor')

content = content.replace('                \'precio_minimo\': precio_minimo_val,',
                          '                \'precio_por_mayor\': precio_por_mayor_val,\n                \'precio_minimo\': precio_minimo_val,')

# 3. Update the fallback logic (around 279)
content = content.replace('            precio_minimo_pc  = 0',
                          '            precio_por_mayor_pc = 0\n            precio_minimo_pc  = 0')

content = content.replace('                    precio_minimo_pc  = float(detalle_compra.precio_minimo)',
                          '                    precio_por_mayor_pc = float(detalle_compra.precio_por_mayor) if hasattr(detalle_compra, \'precio_por_mayor\') else 0\n                    precio_minimo_pc  = float(detalle_compra.precio_minimo)')

content = content.replace('                    \'precio_minimo\':  precio_minimo_pc, # Por simplificacin',
                          '                    \'precio_por_mayor\': precio_por_mayor_pc,\n                    \'precio_minimo\':  precio_minimo_pc, # Por simplificacin')
content = content.replace('                    \'precio_minimo\':  precio_minimo_pc, # Por simplificación',
                          '                    \'precio_por_mayor\': precio_por_mayor_pc,\n                    \'precio_minimo\':  precio_minimo_pc, # Por simplificación')

# 4. JSON parsing in guardar_venta logic (around 2038)
content = content.replace('                precio_minimo = float(d.precio_venta_contado)',
                          '                precio_por_mayor = float(getattr(d, \'precio_venta_mayor\', 0) or 0)\n                precio_minimo = float(d.precio_venta_contado)')

# But wait, wait, the JSON received might not have 'precio_venta_mayor' mapped in `d` if it's not a model but just POST fields.
# Actually, `d` is an object derived from JSON payload of the sale details!
# Let me look closer at line 2038
# I'll just skip 4 for now and check how the Javascript builds the payload.

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done updating ventas.py")
