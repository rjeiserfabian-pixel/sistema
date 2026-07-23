# Permite reutilizar el mismo DNI/RUC cuando un cliente fue eliminado (estado=0).
# La unicidad se valida en la vista solo entre activos (estado=1).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('software', '0006_drop_unique_indexes_almacenes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cliente',
            name='numdoc',
            field=models.CharField(max_length=25, verbose_name='Número de Documento'),
        ),
    ]

