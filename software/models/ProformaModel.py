from django.db import models
from django.core.validators import MinValueValidator
from software.models.ClienteModel import Cliente
from software.models.UsuarioModel import Usuario


class Proforma(models.Model):
    """
    Cabecera de una Proforma (cotización comercial).
    No es un comprobante de pago.
    """

    ESTADO_CHOICES = [
        (1, 'Activa'),
        (2, 'Convertida en Venta'),
        (3, 'Anulada'),
    ]

    idproforma = models.AutoField(primary_key=True, db_column='idproforma')
    numero_proforma = models.CharField(
        max_length=20,
        unique=True,
        default='',
        verbose_name='Número de Proforma',
        help_text='Número correlativo (ej: PRO-000001)'
    )
    idcliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        db_column='idcliente',
        related_name='proformas',
        verbose_name='Cliente'
    )
    idusuario = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        db_column='idusuario',
        related_name='proformas',
        verbose_name='Asesor Comercial'
    )
    fecha_emision = models.DateField(
        auto_now_add=True,
        verbose_name='Fecha de Emisión'
    )
    fecha_vencimiento = models.DateField(
        null=True, blank=True,
        verbose_name='Fecha de Vencimiento'
    )
    idempresa = models.IntegerField(
        null=True, blank=True,
        verbose_name='ID Empresa'
    )

    # Condiciones comerciales
    forma_pago = models.CharField(
        max_length=255, default='Contado',
        verbose_name='Forma de Pago'
    )
    tiempo_entrega = models.CharField(
        max_length=255, default='Inmediata',
        verbose_name='Tiempo de Entrega'
    )
    garantia = models.CharField(
        max_length=255, default='Según fabricante',
        verbose_name='Garantía'
    )
    observaciones = models.TextField(
        null=True, blank=True,
        verbose_name='Observaciones'
    )

    # Totales económicos
    subtotal = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Subtotal'
    )
    igv = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        validators=[MinValueValidator(0)],
        verbose_name='IGV (18%)'
    )
    descuento = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Descuento Total'
    )
    total = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Total'
    )

    estado = models.IntegerField(
        default=1, choices=ESTADO_CHOICES,
        verbose_name='Estado'
    )

    class Meta:
        managed = True
        db_table = 'proformas'
        verbose_name = 'Proforma'
        verbose_name_plural = 'Proformas'
        ordering = ['-idproforma']

    def __str__(self):
        return f"{self.numero_proforma} - {self.idcliente.razonsocial}"
