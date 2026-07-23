from django.db import models


class Modelo(models.Model):
    idmodelo = models.AutoField(primary_key=True, db_column='idmodelo')
    nombremodelo = models.CharField(max_length=100, db_column='nombremodelo')
    estado = models.IntegerField(db_column='estado', default=1)

    class Meta:
        managed = True
        db_table = 'modelo'

    def __str__(self):
        return self.nombremodelo
