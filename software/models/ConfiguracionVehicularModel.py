from django.db import models

class ConfiguracionVehicular(models.Model):
    id_configuracion = models.AutoField(primary_key=True, db_column='id')
    nombre = models.CharField(max_length=50)
    estado = models.IntegerField(default=1) # 1: Activo, 0: Inactivo

    def __str__(self):
        return self.nombre

    class Meta:
        managed = True
        db_table = 'configuracion_vehicular'
        verbose_name = 'Configuración Vehicular'
        verbose_name_plural = 'Configuraciones Vehiculares'
