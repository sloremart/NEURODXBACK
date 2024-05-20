import os
from django.db import models
from django.dispatch import receiver
from django.db.models.signals import pre_delete,pre_save,post_save
from django.contrib.auth.models import User
from django.conf import settings



class ArchivoFacturacion(models.Model):
    IdArchivo = models.AutoField(primary_key=True)
    Admision_id =  models.IntegerField() 
    Tipo = models.CharField(max_length=50, choices=[])
    Usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    NombreArchivo = models.CharField(max_length=255, default="sin_nombre")
    RutaArchivo = models.FileField(upload_to='GeDocumental/archivosFacturacion', max_length=255, blank=True, null=True)
    NumeroAdmision = models.IntegerField() 
    Observacion = models.TextField(blank=True, null=True)
    FechaCreacionArchivo = models.DateTimeField(auto_now_add=True)
    RevisionPrimera = models.BooleanField(default=False)
    RevisionSegunda = models.BooleanField(default=False)
    RevisionTercera = models.BooleanField(default=False)
    

    def save(self, *args, **kwargs):
        if self.RutaArchivo:
            self.NombreArchivo = os.path.basename(self.RutaArchivo.name)
        super(ArchivoFacturacion, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.RutaArchivo:
            storage, path = self.RutaArchivo.storage, self.RutaArchivo.path
            storage.delete(path)
        super(ArchivoFacturacion, self).delete(*args, **kwargs)

    class Meta:
        db_table = 'archivos'
        managed = True        




        
######### CUENTAS MEDICAS - TALENTO HUMANO   ###########
    
class AuditoriaCuentasMedicas(models.Model):
    AdmisionId = models.IntegerField(primary_key=True)
    FechaCreacion = models.DateTimeField(auto_now_add=True)
    FechaCargueArchivo = models.DateTimeField(auto_now_add=True)    
    Observacion = models.CharField(max_length=255, default="sin_nombre")
    RevisionCuentasMedicas = models.BooleanField(default=False)
    RevisionTesoreria = models.BooleanField(default=False)

    class Meta:
        db_table = 'AdmisionAuditoria'
        managed = True

@receiver(post_save, sender=ArchivoFacturacion)
def update_revision_cuentas_medicas(sender, instance, **kwargs):
    archivos_admision = ArchivoFacturacion.objects.filter(Admision_id=instance.Admision_id)

    # Verificar si todos los archivos tienen RevisionPrimera en True
    if archivos_admision.exists() and not archivos_admision.filter(RevisionPrimera=False).exists():
        nuevo_modelo, _ = AuditoriaCuentasMedicas.objects.get_or_create(AdmisionId=instance.Admision_id)
        nuevo_modelo.RevisionCuentasMedicas = True
        nuevo_modelo.save()
    else:
        nuevo_modelo, _ = AuditoriaCuentasMedicas.objects.get_or_create(AdmisionId=instance.Admision_id)
        nuevo_modelo.RevisionCuentasMedicas = False
        nuevo_modelo.save()



class ObservacionesArchivos(models.Model):
    IdArchivo = models.ForeignKey(ArchivoFacturacion, on_delete=models.CASCADE, related_name='Observaciones')
    IdObservacion = models.AutoField(primary_key=True)
    FechaObservacion = models.DateTimeField(auto_now_add=True)
    Descripcion = models.CharField(max_length=255, default="")

    class Meta:
        db_table = 'ObservacionArchivo'
        managed = True

@receiver(post_save, sender=ArchivoFacturacion)
def create_observacion_archivo(sender, instance, created, **kwargs):
    print("Señal post_save recibida para ArchivoFacturacion")
    if created and instance.Observacion:
        observacion_obj = ObservacionesArchivos.objects.create(IdArchivo=instance, Descripcion=instance.Observacion)
        print("Instancia de ObservacionesArchivos creada:", observacion_obj)


