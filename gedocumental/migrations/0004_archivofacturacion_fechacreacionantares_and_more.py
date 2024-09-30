from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('gedocumental', '0003_alter_archivofacturacion_rutaarchivo'),
    ]

    operations = [
        migrations.AddField(
            model_name='observacionsinarchivo',
            name='Revisada',
            field=models.BooleanField(default=False),
        ),
    ]