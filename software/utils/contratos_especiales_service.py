import os
from io import BytesIO
from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, KeepTogether
from reportlab.lib import colors
from software.utils.logo_utils import get_logo_image_for_pdf
from reportlab.lib.units import cm
from django.utils import timezone
from datetime import timedelta
from software.utils.numero_a_letras import numero_a_letras

def formatear_fecha_es(fecha):
    meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    return f"{fecha.day:02d} de {meses[fecha.month - 1]} del {fecha.year}"

def detectar_frecuencia(credito):
    """
    Detecta la frecuencia de pago basada en el cronograma de cuotas.
    Retorna: ('DIARIO', 'DIARIAS'), ('SEMANAL', 'SEMANALES'), ('QUINCENAL', 'QUINCENALES'), ('MENSUAL', 'MENSUALES')
    """
    from software.models.CuotasVentaModel import CuotasVenta
    if credito.idventa:
        cuotas = CuotasVenta.objects.filter(idventa=credito.idventa, estado=1, numero_cuota__gt=0).order_by('numero_cuota')
    else:
        cuotas = CuotasVenta.objects.filter(idcredito=credito, estado=1, numero_cuota__gt=0).order_by('numero_cuota')
    
    if cuotas.count() < 2:
        return 'MENSUAL', 'MENSUALES'
    
    # Calcular diferencia promedio en días entre las primeras cuotas
    c1 = cuotas[0].fecha_vencimiento
    c2 = cuotas[1].fecha_vencimiento
    diff = (c2 - c1).days
    
    if diff < 7:
        return 'DIARIO', 'DIARIAS'
    elif diff <= 13:
        return 'SEMANAL', 'SEMANALES'
    elif diff <= 20:
        return 'QUINCENAL', 'QUINCENALES'
    else:
        return 'MENSUAL', 'MENSUALES'

def generar_contrato_especial_pdf(credito, empresa, asume_gastos=False):
    """
    Genera el PDF del contrato de alquiler-venta especial basado en los datos del crédito.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    
    titulo_style = ParagraphStyle(
        'Titulo',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=11,
        alignment=1, # Centrado
        spaceAfter=15
    )
    
    texto_style = ParagraphStyle(
        'Texto',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        alignment=4, # Justificado
        leading=12,
        spaceAfter=8
    )
    
    firma_style = ParagraphStyle(
        'Firma',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        alignment=1 # Centrado
    )

    story = []

    # Extraer datos
    cliente = credito.idventa.idcliente if (credito.idventa and credito.idventa.idcliente) else credito.idcliente
    
    vehiculo = None
    if credito.id_vehiculo_id:
        from software.models.VehiculosModel import Vehiculo
        vehiculo = Vehiculo.objects.filter(pk=credito.id_vehiculo_id).first()

    if not vehiculo and credito.idventa:
        from software.models.VentaDetalleModel import VentaDetalle
        detalle = VentaDetalle.objects.filter(
            idventa=credito.idventa,
            tipo_item='vehiculo',
            estado=1,
            id_vehiculo__idproducto__isnull=False
        ).select_related(
            'id_vehiculo__idproducto__idmarca',
            'id_vehiculo__idproducto__idmodelo',
            'id_vehiculo__idproducto__idcolor',
            'id_vehiculo__idproducto__idcategoria',
            'id_vehiculo__idestadoproducto',
        ).first()
        if detalle:
            vehiculo = detalle.id_vehiculo
            
    producto = vehiculo.idproducto if vehiculo else None
    garante = credito.id_garante

    gerente = empresa.gerente_general or "JEISER FABIAN ROJAS DIAZ"
    dni_gerente = empresa.dni_gerente or "75733846"
    ruc_empresa = empresa.ruc or "20604051984"
    
    # Obtener dirección del gerente con su ubigeo
    def get_direccion_gerente_full(emp):
        parts = []
        if emp.direccion_gerente:
            parts.append(emp.direccion_gerente)
        
        ubigeo_parts = []
        if emp.id_distrito_gerente: ubigeo_parts.append(f"Distrito de {emp.id_distrito_gerente.nombre_distrito}")
        if emp.id_provincia_gerente: ubigeo_parts.append(f"Provincia de {emp.id_provincia_gerente.nombre_provincia}")
        if emp.id_region_gerente: ubigeo_parts.append(f"Departamento de {emp.id_region_gerente.nombre_region}")
        
        if ubigeo_parts:
            parts.append(", ".join(ubigeo_parts))
            
        return ", ".join(parts) if parts else emp.direccion

    domicilio_gerente = get_direccion_gerente_full(empresa)
    
    # Función para determinar etiqueta de documento
    def get_doc_label(numero):
        if not numero: return "DNI"
        num_str = str(numero).strip()
        return "RUC" if len(num_str) == 11 else "DNI"

    label_gerente = get_doc_label(dni_gerente)
    label_cliente = get_doc_label(cliente.numdoc)
    
    conyuge_nombre = cliente.conyuge_nombre
    conyuge_dni = cliente.conyuge_dni
    label_conyuge = get_doc_label(conyuge_dni) if conyuge_nombre else ""
    
    # Detección de frecuencia
    frec_nom, frec_adj = detectar_frecuencia(credito)
    
    # Ubicación formateada
    def get_ubigeo_text(obj):
        parts = []
        if obj.id_distrito: parts.append(f"Distrito de {obj.id_distrito.nombre_distrito}")
        if obj.id_provincia: parts.append(f"Provincia de {obj.id_provincia.nombre_provincia}")
        if obj.id_region: parts.append(f"Departamento de {obj.id_region.nombre_region}")
        return ", ".join(parts)

    ubicacion_cliente = get_ubigeo_text(cliente)
    if not ubicacion_cliente: ubicacion_cliente = "Distrito de Soritor, Provincia de Moyobamba, Departamento de San Martín"
    
    fecha_hoy = timezone.now()
    meses_es = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    ciudad_final = "TARAPOTO"
    if cliente and cliente.id_distrito:
        ciudad_final = cliente.id_distrito.nombre_distrito.upper()
    
    # -------------------------------------------------------------
    # LOGO
    # -------------------------------------------------------------
    logo_rl = get_logo_image_for_pdf(empresa, width_mm=80, height_mm=40, circular=False)
    if logo_rl:
        story.append(logo_rl)
        story.append(Spacer(1, 10))

    # -------------------------------------------------------------
    # CABECERA
    # -------------------------------------------------------------
    story.append(Paragraph("<b>CONTRATO DE ALQUILER VENTA A PLAZOS CON RETENCION DE VEHICULO</b>", titulo_style))
    
    texto_intro = f"""
    Conste por el presente documento un contrato de ALQUILER VENTA A PLAZOS CON RETENCION DE PROPIEDAD de un vehículo, 
    que celebran de una parte la empresa {empresa.razonsocial}, con RUC N° {ruc_empresa}, representada por su Gerente 
    General el(la) Sr(a). <b>{gerente}</b> con {label_gerente} N° <b>{dni_gerente}</b> con domicilio en {domicilio_gerente}, a quien en adelante se le denominara 
    como LA EMPRESA, y de la otra parte a quien se le llamara como EL ARRENDATARIO el Sr(a). <b>{cliente.razonsocial}</b> con {label_cliente} Nº <b>{cliente.numdoc}</b>; 
    """
    
    if conyuge_nombre:
        texto_intro += f"CONYUGUE del ARRENDATARIO la Sra/Sr. <b>{conyuge_nombre}</b> con {label_conyuge} N° <b>{conyuge_dni}</b>, "
    
    texto_intro += f"domiciliados en {cliente.direccion}, {ubicacion_cliente}, "
    
    if garante:
        label_garante = get_doc_label(garante.numdoc)
        ubicacion_garante = get_ubigeo_text(garante)
        texto_intro += f"interviniendo además el(la) Sr(a). <b>{garante.nombre}</b> con {label_garante} N° <b>{garante.numdoc}</b>, con domicilio en {garante.direccion}, {ubicacion_garante} a quien se le llamara LA GARANTE, "
    
    texto_intro += "en los siguientes términos y condiciones:"
    
    story.append(Paragraph(texto_intro, texto_style))

    v_estado_txt = "semi-nueva"
    if vehiculo and vehiculo.idestadoproducto:
        estado_db = vehiculo.idestadoproducto.nombreestadoproducto.lower()
        if estado_db == 'segunda':
            v_estado_txt = 'semi-nueva'
        elif estado_db == 'primera':
            v_estado_txt = 'nueva'
        else:
            v_estado_txt = estado_db

    # PRIMERO
    texto_primero = f"""
    <b>PRIMERO:</b> La Empresa {empresa.razonsocial}, entrega a EL ARRENDATARIO en calidad de alquiler-venta a <b>PAGO {frec_nom}</b>, 
    conforme a lo acordado ambas partes en el siguiente bien:
    <br/>
    Un {producto.idcategoria.nomcategoria if producto and producto.idcategoria else 'VEHÍCULO'} {v_estado_txt} marca <b>{producto.idmarca.nombremarca if producto and producto.idmarca else ''}</b>, donde los recibe a su entera satisfacción y en perfecto estado de funcionamiento previa comprobación por EL ARRENDATARIO; el mismo que cuenta con las siguientes características:
    """
    story.append(Paragraph(texto_primero, texto_style))
    
    # Tabla características
    v_serie = vehiculo.serie_chasis if vehiculo else ""
    v_motor = vehiculo.serie_motor if vehiculo else ""
    v_color = producto.idcolor.nombrecolor if producto and producto.idcolor else ""
    v_modelo = producto.idmodelo.nombremodelo if producto and producto.idmodelo else ""
    v_anio = str(vehiculo.anio) if vehiculo and vehiculo.anio else ""

    if asume_gastos:
        txt_asume_tramite = "ASUME LA EMPRESA"
        txt_asume_transf = "ASUME LA EMPRESA DEPENDIENDO DE SU PUNTUALIDAD."
    else:
        txt_asume_tramite = "ASUME EL ARRENDATARIO"
        txt_asume_transf = "ASUME EL ARRENDATARIO"

    caract_data = [
        ["MARCA", ":", producto.idmarca.nombremarca if producto and producto.idmarca else ""],
        ["MODELO", ":", v_modelo],
        ["AÑO DE MODELO", ":", v_anio],
        ["TIPO DE CARROCERIA", ":", producto.idcategoria.nomcategoria if producto and producto.idcategoria else ""],
        ["SERIE N°", ":", v_serie],
        ["MOTOR N°", ":", v_motor],
        ["COLOR", ":", v_color],
        ["TARJETA, PLACA", ":", txt_asume_tramite],
        ["TRANSFERENCIA", ":", txt_asume_transf]
    ]
    t_caract = Table(caract_data, colWidths=[4*cm, 0.5*cm, 10.5*cm])
    t_caract.setStyle(TableStyle([('FONT', (0,0), (-1,-1), 'Helvetica', 9), ('BOTTOMPADDING', (0,0), (-1,-1), 1)]))
    story.append(t_caract)
    
    story.append(Paragraph("EL ARRENDATARIO acepta el presente contrato y reconoce que el vehículo en adquisición será materia de GARANTIA VEHICULAR para la empresa hasta completar el 100% de pago del alquiler a fin de garantizar la deuda detallada en mención.", texto_style))

    # Obtener monto de cuota real desde el cronograma
    from software.models.CuotasVentaModel import CuotasVenta
    if credito.idventa:
        cuotas = CuotasVenta.objects.filter(idventa=credito.idventa, estado=1).order_by('numero_cuota')
    else:
        cuotas = CuotasVenta.objects.filter(idcredito=credito, estado=1).order_by('numero_cuota')

    m_cuota = 0
    if cuotas:
        c_ej = cuotas.filter(numero_cuota__gt=0).first()
        if not c_ej: c_ej = cuotas.first()
        if c_ej: m_cuota = c_ej.total
    if m_cuota == 0:
        m_cuota = (credito.monto_total - credito.monto_adelanto) / (credito.cantidad_cuotas if credito.cantidad_cuotas else 1)

    # SEGUNDO
    monto_letras = numero_a_letras(credito.monto_total).upper()
    texto_segundo = f"""
    <b>SEGUNDO:</b> El precio estipulado es de S/. {credito.monto_total:,.2f} ({monto_letras}), que EL ARRENDATARIO se obliga a cancelar en la forma siguiente: 
    A la firma del presente contrato de adelanto la suma de S/. {credito.monto_adelanto:,.2f} y el saldo será cancelado en <b>{credito.cantidad_cuotas} cuotas {frec_adj}</b> de S/. {m_cuota:,.2f} cada uno.
    """
    story.append(Paragraph(texto_segundo, texto_style))

    frec_pagos = "diarios" if frec_nom == "DIARIO" else frec_adj.lower()

    # Cláusulas estándar
    clauses = [
        "<b>TERCERO:</b> LA EMPRESA extenderá letras de cambio NO RENOVABLES giradas por la Empresa y/o un recibo por cada pago que realice y que son aceptadas por EL ARRENDATARIO.",
        "<b>CUARTO:</b> LA EMPRESA informa a EL ARRENDATARIO, que los pagos los realizara en el LOCAL ó ENTIDADES BANCARIAS, donde podrán abonar a las cuentas respectivas autorizadas por la Empresa en caso de no poder acudir a la oficina principal, asimismo EL ARRENDATARIO se hará Responsable de su mantenimiento y funcionamiento de su vehículo.",
        f"<b>QUINTO:</b> En caso de EXTRAVÍO y/o URTO del vehículo EL ARRENDATARIO se hará responsable de cumplir con los pagos hasta completar el total pactado, no libera a EL ARRENDATARIO de la obligación a continuar sus pagos {frec_pagos} conforme a lo estipulado en el presente contrato.",
        "<b>SEXTO:</b> Por medio de este contrato EL ARRENDATARIO se compromete a realizar sus pagos responsablemente, si en los últimos casos se aconteciera algún tipo de inconveniente establecido en el cronograma de pago; EL ARRENDATARIO tiene 24 horas para regularizarlo, en caso de que no se diera lo acordado de lo contrario como Empresa no veremos en la obligación o necesidad de realizar LA RETENCION DEL VEHICULO. como tal, la falta de pago generara intereses contando con solo 24 horas para recogerlo siempre y cuando se haya dado la regularización del pago.",
        f"<b>SEPTIMO:</b> En caso que EL ARRENDATARIO por motivos personales no se siente en condiciones de seguir realizando los pagos y/o incumpliese el pago de una de las armadas {frec_adj.lower()}, quedara sin efecto el presente contrato, estando obligado EL COMPRADOR a devolver el vehículo en las mismas condiciones como lo recibió por LA EMPRESA, perdiendo el monto cancelado hasta la fecha del incumplimiento, incluyendo el pago inicial, siendo exigible el pago íntegro del saldo deudor, más los cargos por concepto de interés, gastos de protestos de los avisos dados y demás pertenencias a la cobranza frustrada.",
        "<b>OCTAVO:</b> Ambas partes declaran que entre el precio pactado y el vehículo materia de GARANTIA VEHICULAR, existe la más justa y perfecta equivalencia no teniendo nada que reclamarse al respecto.",
        "<b>NOVENO:</b> Ambas partes dejan constancia que es de cuenta y responsabilidad del COMPRADOR, cualquier multa, infracción, accidentes, medida judicial y extrajudicial que pueda obtener con el vehículo.",
        "<b>DECIMO:</b> Durante la vigencia del presente contrato, EL ARRENDATARIO no podrá hacer ninguna modificación, ni contrato ó transacción, ni transferencia a terceros que involucre al vehículo, para ningún efecto, por estar pactada la reserva del derecho de LA EMPRESA."
    ]
    
    for clause in clauses:
        story.append(Paragraph(clause, texto_style))
        
    # Jurisdicción y datos de ciudad
    fecha_hoy = timezone.now()
    meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    
    sucursal = empresa.sucursales.filter(es_principal=True).first() if hasattr(empresa, 'sucursales') else None
    if not sucursal and hasattr(empresa, 'sucursales'):
        sucursal = empresa.sucursales.first()
        
    ciudad = sucursal.id_distrito.nombre_distrito if sucursal and sucursal.id_distrito else "TARAPOTO"
    provincia_empresa = sucursal.id_distrito.id_provincia.nombre_provincia if sucursal and sucursal.id_distrito and sucursal.id_distrito.id_provincia else "San Martin"

    # Cláusulas de Garante (Condicionales)
    if garante:
        garante_clauses = [
            "<b>DECIMO PRIMERO:</b> EL GARANTE realiza su firma con el pleno conocimiento, de que si en los últimos casos, EL ARRENDATARIO no cumpla con su compromiso plasmada en el contrato; EL GARANTE acepta y asume la responsabilidad total de todos los pagos que quedaron pendientes, cabe indicar, infracciones ante la ley, accidentes, robos, etc.",
            "<b>DECIMO SEGUNDO:</b> LA EMPRESA tendrá la facultad de liberar de toda obligación a EL GARANTE, solamente cuando éste entregue a LA EMPRESA la mercadería indicada en el presente contrato.",
            "<b>DECIMO TERCERO:</b> Si en caso EL ARRENDATARIO por motivos personales no se siente en condiciones de seguir realizando los pagos, EL GARANTE está en todo el derecho de tomar disposición del vehículo y seguir con los pagos hasta el 100% de lo pactado.",
            f"<b>DECIMO CUARTO:</b> Las partes que suscriben el presente contrato, así como EL GARANTE renuncian al fuero de sus domicilios y se someten expresamente a la jurisdicción de los tribunales y jueces de la ciudad de {provincia_empresa}, donde se encuentra el domicilio de LA EMPRESA."
        ]
        for gc in garante_clauses:
            story.append(Paragraph(gc, texto_style))
    else:
        # Si no hay garante, la cláusula final de jurisdicción igual debe estar (pero sin mencionar al garante)
        story.append(Paragraph(f"<b>DECIMO PRIMERO:</b> Las partes que suscriben el presente contrato renuncian al fuero de sus domicilios y se someten expresamente a la jurisdicción de los tribunales y jueces de la ciudad de {provincia_empresa}, donde se encuentra el domicilio de LA EMPRESA.", texto_style))

    # Texto final con fecha
    texto_final = f"En fe de lo acordado en pleno uso de sus facultades mentales y leído el presente documento por ambas partes, lo firman en señal de conformidad en la ciudad de {ciudad_final} a los {fecha_hoy.day:02d} días del mes de {meses_es[fecha_hoy.month - 1]} del {fecha_hoy.year}."
    
    bloque_firmas = []
    bloque_firmas.append(Spacer(1, 10))
    bloque_firmas.append(Paragraph(texto_final, texto_style))
    bloque_firmas.append(Spacer(1, 40))

    # Preparar bloques de firma dinámicos
    def crear_bloque_firma(texto):
        if not texto:
            return ""
        
        # Bloque izquierdo: Línea y texto
        t_izq = Table([
            [Paragraph("----------------------------------------------", firma_style)],
            [Paragraph(texto, firma_style)]
        ], colWidths=[6.5*cm])
        
        # Bloque derecho: Cuadro para huella
        t_der = Table([[""]], colWidths=[2.2*cm], rowHeights=[2.5*cm])
        t_der.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.black),
        ]))
        
        # Combinar en una tabla
        t_bloque = Table([[t_izq, t_der]], colWidths=[6.5*cm, 2.5*cm])
        t_bloque.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
        ]))
        return t_bloque

    firmas = []
    
    # Lista de firmas en orden
    bloques = [crear_bloque_firma(f"{cliente.razonsocial.upper()}<br/>DNI: {cliente.numdoc}<br/>EL ARRENDATARIO")]
    
    if conyuge_nombre:
        bloques.append(crear_bloque_firma(f"{conyuge_nombre.upper()}<br/>DNI: {conyuge_dni}<br/>CONYUGUE"))
        
    if garante:
        bloques.append(crear_bloque_firma(f"{garante.nombre.upper()}<br/>DNI: {garante.numdoc}<br/>GARANTE"))
        
    bloques.append(crear_bloque_firma(f"{empresa.razonsocial.upper()}<br/>RUC: {ruc_empresa}<br/>LA EMPRESA"))
    
    # Agrupar en filas de 2
    for i in range(0, len(bloques), 2):
        fila = bloques[i:i+2]
        while len(fila) < 2:
            fila.append("")
        firmas.append(fila)
        # Añadir espaciado entre filas si hay más bloques
        if i + 2 < len(bloques):
            firmas.append([Spacer(1, 25), Spacer(1, 25)])

    t_firmas = Table(firmas, colWidths=[9*cm, 9*cm])
    bloque_firmas.append(t_firmas)
    story.append(KeepTogether(bloque_firmas))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
