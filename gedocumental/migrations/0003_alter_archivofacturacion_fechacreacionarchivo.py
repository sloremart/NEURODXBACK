# Generated by Django 5.0.1 on 2024-02-06 19:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gedocumental', '0002_archivofacturacion_observacion_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='archivofacturacion',
            name='FechaCreacionArchivo',
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
