from django.db import models
from django.core.validators import MinLengthValidator, MaxLengthValidator, RegexValidator
from django.utils import timezone


class Empresa(models.Model):
    """
    Modelo para almacenar información de las empresas.
    Incluye datos tributarios, ubicación, credenciales SUNAT y campos adicionales.
    """
    
    idempresa = models.AutoField(primary_key=True, db_column='idempresa')
    
    # Información Tributaria
    ruc = models.CharField(
        max_length=11,
        unique=True,
        validators=[
            MinLengthValidator(11, message="El RUC debe tener 11 dígitos"),
            MaxLengthValidator(11, message="El RUC debe tener 11 dígitos"),
            RegexValidator(
                regex=r'^\d{11}$',
                message='El RUC debe contener solo números'
            )
        ],
        verbose_name='RUC',
        help_text='Registro Único de Contribuyentes (11 dígitos)'
    )
    
    razonsocial = models.CharField(
        max_length=255,
        verbose_name='Razón Social',
        help_text='Razón social de la empresa'
    )
    
    nombrecomercial = models.CharField(
        max_length=255,
        verbose_name='Nombre Comercial',
        help_text='Nombre comercial de la empresa'
    )
    
    # Datos del Representante Legal
    gerente_general = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='Gerente General',
        help_text='Nombre completo del representante legal'
    )
    
    dni_gerente = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='DNI Gerente',
        help_text='DNI del representante legal'
    )

    celular_gerente = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='Celular Gerente',
        help_text='Número de celular del representante legal'
    )

    direccion_gerente = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name="Dirección Gerente"
    )
    id_region_gerente = models.ForeignKey(
        'Region', 
        on_delete=models.SET_NULL, 
        db_column='id_region_gerente', 
        blank=True, 
        null=True, 
        verbose_name="Departamento Gerente"
    )
    id_provincia_gerente = models.ForeignKey(
        'Provincia', 
        on_delete=models.SET_NULL, 
        db_column='id_provincia_gerente', 
        blank=True, 
        null=True, 
        verbose_name="Provincia Gerente"
    )
    id_distrito_gerente = models.ForeignKey(
        'Distrito', 
        on_delete=models.SET_NULL, 
        db_column='id_distrito_gerente', 
        blank=True, 
        null=True, 
        verbose_name="Distrito Gerente"
    )
    
    # Ubicación
    direccion = models.CharField(
        max_length=255,
        verbose_name='Dirección',
        help_text='Dirección fiscal de la empresa'
    )
    
    ubigueo = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        verbose_name='Ubigeo',
        help_text='Código de ubicación geográfica (ubigeo)'
    )
    
    # Información de Contacto
    telefono = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        verbose_name='Teléfono',
        help_text='Teléfono de contacto'
    )
    
    gmail_1 = models.EmailField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='Gmail 1',
        help_text='Primer correo electrónico de la empresa'
    )
    
    gmail_2 = models.EmailField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='Gmail 2',
        help_text='Segundo correo electrónico de la empresa'
    )
    
    # Logo
    logo = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name='Logo',
        help_text='URL del logo en Cloudinary'
    )
    
    # Logo Ticket
    logo_ticket = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name='Logo Ticket',
        help_text='URL del logo para tickets en Cloudinary'
    )
    
    # Credenciales SUNAT
    usersec = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='Usuario SUNAT',
        help_text='Usuario para acceso a servicios SUNAT'
    )
    
    passwordsec = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='Clave SUNAT',
        help_text='Clave de seguridad para servicios SUNAT'
    )

    # Configuración UltraMsg (WhatsApp)
    ultramsg_instance = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='UltraMsg Instance ID',
        help_text='ID de instancia de UltraMsg (ej: instance175698)'
    )
    
    ultramsg_token = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='UltraMsg Token',
        help_text='Token de autenticación de UltraMsg'
    )
    
    # Configuración del Sistema
    mododev = models.IntegerField(
        default=0,
        choices=[
            (0, 'Desarrollo'),
            (1, 'Producción')
        ],
        verbose_name='Modo de Operación',
        help_text='0: Desarrollo, 1: Producción'
    )
    
    # Información Adicional de Marketing
    slogan = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='Slogan',
        help_text='Slogan o frase promocional de la empresa'
    )

    pagina = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='Pagina',
        help_text='Pagina web de la empresa'
    )
    
    
    publicidad = models.TextField(
        null=True,
        blank=True,
        verbose_name='Publicidad',
        help_text='Descripción de actividades o mensaje publicitario'
    )

    agradecimiento = models.TextField(
        null=True,
        blank=True,
        verbose_name='Agradecimiento',
        help_text='Mensaje de agradecimiento para los clientes'
    )
    
    condiciones_comerciales = models.TextField(
        null=True,
        blank=True,
        default='Precios sujetos a cambios sin previo aviso según fluctuación del dólar.',
        verbose_name='Condiciones Comerciales',
        help_text='Condiciones comerciales por defecto para las proformas'
    )
    
    # Parámetros Tributarios
    igv = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=18.00,
        verbose_name='IGV (%)',
        help_text='Porcentaje de IGV aplicable'
    )
    
    icbper = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        verbose_name='ICBPER',
        help_text='Impuesto al Consumo de Bolsas Plásticas'
    )
    
    isc = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        verbose_name='ISC (%)',
        help_text='Impuesto Selectivo al Consumo'
    )
    
    afectacion_sunat = models.IntegerField(
        default=20,
        verbose_name='Afectación General SUNAT',
        help_text='Código de afectación tributaria general'
    )
    
    # Parámetros de Créditos
    cobrar_mora = models.BooleanField(
        default=True,
        verbose_name="Cobrar Mora",
        help_text="Activa o desactiva el cobro de mora en todos los créditos"
    )
    
    interes_mora_base = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=5.00,
        verbose_name='Interés Mora Base (%)',
        help_text='Tasa de interés que se aplica a partir del día configurado'
    )

    dias_mora_inicio = models.IntegerField(
        default=4,
        verbose_name='Día Inicio Mora',
        help_text='Día en el que empieza a cobrarse el interés (ej: 4)'
    )
    
    limite_dias_verde = models.IntegerField(
        default=10,
        verbose_name='Límite Días Verde',
        help_text='Hasta cuántos días de mora se muestra el color verde'
    )
    
    limite_dias_amarillo = models.IntegerField(
        default=20,
        verbose_name='Límite Días Amarillo',
        help_text='Hasta cuántos días de mora se muestra el color amarillo (mayor a esto será rojo)'
    )

    # ── Límites de mora por frecuencia de pago ────────────────────────────────
    # Diario
    limite_dias_verde_diario = models.IntegerField(
        default=5,
        verbose_name='Límite Verde (Diario)',
        help_text='Días de mora para color verde en créditos diarios'
    )
    limite_dias_amarillo_diario = models.IntegerField(
        default=10,
        verbose_name='Límite Amarillo (Diario)',
        help_text='Días de mora para color amarillo en créditos diarios (más es rojo)'
    )
    # Semanal
    limite_dias_verde_semanal = models.IntegerField(
        default=20,
        verbose_name='Límite Verde (Semanal)',
        help_text='Días de mora para color verde en créditos semanales'
    )
    limite_dias_amarillo_semanal = models.IntegerField(
        default=30,
        verbose_name='Límite Amarillo (Semanal)',
        help_text='Días de mora para color amarillo en créditos semanales (más es rojo)'
    )
    # Quincenal
    limite_dias_verde_quincenal = models.IntegerField(
        default=30,
        verbose_name='Límite Verde (Quincenal)',
        help_text='Días de mora para color verde en créditos quincenales'
    )
    limite_dias_amarillo_quincenal = models.IntegerField(
        default=45,
        verbose_name='Límite Amarillo (Quincenal)',
        help_text='Días de mora para color amarillo en créditos quincenales (más es rojo)'
    )
    # Mensual (se usan cuotas vencidas, no días)
    limite_cuotas_verde_mensual = models.IntegerField(
        default=1,
        verbose_name='Límite Verde (Mensual - Cuotas)',
        help_text='Número de cuotas vencidas para color verde en créditos mensuales'
    )
    limite_cuotas_amarillo_mensual = models.IntegerField(
        default=2,
        verbose_name='Límite Amarillo (Mensual - Cuotas)',
        help_text='Número de cuotas vencidas para color amarillo en créditos mensuales (más es rojo)'
    )
    
    # Campos de auditoría
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Creación',
        null=True,
        blank=True
    )
    
    fecha_actualizacion = models.DateTimeField(
        auto_now=True,
        verbose_name='Última Actualización',
        null=True,
        blank=True
    )
    
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo',
        help_text='Indica si la empresa está activa en el sistema'
    )
    
    
    class Meta:
        managed = True
        db_table = 'empresa'
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'
        ordering = ['nombrecomercial']
    
    def __str__(self):
        return f"{self.nombrecomercial} - RUC: {self.ruc}"
    
    def save(self, *args, **kwargs):
        """
        Sobrescribe el método save para realizar validaciones adicionales.
        """
        # Convertir RUC a mayúsculas y eliminar espacios
        if self.ruc:
            self.ruc = self.ruc.strip()
        
        # Normalizar textos
        if self.razonsocial:
            self.razonsocial = self.razonsocial.strip().upper()
        
        if self.nombrecomercial:
            self.nombrecomercial = self.nombrecomercial.strip()
        
        super().save(*args, **kwargs)
    
    def es_produccion(self):
        """Verifica si la empresa está en modo producción."""
        return self.mododev == 1
    
    def es_desarrollo(self):
        """Verifica si la empresa está en modo desarrollo."""
        return self.mododev == 0
    
    def get_modo_display_custom(self):
        """Retorna el modo de operación en formato legible."""
        return "PRODUCCIÓN" if self.es_produccion() else "DESARROLLO"
    
    def get_igv_decimal(self):
        """Retorna el IGV en formato decimal (ej: 0.18 para 18%)."""
        return self.igv / 100
    
    def calcular_igv(self, monto):
        """Calcula el IGV sobre un monto dado."""
        return monto * self.get_igv_decimal()
    
    def tiene_credenciales_sunat(self):
        """Verifica si tiene configuradas las credenciales SUNAT."""
        return bool(self.usersec and self.passwordsec)
    
    def tiene_logo(self):
        """Verifica si la empresa tiene logo configurado."""
        return bool(self.logo)
    
    def tiene_slogan(self):
        """Verifica si la empresa tiene slogan configurado."""
        return bool(self.slogan)
    
    def tiene_publicidad(self):
        """Verifica si la empresa tiene publicidad configurada."""
        return bool(self.publicidad)