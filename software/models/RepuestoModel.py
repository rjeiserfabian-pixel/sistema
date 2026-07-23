from django.db import models
from software.models.UnidadesModel import Unidades
from software.models.MarcaRepuestoModel import MarcaRepuesto
from software.models.CategoriaRepuestoModel import CategoriaRepuesto
from software.models.CategoriaRepuestoModel import CategoriaRepuesto
from software.models.GarantiaRepuestoModel import GarantiaRepuesto


class Repuesto(models.Model):
    id_repuesto = models.AutoField(primary_key=True, db_column='id_repuesto')
    nombre = models.CharField(max_length=255, db_column='nombre')
    codigo_interno = models.CharField(
        max_length=50, null=True, blank=True,
        db_column='codigo_interno', verbose_name="Codigo Interno"
    )
    estado = models.IntegerField(db_column='estado', default=1)

    # Relaciones
    idunidad = models.ForeignKey(
        Unidades, on_delete=models.DO_NOTHING,
        db_column='idunidad', related_name='repuestos'
    )
    idmarca = models.ForeignKey(
        MarcaRepuesto, on_delete=models.DO_NOTHING,
        db_column='idmarca', related_name='repuestos',
        null=True, blank=True
    )
    id_categoria_repuesto = models.ForeignKey(
        CategoriaRepuesto, on_delete=models.DO_NOTHING,
        db_column='id_categoria_repuesto', related_name='repuestos',
        null=True, blank=True
    )

    # Informacion del repuesto
    modelo_referencia = models.CharField(
        max_length=100, null=True, blank=True,
        db_column='modelo_referencia', verbose_name="Modelo/Referencia"
    )
    codigo_barras = models.CharField(
        max_length=100, null=True, blank=True,
        db_column='codigo_barras', verbose_name="Codigo de Barras",
        db_index=True
    )
    descripcion = models.TextField(
        null=True, blank=True,
        db_column='descripcion', verbose_name="Descripcion"
    )
    compatibilidad = models.TextField(
        null=True, blank=True,
        db_column='compatibilidad', verbose_name="Compatibilidad"
    )

    # Inventario
    stock_minimo = models.IntegerField(
        default=0, db_column='stock_minimo', verbose_name="Stock Minimo"
    )
    stock_maximo = models.IntegerField(
        default=0, db_column='stock_maximo', verbose_name="Stock Maximo"
    )

    # Precios de referencia
    costo_unitario = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        db_column='costo_unitario', verbose_name="Costo Unitario"
    )
    precio_minimo = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        db_column='precio_minimo', verbose_name="Precio Minimo"
    )
    precio_sugerido = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        db_column='precio_sugerido', verbose_name="Precio Sugerido"
    )

    # Informacion adicional
    id_garantia_repuesto = models.ForeignKey(
        GarantiaRepuesto, on_delete=models.DO_NOTHING,
        db_column='id_garantia_repuesto', related_name='repuestos',
        null=True, blank=True, verbose_name="Garantia"
    )
    observaciones = models.TextField(
        null=True, blank=True,
        db_column='observaciones', verbose_name="Observaciones"
    )

    class Meta:
        managed = True
        db_table = 'repuestos'
        indexes = [models.Index(fields=['nombre'])]

    def __str__(self):
        return self.nombre
