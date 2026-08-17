import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'raiz.settings')
django.setup()

from django.db import connection
from software.models.ModulosModel import Modulos
from software.models.detalletipousuarioxmodulosModel import Detalletipousuarioxmodulos
from software.models.TipousuarioModel import Tipousuario

# 1. Resetear la secuencia del autoincrement de la tabla modulos
with connection.cursor() as cursor:
    cursor.execute("SELECT MAX(idmodulo) FROM modulos")
    max_id = cursor.fetchone()[0]
    print(f"MAX idmodulo actual: {max_id}")
    cursor.execute(
        "SELECT setval(pg_get_serial_sequence('modulos','idmodulo'), %s)",
        [max_id]
    )
    print("Secuencia reseteada OK")

# 2. Crear modulo PADRE: Auditorias
padre, created = Modulos.objects.get_or_create(
    nombremodulo='Auditorias',
    idmodulo_padre=None,
    defaults={
        'estado': 1,
        'url': '#',
        'logo': 'bi bi-shield-lock',
        'orden': 11,
    }
)
print(f"Padre creado={created} | ID={padre.idmodulo} | Nombre={padre.nombremodulo}")

# 3. Sub-modulos hijos
submodulos = [
    ('Aud. Ventas',    '/auditorias/ventas/',    'bi bi-circle', 1),
    ('Aud. Compras',   '/auditorias/compras/',   'bi bi-circle', 2),
    ('Aud. Productos', '/auditorias/productos/', 'bi bi-circle', 3),
    ('Aud. Cajas',     '/auditorias/cajas/',     'bi bi-circle', 4),
    ('Aud. Usuarios',  '/auditorias/usuarios/',  'bi bi-circle', 5),
    ('Aud. Creditos',  '/auditorias/creditos/',  'bi bi-circle', 6),
]

hijos = []
for nombre, url, logo, orden in submodulos:
    hijo, c = Modulos.objects.get_or_create(
        nombremodulo=nombre,
        idmodulo_padre=padre,
        defaults={'estado': 1, 'url': url, 'logo': logo, 'orden': orden}
    )
    hijos.append(hijo)
    print(f"  Hijo creado={c} | ID={hijo.idmodulo} | {nombre} -> {url}")

# 4. Asignar permisos al Administrador (ID=1)
admin = Tipousuario.objects.get(idtipousuario=1)
todos = [padre] + hijos
for mod in todos:
    det, c = Detalletipousuarioxmodulos.objects.get_or_create(
        idmodulo=mod,
        idtipousuario=admin
    )
    print(f"  Permiso Admin creado={c} | Modulo={mod.idmodulo} ({mod.nombremodulo})")

print("\nDONE - Modulo Auditorias insertado correctamente.")
