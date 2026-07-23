# Permite reutilizar el mismo DNI/RUC cuando un proveedor fue eliminado (estado=0).
# La unicidad se valida en la vista solo entre activos (estado=1).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('software', '0007_alter_cliente_numdoc_sin_unique'),
    ]

    operations = [
        migrations.AlterField(
            model_name='proveedor',
            name='numdoc',
            field=models.CharField(max_length=255, verbose_name='Número de Documento'),
        ),
    ]

