from django.contrib.auth.models import AbstractUser
from email.headerregistry import Group
from django.db import models



class Admisiones(models.Model):
    Consecutivo = models.IntegerField(primary_key=True)
    SubCentro =  models.IntegerField()
    TipoID = models.CharField(max_length=30)
    IDPaciente = models.CharField(max_length=30)
    Ordinal = models.IntegerField()
    CodigoEntidad = models.CharField(max_length=20)
    PolizaNo = models.CharField(max_length=20)
    Confirmado = models.CharField(max_length=20)
    CedulaResponsable = models.CharField(max_length=20)
    NombreResponsable = models.CharField(max_length=20)
    DireccionResponsable = models.CharField(max_length=20)
    TelefonoResponsable = models.CharField(max_length=20)
    AutorizacionNo = models.CharField(max_length=59)
    FechaCreado = models.DateField()
    FechaModificado = models.DateField()
    CreadoPor =  models.IntegerField() 
    ModificadoPor = models.IntegerField()
    Estado = models.IntegerField()
    FechaSalida =  models.DateField()
    TipoAdmision = models.IntegerField()
    SalidaPor = models.IntegerField() 
    Habitacion = models.CharField(max_length=15)
    FechaHospital =  models.DateField() 
    TipoCirugia = models.IntegerField() 
    MotivoConsulta = models.TextField()
    Facturado = models.IntegerField()
    FacturadoPor = models.IntegerField()
    FacturaNo = models.CharField(max_length=15)
    MDTratante = models.CharField(max_length=15)
    Especialidad = models.TextField()
    Anulada = models.IntegerField()
    Procedimiento1 = models.CharField(max_length=15)
    Procedimiento2 = models.CharField(max_length=15)
    Procedimiento3 = models.CharField(max_length=15)
    Procedimiento4 = models.CharField(max_length=15)
    Procedimiento5 = models.CharField(max_length=15)
    Procedimiento6 = models.CharField(max_length=15)
    TipoEvento = models.IntegerField()
    EmpresaPaciente = models.TextField()
    MunicipioEmpresa = models.CharField(max_length=15)
    NMDTratante = models.TextField()
    VrRecibido = models.TextField()
    Mpago = models.IntegerField()
    SemanasCot = models.TextField()
    Nivel = models.IntegerField()
    Capitado = models.IntegerField()
    NumeroPaciente = models.IntegerField()
    MotivoAnulacion = models.CharField(max_length=15)
    AnuladaPor = models.IntegerField()
    FechaAnulada =  models.DateField()
    Ruta = models.CharField(max_length=15)
    VrInicial = models.IntegerField()
    VrConsumido = models.IntegerField()
    Radicado = models.CharField(max_length=15)
    Diag1 = models.CharField(max_length=15)
    Diag2 = models.CharField(max_length=15)
    Diag3 = models.CharField(max_length=15)
    FechaAutorizada  = models.DateField()
    FCreada = models.DateField()
    ConceptoRC = models.TextField()
    NumeroRC = models.TextField()
    FechaImpreso = models.DateField()
    ListoFarmacia = models.IntegerField()
    ListoLaboratorio  = models.IntegerField()
    EvitarDeleted= models.IntegerField()
    Examenes = models.IntegerField()
    CCosto= models.IntegerField()
    EDeleted = models.IntegerField()
    SeccionFactura = models.CharField(max_length=15)
    ObservacionesEnf = models.TextField()
    IdEvento= models.IntegerField()
    Impresiones = models.IntegerField()
    ImpresionFormatos  = models.TextField()
    Diario = models.CharField(max_length=15)
    Remitido = models.IntegerField()
    RemitidoPor  = models.TextField()
    CodigoRemite = models.TextField()
    MpioRemite = models.TextField()
    Triage = models.IntegerField()
    Cobertura = models.IntegerField()
    OrigenAttn = models.IntegerField()
    Destino= models.IntegerField()
    TipoSolicitud = models.CharField(max_length=15)
    Prioridad= models.CharField(max_length=15)
    PteAtendido = models.IntegerField()
    HoraAtencion = models.DateField()
    IdCita= models.IntegerField()
    Murgencias = models.CharField(max_length=15)
    HoraLlegada = models.DateField()
    SegundosAtencion = models.IntegerField()
    IDAnarlab = models.CharField(max_length=15)
    TratarEnfBase = models.IntegerField()
    tRegimen= models.IntegerField()
    TipoAfiliado  = models.CharField(max_length=15)
    MedicoOrdena = models.TextField()
    IPSOrdena = models.TextField()
    EspMDOrdena= models.IntegerField()
     
    class Meta:
        
        db_table = 'admisiones'
        app_label = 'datosipsndx'
        managed = False







class Factura(models.Model):
    AdmisionNo = models.IntegerField(primary_key=True)
    FacturaNo =  models.IntegerField()
    Fecha = models.DateField()
    Plan= models.TextField()
    TotalServicio= models.DecimalField(max_digits=12, decimal_places=2)
    TotalTerceros= models.DecimalField(max_digits=12, decimal_places=2)
    TotalFactura= models.DecimalField(max_digits=12, decimal_places=2)
    VrAbono= models.IntegerField()
    VrDescuento = models.IntegerField()
    VrAbonado= models.IntegerField()
    FechaAdmision = models.DateField()
    EnviadoEntidad = models.SmallIntegerField()
    FechaEnvio = models.DateField()
    RemisionNo = models.CharField(max_length=15)
    VrOtros =  models.IntegerField()
    Contabilizada  = models.SmallIntegerField()
    Revisada  = models.SmallIntegerField()
    FechaRecibo = models.DateField()
    FechaReenvio = models.DateField()
    Ruta= models.CharField(max_length=20)
    ReemplazadaPor = models.IntegerField()
    ReemplazadaFactura = models.IntegerField()
    Observaciones  = models.TextField()
    FechaDevolucion = models.DateField()
    Devuelta= models.SmallIntegerField()
    TarifarioFactura= models.SmallIntegerField()
    VrGlosa= models.DecimalField(max_digits=12, decimal_places=2)
    TipoGlosa = models.SmallIntegerField()
    MotivoGlosa= models.TextField()
    Prefijo = models.CharField(max_length=15)
    VrCapitacion = models.IntegerField()
    FechaCreado= models.DateField()
    FechaModificado = models.DateField()
    FechaGlosa = models.DateField()
    FechaRespuesta = models.DateField()
    FechaReciboGlosa= models.DateField()
    FechaElaboracionGlosa= models.DateField()
    VrIVA = models.IntegerField()
    VrAceptado= models.DecimalField(max_digits=12, decimal_places=2)
    VrRecibidoAdmision= models.IntegerField()
    Etimer= models.IntegerField()
    IncluirCuentaCobro = models.SmallIntegerField()
    Impresa= models.SmallIntegerField()
    Modificadapor= models.IntegerField()
    VrLevantadoGlosa= models.DecimalField(max_digits=12, decimal_places=2)
    FechaLevante = models.DateField()
    IDPaciente= models.CharField(max_length=15)
    FacturaCC = models.IntegerField()
    VrCopago= models.IntegerField()
    VrCuotaModeradora= models.IntegerField()
    FacturaAnulada= models.IntegerField()
    EstadoContGlosa= models.IntegerField()
    CreoGlosa= models.IntegerField()
    ContestoGlosa = models.IntegerField()
    DetalleFact= models.TextField()
    TipoDoc1= models.TextField()
    TipoDoc2= models.TextField()
    TipoDoc3= models.TextField()
    TipoDoc4= models.TextField()
    TipoDoc5= models.TextField()
    TipoDoc6= models.TextField()
    VrRatificado= models.DecimalField(max_digits=12, decimal_places=2)
    VrAceptadoConc= models.DecimalField(max_digits=12, decimal_places=2)
    VrSoportadoEntidad = models.DecimalField(max_digits=12, decimal_places=2)
    FechaRatificado = models.DateField()
    FechaConciliacion = models.DateField()
    rCUFE= models.CharField(max_length=15)
    rHora= models.CharField(max_length=15)
    regResolucion= models.IntegerField()
    rEnviado= models.SmallIntegerField()
    EstadoAuditoria = models.SmallIntegerField()
    FechaAnulada= models.DateField()
    AnuladaPor= models.IntegerField()
    QRCode= models.BinaryField()
    MedioPago= models.SmallIntegerField()
     
    class Meta:
        
        db_table = 'facturas'
        app_label = 'datosipsndx'
        managed = False


class ArchivoFacturacion(models.Model):
    IdArchivo = models.AutoField(primary_key=True)
    Admision = models.ForeignKey(Admisiones, on_delete=models.CASCADE)
    Tipo = models.CharField(max_length=50)
    RutaArchivo = models.FileField(upload_to='GeDocumental/archivosFacturacion', max_length=255, blank=True, null=True)
    
        
    NumeroAdmision = models.IntegerField() 
    FechaCreacionArchivo = models.DateField()

    def save(self, *args, **kwargs):
        # Actualizar el número de admisión antes de guardar
        self.NumeroAdmision = self.Admision.Consecutivo
        super(ArchivoFacturacion, self).save(*args, **kwargs)

    class Meta:
        db_table = 'archivos'
        app_label = 'datosipsndx'
        managed = True

#############################################
        