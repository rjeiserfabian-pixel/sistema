
from django.db import models
from software.models.Tipo_entidadModel import TipoEntidad


class Proveedor(models.Model):
    idproveedor = models.AutoField(primary_key=True)
    # Único solo entre proveedores activos (estado=1). Se valida a nivel de vista.
    numdoc = models.CharField(max_length=255, verbose_name="Número de Documento")
    razonsocial = models.CharField(max_length=255, verbose_name="Razón Social/Nombre Completo")
    estado = models.IntegerField(default=1, verbose_name="Estado")
    nombre_comercial = models.CharField(max_length=255, blank=True, null=True, verbose_name="Nombre Comercial")
    direccion = models.CharField(max_length=255, blank=True, null=True, verbose_name="Dirección")
    telefono = models.CharField(max_length=150, blank=True, null=True, verbose_name="Teléfono")
    email = models.EmailField(max_length=255, blank=True, null=True, verbose_name="Correo Electrónico")
    
    # Nuevos campos para información SUNAT/RENIEC
    departamento = models.CharField(max_length=100, blank=True, null=True, verbose_name="Departamento")
    provincia = models.CharField(max_length=100, blank=True, null=True, verbose_name="Provincia")
    distrito = models.CharField(max_length=100, blank=True, null=True, verbose_name="Distrito")
    
    id_tipo_entidad = models.ForeignKey(
        TipoEntidad, 
        on_delete=models.DO_NOTHING, 
        db_column='id_tipo_entidad',
        related_name='proveedores',
        verbose_name="Tipo de Entidad"
    )
    
    class Meta:
        managed = True  
        db_table = 'proveedores'
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'
    
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
    
    @property
    def ubicacion_completa(self):
        """Retorna la ubicación completa concatenada"""
        partes = [self.distrito, self.provincia, self.departamento]
        return ', '.join([p for p in partes if p])