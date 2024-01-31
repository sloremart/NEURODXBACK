import os
from django.contrib.auth.models import AbstractUser
from email.headerregistry import Group
from django.db import models
from django.dispatch import receiver
from django.db.models.signals import pre_delete

from .modelsFacturacion import Admisiones




class ArchivoFacturacion(models.Model):
    IdArchivo = models.AutoField(primary_key=True)
    Admision = models.ForeignKey(Admisiones, on_delete=models.CASCADE)
    Tipo = models.CharField(max_length=50)
    NombreArchivo = models.CharField(max_length=255, default="sin_nombre")
    RutaArchivo = models.FileField(upload_to='GeDocumental/archivosFacturacion', max_length=255, blank=True, null=True)
    NumeroAdmision = models.IntegerField() 
    FechaCreacionArchivo = models.DateField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Actualizar el número de admisión antes de guardar
        self.NumeroAdmision = self.Admision.Consecutivo
        if self.RutaArchivo:
            self.NombreArchivo = os.path.basename(self.RutaArchivo.name)
        super(ArchivoFacturacion, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Eliminar el archivo físico al eliminar el objeto ArchivoFacturacion
        if self.RutaArchivo:
            storage, path = self.RutaArchivo.storage, self.RutaArchivo.path
            storage.delete(path)
        super(ArchivoFacturacion, self).delete(*args, **kwargs)

    class Meta:
        db_table = 'archivos'
        managed = True

@receiver(pre_delete, sender=ArchivoFacturacion)
def delete_file_on_delete(sender, instance, **kwargs):
    # Eliminar el archivo físico al eliminar el objeto ArchivoFacturacion
    if instance.RutaArchivo:
        storage, path = instance.RutaArchivo.storage, instance.RutaArchivo.path
        storage.delete(path)
#############################################
        