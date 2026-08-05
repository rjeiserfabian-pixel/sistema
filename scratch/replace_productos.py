import os

modales_path = r'c:\Users\JEISER\Desktop\PREMIUN\Sistemas-de-ventas\templates\productos\componentes\repuestos_modales.html'
tab_path = r'c:\Users\JEISER\Desktop\PREMIUN\Sistemas-de-ventas\templates\productos\componentes\repuestos_tab.html'

# Update modales
with open(modales_path, 'r', encoding='utf-8') as f:
    modales_content = f.read()

modales_content = modales_content.replace('Precio x Mayor (S/)', 'Precio Cash (S/)')
modales_content = modales_content.replace('Precio x Menor (S/)', 'Precio Lista (S/)')

with open(modales_path, 'w', encoding='utf-8') as f:
    f.write(modales_content)

# Update tab
with open(tab_path, 'r', encoding='utf-8') as f:
    tab_content = f.read()

tab_content = tab_content.replace('Precio x Menor', 'Precio Lista')
# Just in case there's any hidden "Precio x Mayor"
tab_content = tab_content.replace('Precio x Mayor', 'Precio Cash')

with open(tab_path, 'w', encoding='utf-8') as f:
    f.write(tab_content)

print('Done replacing in productos!')
