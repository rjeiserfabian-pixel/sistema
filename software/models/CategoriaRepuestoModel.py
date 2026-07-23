from django.db import models


class CategoriaRepuesto(models.Model):
    idcategoria_repuesto = models.AutoField(primary_key=True, db_column='idcategoria_repuesto')
    nomcategoria = models.CharField(max_length=255, db_column='nomcategoria', verbose_name="Nombre Categoria")
    estado = models.IntegerField(db_column='estado', default=1)

    class Meta:
        managed = True
        db_table = 'categoria_repuesto'
        ordering = ['nomcategoria']

    def __str__(self):
        return self.nomcategoria
