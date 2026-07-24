# software/models/UsuarioModel.py
from django.db import models
from software.models.TipousuarioModel import Tipousuario
from software.models.empresaModel import Empresa
from software.models.sucursalesModel import Sucursales

class Usuario(models.Model):
    idusuario = models.AutoField(primary_key=True)
    nombrecompleto = models.CharField(max_length=255)
    correo = models.CharField(max_length=255)
    gmail = models.CharField(max_length=255, null=True, blank=True)
    contrasena = models.CharField(max_length=255)
    idtipousuario = models.ForeignKey(Tipousuario, models.DO_NOTHING, db_column='idtipousuario')
    celular = models.CharField(max_length=10)
    dni = models.CharField(max_length=10)
    es_dueno = models.BooleanField(default=False,null=True, blank=True)
    estado = models.IntegerField()
    idempresa = models.ForeignKey(Empresa, models.DO_NOTHING, db_column='idempresa', null=True, blank=True)
    id_sucursal = models.ForeignKey(Sucursales, models.DO_NOTHING, db_column='id_sucursal', null=True, blank= True)
    notificaciones_sonido = models.BooleanField(default=True)
    sonido_notificacion = models.FileField(upload_to='notificaciones/sonidos/', null=True, blank=True)
    imagen_perfil = models.CharField(max_length=255, null=True, blank=True)
    puede_gestionar_logistica = models.BooleanField(default=False, null=True, blank=True)
    

    class Meta: 
        managed = True
        db_table = 'usuario'