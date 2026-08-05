import sys

file_path = r'c:\Users\JEISER\Desktop\PREMIUN\Sistemas-de-ventas\templates\ventas\ventas.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('>P. X MAYOR</th>', '>PRECIO CASH</th>')
content = content.replace('>P. X MENOR</th>', '>PRECIO LISTA</th>')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Done replacing in ventas.html!')
