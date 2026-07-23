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
    from software.models.CuotasVentaModel import CuotasVenta
    if credito.idventa:
        cuotas = CuotasVenta.objects.filter(idventa=credito.idventa, estado=1, numero_cuota__gt=0).order_by('numero_cuota')
    else:
        cuotas = CuotasVenta.objects.filter(idcredito=credito, estado=1, numero_cuota__gt=0).order_by('numero_cuota')
    
    if cuotas.count() < 2:
        return 'MENSUAL', 'MENSUALES'
    
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

def generar_contrato_pdf(credito, empresa, asume_gastos=None):
    """
    Genera el PDF del contrato de alquiler-venta completo (4 partes) con las mejoras implementadas.
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
    # Obtener cuotas (sincronizado con la lógica del modelo Credito)
    from software.models.CuotasVentaModel import CuotasVenta
    if credito.idventa:
        cuotas = CuotasVenta.objects.filter(idventa=credito.idventa, estado=1).order_by('numero_cuota')
    else:
        cuotas = CuotasVenta.objects.filter(idcredito=credito, estado=1).order_by('numero_cuota')

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
    
    frec_nom, frec_adj = detectar_frecuencia(credito)
    
    # Estado dinámico
    v_estado_txt = "semi-nueva"
    if vehiculo and vehiculo.idestadoproducto:
        estado_db = vehiculo.idestadoproducto.nombreestadoproducto.lower()
        if estado_db == 'segunda':
            v_estado_txt = 'semi-nueva'
        elif estado_db == 'primera':
            v_estado_txt = 'nueva'
        else:
            v_estado_txt = estado_db

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
    # PARTE 1: CONTRATO PRINCIPAL
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
        if not ubicacion_garante: ubicacion_garante = "Distrito de Soritor, Provincia de Moyobamba, Departamento de San Martín"
        texto_intro += f"interviniendo además el(la) Sr(a). <b>{garante.nombre}</b> con {label_garante} N° <b>{garante.numdoc}</b>, con domicilio en {garante.direccion}, {ubicacion_garante} a quien se le llamara LA GARANTE, "
    
    texto_intro += "en los siguientes términos y condiciones:"
    
    story.append(Paragraph(texto_intro, texto_style))

    # PRIMERO
    texto_primero = f"""
    <b>PRIMERO:</b> La Empresa {empresa.razonsocial}, entrega a EL ARRENDATARIO en calidad de alquiler-venta a <b>PAGO {frec_nom}</b>, 
    conforme a lo acordado ambas partes in el siguiente bien:
    <br/>
    Un {producto.idcategoria.nomcategoria if producto and producto.idcategoria else 'Motocicleta'} {v_estado_txt} marca <b>{producto.idmarca.nombremarca if producto and producto.idmarca else 'Honda'}</b>, donde los recibe a su entera satisfacción y en perfecto estado de funcionamiento previa comprobación por EL ARRENDATARIO; el mismo que cuenta con las siguientes características:
    """
    story.append(Paragraph(texto_primero, texto_style))
    
    v_serie = vehiculo.serie_chasis if vehiculo else "________"
    v_motor = vehiculo.serie_motor if vehiculo else "________"
    v_color = producto.idcolor.nombrecolor if producto and producto.idcolor else "________"
    v_modelo = producto.idmodelo.nombremodelo if producto and producto.idmodelo else "________"
    v_anio = str(vehiculo.anio) if vehiculo and vehiculo.anio else "________"

    # Detectar si la empresa asume trámites
    if asume_gastos is not None:
        asume_empresa = asume_gastos
    else:
        # Basado en si hay costos registrados para el cliente
        from software.models.ImposicionPlacaModel import ImposicionPlaca
        tramite_reg = ImposicionPlaca.objects.filter(idventa=credito.idventa, estado=1).first()
        asume_empresa = True
        if tramite_reg and tramite_reg.total_costo > 0:
            asume_empresa = False
        
    txt_asume_tramite = "ASUME LA EMPRESA" if asume_empresa else "ASUME EL ARRENDATARIO"
    txt_asume_transf = "ASUME LA EMPRESA DEPENDIENDO DE SU PUNTUALIDAD." if asume_empresa else "ASUME EL ARRENDATARIO."

    # Determinar placa
    placa_asignada = "PENDIENTE"
    if credito.idventa:
        imposicion = ImposicionPlaca.objects.filter(idventa=credito.idventa, estado=1).order_by('-id_imposicion').first()
        if imposicion:
            if imposicion.numero_placa:
                placa_asignada = imposicion.numero_placa
            else:
                placa_asignada = "EN TRÁMITE"
        else:
            if vehiculo and vehiculo.placas and vehiculo.placas.strip():
                placa_asignada = vehiculo.placas.strip()
            else:
                placa_asignada = "EN TRÁMITE"

    caract_data = [
        ["MARCA", ":", producto.idmarca.nombremarca if producto and producto.idmarca else ""],
        ["MODELO", ":", v_modelo],
        ["AÑO DE MODELO", ":", v_anio],
        ["TIPO DE CARROCERIA", ":", producto.idcategoria.nomcategoria if producto and producto.idcategoria else ""],
        ["SERIE N°", ":", v_serie],
        ["MOTOR N°", ":", v_motor],
        ["COLOR", ":", v_color],
        ["N° DE PLACA", ":", placa_asignada.upper()],
        ["TARJETA, PLACA", ":", txt_asume_tramite],
        ["TRANSFERENCIA", ":", txt_asume_transf]
    ]
    t_caract = Table(caract_data, colWidths=[4*cm, 0.5*cm, 10.5*cm])
    t_caract.setStyle(TableStyle([('FONT', (0,0), (-1,-1), 'Helvetica', 9), ('BOTTOMPADDING', (0,0), (-1,-1), 1)]))
    story.append(t_caract)
    
    story.append(Paragraph(f"EL ARRENDATARIO acepta el presente contrato y reconoce que el vehículo en adquisición será materia de GARANTIA VEHICULAR para la empresa hasta completar el 100% de pago del alquiler a fin de garantizar la deuda detallada en mención.", texto_style))

    # Obtener monto de cuota para la cláusula SEGUNDO
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

    # Cláusulas
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
        
    provincia_jur = "San Martín"
    if garante:
        garante_clauses = [
            "<b>DECIMO PRIMERO:</b> EL GARANTE realiza su firma con el pleno conocimiento, de que si en los últimos casos, EL ARRENDATARIO no cumpla con su compromiso plasmada en el contrato; EL GARANTE acepta y asume la responsabilidad total de todos los pagos que quedaron pendientes, cabe indicar, infracciones ante la ley, accidentes, robos, etc.",
            "<b>DECIMO SEGUNDO:</b> LA EMPRESA tendrá la facultad de liberar de toda obligación a EL GARANTE, solamente cuando éste entregue a LA EMPRESA la mercadería indicada en el presente contrato.",
            "<b>DECIMO TERCERO:</b> Si en caso EL ARRENDATARIO por motivos personales no se siente en condiciones de seguir realizando los pagos, EL GARANTE está en todo el derecho de tomar disposición del vehículo y seguir con los pagos hasta el 100% de lo pactado.",
            f"<b>DECIMO CUARTO:</b> Las partes que suscriben el presente contrato, así como EL GARANTE renuncian al fuero de sus domicilios y se someten expresamente a la jurisdicción de los tribunales y jueces de la ciudad de {provincia_jur}, donde se encuentra el domicilio de LA EMPRESA."
        ]
        for gc in garante_clauses:
            story.append(Paragraph(gc, texto_style))
    else:
        story.append(Paragraph(f"<b>DECIMO PRIMERO:</b> Las partes que suscriben el presente contrato renuncian al fuero de sus domicilios y se someten expresamente a la jurisdicción de los tribunales y jueces de la ciudad de {provincia_jur}, donde se encuentra el domicilio de LA EMPRESA.", texto_style))

    # Firmas Parte 1
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

    # -------------------------------------------------------------
    # PARTE 2: DECLARACION JURADA
    # -------------------------------------------------------------
    story.append(PageBreak())
    story.append(Paragraph("<b>DECLARACIÓN JURADA DE COMPROMISO</b>", titulo_style))
    
    hora_actual = fecha_hoy.strftime("%I:%M %p")
    txt_dj = f"""
    Siendo las {hora_actual} del día {fecha_hoy.day:02d} de {meses_es[fecha_hoy.month - 1]} del {fecha_hoy.year}, YO <b>{cliente.razonsocial.upper()}</b> con DNI N.º <b>{cliente.numdoc}</b> 
    {f'mi esposa(o) la Sra/Sr. <b>{conyuge_nombre.upper()}</b> con DNI: <b>{conyuge_dni}</b>' if conyuge_nombre else ''}, dejamos constancia con cada una de nuestras firmas y huellas, 
    que la empresa {empresa.razonsocial}, nos explicaron claramente los términos y condiciones antes de la entrega del vehículo.
    """
    story.append(Paragraph(txt_dj, texto_style))
    
    bullets = [
        "LA EMPRESA ES DUEÑO DE EL VEHICULO HASTA EL TERMINO DE MI CANCELACION.",
        "PASADO 5 DIAS DE RETRASO LA EMPRESA ME RETENDRA EL VEHICULO.",
        f"LA: {producto.idcategoria.nomcategoria.upper() if producto and producto.idcategoria else 'MOTOCICLETA'} {producto.idmarca.nombremarca.upper() if producto and producto.idmarca else ''} {v_modelo.upper()} COLOR: {v_color.upper()} SERIE: {v_serie} MOTOR: {v_motor} AÑO: {v_anio}, FUE ENTREGADO EN PRESENCIA DE CADA UNO DE LOS INTEGRANTES MENCIONADOS LINEAS ARRIBA. EN PERFECTAS CONDICIONES TODO {v_estado_txt.upper()} DE FABRICA."
    ]
    for b in bullets:
        story.append(Paragraph(f"• {b}", texto_style))
    
    story.append(Spacer(1, 40))
    story.append(Paragraph("FIRMA: -----------------------------------------------------------", texto_style))
    story.append(Paragraph(f"NOMBRE: {cliente.razonsocial.upper()}", texto_style))
    story.append(Paragraph(f"DNI: {cliente.numdoc}", texto_style))

    # -------------------------------------------------------------
    # PARTE 3: INFORMACION DE TRANSFERENCIA
    # -------------------------------------------------------------
    story.append(PageBreak())
    story.append(Paragraph("<b>INFORMACION DE LA TRANSFERENCIA</b>", titulo_style))
    
    txt_inf_trans = f"""
    YO: <b>{cliente.razonsocial.upper()}</b> con DNI N.º <b>{cliente.numdoc}</b> {f'mi esposa(o) la Sra/Sr. <b>{conyuge_nombre.upper()}</b> con DNI: <b>{conyuge_dni}</b>' if conyuge_nombre else ''} 
    CON ESTA FIRMA DEJAMOS CONSTANCIA, DE QUE LA EMPRESA {empresa.nombrecomercial.upper()}, SI ME INFORMO RESPECTO AL TEMA DE LOS PAPELES DE EL VEHICULO
    <br/><br/>
    *LA TARJETA Y LA PLACA DE LA MOTO SALEN A NOMBRE DE LA EMPRESA {empresa.razonsocial.upper()}, QUEDANDO CLARAMENTE INFORMADO QUE EL TEMA DE LA TRANSFERENCIA DE EL VEHICULO, 
    ASUMIRA LA EMPRESA. SIEMPRE Y CUANDO MI PAGO SEA PUNTUAL SIN NINGUN RETRASO, AHORA SI ES QUE HE TENIDO RETRASOS EN EL PAGO DE MIS CUOTAS. LA TRANSFERENCIA ASUMIRE YO COMO CLIENTE EN SU TOTALIDAD.
    """
    story.append(Paragraph(txt_inf_trans, texto_style))
    
    story.append(Spacer(1, 40))
    story.append(Paragraph("FIRMA: -----------------------------------------------------------", texto_style))
    story.append(Paragraph(f"NOMBRE: {cliente.razonsocial.upper()}", texto_style))
    story.append(Paragraph(f"DNI: {cliente.numdoc}", texto_style))

    # -------------------------------------------------------------
    # PARTE 4: ACTA DE CONSTATACION
    # -------------------------------------------------------------
    story.append(PageBreak())
    story.append(Paragraph("<b>ACTA DE CONSTATACIÓN DE UN VEHÍCULO MOTORIZADO</b>", titulo_style))
    
    # Obtener nombre de configuración dinámica
    config_nombre = "LINEAL"
    if producto and producto.id_configuracion:
        config_nombre = producto.id_configuracion.nombre.upper()

    txt_acta_intro = f"""
    LA EMPRESA {empresa.razonsocial.upper()} con RUC N° {ruc_empresa}; en nuestra Tienda Principal "{empresa.nombrecomercial.upper()}" LOCAL COMERCIAL quien es único propietario del vehículo automotor menor, 
    hace entrega el vehículo al ARRENDATARIO <b>{cliente.razonsocial.upper()}</b> con DNI N.º <b>{cliente.numdoc}</b>, 
    {f'también interviene su esposa(o) la Sra/Sr. <b>{conyuge_nombre.upper()}</b> con DNI: <b>{conyuge_dni}</b>' if conyuge_nombre else ''} 
    ambos con domicilio en {cliente.direccion} - {ciudad_final} con la finalidad de suscribir el presente ACTA y RECEPCION del VEHICULO {config_nombre} para ALQUILER según lo acordado 
    que se encuentra en condición de {v_estado_txt.upper()} destinado único y exclusivamente para su uso PERSONAL.
    """
    story.append(Paragraph(txt_acta_intro, texto_style))
    
    # Obtener el monto de la cuota real desde el cronograma
    monto_cuota_val = 0
    if cuotas:
        cuota_ej = cuotas.filter(numero_cuota__gt=0).first()
        if not cuota_ej: cuota_ej = cuotas.first()
        if cuota_ej: monto_cuota_val = cuota_ej.total
    
    if monto_cuota_val == 0:
        monto_cuota_val = (credito.monto_total - credito.monto_adelanto) / (credito.cantidad_cuotas if credito.cantidad_cuotas else 1)

    # Fecha de inicio: Fecha de creación del crédito
    fecha_inicio_val = credito.fecha_credito.strftime('%Y-%m-%d')

    # Fecha de fin: Fecha de vencimiento de la última cuota
    fecha_fin_val = (fecha_hoy + timedelta(days=30*credito.cantidad_cuotas)).strftime('%Y-%m-%d')
    if cuotas:
        fecha_fin_val = cuotas.last().fecha_vencimiento.strftime('%Y-%m-%d')

    txt_acta_det = f"""
    El vehículo que se otorgara en modalidad de ALQUILER VENTA inicia a partir del {fecha_inicio_val} al {fecha_fin_val} 
    con pago de S/. {monto_cuota_val:,.2f} {frec_nom.lower()} con las siguientes características:
    """
    story.append(Paragraph(txt_acta_det, texto_style))
    
    # Determinar placa
    placa_asignada = "PENDIENTE"
    from software.models.ImposicionPlacaModel import ImposicionPlaca
    if credito.idventa:
        imposicion = ImposicionPlaca.objects.filter(idventa=credito.idventa, estado=1).order_by('-id_imposicion').first()
        if imposicion and imposicion.numero_placa:
            placa_asignada = imposicion.numero_placa
        elif vehiculo and vehiculo.placas and vehiculo.placas.strip():
            placa_asignada = vehiculo.placas.strip()
    acta_caract_data = [
        ["TIPO DE CARROCERIA", ":", producto.idcategoria.nomcategoria.upper() if producto and producto.idcategoria else "", "AÑO DE FABRICACION", ":", v_anio],
        ["MARCA", ":", producto.idmarca.nombremarca.upper() if producto and producto.idmarca else "", "N° DE SERIE", ":", v_serie],
        ["MODELO", ":", v_modelo.upper(), "N° DE MOTOR", ":", v_motor],
        ["COLOR", ":", v_color.upper(), "N° DE PLACA", ":", placa_asignada.upper()]
    ]
    t_acta = Table(acta_caract_data, colWidths=[3.5*cm, 0.5*cm, 4.5*cm, 3.5*cm, 0.5*cm, 4.5*cm])
    t_acta.setStyle(TableStyle([('FONT', (0,0), (-1,-1), 'Helvetica', 8)]))
    story.append(t_acta)
    story.append(Spacer(1, 10))
    
    txt_acta_legal_1 = f"""
    LA EMPRESA, otorga la posición de la {producto.idcategoria.nomcategoria.upper() if producto and producto.idcategoria else 'MOTOCICLETA'} al ARRENDATARIO quien declara recibir el vehículo en óptimas condiciones y a su entera satisfacción, el mismo que se hará responsable de su mantenimiento y funcionamiento en talleres autorizados, asimismo se obliga a conservar y tener limpio el vehículo como fue entregado por el PROPIETARIO; EL ARRENDATARIO queda tajantemente prohibido de realizar cambios o modificaciones internas o externas, prestar o alquilar a terceros y asimismo no salir fuera de zona autorizada sino de lo contrario se anulara inmediatamente dicho contrato viéndose el personal autorizado a retener y recuperar el vehículo donde EL ARRENDATARIO perderá todo lo pactado con la EMPRESA; EL ARRENDATARIO está en la responsabilidad de realizar los pagos directamente en la oficina respetando los horarios de la misma y como tal el vehículo tendrá que hacer presencia cada vez que se apersone a realizar su pago.
    <br/><br/>
    LA EMPRESA se compromete hacer los trámites necesarios al termino del pago total del vehículo a favor del ARRENDATARIO, cabe decir únicamente el documento de TRANSFERENCIA NOTARIAL, siendo LA EMPRESA o EL ARRENDATARIO quien asuma los gastos según lo acordado en el contrato de alquiler venta.
    <br/>
    Al generar días de atraso, el sistema automáticamente le generara MORA por pagar por nivelación de deuda. Teniendo en cuenta que el vehículo se encuentra en garantía mobiliaria.
    <br/>
    LA EMPRESA informa a EL ARRENDATARIO que sus vehículos en modalidad de alquiler venta son PROPIEDAD única de la empresa, por la cual también deben salir pintado y de carácter obligatorio el logo de la empresa antes de su entrega.
    <br/><br/>
    EL ARRENDATARIO: YO <b>{cliente.razonsocial.upper()}</b> con DNI N.º <b>{cliente.numdoc}</b> {f'mi esposa(o) la Sra/Sr. <b>{conyuge_nombre.upper()}</b> con DNI: <b>{conyuge_dni}</b>' if conyuge_nombre else ''}, declaramos comprometernos que, en caso de pérdida o robo de los documentos, asumiré la responsabilidad de todo el proceso y costo para la recuperación y/u obtención; Si el vehículo automotor menor que recibí me es robado, asumo la responsabilidad de devolver el vehículo o cancelar la totalidad del bien pactado entre las partes, en un lapso de 30 días calendarios.
    <br/><br/>
    En caso de incumplimiento de la presente acta, estoy obligado a entregar el vehículo {producto.idcategoria.nomcategoria.upper() if producto and producto.idcategoria else 'MOTOCICLETA'} personalmente en las oficinas de la empresa {empresa.razonsocial.upper()}; en las mismas condiciones que se me fue entregado y todos los documentos dados a mi persona, con el simple requerimiento verbal o mediante carta notarial, asimismo, pagar en calidad de penalidad compensatorio un importe ascendente a S/. 25.00 (veinte cinco y 00/100 soles), por cada día de demora en la entrega del vehículo. De igual forma, faculto a la empresa {empresa.razonsocial.upper()}; en caso de incumplimiento retener el vehículo donde se encuentre ubicado o en su defecto tomar acciones legales frente a las instalaciones pertinentes, denunciándome por los delitos contra el patrimonio en cualquiera de sus modalidades en que hubiera incurrido.
    """
    story.append(Paragraph(txt_acta_legal_1, texto_style))
    
    txt_acta_legal_2 = f"""
    Observaciones: .....................................................................................................................................................................................
    <br/><br/>
    No habiendo nada más que hacer constar, se da por concluida el acta y recepción del vehículo a las {hora_actual} del {fecha_hoy.day:02d} de {meses_es[fecha_hoy.month - 1]} del {fecha_hoy.year} firmando la presente acta en señal de conformidad, y para veracidad se certifica notarialmente mi firma.
    """
    
    bloque_acta_firmas = []
    bloque_acta_firmas.append(Spacer(1, 15))
    bloque_acta_firmas.append(Paragraph(txt_acta_legal_2, texto_style))
    bloque_acta_firmas.append(Spacer(1, 30))
    
    tercero_titulo = None
    tercero_nombre = None
    if garante:
        tercero_titulo = "GARANTE"
        tercero_nombre = garante.nombre.upper()
    elif conyuge_nombre:
        tercero_titulo = "CONYUGUE"
        tercero_nombre = conyuge_nombre.upper()

    if tercero_titulo:
        firma_acta_data = [
            [Paragraph("_______________________", firma_style), Paragraph("_______________________", firma_style), Paragraph("_______________________", firma_style)],
            [Paragraph(f"{empresa.razonsocial.upper()}<br/>LA EMPRESA", firma_style), 
             Paragraph(f"{cliente.razonsocial.upper()}<br/>EL ARRENDATARIO", firma_style), 
             Paragraph(f"{tercero_nombre}<br/>{tercero_titulo}", firma_style)]
        ]
        t_firmas_acta = Table(firma_acta_data, colWidths=[6*cm, 6*cm, 6*cm])
    else:
        firma_acta_data = [
            [Paragraph("_______________________", firma_style), Paragraph("_______________________", firma_style)],
            [Paragraph(f"{empresa.razonsocial.upper()}<br/>LA EMPRESA", firma_style), 
             Paragraph(f"{cliente.razonsocial.upper()}<br/>EL ARRENDATARIO", firma_style)]
        ]
        t_firmas_acta = Table(firma_acta_data, colWidths=[9*cm, 9*cm])
        
    bloque_acta_firmas.append(t_firmas_acta)
    
    bloque_acta_firmas.append(Spacer(1, 20))
    clausula_extra = "<b>Cláusula Adicional:</b> En caso se diera un estado de emergencia dictaminada por el estado, LA EMPRESA realizara el recojo del vehículo del ARRENDATARIO para que así no esté en circulación tanto en manejo como en pago, con la intención que al término del estado de emergencia se continúe con la secuencia del contrato de ALQUILER VENTA, dándose así la actualización de fecha sin ningún pago de más."
    bloque_acta_firmas.append(Paragraph(clausula_extra, texto_style))
    
    story.append(KeepTogether(bloque_acta_firmas))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
