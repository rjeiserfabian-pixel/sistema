import sys
import os

file_path = r'c:\Users\JEISER\Desktop\PREMIUN\Sistemas-de-ventas\templates\stock\stock.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('P. x Mayor (S/.) *', 'P. Cash (S/.) *')
content = content.replace('P. x Mayor *', 'P. Cash *')
content = content.replace('<i class="fa-solid fa-arrow-up me-1"></i>P. x Mayor</th>', '<i class="fa-solid fa-arrow-up me-1"></i>P. Cash</th>')

content = content.replace('P. x Menor (S/.) *', 'P. Lista (S/.) *')
content = content.replace('P. x Menor *', 'P. Lista *')
content = content.replace('<i class="fa-solid fa-arrow-up-right-dots me-1"></i>P. x Menor</th>', '<i class="fa-solid fa-arrow-up-right-dots me-1"></i>P. Lista</th>')

content = content.replace('P. x Mayor: S/ ', 'P. Cash: S/ ')
content = content.replace('P. x Menor: S/ ', 'P. Lista: S/ ')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Done!')
