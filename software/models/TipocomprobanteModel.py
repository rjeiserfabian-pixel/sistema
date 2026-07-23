from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

class Tipocomprobante(models.Model):
    idtipocomprobante = models.AutoField(primary_key=True)
    
    codigo = models.CharField(
        max_length=10,
        verbose_name="Código",
        help_text="Código del tipo de comprobante (ej: 01, 03, 07). Único entre registros activos.",
        validators=[
            RegexValidator(
                regex=r'^[0-9A-Z\-]+$',
                message='El código solo puede contener números, letras mayúsculas y guiones'
            )
        ]
    )
    
    nombre = models.CharField(
        max_length=255,
        verbose_name="Nombre del Comprobante",
        help_text="Nombre completo del tipo de comprobante"
    )
    
    abreviatura = models.CharField(
        max_length=50,
        verbose_name="Abreviatura",
        help_text="Abreviatura del tipo de comprobante (ej: FACT, BOL)"
    )
    
    estado = models.IntegerField(
        default=1,
        verbose_name="Estado"
    )

    class Meta:
        managed = True
        db_table = 'tipocomprobante'
        verbose_name = 'Tipo de Comprobante'
        verbose_name_plural = 'Tipos de Comprobante'
        ordering = ['codigo']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
    
    def clean(self):
        """Validaciones personalizadas a nivel de modelo"""
        errors = {}
        
        # Validar código no vacío
        if not self.codigo or not self.codigo.strip():
            errors['codigo'] = 'El código es obligatorio'
        else:
            # Limpiar espacios
            self.codigo = self.codigo.strip().upper()
            
            # Validar longitud
            if len(self.codigo) < 2:
                errors['codigo'] = 'El código debe tener al menos 2 caracteres'
        
        # Validar nombre no vacío
        if not self.nombre or not self.nombre.strip():
            errors['nombre'] = 'El nombre es obligatorio'
        else:
            self.nombre = self.nombre.strip()
            
            if len(self.nombre) < 3:
                errors['nombre'] = 'El nombre debe tener al menos 3 caracteres'
        
        # Validar abreviatura no vacía
        if not self.abreviatura or not self.abreviatura.strip():
            errors['abreviatura'] = 'La abreviatura es obligatoria'
        else:
            self.abreviatura = self.abreviatura.strip().upper()
            
            if len(self.abreviatura) < 2:
                errors['abreviatura'] = 'La abreviatura debe tener al menos 2 caracteres'
        
        # Validar duplicados de código (excluyendo el actual en edición)
        if self.codigo:
            existe_codigo = Tipocomprobante.objects.filter(
                codigo=self.codigo,
                estado=1
            ).exclude(pk=self.pk).exists()
            
            if existe_codigo:
                errors['codigo'] = f'Ya existe un tipo de comprobante con el código {self.codigo}'
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Override save para ejecutar validaciones antes de guardar"""
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def nombre_completo(self):
        """Devuelve código + nombre"""
        return f"{self.codigo} - {self.nombre}"
    
    @classmethod
    def get_activos(cls):
        """Devuelve solo los tipos de comprobante activos"""
        return cls.objects.filter(estado=1).order_by('codigo')