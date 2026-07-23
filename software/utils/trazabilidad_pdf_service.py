from io import BytesIO
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

from software.utils.logo_utils import get_logo_image_for_pdf

# ── Paleta de colores corporativa ─────────────────────────────────
DARK_BLUE   = colors.HexColor('#0D1B2A')
ACCENT_BLUE = colors.HexColor('#1A73E8')
SILVER      = colors.HexColor('#B0BEC5')
LIGHT_GRAY  = colors.HexColor('#F4F6F8')
WHITE       = colors.white
TEXT_DARK   = colors.HexColor('#212121')
TEXT_MUTED  = colors.HexColor('#546E7A')
GOLD        = colors.HexColor('#F4A900')
SUCCESS_CLR = colors.HexColor('#10b981')
INFO_CLR    = colors.HexColor('#06b6d4')
WARNING_CLR = colors.HexColor('#f59e0b')
DANGER_CLR  = colors.HexColor('#ef4444')
PURPLE_CLR  = colors.HexColor('#a855f7')
PRIMARY_CLR = colors.HexColor('#3b82f6')

def get_styles():
    styles = getSampleStyleSheet()
    def style(name, **kwargs):
        base = styles.get(name, styles['Normal'])
        return ParagraphStyle(name + '_custom', parent=base, **kwargs)

    return {
        's_empresa': style('Heading1', fontSize=18, fontName='Helvetica-Bold', textColor=DARK_BLUE, leading=22, spaceAfter=4),
        's_empresa_sub': style('Normal', fontSize=8, fontName='Helvetica', textColor=TEXT_MUTED, leading=10),
        's_cliente_data': style('Normal', fontSize=9, fontName='Helvetica', textColor=TEXT_DARK, leading=14),
        's_th': style('Normal', fontSize=8, fontName='Helvetica-Bold', textColor=WHITE, alignment=TA_CENTER),
        's_cell': style('Normal', fontSize=8, fontName='Helvetica', textColor=TEXT_DARK, leading=11),
        's_cell_center': style('Normal', fontSize=8, fontName='Helvetica', textColor=TEXT_DARK, alignment=TA_CENTER, leading=11),
        's_cell_right': style('Normal', fontSize=8, fontName='Helvetica', textColor=TEXT_DARK, alignment=TA_RIGHT, leading=11),
        's_section_hdr': style('Normal', fontSize=9, fontName='Helvetica-Bold', textColor=DARK_BLUE, spaceBefore=6, spaceAfter=3),
        'tl_title': style('Normal', fontSize=10, fontName='Helvetica-Bold', textColor=TEXT_DARK, spaceBefore=2),
        'tl_detail': style('Normal', fontSize=9, fontName='Helvetica', textColor=TEXT_MUTED, leading=12),
        'tl_date': style('Normal', fontSize=8, fontName='Helvetica-Oblique', textColor=TEXT_MUTED),
    }

def _crear_encabezado(empresa, titulo="REPORTE DE TRAZABILIDAD", subtitulo=""):
    styles = get_styles()
    empresa_nombre = empresa.nombrecomercial if empresa else 'EMPRESA S.A.C.'
    empresa_ruc    = f"RUC: {empresa.ruc}" if empresa else 'RUC: 00000000000'
    empresa_dir    = empresa.direccion if empresa else '-'
    empresa_tel    = f"Telf.: {empresa.telefono}" if (empresa and empresa.telefono) else ''
    empresa_email  = f"Email: {empresa.pagina}" if (empresa and empresa.pagina) else ''

    col_logo = Paragraph(
        f'<font color="white" size="28">&#9670;</font>',
        ParagraphStyle('logo_icon', fontSize=28, textColor=GOLD, alignment=TA_LEFT)
    )
    logo_rl = get_logo_image_for_pdf(empresa, width_mm=35, height_mm=22, circular=False)
    
    left_col = logo_rl if logo_rl else col_logo

    empresa_info = [
        Paragraph(empresa_nombre, styles['s_empresa']),
        Paragraph(empresa_ruc, styles['s_empresa_sub']),
        Paragraph(empresa_dir, styles['s_empresa_sub']),
        Paragraph(empresa_tel, styles['s_empresa_sub']),
        Paragraph(empresa_email, styles['s_empresa_sub']),
    ]

    proforma_info = [
        Paragraph(f'<font color="#F4A900"><b>{titulo}</b></font>',
                  ParagraphStyle('pf_num', fontSize=16, fontName='Helvetica-Bold',
                                 textColor=GOLD, alignment=TA_RIGHT, leading=20)),
        Paragraph(f'<b>{subtitulo}</b>',
                  ParagraphStyle('pf_n', fontSize=10, fontName='Helvetica-Bold',
                                 textColor=DARK_BLUE, alignment=TA_RIGHT, leading=14)),
    ]

    info_table = Table(
        [[left_col, empresa_info, proforma_info]],
        colWidths=[4.2 * cm, 9.3 * cm, 5 * cm]
    )
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), WHITE),
        ('BOX', (0, 0), (-1, -1), 0.8, SILVER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (0, 0), 10),
        ('LEFTPADDING', (1, 0), (1, 0), 8),
        ('RIGHTPADDING', (-1, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('ROUNDEDCORNERS', [6, 6, 6, 6]),
    ]))
    return info_table

def generar_pdf_vehiculo(data, empresa):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=1.5 * cm, leftMargin=1.5 * cm, topMargin=1.5 * cm, bottomMargin=2 * cm
    )
    story = []
    styles = get_styles()

    v = data['vehiculo']
    story.append(_crear_encabezado(empresa, "TRAZABILIDAD", f"VEHÍCULO: {v['serie_motor']}"))
    story.append(Spacer(1, 10))

    # --- Detalles del Vehiculo ---
    detalles_rows = [
        [Paragraph('<b>DATOS DEL VEHÍCULO</b>',
                   ParagraphStyle('cli_hdr', fontSize=9, fontName='Helvetica-Bold', textColor=ACCENT_BLUE)), ''],
        [Paragraph('<b>Vehículo:</b>', styles['s_cliente_data']), Paragraph(f"{v['nombre']}", styles['s_cliente_data'])],
        [Paragraph('<b>Marca / Modelo:</b>', styles['s_cliente_data']), Paragraph(f"{v['marca']} / {v['modelo']}", styles['s_cliente_data'])],
        [Paragraph('<b>Serie Motor:</b>', styles['s_cliente_data']), Paragraph(f"{v['serie_motor']}", styles['s_cliente_data'])],
        [Paragraph('<b>Serie Chasis:</b>', styles['s_cliente_data']), Paragraph(f"{v['serie_chasis']}", styles['s_cliente_data'])],
        [Paragraph('<b>Color / Año:</b>', styles['s_cliente_data']), Paragraph(f"{v['color']} / {v['anio']}", styles['s_cliente_data'])],
        [Paragraph('<b>Estado Actual:</b>', styles['s_cliente_data']), Paragraph(f"<b>{v['estado_label']}</b>", styles['s_cliente_data'])],
    ]
    det_table = Table(detalles_rows, colWidths=[4 * cm, 14.5 * cm])
    det_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT_GRAY),
        ('SPAN', (0, 0), (-1, 0)),
        ('BOX', (0, 0), (-1, -1), 0.8, SILVER),
        ('INNERGRID', (0, 1), (-1, -1), 0.3, SILVER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(det_table)
    story.append(Spacer(1, 15))

    # --- Linea de tiempo ---
    story.append(Paragraph('LÍNEA DE TIEMPO', styles['s_section_hdr']))
    story.append(HRFlowable(width='100%', thickness=0.5, color=SILVER, spaceAfter=8))
    
    tl_data = []
    def add_tl_item(date_str, title_str, detail_str, color):
        bullet = Paragraph(f'<font color="{color}">•</font>', ParagraphStyle('b', fontSize=18, alignment=TA_CENTER))
        body = [
            Paragraph(title_str, styles['tl_title']),
            Paragraph(date_str, styles['tl_date']),
            Paragraph(detail_str, styles['tl_detail'])
        ]
        tl_data.append([bullet, body])

    if data.get('compra'):
        c = data['compra']
        add_tl_item(
            c['fecha'],
            "Ingreso al Stock",
            f"Proveedor: {c['proveedor']} | Precio Compra: {c['precio_compra']} | Almacén: {c['almacen']} | Comprobante: {c['comprobante']}",
            PRIMARY_CLR.hexval()
        )
        
    for t in data.get('transferencias', []):
        add_tl_item(
            t['fecha'],
            "Transferencia",
            f"{t['origen']} -> {t['destino']} | Guía: {t['guia']} | Estado: {t['estado']}",
            PURPLE_CLR.hexval()
        )
        
    if data.get('venta'):
        venta_det = data['venta']
        add_tl_item(
            venta_det['fecha'],
            f"Vendido - {venta_det['tipo_comprobante']}: {venta_det['comprobante']}",
            f"Cliente: {venta_det['cliente']} (Doc: {venta_det['cliente_doc']}) | Venta: {venta_det['precio_venta']} | Pago: {venta_det['forma_pago']} | Almacén: {venta_det['almacen']} | Estado: {venta_det['estado']}",
            SUCCESS_CLR.hexval()
        )
        
    if data.get('credito'):
        cr = data['credito']
        add_tl_item(
            "-",
            f"Crédito Generado - {cr['codigo']}",
            f"Total: {cr['monto_total']} | Adelanto: {cr['adelanto']} | Saldo: {cr['saldo']} | Cuotas: {cr['cuotas']} | Estado: {cr['estado']} | Garante: {cr['garante']}",
            INFO_CLR.hexval()
        )
        
    for a in data.get('auditorias', []):
        add_tl_item(
            a['fecha'],
            a['accion'],
            f"Motivo: {a['motivo']} | Usuario: {a['usuario']}",
            DANGER_CLR.hexval()
        )

    if not tl_data:
        tl_data.append(["", Paragraph("Sin eventos registrados.", styles['tl_detail'])])

    tl_table = Table(tl_data, colWidths=[1*cm, 17.5*cm])
    tl_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(tl_table)

    doc.build(story)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Trazabilidad_{v["serie_motor"]}.pdf"'
    return response


def generar_pdf_repuesto(data, empresa):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=1.5 * cm, leftMargin=1.5 * cm, topMargin=1.5 * cm, bottomMargin=2 * cm
    )
    story = []
    styles = get_styles()

    r = data['repuesto']
    story.append(_crear_encabezado(empresa, "TRAZABILIDAD", f"REPUESTO: {r['codigo_barras']}"))
    story.append(Spacer(1, 10))

    # --- Detalles del Repuesto ---
    detalles_rows = [
        [Paragraph('<b>DATOS DEL REPUESTO</b>',
                   ParagraphStyle('cli_hdr', fontSize=9, fontName='Helvetica-Bold', textColor=ACCENT_BLUE)), ''],
        [Paragraph('<b>Repuesto:</b>', styles['s_cliente_data']), Paragraph(f"{r['nombre']}", styles['s_cliente_data'])],
        [Paragraph('<b>Marca / Categoría:</b>', styles['s_cliente_data']), Paragraph(f"{r['marca']} / {r['categoria']}", styles['s_cliente_data'])],
        [Paragraph('<b>Código de Barras:</b>', styles['s_cliente_data']), Paragraph(f"{r['codigo_barras']}", styles['s_cliente_data'])],
        [Paragraph('<b>Código Interno:</b>', styles['s_cliente_data']), Paragraph(f"{r['codigo_interno']}", styles['s_cliente_data'])],
        [Paragraph('<b>Compatibilidad:</b>', styles['s_cliente_data']), Paragraph(f"{r['compatibilidad']}", styles['s_cliente_data'])],
        [Paragraph('<b>Stock Actual:</b>', styles['s_cliente_data']), Paragraph(f"<b>{r['stock_actual']} uds.</b>", styles['s_cliente_data'])],
    ]
    det_table = Table(detalles_rows, colWidths=[4 * cm, 14.5 * cm])
    det_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT_GRAY),
        ('SPAN', (0, 0), (-1, 0)),
        ('BOX', (0, 0), (-1, -1), 0.8, SILVER),
        ('INNERGRID', (0, 1), (-1, -1), 0.3, SILVER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(det_table)
    story.append(Spacer(1, 15))

    # --- Resumen Estadistico ---
    story.append(Paragraph('RESUMEN DE MOVIMIENTOS', styles['s_section_hdr']))
    story.append(HRFlowable(width='100%', thickness=0.5, color=SILVER, spaceAfter=8))
    
    stats_data = [
        [
            Paragraph(f"<font color='{PRIMARY_CLR.hexval()}'><b>{r['total_ingresado']}</b></font><br/>INGRESADOS", styles['s_cell_center']),
            Paragraph(f"<font color='{DANGER_CLR.hexval()}'><b>{r['total_vendido']}</b></font><br/>VENDIDOS", styles['s_cell_center']),
            Paragraph(f"<font color='{SUCCESS_CLR.hexval()}'><b>{r['stock_actual']}</b></font><br/>STOCK ACTUAL", styles['s_cell_center'])
        ]
    ]
    stats_table = Table(stats_data, colWidths=[6.1*cm, 6.1*cm, 6.1*cm])
    stats_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.8, SILVER),
        ('INNERGRID', (0, 0), (-1, -1), 0.3, SILVER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY)
    ]))
    story.append(stats_table)
    story.append(Spacer(1, 15))

    # Helper function for rendering tables of compras/ventas
    def create_history_table(title, headers, data_rows, col_widths):
        story.append(Paragraph(title, styles['s_section_hdr']))
        story.append(HRFlowable(width='100%', thickness=0.5, color=SILVER, spaceAfter=8))
        
        table_data = [[Paragraph(h, styles['s_th']) for h in headers]]
        for row in data_rows:
            table_data.append([Paragraph(str(item), styles['s_cell']) for item in row])
            
        t = Table(table_data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), DARK_BLUE),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
            ('BOX', (0, 0), (-1, -1), 0.8, SILVER),
            ('INNERGRID', (0, 0), (-1, -1), 0.3, SILVER),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(t)
        story.append(Spacer(1, 15))

    # --- Historial de Compras ---
    if data['compras']:
        c_rows = []
        for c in data['compras']:
            c_rows.append([c['fecha'], c['proveedor'], c['cantidad'], c['precio_unitario'], c['subtotal'], c['comprobante'], c['almacen']])
        create_history_table("HISTORIAL DE COMPRAS", 
                             ['Fecha', 'Proveedor', 'Cant.', 'P. Unit', 'Subtotal', 'Comprobante', 'Almacén'], 
                             c_rows, [2*cm, 4*cm, 1.2*cm, 2*cm, 2*cm, 3*cm, 4.3*cm])

    # --- Historial de Ventas ---
    if data['ventas']:
        v_rows = []
        for v in data['ventas']:
            v_rows.append([v['fecha'], v['cliente'], v['cantidad'], v['precio_unitario'], v['subtotal'], v['comprobante'], v['almacen']])
        create_history_table("HISTORIAL DE VENTAS", 
                             ['Fecha', 'Cliente', 'Cant.', 'P. Unit', 'Subtotal', 'Comprobante', 'Almacén'], 
                             v_rows, [2.5*cm, 4*cm, 1.2*cm, 2*cm, 2*cm, 3*cm, 3.8*cm])

    # --- Stock por Almacen ---
    if data['stock_detalle']:
        s_rows = []
        for s in data['stock_detalle']:
            s_rows.append([s['almacen'], s['cantidad']])
        create_history_table("STOCK POR ALMACÉN", 
                             ['Almacén', 'Cantidad Disponible'], 
                             s_rows, [10*cm, 8.5*cm])


    doc.build(story)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Trazabilidad_Rep_{r["codigo_barras"]}.pdf"'
    return response
