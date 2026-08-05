import sys

file_path = r'c:\Users\JEISER\Desktop\PREMIUN\Sistemas-de-ventas\templates\ventas\ventas.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# For lines 2490, 2649, 2910 where we define precioVenta:
content = content.replace('      const precioVenta = parseFloat(el.precio_minimo) || 0;',
                          '      const precioMayor = parseFloat(el.precio_por_mayor) || 0;\n      const precioVenta = parseFloat(el.precio_minimo) || 0;')

content = content.replace('        const precioVenta = parseFloat(el.precio_minimo) || 0;',
                          '        const precioMayor = parseFloat(el.precio_por_mayor) || 0;\n        const precioVenta = parseFloat(el.precio_minimo) || 0;')

# For line 2055:
content = content.replace('        const precioVenta = parseFloat(selected.data(\'pv\')) || 0;',
                          '        const precioMayor = parseFloat(selected.data(\'pmayor\')) || 0;\n        const precioVenta = parseFloat(selected.data(\'pv\')) || 0;')


with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done updating ventas.html JS")
