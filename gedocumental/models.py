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
    RutaArchivo = models.FileField(upload_to='gdocumental/archivosFacturacion', max_length=255, blank=True, null=True)
    NumeroAdmision = models.IntegerField() 
    Observacion = models.TextField(blank=True, null=True)
    FechaCreacionArchivo = models.DateTimeField(auto_now_add=True)
    FechaCreacionAntares = models.DateTimeField(null=True, blank=True)
    RevisionPrimera = models.BooleanField(default=False)
    RevisionSegunda = models.BooleanField(default=False)
    RevisionTercera = models.BooleanField(default=False)
    UsuarioCuentasMedicas = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='cuentas_medicas_archivos')
    UsuariosTesoreria = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='tesoreria_archivos')
    Regimen = models.CharField(max_length=1, null=True, blank=True) 

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

    # Verificar RevisionPrimera
    revision_primera_complete = archivos_admision.exists() and not archivos_admision.filter(RevisionPrimera=False).exists()
    
    # Verificar RevisionSegunda
    revision_segunda_complete = archivos_admision.exists() and not archivos_admision.filter(RevisionSegunda=False).exists()
    
    nuevo_modelo, _ = AuditoriaCuentasMedicas.objects.get_or_create(AdmisionId=instance.Admision_id)
    nuevo_modelo.RevisionCuentasMedicas = revision_primera_complete
    nuevo_modelo.RevisionTesoreria = revision_segunda_complete

    nuevo_modelo.save()

class ObservacionesArchivos(models.Model):
    IdArchivo = models.ForeignKey(ArchivoFacturacion, on_delete=models.CASCADE, related_name='Observaciones')
    IdObservacion = models.AutoField(primary_key=True)
    FechaObservacion = models.DateTimeField(auto_now_add=True)
    Descripcion = models.CharField(max_length=255, default="")
    ObservacionCuentasMedicas = models.BooleanField(default=False)
    ObservacionTesoreria = models.BooleanField(default=False)

    class Meta:
        db_table = 'ObservacionArchivo'
        managed = True

@receiver(post_save, sender=ArchivoFacturacion)
def create_observacion_archivo(sender, instance, created, **kwargs):
    if created and instance.Observacion:
        # Determinar si la observación está relacionada con cuentas médicas o tesorería
        observacion_obj = ObservacionesArchivos.objects.create(IdArchivo=instance, Descripcion=instance.Observacion)
        observacion_cuentas_medicas = instance.ObservacionCuentasMedicas
        observacion_tesoreria = instance.ObservacionTesoreria
        print("Instancia de ObservacionesArchivos creada:", observacion_obj)

        ObservacionesArchivos.objects.create(
            IdArchivo=instance,
            Descripcion=instance.Observacion,
            ObservacionCuentasMedicas=observacion_cuentas_medicas,
            ObservacionTesoreria=observacion_tesoreria
        )



#### PARA CREAR OBSERVACIONES SIN ARCHIVOS ######

class ObservacionSinArchivo(models.Model):
    AdmisionId = models.IntegerField()
    Usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    Descripcion = models.TextField()
    TipoArchivo = models.CharField(max_length=50)
    FechaObservacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'observaciones_sin_archivo'
        managed = True
        verbose_name = 'Observación sin Archivo'
        verbose_name_plural = 'Observaciones sin Archivo'

    def __str__(self):
        return f'Observación {self.id} para la admisión {self.AdmisionId}'



