import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'raiz.settings')
django.setup()

from django.db.models import Max
from software.models.ModulosModel import Modulos

padre = Modulos.objects.filter(nombremodulo__icontains='Reportes', idmodulo_padre__isnull=True).first()
if padre:
    print(f"Módulo padre encontrado: {padre.nombremodulo} (ID: {padre.idmodulo})")
    
    existe = Modulos.objects.filter(url='/reportes/articulos-vendidos/').first()
    if not existe:
        max_id = Modulos.objects.aggregate(Max('idmodulo'))['idmodulo__max'] or 0
        nuevo_modulo = Modulos.objects.create(
            idmodulo=max_id + 1,
            nombremodulo='Artículos Vendidos',
            estado=1,
            url='/reportes/articulos-vendidos/',
            logo='bi bi-circle',
            idmodulo_padre=padre,
            orden=padre.submodulos.count() + 1
        )
        print(f"Creado sub-módulo 'Artículos Vendidos' con ID: {nuevo_modulo.idmodulo}")
    else:
        print("El sub-módulo 'Artículos Vendidos' ya existe.")
else:
    print("Error: No se encontró el módulo padre 'Reportes'.")
