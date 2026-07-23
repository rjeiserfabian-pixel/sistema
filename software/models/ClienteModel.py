
from django.db import models
from software.models.Tipo_entidadModel import TipoEntidad

class Cliente(models.Model):
    idcliente = models.AutoField(primary_key=True)
    numdoc = models.CharField(max_length=25, unique=True, verbose_name="Número de Documento")
    razonsocial = models.CharField(max_length=255, verbose_name="Razón Social/Nombre Completo")
    direccion = models.CharField(max_length=255, blank=True, null=True, verbose_name="Dirección")
    estado = models.IntegerField(default=1, verbose_name="Estado")
    id_tipo_entidad = models.ForeignKey(
        TipoEntidad, 
        on_delete=models.DO_NOTHING, 
        db_column='id_tipo_entidad', 
        related_name='clientes',
        verbose_name="Tipo de Entidad"
    )
    telefono = models.CharField(max_length=150, blank=True, null=True, verbose_name="Teléfono")
    email = models.CharField(max_length=255, blank=True, null=True, verbose_name="Email")
    
    # Ubicación
    id_region = models.ForeignKey('Region', on_delete=models.DO_NOTHING, db_column='id_region', blank=True, null=True, verbose_name="Departamento")
    id_provincia = models.ForeignKey('Provincia', on_delete=models.DO_NOTHING, db_column='id_provincia', blank=True, null=True, verbose_name="Provincia")
    id_distrito = models.ForeignKey('Distrito', on_delete=models.DO_NOTHING, db_column='iddistrito', blank=True, null=True, verbose_name="Distrito")
    nombre_comercial_cliente = models.CharField(max_length=255, blank=True, null=True, verbose_name="Nombre Comercial")
    
    # Información del Cónyuge
    conyuge_nombre = models.CharField(max_length=255, blank=True, null=True, verbose_name="Nombre del Cónyuge")
    conyuge_dni = models.CharField(max_length=20, blank=True, null=True, verbose_name="DNI del Cónyuge")
    
    class Meta:
        managed = True  
        db_table = 'clientes'
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
    
    def __str__(self):
        return self.razonsocial
    
    @property
    def tipo_documento(self):
        """Determina el tipo de documento basado en la longitud"""
        if len(self.numdoc) == 8:
            return 'DNI'
        elif len(self.numdoc) == 11:
            return 'RUC'
        else:
            return 'OTRO'
        


