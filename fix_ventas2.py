import os

filepath = r"c:\Users\JEISER\Desktop\PREMIUN\Sistemas-de-ventas\software\views\ventas.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("request.POST['importe_recibido'] = str(total_recibido)", "request.POST['importe_recibido'] = str(round(total_recibido, 2))")
content = content.replace("total_recibido += val", "total_recibido += round(val, 2)") # Apply rounding to cobro total_recibido too

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print('Done')
