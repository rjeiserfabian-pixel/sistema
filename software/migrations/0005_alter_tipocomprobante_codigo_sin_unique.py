# Permite reutilizar el mismo código al crear un tipo de comprobante
# después de haber eliminado uno (estado=0). La unicidad se valida en la vista solo entre activos (estado=1).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('software', '0004_proforma_module'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tipocomprobante',
            name='codigo',
            field=models.CharField(
                max_length=10,
                verbose_name='Código',
                help_text='Código del tipo de comprobante (ej: 01, 03, 07). Único entre registros activos.',
            ),
        ),
    ]
