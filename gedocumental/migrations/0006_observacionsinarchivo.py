# Generated by Django 5.0.1 on 2024-07-08 01:27

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gedocumental', '0005_archivofacturacion_regimen_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ObservacionSinArchivo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('AdmisionId', models.IntegerField()),
                ('Descripcion', models.TextField()),
                ('TipoArchivo', models.CharField(max_length=50)),
                ('FechaObservacion', models.DateTimeField(auto_now_add=True)),
                ('Usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Observación sin Archivo',
                'verbose_name_plural': 'Observaciones sin Archivo',
                'db_table': 'observaciones_sin_archivo',
                'managed': True,
            },
        ),
    ]
