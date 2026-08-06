from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from software.models.TipocomprobanteModel import Tipocomprobante
from software.models.sucursalesModel import Sucursales


class Seriecomprobante(models.Model):
    idseriecomprobante = models.AutoField(primary_key=True)
    
    idtipocomprobante = models.ForeignKey(
        Tipocomprobante,
        on_delete=models.CASCADE,
        db_column='idtipocomprobante',
        related_name='seriecomprobante',
        verbose_name="Tipo de Comprobante"
    )
    
    id_sucursal = models.ForeignKey(
        Sucursales,
        on_delete=models.CASCADE,
        db_column='id_sucursal',
        related_name='series_comprobante',
        verbose_name="Sucursal",
        null=True, 
        blank=True
    )
    
    serie = models.CharField(
        max_length=4,
        verbose_name="Serie",
        help_text="Serie del comprobante (4 caracteres alfanuméricos)",
        validators=[
            RegexValidator(
                regex=r'^[A-Z0-9]{4}$',
                message='La serie debe tener exactamente 4 caracteres alfanuméricos en mayúsculas'
            )
        ]
    )
    
    numero_actual = models.IntegerField(
        default=0,  # ✅ INICIA EN 0 para que el primer comprobante sea 00000001
        verbose_name="Número Actual",
        help_text="Número correlativo actual del comprobante (inicia en 0)"
    )
    
    estado = models.IntegerField(
        default=1,
        verbose_name="Estado"
    )

    class Meta:
        managed = True
        db_table = 'seriecomprobante'
        verbose_name = 'Serie de Comprobante'
        verbose_name_plural = 'Series de Comprobante'
        ordering = ['idtipocomprobante__codigo', 'serie']
        # Constraint para evitar duplicados de serie por tipo de comprobante
        unique_together = [['idtipocomprobante', 'serie']]

    def __str__(self):
        return f"{self.idtipocomprobante.codigo} - {self.serie}"
    
    def clean(self):
        """Validaciones personalizadas a nivel de modelo"""
        errors = {}
        
        # Validar tipo de comprobante
        if not self.idtipocomprobante:
            errors['idtipocomprobante'] = 'Debe seleccionar un tipo de comprobante'
        
        # Validar serie no vacía
        if not self.serie or not self.serie.strip():
            errors['serie'] = 'La serie es obligatoria'
        else:
            # Limpiar y convertir a mayúsculas
            self.serie = self.serie.strip().upper()
            
            # Validar longitud exacta de 4 caracteres
            if len(self.serie) != 4:
                errors['serie'] = 'La serie debe tener exactamente 4 caracteres'
            
            # Validar formato alfanumérico
            if not self.serie.isalnum():
                errors['serie'] = 'La serie solo puede contener letras y números (sin espacios ni caracteres especiales)'
        
        # Validar número actual
        if self.numero_actual is not None:
            if self.numero_actual < 0:  # ✅ PERMITE 0
                errors['numero_actual'] = 'El número actual debe ser mayor o igual a 0'
            
            if self.numero_actual > 99999999:
                errors['numero_actual'] = 'El número actual no puede exceder 99999999 (8 dígitos)'
        else:
            errors['numero_actual'] = 'El número actual es obligatorio'
        
        # Validar duplicados de serie para el mismo tipo de comprobante (excluyendo el actual en edición)
        if self.serie and self.idtipocomprobante:
            existe_serie = Seriecomprobante.objects.filter(
                idtipocomprobante=self.idtipocomprobante,
                serie=self.serie,
                estado=1
            ).exclude(pk=self.pk).exists()
            
            if existe_serie:
                errors['serie'] = f'Ya existe una serie {self.serie} para el tipo de comprobante {self.idtipocomprobante.nombre}'
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Override save para ejecutar validaciones antes de guardar"""
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def serie_completa(self):
        """Devuelve la serie con formato completo (siguiente número a emitir)"""
        siguiente = self.numero_actual + 1
        return f"{self.serie}-{str(siguiente).zfill(8)}"
    
    @property
    def siguiente_numero(self):
        """Devuelve el siguiente número disponible"""
        return self.numero_actual + 1
    
    @property
    def ultimo_comprobante_emitido(self):
        """Devuelve el último comprobante emitido (si numero_actual > 0)"""
        if self.numero_actual > 0:
            return f"{self.serie}-{str(self.numero_actual).zfill(8)}"
        return "Sin comprobantes emitidos"
    
    def incrementar_numero(self):
        """Incrementa el número actual en 1"""
        self.numero_actual += 1
        self.save()
    
    @classmethod
    def get_activos(cls):
        """Devuelve solo las series activas"""
        return cls.objects.filter(estado=1).select_related('idtipocomprobante').order_by('idtipocomprobante__codigo', 'serie')
    
    @classmethod
    def get_por_tipo(cls, idtipocomprobante):
        """Devuelve series activas filtradas por tipo de comprobante"""
        return cls.objects.filter(
            idtipocomprobante=idtipocomprobante,
            estado=1
        ).order_by('serie')