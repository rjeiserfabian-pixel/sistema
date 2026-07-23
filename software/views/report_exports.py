import openpyxl
from django.http import HttpResponse

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

def export_to_excel(headers, data_rows, filename):
    """
    Genera un archivo Excel (.xlsx) y lo retorna en una respuesta HTTP.
    headers: List[str]
    data_rows: List[List[Any]]
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reporte"
    
    # Escribir cabeceras
    ws.append(headers)
    
    # Escribir filas
    for row in data_rows:
        ws.append(row)
        
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename={filename}.xlsx'
    wb.save(response)
    
    return response

def export_to_pdf(headers, data_rows, title, filename):
    """
    Genera un archivo PDF tabular y lo retorna en una respuesta HTTP.
    Soluciona problemas de tablas muy anchas usando ajuste de texto y ajuste de tamaño.
    """
    from software.models.empresaModel import Empresa
    from software.utils.logo_utils import get_logo_image_for_pdf
    from reportlab.lib.units import mm

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
    
    # Ancho A4 landscape = 841.89 pt. Márgenes de 30 pt a cada lado -> 781.89 pt usables.
    doc = SimpleDocTemplate(response, pagesize=landscape(A4), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
    elements = []
    
    styles = getSampleStyleSheet()
    from reportlab.lib.styles import ParagraphStyle
    
    empresa = Empresa.objects.filter(activo=True).first()
    logo_rl = get_logo_image_for_pdf(empresa, width_mm=80, height_mm=40, circular=False)
    
    title_style = ParagraphStyle(
        'HeaderTitle',
        parent=styles['Title'],
        alignment=0, # Izquierda
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#003153')
    )
    
    title_p = Paragraph(title, title_style)
    
    header_data = [[title_p, logo_rl if logo_rl else '', '']]
    # Ajustamos anchos: más espacio a la izquierda para el texto, espacio suficiente al centro para el logo de 80mm
    header_table = Table(header_data, colWidths=[310, 230, 241])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
    ]))
    
    elements.append(header_table)
    elements.append(Spacer(1, 20))
    
    # Estilos para celdas con salto de línea automático
    cell_style = ParagraphStyle(
        'CustomCell',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        alignment=1, # Centrado
        textColor=colors.black
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Normal'],
        fontSize=9,
        leading=11,
        textColor=colors.whitesmoke,
        fontName='Helvetica-Bold',
        alignment=1 # Centrado
    )
    
    # Convertimos todo a Paragraph para que haga word-wrap si es muy largo
    table_data = []
    table_data.append([Paragraph(str(h), header_style) for h in headers])
    
    import html
    for row in data_rows:
        str_row = []
        for item in row:
            text = str(item) if item is not None else ""
            # Escape HTML to prevent ReportLab XML parser from breaking on < or &
            text = html.escape(text)
            # Restore our explicit <br/> tags that we added manually
            text = text.replace('&lt;br/&gt;', '<br/>')
            # DEBUG
            if len(text) > 50 or '<br/>' in text:
                pass # don't spam
            str_row.append(Paragraph(text, cell_style))
        table_data.append(str_row)
        
    # Asignar ancho de columnas para que encajen exacto en 780 pts
    num_cols = len(headers)
    col_widths = [781.0 / num_cols] * num_cols if num_cols > 0 else None
        
    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#003153')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f8f9fa')),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#dee2e6')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
    ]))
    
    elements.append(t)
    doc.build(elements)
    
    return response

def export_to_pdf_stock(vehiculos_headers, vehiculos_data, repuestos_headers, repuestos_data, title, filename):
    """
    Genera un archivo PDF tabular para el inventario de Stock con múltiples tablas (Vehículos y Repuestos)
    y lo retorna en una respuesta HTTP.
    """
    from software.models.empresaModel import Empresa
    from software.utils.logo_utils import get_logo_image_for_pdf
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from django.http import HttpResponse

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
    
    doc = SimpleDocTemplate(response, pagesize=landscape(A4), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
    elements = []
    
    styles = getSampleStyleSheet()
    
    empresa = Empresa.objects.filter(activo=True).first()
    logo_rl = get_logo_image_for_pdf(empresa, width_mm=80, height_mm=40, circular=False)
    
    title_style = ParagraphStyle(
        'HeaderTitle',
        parent=styles['Title'],
        alignment=0, # Izquierda
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#003153')
    )
    
    title_p = Paragraph(title, title_style)
    
    header_data = [[title_p, logo_rl if logo_rl else '', '']]
    header_table = Table(header_data, colWidths=[310, 230, 241])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
    ]))
    
    elements.append(header_table)
    elements.append(Spacer(1, 15))
    
    cell_style = ParagraphStyle(
        'CustomCell',
        parent=styles['Normal'],
        fontSize=7,
        leading=9,
        alignment=1, # Centrado
        textColor=colors.black
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        textColor=colors.whitesmoke,
        fontName='Helvetica-Bold',
        alignment=1 # Centrado
    )
    
    def render_table(headers, data, title_text):
        if not data and not headers:
            return
            
        elements.append(Paragraph(title_text, ParagraphStyle('t', parent=styles['Heading3'], textColor=colors.HexColor('#003153'))))
        elements.append(Spacer(1, 5))
        
        table_data = []
        table_data.append([Paragraph(str(h), header_style) for h in headers])
        
        for row in data:
            str_row = [Paragraph(str(item) if item is not None else "", cell_style) for item in row]
            table_data.append(str_row)
            
        num_cols = len(headers)
        col_widths = [781.0 / num_cols] * num_cols if num_cols > 0 else None
            
        t = Table(table_data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#003153')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f8f9fa')),
            ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#dee2e6')),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('TOPPADDING', (0,0), (-1,-1), 4),
        ]))
        
        elements.append(t)
        elements.append(Spacer(1, 15))

    if vehiculos_data:
        render_table(vehiculos_headers, vehiculos_data, "VEHÍCULOS")
    if repuestos_data:
        render_table(repuestos_headers, repuestos_data, "REPUESTOS")
        
    doc.build(elements)
    
    return response
