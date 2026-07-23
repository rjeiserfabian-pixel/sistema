"""
Script para insertar los nuevos estados de producto requeridos
por el módulo de retención de vehículos.

Uso:
    .\env\Scripts\python.exe manage.py shell < scratch/script_estados.py
  o directamente:
    .\env\Scripts\python.exe scratch/script_estados.py
"""

import os
import sys
import django

# Configurar Django si se ejecuta como script directo
if __name__ == '__main__':
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, BASE_DIR)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'raiz.settings')
    django.setup()

from software.models.estadoproductoModel import EstadoProducto

ESTADOS_REQUERIDOS = [
    'RETENIDO',
    'EN CREDITO',
    'EN REPARACION',
    'REPARADO',
]

print("=" * 50)
print("Insertando estados para módulo de retención...")
print("=" * 50)

for nombre in ESTADOS_REQUERIDOS:
    obj, created = EstadoProducto.objects.get_or_create(
        nombreestadoproducto__iexact=nombre,
        defaults={
            'nombreestadoproducto': nombre,
            'estado': 1
        }
    )
    if created:
        print(f"  [CREADO]   -> {nombre} (id: {obj.idestadoproducto})")
    else:
        if obj.estado != 1:
            obj.estado = 1
            obj.save()
            print(f"  [ACTIVADO] -> {nombre} (id: {obj.idestadoproducto})")
        else:
            print(f"  [EXISTE]   -> {nombre} (id: {obj.idestadoproducto})")

print()
print("Estados actuales en la base de datos:")
for e in EstadoProducto.objects.filter(estado=1).order_by('idestadoproducto'):
    print(f"  [{e.idestadoproducto}] {e.nombreestadoproducto}")

print()
print("✅ Script completado.")
