# Generated by Django 5.0.1 on 2024-09-17 15:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gedocumental', '0011_archivofacturacion_fecharevisionprimera_and_more'),
    ]

    operations = [
      
    
        migrations.AddField(
            model_name='archivofacturacion',
            name='IdRevisorTesoreria',
            field=models.IntegerField(blank=True, null=True),
        ),
    
    
     
    
    ]
