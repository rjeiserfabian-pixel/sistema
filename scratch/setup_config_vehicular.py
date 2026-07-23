import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'raiz.settings')
django.setup()

from software.models.ModulosModel import Modulos
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos
from software.models.TipousuarioModel import Tipousuario

def setup_module():
    # 1. Crear el módulo en la tabla 'modulos'
    # El ID del padre 'Almacén' es 26
    padre_almacen = Modulos.objects.filter(idmodulo=26).first()
    if not padre_almacen:
        print("Error: No se encontró el módulo padre 'Almacén' (ID 26)")
        return

    modulo, created = Modulos.objects.get_or_create(
        nombremodulo='Configuración Vehicular',
        defaults={
            'idmodulo_padre': padre_almacen,
            'url': 'configuracion_vehicular',
            'logo': 'bi bi-circle',
            'estado': 1,
            'orden': 99
        }
    )

    if created:
        print(f"Módulo '{modulo.nombremodulo}' creado con éxito.")
    else:
        print(f"Módulo '{modulo.nombremodulo}' ya existía.")

    # 2. Asignar permisos al Administrador (ID 1)
    admin_tipo = Tipousuario.objects.filter(idtipousuario=1).first()
    if admin_tipo:
        permiso, p_created = Detalletipousuarioxmodulos.objects.get_or_create(
            idtipousuario=admin_tipo,
            idmodulo=modulo
        )
        if p_created:
            print(f"Permisos asignados al Administrador para el módulo '{modulo.nombremodulo}'.")
        else:
            print(f"El Administrador ya tenía permisos para el módulo '{modulo.nombremodulo}'.")
    else:
        print("Error: No se encontró el tipo de usuario 'Administrador' (ID 1)")

if __name__ == '__main__':
    setup_module()
