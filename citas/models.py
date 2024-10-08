from django.contrib.auth.models import AbstractUser
from email.headerregistry import Group
from django.db import models
from django.db import models


########## CONFIRMACION CITAS ###########################
class Citas(models.Model):
    IdCita = models.AutoField(primary_key=True)
    FechaSolicitud = models.DateField()
    FeCita = models.DateField()
    FechaCita = models.CharField(max_length=255)
    IdMedico = models.CharField(max_length=255)
    NumeroPaciente = models.IntegerField() 
    CreadoPor = models.IntegerField()
    ModificadoPor = models.IntegerField()
    Estado = models.BooleanField()
    Cumplida = models.BooleanField()
    Observaciones = models.TextField() 
    Procedimiento = models.CharField(max_length=255)
    VrProcedimiento =  models.IntegerField() 
    IdServicio = models.CharField(max_length=255)
    Autorizacion = models.CharField(max_length=255)
    FechaModificado =  models.DateField()
    Entidad = models.CharField(max_length=255)
    VigenciaAutorizacion = models.DateField()
    Cancelada =  models.IntegerField() 
    Facturada =  models.IntegerField() 
    HoraLlegada = models.DateField()
    HoraAtencion = models.DateField()
    AdmisionNo =  models.IntegerField()  
    PacienteEnSala = models.IntegerField()  
    DiasOportunidad = models.IntegerField()  
    VarOportunidad = models.IntegerField()  
    FechaPideUsuario = models.IntegerField()  
    EDeleted =  models.IntegerField() 
    Agenda =  models.IntegerField() 
    tAsignada =  models.IntegerField() 
    PteAtendido =  models.IntegerField() 
    Bloqueado =  models.IntegerField() 
    Programa =  models.IntegerField() 
    Prioritaria = models.IntegerField() 
    SolicitudNo = models.CharField(max_length=255)
    CanceladaPor = models.IntegerField() 
    FechaCancelacion = models.DateField()
    Turno = models.CharField(max_length=1, choices=[('1', 'Opción 1'), ('2', 'Opción 2')])
    CitaRef = models.IntegerField() 
    MotivoCancela =  models.BooleanField() 

    class Meta:
        # Especifica la base de datos a utilizar para este modelo
        db_table = 'citas'
        app_label = 'datosipsndx'
        managed = False
        

class Pacientes(models.Model):
    NumeroPaciente = models.AutoField(primary_key=True)
    IDPaciente =  models.CharField(max_length=255)
    Ordinal = models.IntegerField() 
    Apellido1 = models.CharField(max_length=30)
    Apellido2 = models.CharField(max_length=30)
    Nombre1 = models.CharField(max_length=20)
    Nombre2 = models.CharField(max_length=20)
    TipoAfiliacion = models.CharField(max_length=20)
    TipoUsuario = models.FloatField()
    PACI_ATEN = models.CharField(max_length=20)
    FechaNacimiento = models.DateField()
    SexoPaciente = models.CharField(max_length=20)
    Direccion = models.CharField(max_length=59)
    Municipio = models.CharField(max_length=20)
    Telefono = models.CharField(max_length=30)
    Zona =  models.CharField(max_length=30)
    Ocupacion = models.CharField(max_length=30)
    Creado = models.DateField()
    Modificado =  models.DateField()
    CreadoPor = models.IntegerField() 
    ModificadoPor = models.IntegerField() 
    NITEPS = models.CharField(max_length=15)
    Consecutivo =  models.BooleanField() 
    EstaEnIPS = models.IntegerField() 
    EstadoCivil = models.IntegerField() 
    HistoriaPrevias = models.IntegerField() 
    LugarExpedicion = models.CharField(max_length=15)
    FechaCreado = models.DateField()
    FechaModificado = models.DateField()
    EntidadPaciente =models.CharField(max_length=14)
    Nivel = models.ImageField()
    Diagnostico = models.TextField()
    TipoInconsistencia = models.IntegerField()
    MalTipoID = models.TextField()
    MalIdPaciente = models.TextField()
    MalApellido1 = models.TextField()
    MalApellido2 = models.TextField()
    MalNombre1 = models.TextField()
    MalNombre2 = models.TextField()
    MalfechaNac = models.DateField()
    GrupoSanguineo = models.CharField(max_length=2)
    RH = models.CharField(max_length=2)
    LugarNacimiento = models.TextField()
    DxP1 = models.CharField(max_length=4)
    DxP2 = models.CharField(max_length=4)
    DxP3 = models.CharField(max_length=4)
    FechaIngreso = models.DateField()
    Estadio = models.TextField()
    FechaDx = models.DateField()
    Muerto = models.IntegerField()
    FechaMuerte = models.DateField()
    NCompleto = models.CharField(max_length=80)
    Raza = models.TextField()
    Relegion = models.TextField()
    FechaInicioTratamiento = models.DateField()
    Talla = models.TextField()
    TipoDialisis = models.IntegerField()
    AccesoVascular = models.TextField()
    TipoIngreso = models.IntegerField()
    CorreoE = models.TextField()
    Procedencia = models.CharField(max_length=5)
    Escolaridad = models.IntegerField()
    CarneNo = models.CharField(max_length=10)
  


        
    class Meta:
        db_table = 'pacientes'
        app_label = 'datosipsndx'
        managed = False
        