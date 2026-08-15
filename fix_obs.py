# -*- coding: utf-8 -*-
import os
import re

filepath = r"c:\Users\JEISER\Desktop\PREMIUN\Sistemas-de-ventas\software\views\ventas.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# I will use a different matching approach that is simpler to avoid regex escaping hell

old_multi = '''                        # Generar string de consolidación
                        partes = []
                        for i in range(len(tipos_pago_ids)):
                            tp_id = tipos_pago_ids[i]
                            monto = montos_pago[i]
                            nro = nros_operacion[i] if i < len(nros_operacion) else ''
                            tp_obj = TipoPago.objects.filter(pk=int(tp_id)).first()
                            tp_nombre = tp_obj.nombre if tp_obj else f"Pago {tp_id}"
                            nro_str = f" (Op: {nro})" if nro else ""
                            partes.append(f"{tp_nombre}: S/ {monto}{nro_str}")'''

new_multi = '''                        # Generar string de consolidación
                        partes = []
                        monedas_pago = request.POST.getlist('moneda_pago[]')
                        tcs_pago = request.POST.getlist('tc_pago[]')
                        for i in range(len(tipos_pago_ids)):
                            tp_id = tipos_pago_ids[i]
                            monto = montos_pago[i]
                            nro = nros_operacion[i] if i < len(nros_operacion) else ''
                            tp_obj = TipoPago.objects.filter(pk=int(tp_id)).first()
                            tp_nombre = tp_obj.nombre if tp_obj else f"Pago {tp_id}"
                            nro_str = f" (Op: {nro})" if nro else ""
                            moneda = monedas_pago[i] if i < len(monedas_pago) else 'PEN'
                            if moneda == 'USD':
                                tc = Decimal(tcs_pago[i]) if i < len(tcs_pago) and tcs_pago[i] else Decimal('1')
                                eqv = round(Decimal(monto) * tc, 2)
                                partes.append(f"{tp_nombre} (USD): $ {monto} (TC: {tc}) = S/ {eqv}{nro_str}")
                            else:
                                partes.append(f"{tp_nombre}: S/ {monto}{nro_str}")'''

# Let's check how it's actually indented
# Wait, let's just do a generic replace that ignores whitespace.
# It's easier to download the file and do multi_replace_file_content! Wait, the file is 2000 lines long.
