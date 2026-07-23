from django.db import models


class Servicio(models.Model):
    id_servicio = models.AutoField(primary_key=True, db_column='id_servicio')
    nombre = models.CharField(max_length=255, db_column='nombre', verbose_name='Nombre del Servicio')
    precio_defecto = models.DecimalField(max_digits=10, decimal_places=2, db_column='precio_defecto', verbose_name='Precio Base')
    descripcion = models.TextField(blank=True, null=True, db_column='descripcion', verbose_name='Descripción')
    estado = models.IntegerField(default=1, db_column='estado')

    class Meta:
        managed = True
        db_table = 'servicios_tramites'
        ordering = ['nombre']
        verbose_name = 'Servicio / Trámite'
        verbose_name_plural = 'Servicios / Trámites'

    def __str__(self):
        return self.nombre
