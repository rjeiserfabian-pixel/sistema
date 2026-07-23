
from django.db import models

class Unidades(models.Model):
    idunidad = models.AutoField(primary_key=True)
    abrunidad = models.CharField(max_length=255, verbose_name="Nombre de la unidad")
    codigo_sunat = models.CharField(max_length=10, verbose_name="Código SUNAT")
    estado = models.BooleanField(default=False, verbose_name="Estado", help_text="Indica si la unidad está activa (True) o desactivada (False)")

    class Meta:
        managed = True
        db_table = 'unidades'  # Define la tabla en la base de datos
        verbose_name = "Unidad"
        verbose_name_plural = "Unidades"
        ordering = ['idunidad']  # Orden por ID por defecto

    def __str__(self):
        # Devuelve una representación legible del objeto
        return f"{self.codigo_sunat} - {self.abrunidad}"

