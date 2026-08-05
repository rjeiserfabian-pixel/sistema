import sys

file_path = r'c:\Users\JEISER\Desktop\PREMIUN\Sistemas-de-ventas\software\views\stock.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Line 461 - Repuesto update
content = content.replace('                precio_minimo=precio_minimo,',
                          '                precio_por_mayor=precio_por_mayor,\n                precio_minimo=precio_minimo,')
content = content.replace('precio_minimo = float(request.POST.get(\'precio_minimo\', \'0.0\'))',
                          'precio_por_mayor = float(request.POST.get(\'precio_por_mayor\', \'0.0\'))\n            precio_minimo = float(request.POST.get(\'precio_minimo\', \'0.0\'))')

# Update CompraDetalle logic
content = content.replace('            detalle_compra.precio_minimo = precio_minimo',
                          '            detalle_compra.precio_por_mayor = precio_por_mayor\n            detalle_compra.precio_minimo = precio_minimo')

# Line 842 - vehiculos api json
content = content.replace('            \'precio_minimo\': str(det.precio_minimo),',
                          '            \'precio_por_mayor\': str(det.precio_por_mayor) if hasattr(det, \'precio_por_mayor\') else \'0.00\',\n            \'precio_minimo\': str(det.precio_minimo),')

# Line 950 - repuestos api json
content = content.replace('        p_minimo = rep.precio_minimo or (det.precio_minimo if det else 0)',
                          '        p_por_mayor = getattr(rep, \'precio_por_mayor\', 0) or (getattr(det, \'precio_por_mayor\', 0) if det else 0)\n        p_minimo = rep.precio_minimo or (det.precio_minimo if det else 0)')

content = content.replace('            \'precio_minimo\': str(p_minimo),',
                          '            \'precio_por_mayor\': str(p_por_mayor),\n            \'precio_minimo\': str(p_minimo),')

# Update stock exports (lines 1098, 1129)
content = content.replace('            \'p_mayor\': float(det.precio_minimo) if det.precio_minimo else 0,',
                          '            \'p_mayor\': float(det.precio_minimo) if det.precio_minimo else 0,\n            \'p_por_mayor\': float(det.precio_por_mayor) if hasattr(det, \'precio_por_mayor\') and det.precio_por_mayor else 0,')
                          
content = content.replace('        p_mayor = float(rep.precio_minimo) if rep.precio_minimo else (float(det.precio_minimo) if det and det.precio_minimo else 0)',
                          '        p_por_mayor = float(rep.precio_por_mayor) if getattr(rep, \'precio_por_mayor\', None) else (float(det.precio_por_mayor) if det and getattr(det, \'precio_por_mayor\', None) else 0)\n        p_mayor = float(rep.precio_minimo) if rep.precio_minimo else (float(det.precio_minimo) if det and det.precio_minimo else 0)')


with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done updating stock.py")
