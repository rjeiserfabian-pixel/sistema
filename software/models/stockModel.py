from django.db import models
from software.models.almacenesModel import Almacenes
from software.models.VehiculosModel import Vehiculo
from software.models.RespuestoCompModel import RepuestoComp
from software.models.compradetalleModel import CompraDetalle


class Stock(models.Model):
    id_stock = models.AutoField(primary_key=True)
    id_almacen = models.ForeignKey(Almacenes, on_delete=models.CASCADE, db_column='id_almacen', related_name='stocks')
    idcompradetalle = models.ForeignKey(CompraDetalle, on_delete=models.CASCADE, db_column='idcompradetalle', related_name='stocks', null=True, blank=True)
    # Producto puede ser vehículo o repuesto
    id_vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, db_column='id_vehiculo', related_name='stocks', null=True, blank=True)
    id_repuesto_comprado = models.ForeignKey(RepuestoComp, on_delete=models.CASCADE, db_column='id_repuesto_comprado', related_name='stocks', null=True, blank=True)
    cantidad_disponible = models.IntegerField(default=0, db_column='cantidad_disponible')
    fecha_ultima_actualizacion = models.DateTimeField(auto_now=True, db_column='fecha_ultima_actualizacion')
    estado = models.IntegerField(default=1, db_column='estado')
    
    class Meta:
        managed = True
        db_table = 'stock'
        
    
    def __str__(self):
        if self.id_vehiculo:
            return f"Stock: {self.id_vehiculo.idproducto.nomproducto} - {self.id_almacen.nombre_almacen} ({self.cantidad_disponible})"
        elif self.id_repuesto_comprado:
            return f"Stock: {self.id_repuesto_comprado.id_repuesto.nombre} - {self.id_almacen.nombre_almacen} ({self.cantidad_disponible})"
        return f"Stock #{self.id_stock}"
    
    def agregar_stock(self, cantidad):
        """Incrementa el stock de forma atómica (sin race conditions)."""
        from django.db.models import F
        Stock.objects.filter(pk=self.pk).update(
            cantidad_disponible=F('cantidad_disponible') + cantidad
        )
        self.refresh_from_db(fields=['cantidad_disponible'])

    def descontar_stock(self, cantidad):
        """
        Decrementa el stock de forma atómica (sin race conditions).
        El UPDATE solo se ejecuta si hay suficiente stock en ese instante,
        evitando que dos requests simultáneos resten el mismo stock.
        Retorna True si el descuento fue exitoso, False si no hay stock suficiente.
        """
        from django.db.models import F
        filas_actualizadas = Stock.objects.filter(
            pk=self.pk,
            cantidad_disponible__gte=cantidad  # Condición atómica en la DB
        ).update(cantidad_disponible=F('cantidad_disponible') - cantidad)

        if filas_actualizadas:
            self.refresh_from_db(fields=['cantidad_disponible'])
            return True
        return False
    
    @property
    def tiene_stock(self):
        """Verifica si hay stock disponible"""
        return self.cantidad_disponible > 0