# Generated manually to fix DB unique indexes.
# Reason: the database currently enforces UNIQUE on `codigo_almacen` (global)
# and UNIQUE on `id_sucursal` (only one almacén per sucursal), which breaks the
# intended soft-delete logic (estado=0) and the business rules (unique per sucursal).

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("software", "0005_alter_tipocomprobante_codigo_sin_unique"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                # Drop unexpected UNIQUE indexes if they exist.
                'DROP INDEX IF EXISTS "codigo_almacen";',
                'DROP INDEX IF EXISTS "id_sucursal";',
            ],
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]

