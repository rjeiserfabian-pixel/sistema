import os
import re

filepath = r"c:\Users\JEISER\Desktop\PREMIUN\Sistemas-de-ventas\software\views\ventas.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Replace 1: nueva_venta_view
old1 = '''                    movimiento_caja = MovimientoCaja.objects.create(
                        id_caja=caja,
                        id_movimiento=apertura,  # 3. Asociar a la apertura actual
                        idusuario=usuario,
                        tipo_movimiento='ingreso',
                        monto=total,
                        descripcion=descripcion_movimiento,
                        idventa=venta,
                        estado=1
                    )'''
# Sometimes the comment has an encoding artifact like # o. Asociar a la apertura actual
# Better to use regex

pattern1 = r"movimiento_caja = MovimientoCaja\.objects\.create\(\s*id_caja=caja,\s*id_movimiento=apertura,.*?\s*idusuario=usuario,\s*tipo_movimiento='ingreso',\s*monto=total,\s*descripcion=descripcion_movimiento,\s*idventa=venta,\s*estado=1\s*\)"

repl1 = '''m_pagos = request.POST.getlist('monto_pago[]')
                    c_pagos = request.POST.getlist('moneda_pago[]')
                    t_pagos = request.POST.getlist('tc_pago[]')
                    if m_pagos:
                        for idx_pago, m_val in enumerate(m_pagos):
                            if m_val:
                                val_dec = Decimal(m_val)
                                moneda_str = c_pagos[idx_pago] if idx_pago < len(c_pagos) else 'PEN'
                                tc_dec = Decimal('1')
                                if moneda_str == 'USD':
                                    tc_dec = Decimal(t_pagos[idx_pago]) if idx_pago < len(t_pagos) and t_pagos[idx_pago] else Decimal('1')
                                monto_soles_dec = round(val_dec * tc_dec, 2)
                                movimiento_caja = MovimientoCaja.objects.create(
                                    id_caja=caja,
                                    id_movimiento=apertura,
                                    idusuario=usuario,
                                    tipo_movimiento='ingreso',
                                    monto=val_dec,
                                    moneda=moneda_str,
                                    tipo_cambio_aplicado=tc_dec,
                                    monto_base_soles=monto_soles_dec,
                                    descripcion=descripcion_movimiento,
                                    idventa=venta,
                                    estado=1
                                )
                    else:
                        movimiento_caja = MovimientoCaja.objects.create(
                            id_caja=caja,
                            id_movimiento=apertura,
                            idusuario=usuario,
                            tipo_movimiento='ingreso',
                            monto=total,
                            moneda='PEN',
                            tipo_cambio_aplicado=Decimal('1'),
                            monto_base_soles=total,
                            descripcion=descripcion_movimiento,
                            idventa=venta,
                            estado=1
                        )'''

content = re.sub(pattern1, repl1, content, flags=re.DOTALL)

# Replace 2: cobrar_venta_pendiente
pattern2 = r"MovimientoCaja\.objects\.create\(\s*id_caja=caja,\s*id_movimiento=apertura,\s*idusuario=usuario,\s*tipo_movimiento='ingreso',\s*monto=venta\.total_venta,\s*descripcion=descripcion,\s*idventa=venta,\s*estado=1\s*\)"

repl2 = '''m_pagos = request.POST.getlist('monto_pago[]')
                c_pagos = request.POST.getlist('moneda_pago[]')
                t_pagos = request.POST.getlist('tc_pago[]')
                if m_pagos:
                    for idx_pago, m_val in enumerate(m_pagos):
                        if m_val:
                            val_dec = Decimal(m_val)
                            moneda_str = c_pagos[idx_pago] if idx_pago < len(c_pagos) else 'PEN'
                            tc_dec = Decimal('1')
                            if moneda_str == 'USD':
                                tc_dec = Decimal(t_pagos[idx_pago]) if idx_pago < len(t_pagos) and t_pagos[idx_pago] else Decimal('1')
                            monto_soles_dec = round(val_dec * tc_dec, 2)
                            MovimientoCaja.objects.create(
                                id_caja=caja,
                                id_movimiento=apertura,
                                idusuario=usuario,
                                tipo_movimiento='ingreso',
                                monto=val_dec,
                                moneda=moneda_str,
                                tipo_cambio_aplicado=tc_dec,
                                monto_base_soles=monto_soles_dec,
                                descripcion=descripcion,
                                idventa=venta,
                                estado=1
                            )
                else:
                    MovimientoCaja.objects.create(
                        id_caja=caja,
                        id_movimiento=apertura,
                        idusuario=usuario,
                        tipo_movimiento='ingreso',
                        monto=venta.total_venta,
                        moneda='PEN',
                        tipo_cambio_aplicado=Decimal('1'),
                        monto_base_soles=venta.total_venta,
                        descripcion=descripcion,
                        idventa=venta,
                        estado=1
                    )'''

content = re.sub(pattern2, repl2, content, flags=re.DOTALL)


# Replace 3: actualizar_venta
pattern3 = r"MovimientoCaja\.objects\.create\(\s*id_caja_id=id_caja_session,\s*id_movimiento=apertura,\s*idusuario_id=request\.session\.get\('idusuario'\),\s*idventa=venta,\s*tipo_movimiento='ingreso',\s*monto=total_calculado,\s*descripcion=f'Venta \{venta\.numero_comprobante\} - Cliente: \{venta\.idcliente\.razonsocial\}',\s*estado=1\s*\)"

repl3 = '''m_pagos = request.POST.getlist('monto_pago[]')
                    c_pagos = request.POST.getlist('moneda_pago[]')
                    t_pagos = request.POST.getlist('tc_pago[]')
                    if m_pagos:
                        for idx_pago, m_val in enumerate(m_pagos):
                            if m_val:
                                val_dec = Decimal(m_val)
                                moneda_str = c_pagos[idx_pago] if idx_pago < len(c_pagos) else 'PEN'
                                tc_dec = Decimal('1')
                                if moneda_str == 'USD':
                                    tc_dec = Decimal(t_pagos[idx_pago]) if idx_pago < len(t_pagos) and t_pagos[idx_pago] else Decimal('1')
                                monto_soles_dec = round(val_dec * tc_dec, 2)
                                MovimientoCaja.objects.create(
                                    id_caja_id=id_caja_session,
                                    id_movimiento=apertura,
                                    idusuario_id=request.session.get('idusuario'),
                                    idventa=venta,
                                    tipo_movimiento='ingreso',
                                    monto=val_dec,
                                    moneda=moneda_str,
                                    tipo_cambio_aplicado=tc_dec,
                                    monto_base_soles=monto_soles_dec,
                                    descripcion=f'Venta {venta.numero_comprobante} - Cliente: {venta.idcliente.razonsocial}',
                                    estado=1
                                )
                    else:
                        MovimientoCaja.objects.create(
                            id_caja_id=id_caja_session,
                            id_movimiento=apertura,
                            idusuario_id=request.session.get('idusuario'),
                            idventa=venta,
                            tipo_movimiento='ingreso',
                            monto=total_calculado,
                            moneda='PEN',
                            tipo_cambio_aplicado=Decimal('1'),
                            monto_base_soles=total_calculado,
                            descripcion=f'Venta {venta.numero_comprobante} - Cliente: {venta.idcliente.razonsocial}',
                            estado=1
                        )'''

content = re.sub(pattern3, repl3, content, flags=re.DOTALL)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("Done with MovimientoCaja updates")
