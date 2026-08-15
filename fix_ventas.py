import os

filepath = r"c:\Users\JEISER\Desktop\PREMIUN\Sistemas-de-ventas\software\views\ventas.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

import re

# Block 1
pattern1 = r"(tipos_pago_ids = request\.POST\.getlist\('tipo_pago_id\[\]'\)\s+montos_pago = request\.POST\.getlist\('monto_pago\[\]'\)\s+nros_operacion = request\.POST\.getlist\('nro_operacion\[\]'\)\s+if tipos_pago_ids:\s+# Calcular total de los pagos recibidos\s+)total_recibido = sum\(Decimal\(m\) for m in montos_pago if m\)\s+request\.POST\['importe_recibido'\] = str\(total_recibido\)"

repl1 = r"\1total_recibido = Decimal('0')\n                    for i, m in enumerate(montos_pago):\n                        if m:\n                            val = Decimal(m)\n                            moneda = request.POST.getlist('moneda_pago[]')[i] if i < len(request.POST.getlist('moneda_pago[]')) else 'PEN'\n                            if moneda == 'USD':\n                                tcs = request.POST.getlist('tc_pago[]')\n                                tc = Decimal(tcs[i]) if i < len(tcs) and tcs[i] else Decimal('1')\n                                val = val * tc\n                            total_recibido += val\n                    request.POST['importe_recibido'] = str(total_recibido)"

content = re.sub(pattern1, repl1, content)

# Block 2
pattern2 = r"(tipos_pago_ids = request\.POST\.getlist\('tipo_pago_id\[\]'\)\s+montos_pago = request\.POST\.getlist\('monto_pago\[\]'\)\s+nros_operacion = request\.POST\.getlist\('nro_operacion\[\]'\)\s+if not tipos_pago_ids:\s+return JsonResponse\(\{'ok': False, 'error': 'No se especificaron m.+todos de pago.'\}, status=400\)\s+)total_recibido = sum\(Decimal\(m\) for m in montos_pago if m\)"

repl2 = r"\1total_recibido = Decimal('0')\n            for i, m in enumerate(montos_pago):\n                if m:\n                    val = Decimal(m)\n                    moneda = request.POST.getlist('moneda_pago[]')[i] if i < len(request.POST.getlist('moneda_pago[]')) else 'PEN'\n                    if moneda == 'USD':\n                        tcs = request.POST.getlist('tc_pago[]')\n                        tc = Decimal(tcs[i]) if i < len(tcs) and tcs[i] else Decimal('1')\n                        val = val * tc\n                    total_recibido += val"

content = re.sub(pattern2, repl2, content)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print('Done')
