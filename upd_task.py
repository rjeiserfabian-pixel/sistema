import os

filepath = r"c:\Users\JEISER\.gemini\antigravity-ide\brain\4e8e8a48-34af-473a-9dc9-690c8fd73b48\task.md"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("- [ ] Update entas.py (
ueva_venta_view, ctualizar_venta y cobros) to generate multi-currency MovimientoCaja records.", "- [x] Update entas.py (
ueva_venta_view, ctualizar_venta y cobros) to generate multi-currency MovimientoCaja records.")
content = content.replace("- [ ] Update entas.py to generate detailed multi-currency strings in Ventas.observaciones.", "- [x] Update entas.py to generate detailed multi-currency strings in Ventas.observaciones.")
content = content.replace("- [ ] Identify and update the 'Movimientos de Caja' UI template to show actual currency amount and symbol.", "- [/] Identify and update the 'Movimientos de Caja' UI template to show actual currency amount and symbol.")

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
