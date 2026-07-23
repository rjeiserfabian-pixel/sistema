
from django.db import models

from software.models.categoriaModel import Categoria
from software.models.UnidadesModel import Unidades
from software.models.marcaModel import Marca
from software.models.cilindradaModel import Cilindrada
from software.models.colorModel import Color
from software.models.modeloModel import Modelo
from software.models.ConfiguracionVehicularModel import ConfiguracionVehicular
from software.models.DetalleColorModel import DetalleColor


class Producto(models.Model):
    idproducto = models.AutoField(primary_key=True, db_column='idproducto')
    nomproducto = models.CharField(max_length=255, db_column='nomproducto')
    imagenprod = models.CharField(max_length=255, db_column='imagenprod')
    estado = models.IntegerField(db_column='estado')
    idcategoria = models.ForeignKey(Categoria, on_delete=models.DO_NOTHING, db_column='idcategoria', related_name='productos')
    idunidad = models.ForeignKey(Unidades, on_delete=models.DO_NOTHING, db_column='idunidad', related_name='productos')
    idmarca = models.ForeignKey(Marca, on_delete=models.DO_NOTHING, db_column='idmarca', related_name='productos')
    idmodelo = models.ForeignKey(Modelo, on_delete=models.DO_NOTHING, db_column='idmodelo', related_name='productos', null=True, blank=True)
    idcilindrada = models.ForeignKey(Cilindrada, on_delete=models.DO_NOTHING, db_column='idcilindrada', related_name='productos')

    idcolor = models.ForeignKey(Color, on_delete=models.DO_NOTHING, db_column='idcolor', related_name='productos')
    id_detalle_color = models.ForeignKey(
        DetalleColor,
        on_delete=models.SET_NULL,
        db_column='id_detalle_color',
        null=True,
        blank=True,
        related_name='productos'
    )
    codigo_interno = models.CharField(max_length=50, null=True, blank=True, db_column='codigo_interno')
    id_configuracion = models.ForeignKey(
        ConfiguracionVehicular, 
        on_delete=models.SET_NULL, 
        db_column='id_configuracion', 
        null=True, 
        blank=True, 
        related_name='productos'
    )
    
    def __str__(self):
        return self.nomproducto

    @staticmethod
    def actualizar_nombres_en_cascada(productos):
        if not productos:
            return
        
        productos_a_actualizar = []
        for prod in productos:
            partes = []
            if prod.idcategoria and prod.idcategoria.nomcategoria: 
                partes.append(prod.idcategoria.nomcategoria.strip())
            if prod.idmarca and prod.idmarca.nombremarca: 
                partes.append(prod.idmarca.nombremarca.strip())
            if prod.idmodelo and prod.idmodelo.nombremodelo: 
                partes.append(prod.idmodelo.nombremodelo.strip())
            if prod.id_configuracion and prod.id_configuracion.nombre: 
                partes.append(prod.id_configuracion.nombre.strip())
            if prod.idcolor and prod.idcolor.nombrecolor: 
                partes.append(prod.idcolor.nombrecolor.strip())
            
            # Limpiar espacios múltiples y unir
            nuevo_nombre = " ".join([p for p in partes if p])
            if prod.nomproducto != nuevo_nombre:
                prod.nomproducto = nuevo_nombre
                productos_a_actualizar.append(prod)
                
        if productos_a_actualizar:
            Producto.objects.bulk_update(productos_a_actualizar, ['nomproducto'])

    class Meta:
        managed = True
        db_table = 'producto'
        indexes = [models.Index(fields=['nomproducto'])]
