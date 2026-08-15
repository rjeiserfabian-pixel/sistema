import os
import qrcode
from io import BytesIO
from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.units import cm
from django.utils import timezone
from software.utils.logo_utils import get_logo_image_for_pdf

def generar_guia_pdf(transferencia, logistica, detalles, empresa):
    """
    Genera el PDF de la Guía de Remisión Remitente basado en los datos de la transferencia.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1*cm,
        leftMargin=1*cm,
        topMargin=1*cm,
        bottomMargin=1*cm
    )

    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    estilo_normal = ParagraphStyle('Normal_Small', parent=styles['Normal'], fontSize=8, leading=10)
    estilo_negrita = ParagraphStyle('Bold_Small', parent=styles['Normal'], fontSize=8, leading=10, fontName='Helvetica-Bold')
    estilo_titulo_seccion = ParagraphStyle('SectionTitle', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', textColor=colors.white, backColor=colors.HexColor('#2c3e50'), borderPadding=2)
    
    story = []

    # --- CABECERA ---
    # circular=False para mostrar el logo completo (igual que PDF de compras)
    logo_rl = get_logo_image_for_pdf(empresa, width_mm=35, height_mm=22, circular=False)

    # Fila superior: Logo y Datos Empresa | Recuadro RUC
    datos_empresa = [
        [
            logo_rl if logo_rl else Paragraph("[LOGO EMPRESA]", estilo_normal),
            Table([
                [Paragraph(f"<b>{empresa.razonsocial}</b>", ParagraphStyle('Emp', fontSize=12, leading=14))],
                [Paragraph(f"{empresa.direccion}", estilo_normal)],
                [Paragraph(f"Teléfono: {empresa.telefono or ''}", estilo_normal)],
                [Paragraph(f"Email: {empresa.usersec or ''}", estilo_normal)],
            ], colWidths=[9.5*cm]),
            Table([
                [Paragraph(f"<b>R.U.C. {empresa.ruc}</b>", ParagraphStyle('Ruc', fontSize=12, alignment=1))],
                [Paragraph("<b>GUÍA DE REMISIÓN REMITENTE</b>", ParagraphStyle('Title', fontSize=10, alignment=1, textColor=colors.white, backColor=colors.HexColor('#003399')))],
                [Paragraph(f"<font color='red'>{transferencia.numero_guia or 'PENDIENTE'}</font>", ParagraphStyle('Num', fontSize=12, alignment=1))],
            ], colWidths=[5*cm], style=TableStyle([
                ('BOX', (0,0), (-1,-1), 1, colors.black),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))
        ]
    ]
    t_header = Table(datos_empresa, colWidths=[4*cm, 9.5*cm, 5.5*cm])
    t_header.setStyle(TableStyle([
        ('VALIGN',      (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (0, 0),   8),
        ('TOPPADDING',  (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_header)

    story.append(Spacer(1, 10))

    # --- DATOS DEL TRASLADO Y DESTINATARIO ---
    datos_traslado_dest = [
        [
            Table([
                [Paragraph("<b>DATOS DEL TRASLADO</b>", estilo_titulo_seccion)],
                [Paragraph(f"<b>Fecha de Emisión:</b> {transferencia.fecha_transferencia.strftime('%d/%m/%Y')}", estilo_normal)],
                [Paragraph(f"<b>Fecha Inicio Traslado:</b> {logistica.fecha_salida.strftime('%d/%m/%Y %H:%M') if logistica and logistica.fecha_salida else '---'}", estilo_normal)],
                [Paragraph(f"<b>Motivo del Traslado:</b> {transferencia.get_tipo_transferencia_display()}", estilo_normal)],
            ], colWidths=[9*cm]),
            Table([
                [Paragraph("<b>DATOS DEL DESTINATARIO</b>", estilo_titulo_seccion)],
                [Paragraph(f"<b>Razón Social / Nombres:</b> {empresa.razonsocial if not transferencia.id_almacen_destino else 'Traslado Interno'}", estilo_normal)],
                [Paragraph(f"<b>RUC / DNI:</b> {empresa.ruc}", estilo_normal)],
            ], colWidths=[9*cm])
        ]
    ]
    t_traslado = Table(datos_traslado_dest, colWidths=[9.5*cm, 9.5*cm])
    story.append(t_traslado)
    story.append(Spacer(1, 5))

    # --- PUNTOS DE PARTIDA Y LLEGADA ---
    puntos_data = [
        [Paragraph("<b>PUNTOS DE PARTIDA Y LLEGADA</b>", estilo_titulo_seccion), ""],
        [Paragraph(f"<b>Lugar de Partida:</b> {transferencia.lugar_origen or (transferencia.id_almacen_origen.nombre_almacen if transferencia.id_almacen_origen else '---')}", estilo_normal),
         Paragraph(f"<b>Lugar de Llegada:</b> {transferencia.lugar_destino or (transferencia.id_almacen_destino.nombre_almacen if transferencia.id_almacen_destino else '---')}", estilo_normal)],
        [Paragraph(f"<b>Dirección de Partida:</b> {transferencia.direccion_origen or (transferencia.id_almacen_origen.direccion if transferencia.id_almacen_origen and transferencia.id_almacen_origen.direccion else (transferencia.id_almacen_origen.id_sucursal.direccion if transferencia.id_almacen_origen else '---'))}", estilo_normal),
         Paragraph(f"<b>Dirección de Llegada:</b> {transferencia.direccion_destino or (transferencia.id_almacen_destino.direccion if transferencia.id_almacen_destino and transferencia.id_almacen_destino.direccion else (transferencia.id_almacen_destino.id_sucursal.direccion if transferencia.id_almacen_destino else '---'))}", estilo_normal)]
    ]
    t_puntos = Table(puntos_data, colWidths=[9.5*cm, 9.5*cm])
    t_puntos.setStyle(TableStyle([('SPAN', (0,0), (1,0))]))
    story.append(t_puntos)
    story.append(Spacer(1, 5))

    # --- UNIDAD DE TRANSPORTE Y CONDUCTOR ---
    transp_data = [
        [Paragraph("<b>UNIDAD DE TRANSPORTE Y CONDUCTOR</b> (Transporte Privado)", estilo_titulo_seccion), ""],
        [
            Paragraph(f"<b>Conductor:</b> {logistica.id_transporte_conductor.nombre_completo if logistica else '---'}", estilo_normal),
            Paragraph(f"<b>Marca del Vehículo:</b> {logistica.id_transporte_vehiculo.marca if logistica else '---'}", estilo_normal)
        ],
        [
            Paragraph(f"<b>DNI del Conductor:</b> {logistica.id_transporte_conductor.dni if logistica else '---'}", estilo_normal),
            Paragraph(f"<b>Placa del Vehículo:</b> {logistica.id_transporte_vehiculo.placa if logistica else '---'}", estilo_normal)
        ],
        [
            Paragraph(f"<b>Licencia de Conducir:</b> {logistica.id_transporte_conductor.licencia_conducir if logistica else '---'}", estilo_normal),
            Paragraph(f"<b>Tipo de Vehículo:</b> {logistica.id_transporte_vehiculo.get_tipo_display() if logistica else '---'}", estilo_normal)
        ]
    ]
    t_transp = Table(transp_data, colWidths=[9.5*cm, 9.5*cm])
    t_transp.setStyle(TableStyle([('SPAN', (0,0), (1,0))]))
    story.append(t_transp)
    story.append(Spacer(1, 10))

    # --- TABLA DE ITEMS ---
    header_table = [
        Paragraph("<b>ITEM</b>", ParagraphStyle('h', alignment=1, fontSize=8, textColor=colors.white)),
        Paragraph("<b>CANTIDAD</b>", ParagraphStyle('h', alignment=1, fontSize=8, textColor=colors.white)),
        Paragraph("<b>UNIDAD</b>", ParagraphStyle('h', alignment=1, fontSize=8, textColor=colors.white)),
        Paragraph("<b>DESCRIPCIÓN DEL PRODUCTO / DETALLES</b>", ParagraphStyle('h', alignment=0, fontSize=8, textColor=colors.white))
    ]
    
    tabla_items_data = [header_table]
    
    for i, detalle in enumerate(detalles, 1):
        if detalle.id_vehiculo:
            nombre = detalle.id_vehiculo.idproducto.nomproducto
            det_text = f"• Motor: {detalle.id_vehiculo.serie_motor}\n• Chasis: {detalle.id_vehiculo.serie_chasis}"
            unidad = "NIU (Unidad)"
        else:
            nombre = detalle.id_repuesto_comprado.id_repuesto.nombre
            det_text = f"• Código: {detalle.id_repuesto_comprado.id_repuesto.codigo_barras or '---'}"
            unidad = "UND (Unidad)"
            
        tabla_items_data.append([
            Paragraph(str(i), ParagraphStyle('c', alignment=1, fontSize=8)),
            Paragraph(str(detalle.cantidad), ParagraphStyle('c', alignment=1, fontSize=8)),
            Paragraph(unidad, ParagraphStyle('c', alignment=1, fontSize=8)),
            Paragraph(f"<b>{nombre}</b><br/>{det_text.replace(chr(10), '<br/>')}", estilo_normal)
        ])

    t_items = Table(tabla_items_data, colWidths=[1.5*cm, 2*cm, 2.5*cm, 13*cm])
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#003399')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(t_items)
    story.append(Spacer(1, 10))

    # --- PIE DE PÁGINA (Observaciones y QR) ---
    # Generar QR
    qr_data = f"Guía: {transferencia.numero_guia} | RUC: {empresa.ruc} | Fecha: {transferencia.fecha_transferencia}"
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white")
    
    qr_buffer = BytesIO()
    img_qr.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)
    
    obs_text = f"Referencia de sistema: Transferencia #{transferencia.id_transferencia}.\n{transferencia.observaciones or ''}"
    
    pie_data = [
        [
            Table([
                [Paragraph("<b>Observaciones:</b>", estilo_normal)],
                [Table([[Paragraph(obs_text.replace(chr(10), '<br/>'), estilo_normal)]], colWidths=[10*cm], style=TableStyle([('BOX', (0,0), (-1,-1), 0.5, colors.black)]))],
            ], colWidths=[11*cm]),
            Spacer(1, 1),
            Table([
                [Spacer(1, 30)],
                [Paragraph("_______________________", ParagraphStyle('f', alignment=1))],
                [Paragraph("<b>Recibí Conforme</b><br/>Nombre, Firma y DNI", ParagraphStyle('f', alignment=1, fontSize=7))],
            ], colWidths=[5*cm])
        ],
        [
            Image(qr_buffer, width=2.5*cm, height=2.5*cm),
            "",
            Paragraph("<font size=6>Representación impresa de la<br/>Guía de Remisión de Remitente.<br/>Generado por el sistema.</font>", ParagraphStyle('small', leading=8))
        ]
    ]
    t_pie = Table(pie_data, colWidths=[11*cm, 3*cm, 5*cm])
    t_pie.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
        ('SPAN', (0,1), (1,1)), # Placeholder
    ]))
    story.append(t_pie)

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
