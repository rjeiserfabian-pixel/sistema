import os
from io import BytesIO
from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from software.utils.logo_utils import get_logo_image_for_pdf
from reportlab.lib.units import cm
from django.utils import timezone
from software.utils.numero_a_letras import numero_a_letras

def generar_pagare_pdf(credito, empresa):
    """
    Genera el PDF del Pagaré basado en los datos del crédito y la empresa.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm
    )

    styles = getSampleStyleSheet()
    
    titulo_style = ParagraphStyle(
        'Titulo',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=12,
        alignment=1, # Centrado
        spaceAfter=15
    )
    
    subtitulo_style = ParagraphStyle(
        'Subtitulo',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        alignment=0, # Izquierda
        spaceAfter=5,
        spaceBefore=10
    )
    
    texto_style = ParagraphStyle(
        'Texto',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        alignment=4, # Justificado
        leading=10,
        spaceAfter=5
    )
    
    texto_bold_style = ParagraphStyle(
        'TextoBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        alignment=4,
        leading=10,
        spaceAfter=5
    )

    firma_style = ParagraphStyle(
        'Firma',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        alignment=0 # Izquierda
    )

    story = []

    # Extraer datos
    cliente = credito.idventa.idcliente if (credito.idventa and credito.idventa.idcliente) else credito.idcliente
    garante = credito.id_garante
    
    from software.models.CuotasVentaModel import CuotasVenta
    if credito.idventa:
        cuotas = CuotasVenta.objects.filter(idventa=credito.idventa, estado=1).order_by('-numero_cuota')
    else:
        cuotas = CuotasVenta.objects.filter(idcredito=credito, estado=1).order_by('-numero_cuota')

    # Numero de pagare (reemplazando CR por PG)
    numero_pagare = credito.codigo_credito.replace('CR', 'PG') if credito.codigo_credito else "PG-SN"
    
    # Fecha de vencimiento (última cuota)
    fecha_vencimiento = None
    if cuotas.exists():
        fecha_vencimiento = cuotas.first().fecha_vencimiento
    else:
        fecha_vencimiento = timezone.now().date() # Fallback
        
    meses_es = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    
    monto_total = credito.monto_total
    monto_letras = numero_a_letras(monto_total).upper()
    
    # -------------------------------------------------------------
    # LOGO
    # -------------------------------------------------------------
    logo_rl = get_logo_image_for_pdf(empresa, width_mm=80, height_mm=40, circular=False)
    if logo_rl:
        story.append(logo_rl)
        story.append(Spacer(1, 10))
        
    # Encabezado con montos y fechas
    story.append(Paragraph("<b>PAGARE</b>", titulo_style))
    story.append(Spacer(1, 10))
    
    # Tabla para Importe y Nro Pagare
    data_header = [
        [Paragraph(f"<b>IMPORTE: S/. {monto_total:,.2f}</b>", texto_style), Paragraph(f"<b>Pagare Nro. {numero_pagare}</b>", texto_style)]
    ]
    t_header = Table(data_header, colWidths=[9*cm, 9*cm])
    story.append(t_header)
    story.append(Spacer(1, 5))
    
    txt_vence = f"Vence el <b>{fecha_vencimiento.day:02d}</b> de <b>{meses_es[fecha_vencimiento.month - 1]}</b> del <b>{fecha_vencimiento.year}</b>"
    story.append(Paragraph(txt_vence, texto_style))
    story.append(Paragraph("(Emitido de conformidad con la ley 29349)", texto_style))
    story.append(Spacer(1, 10))
    
    # Declaración inicial
    txt_declaracion = f"""
    Yo (nosotros) <b>{cliente.razonsocial.upper()}</b> reconozco (reconocemos) que adeudo (adeudamos) y pagare (pagaremos) solidariamente en
    la fecha de vencimiento indicada a la orden de la empresa <b>{empresa.razonsocial.upper()}</b>, en adelante
    LA EMPRESA o a quien esta se le hubiera cedido en su domicilio social a donde se presentare para su cobro ; el
    importe de LA EMPRESA o a quien esta se le hubiera cedido en su domicilio social a donde se presentare para su
    cobro; el importe de S/. <b>{monto_total:,.2f}</b> (<b>{monto_letras} NUEVOS SOLES</b>) Importe correspondiente a la liquidación de las
    sumas adeudadas a LA EMPRESA y que son de mi/nuestro cargo, conforme al contrato de crédito, para cuyo fiel
    y exacto cumplimiento, me obligo con todos mis bienes y futuros en la mejor forma de derecho en especial los
    que se encuentren en LA EMPRESA al efecto, asumo la obligación de las siguientes condiciones.
    """
    txt_declaracion = txt_declaracion.replace("LA EMPRESA", "<b>LA EMPRESA</b>")
    story.append(Paragraph(txt_declaracion, texto_style))
    story.append(Spacer(1, 5))
    
    story.append(Paragraph("<u>CLAUSULAS ESPECIALES DEL TITULO</u>", subtitulo_style))
    
    clausulas = [
        "<b>Primera.-</b> Conforme a lo pactado en el contrato de crédito antes indicado, y de conformidad con lo dispuesto por la LEY de Títulos y Valores o aquel que lo sustituya y/o modificatorias, autorizo / autorizamos a LA EMPRESA para que, en caso de producirse alguno de los supuestos establecidos en el referido contrato, los cuales facultan a LA EMPRESA a dar por vencidos todos los plazos del crédito; complete el presente pagare por el importe total adeudado del crédito, incluyendo los intereses, comisiones, títulos y gastos pactados en el referido contrato, en la fecha en que ejerzan la citada facultad, con vencimiento de esa misma fecha.",
        "<b>Segunda.-</b> Este pagare será pagado en la misma moneda que expresa este titulo valor por ser un producto de un préstamo de dinero otorgado por LA EMPRESA.",
        "<b>Tercera.-</b> El importe de este pagare y/o de su cuota, generara desde la fecha de emisión hasta la fecha de sus respectivo(s) vencimiento(s) un interés compensatorio que se pacta en la tasa efectiva de % anual y adicionalmente y sin necesidad de requerimiento previo alguno, el interés moratorio, de conformidad con lo dispuesto en Art. 1242 del Código Civil, por el tiempo que se demore su pago, con una tasa de interés moratorio, de conformidad con lo dispuesto en el Art.1242 del Código Civil, por el tiempo que demore su pago, con una tasa de interés moratorio efectivo de % anual por todo el plazo que pudiera transcurrir desde el otorgamiento del crédito hasta su cancelación total de obligación contenida en este documento,",
        "<b>Cuarta.-</b> Acepto / Aceptamos y doy / damos por valides desde ahora todas las renovaciones y prorrogas totales o parciales efectuada por LA EMPRESA o por su tenedor; por el plazo que este señale en este mismo documento, sin que sea necesario intervención alguna del obligado principal ni de los avalistas solidarios, tal como prevén los Art. 49 y siguiente de la Ley de Títulos Valores y el Art. 1279 del Código Civil y los que sobre la materia darse más adelantada.",
        "<b>Quinta.-</b> En caso de incumplimiento en el pago de una o mas cuotas pactadas, al importe deudor se le aplicara los intereses compensatorios e intereses moratorios a las tasas máximas aprobadas por LA EMPRESA desde la fecha de vencimiento hasta su total cancelación. Sin que sea necesario efectuar requerimiento previo de pago para constituir en mora al obligado principal ni a los avalistas solidarios. Incurriéndose en esta automáticamente por el solo hecho de vencimiento. Siendo de este caso lo dispuesto por el Art. 1323 del Código Civil.",
        "<b>Sexta.-</b> Las tasas de interés compensatorios, moratorios y comisiones podrán ser notificados por LA EMPRESA o su tenedor de tiempo en tiempo, conforme a las variaciones que, con carácter general disponga en su totalidad sin necesidad de avisos previos de acuerdo a las tasas vigentes de conformidad a lo establecido por el Art. 1243 del Código Civil.",
        "<b>Séptima.-</b> Los obligados principales y solidarios suscribientes del presente pagare dejan constancia que este documento no requiere el protesto notarial por falta de pago para tener merito ejecutivo, salvo lo dispuesto en el Art. 81.2 de la LEY 27287 y sus normas complementarias y/o modificatorias.",
        "<b>Octava.-</b> Serán de cargo de los obligados principales y avalistas solidarios, el pago integro de los tributos y gastos que afecten a este pagare o la obligación en el contenida. Los mismos que serán calculados y determinados por LA EMPRESA o su tenedor en la oportunidad en que ello se verifique.",
        "<b>Novena.-</b> El o los obligados principalmente y los avalistas solidarios autorizan desde ya expresamente a LA EMPRESA a cargar directamente en sus cuentas (sea en moneda nacional y/o extranjera) que mantengan en ella. El o las cuotas del Crédito que representan el pagare, así como a compensados con cualquier otro tipo de bien e pudiera tener poder sin que ello obligue o signifique responsabilidad para LA EMPRESA.",
        "<b>Decima.-</b> LA EMPRESA o su tenedor podrá entablar acción judicial para efectuar el cobro de este pagare donde lo tuviera por conveniente a cuyo efecto el obligado principal y los avalistas solidarios renuncian al fuero de su propio domicilio y/o cuantos puedan favorecerlos en el proceso judicial o fuera de el señalando como domicilio para todos los efectos y consecuencias que pudieran derivarse de la emisión del presente pagare, indicando en este documento, lugar donde se enviaran los avisos y se harán llegar todas las comunicaciones y/o notificaciones judiciales que resulten necesarias, para cual se someten expresamente a las leyes de la Republica del Peru y a la competencia de los Jueces y Salas del Distrito Judicial de la ciudad donde se suscribe el presente pagare.",
        "<b>Decima primera.-</b> Dejo \"amos\" constancia que el presente pagare no requiere ser protestado, por falta de pago, para obtener merito ejecutivo; sin embargo, LA EMPRESA, o el tenedor de este titulo, queda facultado a protestarlo por falta de pago en cuyo caso asumiré (mos) los gastos y comisiones de tal diligencia notarial o de la formalidad sustitutoria correspondiente. Esta diligencia del protesto podrá ser hecha mediante notificación que se curse al domicilio del emitente consignado en este pagare, salvo que se opte por la formalidad sustitutoria de Ley.<br/>Que se opte por la formalidad sustitutoria de Ley.",
        "<b>Decima Segunda.-</b> El o los obligado (s) principal (es) y el (los) obligados solidarios que suscriben autorizan desde ya expresamente a LA EMPRESA a cargar directamente en sus cuentas (sea en moneda nacional y/o extranjera) que mantengan en ella, el o las cuotas del crédito que representa el pagare, así como a compénsalos con cualquier otro tipo de bien que pudiera tener en su poder sin que ello obligue o signifique responsabilidad para LA EMPRESA."
    ]
    
    for c in clausulas:
        if c.startswith("<b>Decima.-</b>"):
            story.append(PageBreak())
            
        c = c.replace("LA EMPRESA", "<b>LA EMPRESA</b>")
        story.append(Paragraph(c, texto_style))
        
    story.append(Spacer(1, 35))
    
    # Firmas Cliente y Cónyuge
    def get_ubigeo_text(obj):
        parts = []
        if obj.id_distrito: parts.append(obj.id_distrito.nombre_distrito)
        if obj.id_provincia: parts.append(obj.id_provincia.nombre_provincia)
        if obj.id_region: parts.append(obj.id_region.nombre_region)
        return " - ".join(parts)

    cliente_distrito = cliente.id_distrito.nombre_distrito if cliente.id_distrito else ""
    
    def crear_firma_box(titulo, nombres, dni, domicilio, distrito):
        datos_firma = [
            [Paragraph("________________________________", firma_style)],
            [Paragraph(titulo, ParagraphStyle('TituloFirma', parent=firma_style, alignment=1, spaceAfter=5))],
            [Paragraph(f"Nombres: {nombres}", firma_style)],
            [Paragraph(f"DNI: {dni}", firma_style)],
            [Paragraph(f"Domicilio: {domicilio}", firma_style)],
            [Paragraph(f"Distrito: {distrito}", firma_style)]
        ]
        t_datos = Table(datos_firma, colWidths=[6*cm])
        
        t_bloque = Table([
            [t_datos, ""]
        ], colWidths=[6.5*cm, 2.5*cm], rowHeights=[2.5*cm])
        
        t_bloque.setStyle(TableStyle([
            ('BOX', (1,0), (1,0), 1, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        return t_bloque

    conyuge_nombre = cliente.conyuge_nombre if cliente.conyuge_nombre else ""
    conyuge_dni = cliente.conyuge_dni if cliente.conyuge_dni else ""
    
    firma_cli = crear_firma_box("Cliente", cliente.razonsocial.upper(), cliente.numdoc, cliente.direccion, cliente_distrito)
    firmas_1_row = [firma_cli]
    
    if conyuge_nombre:
        firma_cony_cli = crear_firma_box("Cónyuge o Conviviente del cliente", conyuge_nombre.upper(), conyuge_dni, cliente.direccion, cliente_distrito)
        firmas_1_row.append(firma_cony_cli)

    t_firmas_1 = Table([firmas_1_row], colWidths=[9*cm]*len(firmas_1_row))
    story.append(t_firmas_1)
    
    if garante:
        story.append(Spacer(1, 15))
        
        # FIANZA SOLIDARIA
        story.append(Paragraph("<u>FIANZA SOLIDARIA</u>", subtitulo_style))
        fianza_txt1 = "Nosotros los abajo firmantes nos constituimos en avalistas permanentes y en garantes solidarios de los obligados principales y entre nosotros mismo para la cual comprometemos nuestro patrimonio y depósito en LA EMPRESA en garantía del pago de las obligaciones contenidas en el presente pagare, obligándonos por la cantidad adeudada y aceptando sus limitaciones ni restricciones todas ya cada una de las clausulas especiales que figuran en el presente pagare."
        fianza_txt2 = "Para todos los efectos que pudieran derivarse de la suscripción del presente pagare, señalo / señalamos como mi / nuestro domicilio el, que a continuación aparece, a cuál deberán efectuarse todos los avisos y notificaciones correspondientes, sometiéndome / sometiéndonos expresamente a las leyes de la Republica del Perú y a la competencia de los Jueces y Salas del Distrito Judicial de la ciudad donde se suscribe el presente pagare."
        
        fianza_txt1 = fianza_txt1.replace("LA EMPRESA", "<b>LA EMPRESA</b>")
        
        story.append(Paragraph(fianza_txt1, texto_style))
        story.append(Paragraph(fianza_txt2, texto_style))
        
        story.append(Spacer(1, 45))
        
        garante_nombre = garante.nombre.upper()
        garante_dni = garante.numdoc
        garante_domicilio = garante.direccion
        garante_distrito = garante.id_distrito.nombre_distrito if garante.id_distrito else ""
        
        firma_aval = crear_firma_box("Avalista", garante_nombre, garante_dni, garante_domicilio, garante_distrito)
        firmas_2_row = [firma_aval]
        
        conyuge_aval_nombre = garante.conyuge_nombre if garante.conyuge_nombre else ""
        conyuge_aval_dni = garante.conyuge_dni if garante.conyuge_dni else ""
        
        if conyuge_aval_nombre:
            firma_cony_aval = crear_firma_box("Cónyuge o Conviviente del Aval", conyuge_aval_nombre.upper(), conyuge_aval_dni, garante_domicilio, garante_distrito)
            firmas_2_row.append(firma_cony_aval)
    
        t_firmas_2 = Table([firmas_2_row], colWidths=[9*cm]*len(firmas_2_row))
        story.append(t_firmas_2)

    def add_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(colors.gray)
        direccion = empresa.direccion if empresa.direccion else ""
        # Format as "Direccion - Tarapoto" if Tarapoto is not already there
        if "TARAPOTO" not in direccion.upper():
            texto_footer = f"{direccion} - TARAPOTO"
        else:
            texto_footer = direccion
            
        canvas.drawCentredString(A4[0] / 2.0, 1.5 * cm - 10, texto_footer)
        canvas.restoreState()

    doc.build(story, onFirstPage=add_footer, onLaterPages=add_footer)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
