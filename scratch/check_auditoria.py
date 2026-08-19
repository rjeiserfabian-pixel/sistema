import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'raiz.settings')
django.setup()
from software.models.AuditoriaVentasModel import AuditoriaVentas
from django.db.models import Min, Max
from datetime import date

# Cuántos registros hay en total
total = AuditoriaVentas.objects.count()
print(f'Total registros en BD: {total}')

# Verificar las fechas de los registros existentes
registros = AuditoriaVentas.objects.order_by('fecha_auditoria').values('idauditoria_venta', 'fecha_auditoria')[:5]
print('Primeros 5 registros (orden ASC):')
for r in registros:
    print(f'  ID: {r["idauditoria_venta"]} | fecha_auditoria: {r["fecha_auditoria"]}')

registros_desc = AuditoriaVentas.objects.order_by('-fecha_auditoria').values('idauditoria_venta', 'fecha_auditoria')[:5]
print('Últimos 5 registros (orden DESC):')
for r in registros_desc:
    print(f'  ID: {r["idauditoria_venta"]} | fecha_auditoria: {r["fecha_auditoria"]}')

# Rango total de fechas
rango = AuditoriaVentas.objects.aggregate(min_fecha=Min('fecha_auditoria'), max_fecha=Max('fecha_auditoria'))
print(f'Rango de fechas en BD: min={rango["min_fecha"]} | max={rango["max_fecha"]}')

# Filtro del 01/08/2026 al 18/08/2026
fecha_inicio = date(2026, 8, 1)
fecha_fin = date(2026, 8, 18)
filtrados = AuditoriaVentas.objects.filter(
    fecha_auditoria__date__gte=fecha_inicio,
    fecha_auditoria__date__lte=fecha_fin
).count()
print(f'Registros entre 01/08/2026 y 18/08/2026: {filtrados}')

# Filtro solo primer dia del mes (como aparece en UI: 01/08/2026)
primer_dia = AuditoriaVentas.objects.filter(fecha_auditoria__date=date(2026, 8, 1)).count()
print(f'Registros exactamente el 01/08/2026: {primer_dia}')

# Sin filtro de fecha, cuántos trae
sin_filtro = AuditoriaVentas.objects.all().count()
print(f'Sin filtro de fecha: {sin_filtro}')
