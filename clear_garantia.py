import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'raiz.settings')
django.setup()

from software.models.RepuestoModel import Repuesto

# Limpiar todas las garantias para evitar conflictos de tipo de dato
Repuesto.objects.all().update(garantia=None)
print("Garantias limpiadas correctamente.")
