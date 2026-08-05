import sys

file_path = r'c:\Users\JEISER\Desktop\PREMIUN\Sistemas-de-ventas\software\views\compras.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. _validar_lineas_compra
content = content.replace('            precio_compra = float(request.POST.get(f"precio_compra_{i}") or 0)\n            precio_minimo = float(request.POST.get(f"precio_minimo_{i}") or 0)\n            precio_maximo = float(request.POST.get(f"precio_maximo_{i}") or 0)',
                          '            precio_compra = float(request.POST.get(f"precio_compra_{i}") or 0)\n            precio_por_mayor = float(request.POST.get(f"precio_por_mayor_{i}") or 0)\n            precio_minimo = float(request.POST.get(f"precio_minimo_{i}") or 0)\n            precio_maximo = float(request.POST.get(f"precio_maximo_{i}") or 0)')

content = content.replace('if cantidad <= 0 or precio_compra <= 0 or precio_minimo <= 0 or precio_maximo <= 0:',
                          'if cantidad <= 0 or precio_compra <= 0 or precio_por_mayor <= 0 or precio_minimo <= 0 or precio_maximo <= 0:')

content = content.replace("f'Ítem {i}: la cantidad y los precios deben ser mayores a cero.'",
                          "f'Ítem {i}: la cantidad y los precios deben ser mayores a cero.'") # no change needed

# 2. nueva_compra extract fields
content = content.replace('                    precio_compra = float(request.POST.get(f"precio_compra_{i}") or 0)\n                    precio_minimo = float(request.POST.get(f"precio_minimo_{i}") or 0)\n                    precio_maximo = float(request.POST.get(f"precio_maximo_{i}") or 0)\n                    margen_minimo = float(request.POST.get(f"margen_minimo_{i}") or 0)\n                    margen_maximo = float(request.POST.get(f"margen_maximo_{i}") or 0)',
                          '                    precio_compra = float(request.POST.get(f"precio_compra_{i}") or 0)\n                    precio_por_mayor = float(request.POST.get(f"precio_por_mayor_{i}") or 0)\n                    precio_minimo = float(request.POST.get(f"precio_minimo_{i}") or 0)\n                    precio_maximo = float(request.POST.get(f"precio_maximo_{i}") or 0)\n                    margen_por_mayor = float(request.POST.get(f"margen_por_mayor_{i}") or 0)\n                    margen_minimo = float(request.POST.get(f"margen_minimo_{i}") or 0)\n                    margen_maximo = float(request.POST.get(f"margen_maximo_{i}") or 0)')

# 3. vehiculo CompraDetalle.objects.create
content = content.replace('                            precio_minimo=precio_minimo,\n                            precio_maximo=precio_maximo,\n                            margen_minimo=margen_minimo,\n                            margen_maximo=margen_maximo,',
                          '                            precio_por_mayor=precio_por_mayor,\n                            precio_minimo=precio_minimo,\n                            precio_maximo=precio_maximo,\n                            margen_por_mayor=margen_por_mayor,\n                            margen_minimo=margen_minimo,\n                            margen_maximo=margen_maximo,')

# 4. repuesto CompraDetalle.objects.create (this might match the same as above but let's be safe and check replacement count or do it globally)
# (Done by the previous replace since the text is identical!)

# 5. Repuesto.objects.filter update
content = content.replace('                                costo_unitario=nuevo_ppp,\n                                precio_minimo=precio_minimo,\n                                precio_sugerido=precio_maximo,',
                          '                                costo_unitario=nuevo_ppp,\n                                precio_por_mayor=precio_por_mayor,\n                                precio_minimo=precio_minimo,\n                                precio_sugerido=precio_maximo,')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done updating compras.py")
