import json
from software.models.PreCreditoModel import PreCredito
from software.models.stockModel import Stock

print("Iniciando query...")
vehiculos_en_proceso = PreCredito.objects.filter(
    estado__in=['pendiente', 'aprobado']
).values_list('detalles_vehiculos__id_vehiculo_id', flat=True)

print("Vehiculos en proceso list:", list(vehiculos_en_proceso))

id_almacen = 3  # Based on screenshot "Principal Tarapoto / Caja Principal 3 / Exhibicion Principal"

stocks = Stock.objects.filter(
    id_almacen_id=id_almacen,
    id_vehiculo__isnull=False,
    id_vehiculo__id_situacion__nombre_situacion='DISPONIBLE',
    cantidad_disponible__gt=0,
    estado=1
).exclude(
    id_vehiculo_id__in=vehiculos_en_proceso
)

print("Stocks count:", stocks.count())
