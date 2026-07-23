from django.db import models


class MarcaRepuesto(models.Model):
    idmarca_repuesto = models.AutoField(primary_key=True, db_column='idmarca_repuesto')
    nombremarca = models.CharField(max_length=100, db_column='nombremarca', verbose_name="Nombre Marca")
    estado = models.IntegerField(db_column='estado', default=1)

    class Meta:
        managed = True
        db_table = 'marca_repuesto'
        ordering = ['nombremarca']

    def __str__(self):
        return self.nombremarca
