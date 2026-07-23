from django.db import models

class Garante(models.Model):
    id_garante = models.AutoField(primary_key=True)
    idcliente = models.ForeignKey('Cliente', on_delete=models.CASCADE, db_column='idcliente', related_name='garantes', null=True, blank=True, verbose_name="Cliente")
    nombre = models.CharField(max_length=255, verbose_name="Nombre Completo")
    numdoc = models.CharField(max_length=20, verbose_name="Número de Documento (DNI)")
    direccion = models.CharField(max_length=255, blank=True, null=True, verbose_name="Dirección")
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
    
    # Ubicación
    id_region = models.ForeignKey('Region', on_delete=models.DO_NOTHING, db_column='id_region', blank=True, null=True, verbose_name="Departamento")
    id_provincia = models.ForeignKey('Provincia', on_delete=models.DO_NOTHING, db_column='id_provincia', blank=True, null=True, verbose_name="Provincia")
    id_distrito = models.ForeignKey('Distrito', on_delete=models.DO_NOTHING, db_column='iddistrito', blank=True, null=True, verbose_name="Distrito")
    
    estado = models.IntegerField(default=1, verbose_name="Estado")
    
    # Información del Cónyuge
    conyuge_nombre = models.CharField(max_length=255, blank=True, null=True, verbose_name="Nombre del Cónyuge")
    conyuge_dni = models.CharField(max_length=20, blank=True, null=True, verbose_name="DNI del Cónyuge")

    class Meta:
        managed = True
        db_table = 'garantes'
        verbose_name = 'Garante'
        verbose_name_plural = 'Garantes'

    def __str__(self):
        return f"{self.nombre} - {self.numdoc}"
