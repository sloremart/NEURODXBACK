
from django.utils import timezone
from django.utils.timezone import make_aware
import shutil
from django.db.models import Q, Max
from PyPDF2 import PdfMerger
from urllib.parse import unquote
from django.db import IntegrityError, transaction
from django.db.models.functions import TruncDate
from django.db import connections
from django.http import HttpRequest, HttpResponse, JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import api_view
from gedocumental.modelsFacturacion import Admisiones
from gedocumental.utils.codigoentidad import obtener_tipos_documentos_por_entidad
from login.models import CustomUser
from .serializers import   ArchivoFacturacionSerializer, ObservacionSinArchivoSerializer,  RevisionCuentaMedicaSerializer
from django.http import Http404
from .models import ArchivoFacturacion, AuditoriaCuentasMedicas, ObservacionSinArchivo, ObservacionesArchivos
from django.conf import settings
import os
from django.db.models import Count
from django.views.decorators.http import require_GET
from datetime import datetime, timedelta
from urllib.parse import unquote
from rest_framework.permissions import AllowAny
from datetime import date
from rest_framework.decorators import api_view, permission_classes





class GeDocumentalView(APIView):
    def get(self, request, consecutivo, format=None):
        with connections['datosipsndx'].cursor() as cursor:
            # Consulta para obtener la información de la admisión
            query_admision = '''
                SELECT Consecutivo, IdPaciente, CodigoEntidad, NombreResponsable, FacturaNo, tRegimen
                FROM admisiones
                WHERE Consecutivo = %s
            '''
            cursor.execute(query_admision, [consecutivo])
            admision_data = cursor.fetchone()

            if admision_data:
                # Consulta para obtener el prefijo de la factura asociada a la admisión
                query_factura = 'SELECT Prefijo FROM facturas WHERE AdmisionNo = %s'
                cursor.execute(query_factura, [consecutivo])
                factura_info = cursor.fetchone()
                codigo_entidad = admision_data[2]
                tipos_documentos = obtener_tipos_documentos_por_entidad(codigo_entidad)

                query_tipo_afiliacion = '''
                    SELECT TipoAfiliacion
                    FROM pacientes
                    WHERE IDPaciente = %s
                '''
                cursor.execute(query_tipo_afiliacion, [admision_data[1]])
                tipo_afiliacion = cursor.fetchone()


                
                transformed_data = {
                    'Consecutivo': admision_data[0],
                    'IdPaciente': admision_data[1],
                    'CodigoEntidad': admision_data[2],
                    'NombreResponsable': admision_data[3],
                    'FacturaNo': admision_data[4],
                    'tRegimen': admision_data[5] if len(admision_data) > 5 else None,
                    'Prefijo': factura_info[0] if factura_info else None,
                    'TiposDocumentos': tipos_documentos,
                    'TipoAfiliacion': tipo_afiliacion[0] if tipo_afiliacion else None
                }

                response_data = {
                    "success": True,
                    "detail": f"Información de la admisión con consecutivo {consecutivo}",
                    "data": transformed_data
                }

                return Response(response_data, status=status.HTTP_200_OK)
            else:
                response_data = {
                    "success": False,
                    "detail": f"No se encontró información para la admisión con consecutivo {consecutivo}",
                    "data": None
                }

                return Response(response_data, status=status.HTTP_404_NOT_FOUND)


              
class ArchivoUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, consecutivo, format=None):
        try:
            user_id = request.data.get('userId')
            regimen = request.data.get('regimen')  # Obtener el campo regimen del request
            tipo_documento = request.data.get('tipoDocumentos')

            # Obtener la admisión
            admision = Admisiones.objects.using('datosipsndx').get(Consecutivo=consecutivo)

            # Check for existing files of the same type for the same admission
            existing_files = ArchivoFacturacion.objects.filter(Admision_id=consecutivo, Tipo=tipo_documento)
            if existing_files.exists():
                response_data = {
                    "success": False,
                    "detail": f"Ya existe un archivo del mismo tipo ({tipo_documento}) para la admisión con consecutivo {consecutivo}.",
                    "data": None
                }
                return JsonResponse(response_data, status=status.HTTP_400_BAD_REQUEST)

            # Obtener la fecha de creación desde la base de datos
            fecha_creacion_antares = admision.FechaCreado.date()  # Obtener solo la parte de la fecha

            # Crear el directorio para guardar los archivos
            folder_path = os.path.join(settings.MEDIA_ROOT, 'gdocumental', 'archivosFacturacion', str(admision.Consecutivo))
            os.makedirs(folder_path, exist_ok=True)

            archivos = request.FILES.getlist('files')
            archivos_guardados = []

            for archivo in archivos:
                # Guardar el archivo físicamente
                archivo_path = os.path.join(folder_path, archivo.name)
                with open(archivo_path, 'wb') as file:
                    for chunk in archivo.chunks():
                        file.write(chunk)

                # Construir la ruta relativa del archivo
                ruta_relativa = os.path.join('gdocumental', 'archivosFacturacion', str(admision.Consecutivo), archivo.name)

                fecha_creacion_archivo = datetime.now().replace(second=0, microsecond=0)
                archivo_obj = ArchivoFacturacion(
                    Admision_id=admision.Consecutivo,
                    Tipo=tipo_documento,
                    RutaArchivo=ruta_relativa,
                    FechaCreacionArchivo=fecha_creacion_archivo,  # Guardar solo la fecha
                    FechaCreacionAntares=fecha_creacion_antares,  # Asignar solo la fecha de creación de Antares
                    Usuario_id=user_id,
                    Regimen=regimen  # Asignar el campo regimen
                )
                archivo_obj.NumeroAdmision = admision.Consecutivo
                archivo_obj.save()
                archivos_guardados.append({
                    "id": archivo_obj.IdArchivo,
                    "ruta": archivo_obj.RutaArchivo.url
                })

            response_data = {
                "success": True,
                "detail": f"Archivos guardados exitosamente para la admisión con consecutivo {consecutivo}",
                "data": archivos_guardados
            }

            return JsonResponse(response_data, status=status.HTTP_201_CREATED)

        except Admisiones.DoesNotExist:
            response_data = {
                "success": False,
                "detail": f"No se encontró la admisión con consecutivo {consecutivo}",
                "data": None
            }
            return JsonResponse(response_data, status=status.HTTP_404_NOT_FOUND)

##### EDICION DE ARCHIVOS ##########

class ArchivoEditView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def put(self, request, consecutivo, archivo_id, format=None):
        try:
            admision = Admisiones.objects.using('datosipsndx').get(Consecutivo=consecutivo)
            archivo = ArchivoFacturacion.objects.get(IdArchivo=archivo_id, Admision_id=admision.Consecutivo)
            if 'archivo' in request.FILES:
                archivo_nuevo = request.FILES['archivo']

                # Obtener la ruta de la carpeta actual del archivo
                carpeta_actual = os.path.dirname(archivo.RutaArchivo.path)
                
                # Eliminar el archivo antiguo
                archivo.RutaArchivo.delete(save=False)

                # Guardar el archivo nuevo en la misma carpeta
                archivo_nombre_nuevo = os.path.join(carpeta_actual, archivo_nuevo.name)
                with open(archivo_nombre_nuevo, 'wb') as file:
                    for chunk in archivo_nuevo.chunks():
                        file.write(chunk)

                archivo.NombreArchivo = archivo_nuevo.name 
                archivo.RutaArchivo = archivo_nombre_nuevo  
                archivo.save(update_fields=['NombreArchivo', 'RutaArchivo'])  

                auditoria = AuditoriaCuentasMedicas.objects.get(AdmisionId=archivo.Admision_id)
                auditoria.FechaCargueArchivo = timezone.now()
                auditoria.save(update_fields=['FechaCargueArchivo'])

            response_data = {
                "success": True,
                "detail": f"Archivo {archivo_id} editado exitosamente para la admisión con consecutivo {consecutivo}",
                "data": None
            }

            return JsonResponse(response_data, status=status.HTTP_200_OK)

        except Admisiones.DoesNotExist:
            response_data = {
                "success": False,
                "detail": f"No se encontró la admisión con consecutivo {consecutivo}",
                "data": None
            }
            return JsonResponse(response_data, status=status.HTTP_404_NOT_FOUND)

        except ArchivoFacturacion.DoesNotExist:
            response_data = {
                "success": False,
                "detail": f"No se encontró el archivo con ID {archivo_id} asociado a la admisión con consecutivo {consecutivo}",
                "data": None
            }
            return JsonResponse(response_data, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return JsonResponse({
                "success": False,
                "detail": f"Error desconocido al editar el archivo: {e}",
                "data": None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        
      
      

## BUSCAR ARCHIVOS PARA RADICAR###   
############# archivos ############################
@api_view(['GET'])
def archivos_por_admision_radicacion(request, numero_admision):
    try:
        archivos = ArchivoFacturacion.objects.filter(NumeroAdmision=numero_admision)
        serializer = ArchivoFacturacionSerializer(archivos, many=True)
        
        response_data = {
            "success": True,
            "detail": f"Archivos encontrados para la admisión con número {numero_admision}",
            "data": serializer.data
        }

        return Response(response_data, status=status.HTTP_200_OK)

    except ArchivoFacturacion.DoesNotExist:
        response_data = {
            "success": False,
            "detail": f"No se encontraron archivos para la admisión con número {numero_admision}",
            "data": None
        }

        return Response(response_data, status=status.HTTP_404_NOT_FOUND)
    

@api_view(['GET'])
def archivos_por_admision(request, numero_admision):
    try:
        archivos = ArchivoFacturacion.objects.filter(NumeroAdmision=numero_admision)
        observaciones = ObservacionSinArchivo.objects.filter(AdmisionId=numero_admision)
        
        archivo_serializer = ArchivoFacturacionSerializer(archivos, many=True)
        observacion_serializer = ObservacionSinArchivoSerializer(observaciones, many=True)
        
        response_data = {
            "success": True,
            "detail": f"Archivos encontrados para la admisión con número {numero_admision}",
            "data": {
                "archivos": archivo_serializer.data,
                "observaciones": observacion_serializer.data
            }
        }
        print(f"archivos_por_admision response_data: {response_data}")
        return Response(response_data, status=status.HTTP_200_OK)

    except ArchivoFacturacion.DoesNotExist:
        response_data = {
            "success": False,
            "detail": f"No se encontraron archivos para la admisión con número {numero_admision}",
            "data": None
        }
        print(f"archivos_por_admision response_data: {response_data}")
        return Response(response_data, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        print(f"archivos_por_admision Exception: {str(e)}")
        return Response({"success": False, "detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
      

## visualizar archivo###

@api_view(['GET'])
def downloadFile(request, id_archivo):
    try:
        
        archivo = ArchivoFacturacion.objects.get(IdArchivo=id_archivo)       
        archivo_path = os.path.join(settings.ROOT_PATH_FILES_STORAGE, settings.MEDIA_ROOT, str(archivo.RutaArchivo))

        print("Ruta del archivo:", archivo_path)

        # Verificar si el archivo realmente existe
        if not os.path.exists(archivo_path):
            raise Http404("El archivo no existe")

        #  modo binario
        with open(archivo_path, 'rb') as file:
            # Lee el contenido del archivo
            file_content = file.read()

        # Crea una respuesta de archivo con el contenido leído
        response = HttpResponse(file_content, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename=' + os.path.basename(archivo_path)
        return response

    except FileNotFoundError:
        raise Http404("El archivo no se encontró en el sistema de archivos.")
    except Exception as e:
        print(f"Error al descargar el archivo: {e}")
        raise Http404("Ocurrió un error al intentar descargar el archivo.")
    except ArchivoFacturacion.DoesNotExist:
        raise Http404("El archivo no existe")
    finally:
      
        if 'file' in locals() and not file.closed:
            file.close()


######## REVISION CUENTAS MEDICAS - TALENTO HUMANO #######
         
class AdmisionCuentaMedicaView(APIView):
    def post(self, request, *args, **kwargs):
        print("Datos recibidos en la solicitud:", request.data)
        data = request.data
        archivos = data.get('archivos', [])
        consecutivo_consulta = data.get('consecutivoConsulta')
        usuario_cuentas_medicas_id = request.data.get('UsuarioCuentasMedicas')

        try:
            with transaction.atomic():
                for archivo_data in archivos:
                    archivo_id = archivo_data.get('IdArchivo')
                    try:
                        archivo_existente = ArchivoFacturacion.objects.get(IdArchivo=archivo_id)
                        archivo_serializer = RevisionCuentaMedicaSerializer(archivo_existente, data=archivo_data, partial=True)

                        if archivo_serializer.is_valid():
                            archivo_obj = archivo_serializer.save()
                            # Si hay observación o RevisionPrimera es True, guarda UsuarioCuentasMedicas y FechaRevisionPrimera
                            observacion = archivo_data.get('Observacion')
                            if observacion or archivo_data.get('RevisionPrimera', False):
                                archivo_obj.UsuarioCuentasMedicas_id = usuario_cuentas_medicas_id
                                archivo_obj.FechaRevisionPrimera = date.today()  # Establecer la fecha de revisión
                                archivo_obj.save()
                                print(f"UsuarioCuentasMedicas asignado: {archivo_obj.UsuarioCuentasMedicas_id}")
                                print(f"FechaRevisionPrimera asignada: {archivo_obj.FechaRevisionPrimera}")

                            if observacion:
                                observacion_obj = ObservacionesArchivos.objects.create(
                                    IdArchivo=archivo_existente,
                                    Descripcion=observacion,
                                    ObservacionCuentasMedicas=True  
                                )
                                print("Observación creada:", observacion_obj)
                        else:
                            errors = archivo_serializer.errors
                            return Response({"success": False, "message": "Error de validación en los datos del archivo", "error_details": errors}, status=status.HTTP_400_BAD_REQUEST)

                    except ArchivoFacturacion.DoesNotExist:
                        return Response({"success": False, "message": f"Archivo con ID {archivo_id} no encontrado"}, status=status.HTTP_404_NOT_FOUND)

                admision_ids = [archivo_data.get('Admision_id') for archivo_data in archivos]
                
                auditoria_cuentas_medicas = AuditoriaCuentasMedicas.objects.filter(AdmisionId__in=admision_ids)
                todos_revision_primera_true = all(archivo_data.get('RevisionPrimera', False) for archivo_data in archivos)
                auditoria_cuentas_medicas.update(RevisionCuentasMedicas=todos_revision_primera_true)

                return Response({"success": True, "message": "Datos guardados correctamente"}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"success": False, "message": "Error interno del servidor", "error_details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
######TESORERIA 
class AdmisionTesoreriaView(APIView):
    def post(self, request, *args, **kwargs):
        print("Datos recibidos en la solicitud:", request.data)
        data = request.data
        archivos = data.get('archivos', [])
        consecutivo_consulta = data.get('consecutivoConsulta')
        usuario_tesoreria_id = request.data.get('UsuariosTesoreria')

        try:
            with transaction.atomic():
                for archivo_data in archivos:
                    archivo_id = archivo_data.get('IdArchivo')
                    try:
                        archivo_existente = ArchivoFacturacion.objects.get(IdArchivo=archivo_id)
                        archivo_serializer = RevisionCuentaMedicaSerializer(archivo_existente, data=archivo_data, partial=True)

                        if archivo_serializer.is_valid():
                            archivo_obj = archivo_serializer.save()
                            # Si hay observación o RevisionSegunda es True, guarda UsuariosTesoreria
                            observacion = archivo_data.get('Observacion')
                            if observacion or archivo_data.get('RevisionSegunda', False):
                                archivo_obj.UsuariosTesoreria_id = usuario_tesoreria_id
                                archivo_obj.save()
                                print(f"UsuariosTesoreria asignado: {archivo_obj.UsuariosTesoreria_id}")

                            if observacion:
                                observacion_obj = ObservacionesArchivos.objects.create(
                                    IdArchivo=archivo_existente,
                                    Descripcion=observacion,
                                    ObservacionTesoreria=True  # Se establece en True si es para tesorería
                                )
                                print("Observación creada:", observacion_obj)
                        else:
                            errors = archivo_serializer.errors
                            return Response({"success": False, "message": "Error de validación en los datos del archivo", "error_details": errors}, status=status.HTTP_400_BAD_REQUEST)

                    except ArchivoFacturacion.DoesNotExist:
                        return Response({"success": False, "message": f"Archivo con ID {archivo_id} no encontrado"}, status=status.HTTP_404_NOT_FOUND)

                todos_revision_segunda_true = all(archivo_data.get('RevisionSegunda', False) for archivo_data in archivos)
                print("Todos los archivos tienen RevisionSegunda en True:", todos_revision_segunda_true)

                if todos_revision_segunda_true:
                    auditoria_cuentas_medicas = AuditoriaCuentasMedicas.objects.filter(AdmisionId=consecutivo_consulta)
                    print("Registros de AuditoriaCuentasMedicas antes de la actualización:", auditoria_cuentas_medicas)

                    auditoria_cuentas_medicas.update(RevisionTesoreria=True)
                    print("Registros de AuditoriaCuentasMedicas después de la actualización:", auditoria_cuentas_medicas)

                return Response({"success": True, "message": "Datos guardados correctamente"}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"success": False, "message": "Error interno del servidor", "error_details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        
####### FILTRO DE ADMISIONES Y ARCHIVOS POR FECHA ####


class FiltroAuditoriaCuentasMedicas(APIView):
    def get(self, request):
        user_id = request.query_params.get('user_id', None)
        fecha_inicio_str = request.query_params.get('FechaInicio', None)
        fecha_fin_str = request.query_params.get('FechaFin', None)
        revision_cuentas_medicas = request.query_params.get('RevisionCuentasMedicas', None)
        codigo_entidad = request.query_params.get('CodigoEntidad', None)

        # Obtener todos los archivos de facturación, y luego aplicar filtros si hay parámetros
        archivos_facturacion = ArchivoFacturacion.objects.all()

        # Si 'user_id' está presente, aplicar el filtro por 'Usuario_id'
        if user_id:
            archivos_facturacion = archivos_facturacion.filter(Usuario_id=user_id)

        # Convertir fechas de inicio y fin a objetos datetime
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d') if fecha_inicio_str else None
            fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d') if fecha_fin_str else None
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

        # Filtrar archivos por rango de fechas si están presentes
        if fecha_inicio and fecha_fin:
            archivos_facturacion = archivos_facturacion.filter(
                (Q(FechaCreacionAntares__gte=fecha_inicio) & Q(FechaCreacionAntares__lte=fecha_fin)) |
                (Q(FechaCreacionArchivo__gte=fecha_inicio) & Q(FechaCreacionArchivo__lte=fecha_fin))
            )

        # Filtrar por 'RevisionCuentasMedicas' si está presente
        if revision_cuentas_medicas is not None:
            if revision_cuentas_medicas == "0":
                archivos_facturacion = archivos_facturacion.filter(RevisionPrimera=False)
            elif revision_cuentas_medicas == "1":
                archivos_facturacion = archivos_facturacion.filter(RevisionPrimera=True)

        # Obtener las admisiones asociadas
        admision_ids = archivos_facturacion.values_list('Admision_id', flat=True).distinct()
        queryset = AuditoriaCuentasMedicas.objects.filter(AdmisionId__in=admision_ids)

        response_data = []

        # Ejecutar la consulta a la base de datos externa
        with connections['datosipsndx'].cursor() as cursor:
            for auditoria in queryset:
                cursor.execute('''
                    SELECT Consecutivo, IdPaciente, CodigoEntidad, NombreResponsable, FacturaNo, CedulaResponsable
                    FROM admisiones
                    WHERE Consecutivo = %s
                ''', [auditoria.AdmisionId])
                admision_data = cursor.fetchone()

                if admision_data:
                    # Filtrar por 'CodigoEntidad' si está presente
                    if not codigo_entidad or codigo_entidad == admision_data[2]:
                        archivo_facturacion = archivos_facturacion.filter(Admision_id=auditoria.AdmisionId).first()

                        data = {
                            'AdmisionId': auditoria.AdmisionId,
                            'FechaCreacion': auditoria.FechaCreacion.strftime('%Y-%m-%d'),
                            'FechaCargueArchivo': auditoria.FechaCargueArchivo.strftime('%Y-%m-%d'),
                            'Observacion': auditoria.Observacion,
                            'RevisionCuentasMedicas': auditoria.RevisionCuentasMedicas,
                            'RevisionTesoreria': auditoria.RevisionTesoreria,
                            'Consecutivo': admision_data[0],
                            'IdPaciente': admision_data[1],
                            'CodigoEntidad': admision_data[2],
                            'NombreResponsable': admision_data[3],
                            'CedulaResponsable': admision_data[4],
                            'FacturaNo': admision_data[5] if len(admision_data) > 4 else None,
                            'FechaCreacionAntares': archivo_facturacion.FechaCreacionAntares.strftime('%Y-%m-%d') if archivo_facturacion and archivo_facturacion.FechaCreacionAntares else None,
                            'FechaCreacionArchivo': archivo_facturacion.FechaCreacionArchivo.strftime('%Y-%m-%d') if archivo_facturacion and archivo_facturacion.FechaCreacionArchivo else None
                        }
                        response_data.append(data)

        return Response(response_data, status=200)







class CodigoListView(APIView):
    def get(self, request, format=None):
        codigos = [
    'SAN01', 'SAN02', 'POL11', 'PML01', 'COM01', 'SAL01', 'CAP01', 'DM02', 'EQV01', 
    'PAR01', 'CHM01', 'CHM02', 'COL01', 'MES01', 'UNA02', 'MUL01', 'par01', 'FOM01', 
    'IPSOL1', 'AIR01', 'AXA01', 'POL13', 'BOL01', 'CON01', 'SUR01', 'MUN01', 'ADR01', 
    'MAP01', 'LIB01', 'EQU01', 'EST01', 'BOL02', 'SOL02'
]
        return Response(codigos)
    

### FILTRO QUE TRAE LAS ADM QUE TIENEN OBSER CM  ######

def admisiones_con_observaciones_por_usuario(request, usuario_id):
    try:
        # Filtrar registros de ObservacionesArchivos para el usuario dado con ObservacionCuentasMedicas
        observaciones = ObservacionesArchivos.objects.filter(
            IdArchivo__Usuario_id=usuario_id,
            ObservacionCuentasMedicas=True
        )

        # Obtener los IDs de las admisiones con las observaciones
        admisiones_ids = observaciones.values_list('IdArchivo__Admision_id', flat=True).distinct()

        admisiones_data = []
        with connections['datosipsndx'].cursor() as cursor_datosipsndx, connections['default'].cursor() as cursor_neurodx:
            for admision_id in admisiones_ids:
                # Verificar que al menos un archivo asociado tenga RevisionPrimera=False
                archivos_admision = ArchivoFacturacion.objects.filter(Admision_id=admision_id)
                if not archivos_admision.filter(RevisionPrimera=False).exists():
                    continue

                # Verificar que la admisión tenga RevisionCuentasMedicas=False en AuditoriaCuentasMedicas
                if not AuditoriaCuentasMedicas.objects.filter(AdmisionId=admision_id, RevisionCuentasMedicas=False).exists():
                    continue

                # Obtener datos de la admisión
                query_admision = '''
                    SELECT Consecutivo, IdPaciente, CodigoEntidad, NombreResponsable, FacturaNo
                    FROM admisiones
                    WHERE Consecutivo = %s
                '''
                cursor_datosipsndx.execute(query_admision, [admision_id])
                admision_data = cursor_datosipsndx.fetchone()

                if admision_data:
                    # Consulta para obtener el prefijo de la factura asociada a la admisión
                    query_factura = 'SELECT Prefijo FROM facturas WHERE AdmisionNo = %s'
                    cursor_datosipsndx.execute(query_factura, [admision_id])
                    factura_info = cursor_datosipsndx.fetchone()

                    prefijo = factura_info[0] if factura_info else ''
                    numero_factura = admision_data[4] if len(admision_data) > 4 else ''
                    factura_completa = f"{prefijo}{numero_factura}"

                    # Obtener la fecha más reciente de observación para la admisión
                    fecha_reciente_observacion = ObservacionesArchivos.objects.filter(
                        IdArchivo__Admision_id=admision_id
                    ).aggregate(max_fecha=Max('FechaObservacion'))['max_fecha']

                    # Obtener el campo Modificado1 de la tabla Archivos desde la base de datos 'default'
                    query_modificado = '''
                        SELECT Modificado1
                        FROM archivos
                        WHERE Admision_id = %s
                    '''
                    cursor_neurodx.execute(query_modificado, [admision_id])
                    modificado_info = cursor_neurodx.fetchone()
                    modificado1 = modificado_info[0] if modificado_info else ''

                    transformed_data = {
                        'Consecutivo': admision_data[0],
                        'IdPaciente': admision_data[1],
                        'CodigoEntidad': admision_data[2],
                        'NombreResponsable': admision_data[3],
                        'FacturaNo': factura_completa,
                        'FechaRecienteObservacion': fecha_reciente_observacion,
                        'Modificado1': modificado1
                    }
                    admisiones_data.append(transformed_data)

        response_data = {
            "success": True,
            "detail": f"Admisiones con observaciones encontradas para el usuario con ID {usuario_id}",
            "data": admisiones_data
        }

        return JsonResponse(response_data, status=200)

    except Exception as e:
        response_data = {
            "success": False,
            "detail": "Error interno del servidor",
            "error_details": str(e)
        }

        return JsonResponse(response_data, status=500)
#####FILTRO QUE TRAE LAS ADM QUE TIENEN OBSER CM Y TESOERIA###################
def admisiones_con_revision_tesoreria(request, usuario_id):
    try:
        # Filtrar registros de ObservacionesArchivos para el usuario dado
        observaciones = ObservacionesArchivos.objects.filter(
            IdArchivo__Usuario_id=usuario_id,
            ObservacionTesoreria=True
        )

        # Obtener los Ids de las admisiones con las observaciones
        admisiones_ids = observaciones.values_list('IdArchivo__Admision_id', flat=True).distinct()

        # Filtrar registros de AuditoriaCuentasMedicas con la condición especificada (solo RevisionTesoreria)
        admisiones_con_observaciones = AuditoriaCuentasMedicas.objects.filter(
            AdmisionId__in=admisiones_ids,
            RevisionTesoreria=False  # Solo filtramos por RevisionTesoreria
        )

        admisiones_data = []
        with connections['datosipsndx'].cursor() as cursor:
            for auditoria in admisiones_con_observaciones:
                # Verificar que al menos un archivo asociado tenga RevisionSegunda=False y ObservacionTesoreria=True
                archivos_admision = ArchivoFacturacion.objects.filter(Admision_id=auditoria.AdmisionId)
                if not archivos_admision.filter(RevisionSegunda=False, Observaciones__ObservacionTesoreria=True).exists():
                    continue

                # Obtener datos de la admisión
                query_admision = '''
                    SELECT Consecutivo, IdPaciente, CodigoEntidad, NombreResponsable, FacturaNo
                    FROM admisiones
                    WHERE Consecutivo = %s
                '''
                cursor.execute(query_admision, [auditoria.AdmisionId])
                admision_data = cursor.fetchone()

                if admision_data:
                    # Consulta para obtener el prefijo de la factura asociada a la admisión
                    query_factura = 'SELECT Prefijo FROM facturas WHERE AdmisionNo = %s'
                    cursor.execute(query_factura, [auditoria.AdmisionId])
                    factura_info = cursor.fetchone()

                    prefijo = factura_info[0] if factura_info else ''
                    numero_factura = admision_data[4] if len(admision_data) > 4 else ''
                    factura_completa = f"{prefijo}{numero_factura}"

                    transformed_data = {
                        'Consecutivo': admision_data[0],
                        'IdPaciente': admision_data[1],
                        'CodigoEntidad': admision_data[2],
                        'NombreResponsable': admision_data[3],
                        'FacturaNo': factura_completa,
                    }
                    admisiones_data.append(transformed_data)

        response_data = {
            "success": True,
            "detail": f"Admisiones con revisión de tesorería pendiente encontradas para el usuario con ID {usuario_id}",
            "data": admisiones_data
        }

        return JsonResponse(response_data, status=200)

    except AuditoriaCuentasMedicas.DoesNotExist:
        response_data = {
            "success": False,
            "detail": f"No se encontraron admisiones con revisión de tesorería pendiente para el usuario con ID {usuario_id}",
            "data": None
        }

        return JsonResponse(response_data, status=404)

    except Exception as e:
        response_data = {
            "success": False,
            "detail": "Error interno del servidor",
            "error_details": str(e)
        }

        return JsonResponse(response_data, status=500)
###### FILTRO TESORERIA #####
class FiltroTesoreria(APIView):
    def get(self, request):
        user_id = request.query_params.get('user_id', None)
        fecha_creacion_antares_str = request.query_params.get('FechaCreacionAntares', None)
        fecha_creacion_archivo_str = request.query_params.get('FechaCreacionArchivo', None)
        revision_cuentas_medicas = request.query_params.get('RevisionCuentasMedicas', None)
        revision_tesoreria = request.query_params.get('RevisionTesoreria', None)
        codigo_entidad = request.query_params.get('CodigoEntidad', None)

        if not user_id:
            return Response({"error": "user_id is required"}, status=400)

        archivos_facturacion = ArchivoFacturacion.objects.filter(Usuario_id=user_id)

        if fecha_creacion_antares_str:
            try:
                fecha_creacion_antares = datetime.strptime(fecha_creacion_antares_str, '%Y-%m-%d').date()
                archivos_facturacion = archivos_facturacion.filter(FechaCreacionAntares__date=fecha_creacion_antares)
            except ValueError:
                return Response({'error': 'Formato de fecha inválido para FechaCreacionAntares, debe ser YYYY-MM-DD'}, status=400)

        if fecha_creacion_archivo_str:
            try:
                fecha_creacion_archivo = datetime.strptime(fecha_creacion_archivo_str, '%Y-%m-%d').date()
                archivos_facturacion = archivos_facturacion.filter(FechaCreacionArchivo__date=fecha_creacion_archivo)
            except ValueError:
                return Response({'error': 'Formato de fecha inválido para FechaCreacionArchivo, debe ser YYYY-MM-DD'}, status=400)

        # Filtro por defecto: solo traer donde RevisionPrimera es True
        archivos_facturacion = archivos_facturacion.filter(RevisionPrimera=True)

        admision_ids = archivos_facturacion.values_list('Admision_id', flat=True).distinct()
        queryset = AuditoriaCuentasMedicas.objects.filter(AdmisionId__in=admision_ids)

        if revision_tesoreria is not None:
            revision_tesoreria = bool(int(revision_tesoreria))
            queryset = queryset.filter(RevisionTesoreria=revision_tesoreria)

        response_data = []

        try:
            with connections['datosipsndx'].cursor() as cursor:
                for auditoria in queryset:
                    cursor.execute('''
                        SELECT Consecutivo, IdPaciente, CodigoEntidad, NombreResponsable, FacturaNo, TipoAfiliado
                        FROM admisiones
                        WHERE Consecutivo = %s
                    ''', [auditoria.AdmisionId])
                    admision_data = cursor.fetchone()

                    if admision_data:
                        if not codigo_entidad or codigo_entidad == admision_data[2]:
                            data = {
                                'AdmisionId': auditoria.AdmisionId,
                                'FechaCreacion': auditoria.FechaCreacion.strftime('%Y-%m-%d'),
                                'FechaCargueArchivo': auditoria.FechaCargueArchivo.strftime('%Y-%m-%d'),
                                'Observacion': auditoria.Observacion,
                                'RevisionCuentasMedicas': auditoria.RevisionCuentasMedicas,
                                'RevisionTesoreria': auditoria.RevisionTesoreria,
                                'Consecutivo': admision_data[0],
                                'IdPaciente': admision_data[1],
                                'CodigoEntidad': admision_data[2],
                                'NombreResponsable': admision_data[3],
                                'FacturaNo': admision_data[4] if len(admision_data) > 5 else None,
                            }
                            response_data.append(data)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

        # Filtrar la respuesta para que solo incluya entradas donde RevisionCuentasMedicas es True
        response_data = [item for item in response_data if item['RevisionCuentasMedicas']]

        return Response(response_data, status=200)


###### RADICACION - CUENTAS MEDICAS #####
@api_view(['GET'])
@permission_classes([AllowAny])  # Permitir acceso a cualquier usuario
def radicar_compensar_view(request, numero_admision, idusuario):
    try:
        # Verificar si el idusuario existe en la base de datos y obtener el nombre de usuario
        try:
            user = CustomUser.objects.get(id=idusuario)
            nombre_usuario = user.username  # Obtener el nombre del usuario para usar en la carpeta
            
            # Sanitizar el nombre del usuario si es necesario
            nombre_usuario = "".join(c for c in nombre_usuario if c.isalnum() or c in (' ', '.', '_')).rstrip()
            print(f"Nombre del usuario sanitizado para crear carpeta: {nombre_usuario}")
        except CustomUser.DoesNotExist:
            response_data = {
                "success": False,
                "detail": "Usuario no encontrado."
            }
            return JsonResponse(response_data, status=404)

        # Verificar si ya está radicado
        archivos_a_verificar = ArchivoFacturacion.objects.filter(Admision_id=numero_admision)
        if archivos_a_verificar.exists() and archivos_a_verificar.filter(Radicado=True).exists():
            response_data = {
                "success": False,
                "detail": f"La admisión con número {numero_admision} ya está radicada."
            }
            return JsonResponse(response_data, status=400)

        # Obtener datos de la admisión
        admision_response = GeDocumentalView().get(request._request, consecutivo=numero_admision)
        if admision_response.status_code != 200:
            return admision_response

        admision_data = admision_response.data.get('data')
        factura_numero = admision_data.get('FacturaNo')

        if not factura_numero:
            response_data = {
                "success": False,
                "detail": "La admisión no tiene el número de factura."
            }
            return JsonResponse(response_data, status=400)

        # Obtener el régimen desde el primer archivo de facturación relacionado
        archivo_facturacion = ArchivoFacturacion.objects.filter(Admision_id=numero_admision).first()
        if not archivo_facturacion:
            response_data = {
                "success": False,
                "detail": f"No se encontró el archivo de facturación para la admisión {numero_admision}"
            }
            return JsonResponse(response_data, status=404)

        regimen = archivo_facturacion.Regimen
        if regimen == 'C':
            carpeta_tipo_archivo = 'CONTRIBUTIVO'
        elif regimen == 'S':
            carpeta_tipo_archivo = 'SUBSIDIADO'
        else:
            response_data = {
                "success": False,
                "detail": f"Régimen desconocido: {regimen}"
            }
            return JsonResponse(response_data, status=400)

        # Crear la ruta base para las carpetas utilizando el nombre del usuario
        fecha_actual = datetime.now().strftime('%Y%m%d')
        carpeta_usuario = os.path.join(settings.MEDIA_ROOT, 'gdocumental', 'Radicacion', 'COMPENSAR', fecha_actual, carpeta_tipo_archivo, nombre_usuario)
        if not os.path.exists(carpeta_usuario):
            try:
                os.makedirs(carpeta_usuario)
                print(f"Carpeta creada exitosamente: {carpeta_usuario}")
            except Exception as e:
                response_data = {
                    "success": False,
                    "detail": f"Error al crear la carpeta para el usuario: {str(e)}"
                }
                return JsonResponse(response_data, status=500)

        # Obtener archivos de la admisión
        archivos_response = archivos_por_admision_radicacion(request._request, numero_admision)
        if archivos_response.status_code != 200:
            return archivos_response

        archivos_data = archivos_response.data.get('data', [])
        archivos_requeridos = ['FACTURA', 'COMPROBANTE', 'ORDEN', 'RESULTADO', 'AUTORIZACION', 'HCNEURO']
        archivos_faltantes = []

        # Verificar la existencia de todos los archivos requeridos antes de copiar
        for archivo in archivos_data:
            tipo_archivo = archivo.get('Tipo')
            if tipo_archivo in archivos_requeridos:
                ruta_origen_relative = archivo.get('RutaArchivo')
                ruta_origen_relative = unquote(ruta_origen_relative)  # Decodificar URL

                # Normalizar y formar ruta de origen
                if ruta_origen_relative.startswith('C:'):
                    ruta_origen_relative = ruta_origen_relative[2:]

                ruta_origen_relative = ruta_origen_relative.replace("\\", "/").replace(settings.MEDIA_URL.lstrip('/'), '').lstrip('/')
                ruta_origen = os.path.normpath(os.path.join(settings.MEDIA_ROOT, ruta_origen_relative))

                print(f"Verificando existencia de archivo: {ruta_origen} (Tipo: {tipo_archivo})")

                # Comprobación adicional de permisos
                if not os.path.exists(ruta_origen):
                    archivos_faltantes.append(tipo_archivo)
                elif not os.access(ruta_origen, os.R_OK):
                    archivos_faltantes.append(f"{tipo_archivo} (no hay permisos de lectura)")

        if archivos_faltantes:
            response_data = {
                "success": False,
                "detail": f"Faltan los siguientes archivos requeridos: {', '.join(archivos_faltantes)}"
            }
            return JsonResponse(response_data, status=400)

        archivos_copiados = []
        archivos_fallidos = []

        for archivo in archivos_data:
            tipo_archivo = archivo.get('Tipo')
            if tipo_archivo not in archivos_requeridos:
                continue

            ruta_origen_relative = archivo.get('RutaArchivo')
            ruta_origen_relative = unquote(ruta_origen_relative)  # Decodificar URL

            # Normalizar y formar ruta de origen
            if ruta_origen_relative.startswith('C:'):
                ruta_origen_relative = ruta_origen_relative[2:]

            ruta_origen_relative = ruta_origen_relative.replace("\\", "/").replace(settings.MEDIA_URL.lstrip('/'), '').lstrip('/')
            ruta_origen = os.path.normpath(os.path.join(settings.MEDIA_ROOT, ruta_origen_relative))

            print(f"Ruta de origen relativa: {ruta_origen_relative}")
            print(f"Ruta de origen absoluta: {ruta_origen}")

            # Verificar la existencia del archivo
            if not os.path.exists(ruta_origen):
                print(f"Archivo no encontrado: {ruta_origen}")
                archivos_fallidos.append(ruta_origen)
                continue

            # Formar la ruta de destino
            nombre_archivo = f"{tipo_archivo}{factura_numero}.pdf"
            ruta_destino = os.path.join(carpeta_usuario, nombre_archivo)
            try:
                shutil.copy(ruta_origen, ruta_destino)
                archivos_copiados.append(ruta_destino)
                print(f"Archivo {tipo_archivo} copiado exitosamente a {ruta_destino}.")
            except Exception as e:
                archivos_fallidos.append(ruta_destino)
                print(f"Error al copiar archivo {tipo_archivo} a {ruta_destino}: {str(e)}")

        # Actualizar el campo Radicado en la tabla archivos
        actualizados = archivos_a_verificar.update(Radicado=True)
        print(f"Registros actualizados a Radicado=True: {actualizados}")

        response_data = {
            "success": True,
            "detail": f"Archivos copiados y carpetas creadas para la admisión con número {numero_admision}",
            "archivos_copiados": archivos_copiados,
            "archivos_fallidos": archivos_fallidos
        }
        return JsonResponse(response_data, status=200)

    except ArchivoFacturacion.DoesNotExist:
        response_data = {
            "success": False,
            "detail": f"No se encontraron archivos para la admisión con número {numero_admision}"
        }
        return JsonResponse(response_data, status=404)
    except Exception as e:
        response_data = {
            "success": False,
            "detail": str(e)
        }
        return JsonResponse(response_data, status=500)
######## TABLA RADICACION######
class TablaRadicacion(APIView):
    def get(self, request):
        # Obtener parámetros de consulta
        codigo_entidad = request.query_params.get('CodigoEntidad', None)
        fecha_inicio = request.query_params.get('FechaInicio', None)
        fecha_fin = request.query_params.get('FechaFin', None)

        # Convertir fechas de inicio y fin a objetos datetime
        try:
            fecha_inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d') if fecha_inicio else None
            fecha_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d') if fecha_fin else None

            # Convertir fechas naive a fechas con zona horaria
            if fecha_inicio_dt:
                fecha_inicio_dt = make_aware(fecha_inicio_dt)
            if fecha_fin_dt:
                fecha_fin_dt = make_aware(fecha_fin_dt)
        except ValueError:
            return Response({'error': 'Formato de fecha incorrecto. Use YYYY-MM-DD.'}, status=400)

        # Filtrar auditorías con RevisionCuentasMedicas=True
        auditorias = AuditoriaCuentasMedicas.objects.filter(RevisionCuentasMedicas=True)

        # Inicializar la lista de respuesta
        response_data = []

        # Conectar a la base de datos específica y ejecutar consultas
        with connections['datosipsndx'].cursor() as cursor:
            for auditoria in auditorias:
                # Obtener la admisión asociada a la auditoría
                cursor.execute('''
                    SELECT Consecutivo, IdPaciente, CodigoEntidad, NombreResponsable, FacturaNo
                    FROM admisiones
                    WHERE Consecutivo = %s
                ''', [auditoria.AdmisionId])
                
                admision_data = cursor.fetchone()

                # Si la admisión se encuentra
                if admision_data:
                    # Verificar el filtro de CodigoEntidad
                    if not codigo_entidad or codigo_entidad == admision_data[2]:
                        # Obtener archivos de tipo "RESULTADO" o "HCNEURO" asociados a la admisión
                        archivos_resultado = ArchivoFacturacion.objects.filter(
                            Admision_id=auditoria.AdmisionId,
                            Tipo__in=['RESULTADO', 'HCNEURO', 'FACTURA']  # Filtrar archivos de tipo "RESULTADO" o "HCNEURO"
                        )

                        # Filtrar archivos por rango de fechas si están presentes
                        if fecha_inicio_dt and fecha_fin_dt:
                            archivos_resultado = archivos_resultado.filter(
                                FechaCreacionAntares__range=(fecha_inicio_dt, fecha_fin_dt)
                            )

                        # Si existen archivos después del filtro
                        if archivos_resultado.exists():
                            # Crear la respuesta con todos los campos requeridos
                            for archivo in archivos_resultado:
                                data = {
                                    'AdmisionId': auditoria.AdmisionId,
                                    'FechaCreacion': auditoria.FechaCreacion.strftime('%Y-%m-%d'),
                                    'FechaCargueArchivo': auditoria.FechaCargueArchivo.strftime('%Y-%m-%d'),
                                    'Observacion': auditoria.Observacion,
                                    'RevisionCuentasMedicas': auditoria.RevisionCuentasMedicas,
                                    'Consecutivo': admision_data[0],
                                    'IdPaciente': admision_data[1],
                                    'CodigoEntidad': admision_data[2],
                                    'NombreResponsable': admision_data[3],
                                    'CedulaResponsable': admision_data[4] if len(admision_data) > 4 else None,
                                    'FacturaNo': admision_data[5] if len(admision_data) > 5 else None,
                                    'FechaCreacionAntares': archivo.FechaCreacionAntares.strftime('%Y-%m-%d') if archivo.FechaCreacionAntares else None,
                                    'Radicado': archivo.Radicado
                                }
                                response_data.append(data)
                                break  # No necesitamos buscar más archivos para esta admisión si uno cumple con el criterio

        # Devolver los datos de respuesta
        return Response(response_data)

####### SALUD TOTAL ###
@api_view(['GET'])
@permission_classes([AllowAny])  # Permitir acceso a cualquier usuario
def radicar_salud_total_view(request, numero_admision, idusuario):
    try:
        # Verificar si ya está radicado
        archivos_a_verificar = ArchivoFacturacion.objects.filter(Admision_id=numero_admision)
        if archivos_a_verificar.exists() and archivos_a_verificar.filter(Radicado=True).exists():
            response_data = {
                "success": False,
                "detail": f"La admisión con número {numero_admision} ya está radicada."
            }
            return JsonResponse(response_data, status=400)

        # Obtener los datos de admisión
        admision_response = GeDocumentalView().get(request._request, consecutivo=numero_admision)
        if admision_response.status_code == 200:
            if hasattr(admision_response, 'data') and isinstance(admision_response.data, dict):
                admision_data = admision_response.data.get('data')
                if isinstance(admision_data, dict):
                    factura_numero = admision_data.get('FacturaNo')
                    prefijo = admision_data.get('Prefijo') or ''  # Usa un valor predeterminado si es None

                    # Asegúrate de que prefijo sea una cadena válida
                    if prefijo is None:
                        prefijo = ''  # O asigna un valor por defecto si es necesario

                    if factura_numero is not None:
                        # Obtener los archivos de la admisión
                        archivos_response = archivos_por_admision_radicacion(request._request, numero_admision)
                        if archivos_response.status_code == 200:
                            if hasattr(archivos_response, 'data') and isinstance(archivos_response.data, dict):
                                archivos_data = archivos_response.data.get('data', [])
                                if isinstance(archivos_data, list):
                                    # Verificar si el usuario existe y obtener el nombre
                                    try:
                                        user = CustomUser.objects.get(id=idusuario)
                                        nombre_usuario = user.username  # Obtener el nombre del usuario para usar en la carpeta
                                        # Sanitizar el nombre del usuario si es necesario
                                        nombre_usuario = "".join(c for c in nombre_usuario if c.isalnum() or c in (' ', '.', '_')).rstrip()
                                        print(f"Nombre del usuario sanitizado para crear carpeta: {nombre_usuario}")
                                    except CustomUser.DoesNotExist:
                                        response_data = {
                                            "success": False,
                                            "detail": "Usuario no encontrado."
                                        }
                                        return JsonResponse(response_data, status=404)

                                    # Obtener la fecha de hoy para la carpeta
                                    fecha_hoy = datetime.now().strftime('%Y-%m-%d')

                                    # Crear la ruta completa usando el nombre de usuario
                                    carpeta_path = os.path.join(settings.MEDIA_ROOT, 'gdocumental', 'Radicacion', 'SALUDTOTAL', fecha_hoy, nombre_usuario)
                                    if not os.path.exists(carpeta_path):
                                        os.makedirs(carpeta_path)

                                    # Definir los tipos de archivos requeridos
                                    documentos_requeridos = {
                                        'FACTURA': 1,
                                        'AUTORIZACION': 17,
                                        'ORDEN': 5,
                                        'RESULTADO': 7,
                                        'COMPROBANTE': 15
                                    }

                                    # Verificar la presencia de todos los documentos requeridos
                                    tipos_archivos_presentes = {archivo.get('Tipo') for archivo in archivos_data}
                                    documentos_faltantes = [tipo for tipo in documentos_requeridos if tipo not in tipos_archivos_presentes]

                                    if documentos_faltantes:
                                        response_data = {
                                            "success": False,
                                            "detail": f"Faltan los siguientes documentos requeridos: {', '.join(documentos_faltantes)}"
                                        }
                                        return JsonResponse(response_data, status=400)

                                    # Procesar y copiar los archivos requeridos
                                    for archivo in archivos_data:
                                        tipo_archivo = archivo.get('Tipo')
                                        if tipo_archivo in documentos_requeridos:
                                            ruta_origen_relative = unquote(archivo.get('RutaArchivo'))
                                            numero_tipo_documento = documentos_requeridos[tipo_archivo]

                                            nombre_archivo = f"901119103_{prefijo}_{factura_numero}_{numero_tipo_documento}_1.pdf"
                                            print("Nombre de archivo:", nombre_archivo)

                                            # Normalizar la ruta y eliminar cualquier referencia redundante
                                            ruta_origen = os.path.normpath(os.path.join(settings.MEDIA_ROOT, ruta_origen_relative.replace(settings.MEDIA_URL, "").lstrip('/')))

                                            if os.path.exists(ruta_origen):
                                                ruta_destino = os.path.join(carpeta_path, nombre_archivo)
                                                shutil.copy(ruta_origen, ruta_destino)
                                                print("Archivo copiado exitosamente.")
                                            else:
                                                raise FileNotFoundError(f"La ruta de origen '{ruta_origen}' no es válida")

                                    # Verificar registros antes de la actualización
                                    print(f"Registros encontrados para actualizar: {archivos_a_verificar.count()}")
                                    for archivo in archivos_a_verificar:
                                        print(f"Antes de la actualización - IdArchivo: {archivo.IdArchivo}, Radicado: {archivo.Radicado}")

                                    # Actualizar el campo Radicado en la tabla archivos
                                    actualizados = archivos_a_verificar.update(Radicado=True)
                                    print(f"Registros actualizados a Radicado=True: {actualizados}")

                                    # Verificar registros después de la actualización
                                    archivos_actualizados = ArchivoFacturacion.objects.filter(Admision_id=numero_admision, Radicado=True)
                                    for archivo in archivos_actualizados:
                                        print(f"Después de la actualización - IdArchivo: {archivo.IdArchivo}, Radicado: {archivo.Radicado}")

                                    response_data = {
                                        "success": True,
                                        "detail": f"Archivos copiados y carpetas creadas para la admisión con número {numero_admision}"
                                    }
                                    return JsonResponse(response_data, status=200)
                                else:
                                    raise ValueError("La respuesta de archivos no contiene una lista de datos válida.")
                            else:
                                raise ValueError("La respuesta de archivos no contiene datos válidos.")
                        else:
                            return archivos_response
                    else:
                        raise ValueError("La admisión no tiene el número de factura.")
                else:
                    raise ValueError("Los datos de admisión no están en el formato esperado.")
            else:
                raise ValueError("La respuesta de admisión no contiene datos válidos.")
        else:
            return admision_response
    except ArchivoFacturacion.DoesNotExist:
        response_data = {
            "success": False,
            "detail": f"No se encontraron archivos para la admisión con número {numero_admision}"
        }
        return JsonResponse(response_data, status=404)
    except Exception as e:
        response_data = {
            "success": False,
            "detail": str(e)
        }
        return JsonResponse(response_data, status=500)





#### SANITAS EVENTO
@api_view(['GET'])
@permission_classes([AllowAny])  # Permitir acceso a cualquier usuario
def radicar_sanitas_evento_view(request, numero_admision, idusuario):
    try:
        # Verificar si el usuario existe y obtener el nombre de usuario
        try:
            user = CustomUser.objects.get(id=idusuario)
            nombre_usuario = user.username  # Obtener el nombre del usuario para usar en la carpeta
            # Sanitizar el nombre del usuario si es necesario
            nombre_usuario = "".join(c for c in nombre_usuario if c.isalnum() or c in (' ', '.', '_')).rstrip()
            print(f"Nombre del usuario sanitizado para crear carpeta: {nombre_usuario}")
        except CustomUser.DoesNotExist:
            response_data = {
                "success": False,
                "detail": "Usuario no encontrado."
            }
            return JsonResponse(response_data, status=404)

        # Verificar si ya está radicado
        archivos_a_verificar = ArchivoFacturacion.objects.filter(Admision_id=numero_admision)
        if archivos_a_verificar.exists() and archivos_a_verificar.filter(Radicado=True).exists():
            response_data = {
                "success": False,
                "detail": f"La admisión con número {numero_admision} ya está radicada."
            }
            return JsonResponse(response_data, status=400)

        # Obtener los datos de admisión
        admision_response = GeDocumentalView().get(request._request, consecutivo=numero_admision)
        if admision_response.status_code != 200:
            return admision_response

        admision_data = admision_response.data.get('data')
        factura_numero = admision_data.get('FacturaNo')
        prefijo = admision_data.get('Prefijo') or ''  # Usa un valor predeterminado si es None

        if factura_numero is None:
            raise ValueError("La admisión no tiene el número de factura")

        # Obtener los archivos de la admisión
        archivos_response = archivos_por_admision_radicacion(request._request, numero_admision)
        if archivos_response.status_code != 200:
            return archivos_response

        archivos_data = archivos_response.data.get('data', [])
        archivos_requeridos = ['FACTURA', 'COMPROBANTE', 'ORDEN', 'RESULTADO', 'AUTORIZACION', 'HCNEURO']
        archivos_faltantes = []

        # Verificar la existencia de todos los archivos requeridos antes de proceder
        for archivo in archivos_data:
            tipo_archivo = archivo.get('Tipo')
            if tipo_archivo in archivos_requeridos:
                ruta_origen_relative = unquote(archivo.get('RutaArchivo'))
                ruta_origen_relative = ruta_origen_relative.replace(settings.MEDIA_URL, "").lstrip('/')
                ruta_origen = os.path.normpath(os.path.join(settings.MEDIA_ROOT, ruta_origen_relative))

                print(f"Verificando existencia de archivo: {ruta_origen} (Tipo: {tipo_archivo})")

                if not os.path.exists(ruta_origen):
                    archivos_faltantes.append(tipo_archivo)

        if archivos_faltantes:
            response_data = {
                "success": False,
                "detail": f"Faltan los siguientes archivos requeridos: {', '.join(archivos_faltantes)}"
            }
            return JsonResponse(response_data, status=400)

        # Obtener el archivo de tipo FACTURA
        factura_archivo = next((archivo for archivo in archivos_data if archivo.get('Tipo') == 'FACTURA'), None)
        if not factura_archivo:
            raise FileNotFoundError("No se encontró el archivo de tipo FACTURA para la admisión")

        ruta_origen_relative = unquote(factura_archivo.get('RutaArchivo'))
        ruta_origen_relative = ruta_origen_relative.replace(settings.MEDIA_URL, "").lstrip('/')
        ruta_origen = os.path.normpath(os.path.join(settings.MEDIA_ROOT, ruta_origen_relative))

        if not os.path.exists(ruta_origen):
            raise FileNotFoundError(f"No se encontró el archivo de tipo FACTURA en {ruta_origen}")

        # Crear un nuevo documento PDF combinando los archivos
        merger = PdfMerger()
        merger.append(ruta_origen)

        for archivo in archivos_data:
            if archivo.get('Tipo') != 'FACTURA':
                ruta_origen_relative = unquote(archivo.get('RutaArchivo'))
                ruta_origen_relative = ruta_origen_relative.replace(settings.MEDIA_URL, "").lstrip('/')
                ruta_origen = os.path.normpath(os.path.join(settings.MEDIA_ROOT, ruta_origen_relative))

                print(f'Ruta formada para {archivo.get("Tipo")}: {ruta_origen}')

                if os.path.exists(ruta_origen):
                    merger.append(ruta_origen)
                else:
                    raise FileNotFoundError(f"No se encontró el archivo {archivo.get('Tipo')} en {ruta_origen}")

        # Obtener el régimen desde el primer archivo de facturación relacionado
        archivo_facturacion = ArchivoFacturacion.objects.filter(Admision_id=numero_admision).first()
        if not archivo_facturacion:
            raise FileNotFoundError(f"No se encontró el archivo de facturación para la admisión {numero_admision}")

        regimen = archivo_facturacion.Regimen
        if regimen == 'C':
            carpeta_tipo_archivo = 'CONTRIBUTIVO'
        elif regimen == 'S':
            carpeta_tipo_archivo = 'SUBSIDIADO'
        else:
            raise ValueError(f"Regimen desconocido: {regimen}")

        # Crear la ruta de la carpeta usando la fecha, el régimen y el nombre del usuario
        fecha_hoy = datetime.now().strftime('%Y-%m-%d')
        carpeta_prefijo_numero_factura = f"{prefijo}{factura_numero}"
        carpeta_nombre_archivo = os.path.join(settings.MEDIA_ROOT, 'gdocumental', 'Radicacion', 'SAN01', carpeta_tipo_archivo, fecha_hoy,  nombre_usuario, carpeta_prefijo_numero_factura)
        if not os.path.exists(carpeta_nombre_archivo):
            os.makedirs(carpeta_nombre_archivo)

        ruta_destino_merged = os.path.join(carpeta_nombre_archivo, f"{prefijo}{factura_numero}.pdf")
        merger.write(ruta_destino_merged)
        merger.close()

        print(f"Registros encontrados para actualizar: {archivos_a_verificar.count()}")
        for archivo in archivos_a_verificar:
            print(f"Antes de la actualización - IdArchivo: {archivo.IdArchivo}, Radicado: {archivo.Radicado}")

        # Actualizar el campo Radicado en la tabla archivos
        actualizados = archivos_a_verificar.update(Radicado=True)
        print(f"Registros actualizados a Radicado=True: {actualizados}")

        archivos_actualizados = ArchivoFacturacion.objects.filter(Admision_id=numero_admision, Radicado=True)
        for archivo in archivos_actualizados:
            print(f"Después de la actualización - IdArchivo: {archivo.IdArchivo}, Radicado: {archivo.Radicado}")

        response_data = {
            "success": True,
            "detail": f"Archivos combinados en un solo documento y guardados en {ruta_destino_merged}"
        }
        return JsonResponse(response_data, status=200)

    except ArchivoFacturacion.DoesNotExist:
        response_data = {
            "success": False,
            "detail": f"No se encontraron archivos para la admisión con número {numero_admision}"
        }
        return JsonResponse(response_data, status=404)
    except Exception as e:
        response_data = {
            "success": False,
            "detail": str(e)
        }
        return JsonResponse(response_data, status=500)
##### COLSANITAS###
@api_view(['GET'])
@permission_classes([AllowAny])  # Permitir acceso a cualquier usuario
def radicar_colsanitas_view(request, numero_admision, idusuario):
    try:
        # Verificar si ya está radicado
        archivos_a_verificar = ArchivoFacturacion.objects.filter(Admision_id=numero_admision)
        if archivos_a_verificar.exists() and archivos_a_verificar.filter(Radicado=True).exists():
            response_data = {
                "success": False,
                "detail": f"La admisión con número {numero_admision} ya está radicada."
            }
            return JsonResponse(response_data, status=400)

        # Obtener los datos de admisión
        admision_response = GeDocumentalView().get(request._request, consecutivo=numero_admision)
        if admision_response.status_code == 200:
            if hasattr(admision_response, 'data') and isinstance(admision_response.data, dict):
                admision_data = admision_response.data.get('data')
                if isinstance(admision_data, dict):
                    factura_numero = admision_data.get('FacturaNo')
                    prefijo = admision_data.get('Prefijo') or ''  # Usa un valor predeterminado si es None

                    if factura_numero is not None:
                        # Obtener los archivos de la admisión
                        archivos_response = archivos_por_admision_radicacion(request._request, numero_admision)
                        if archivos_response.status_code == 200:
                            if hasattr(archivos_response, 'data') and isinstance(archivos_response.data, dict):
                                archivos_data = archivos_response.data.get('data', [])
                                if isinstance(archivos_data, list):
                                    # Verificar si el usuario existe y obtener el nombre
                                    try:
                                        user = CustomUser.objects.get(id=idusuario)
                                        nombre_usuario = user.username  # Obtener el nombre del usuario para usar en la carpeta
                                        # Sanitizar el nombre del usuario si es necesario
                                        nombre_usuario = "".join(c for c in nombre_usuario if c.isalnum() or c in (' ', '.', '_')).rstrip()
                                        print(f"Nombre del usuario sanitizado para crear carpeta: {nombre_usuario}")
                                    except CustomUser.DoesNotExist:
                                        response_data = {
                                            "success": False,
                                            "detail": "Usuario no encontrado."
                                        }
                                        return JsonResponse(response_data, status=404)

                                    # Obtener la fecha de hoy para la carpeta
                                    fecha_hoy = datetime.now().strftime('%Y-%m-%d')

                                    # Crear la ruta completa usando el nombre de usuario
                                    carpeta_path = os.path.join(settings.MEDIA_ROOT, 'gdocumental', 'Radicacion', 'COLSANITAS', fecha_hoy, nombre_usuario)
                                    if not os.path.exists(carpeta_path):
                                        os.makedirs(carpeta_path)

                                    # Definir los tipos de archivos requeridos
                                    documentos_requeridos = {'FACTURA', 'RESULTADO', 'COMPROBANTE', 'ORDEN'}
                                    
                                    # Verificar la presencia de todos los documentos requeridos
                                    tipos_archivos_presentes = {archivo.get('Tipo') for archivo in archivos_data}
                                    documentos_faltantes = documentos_requeridos - tipos_archivos_presentes

                                    if documentos_faltantes:
                                        response_data = {
                                            "success": False,
                                            "detail": f"Faltan los siguientes documentos requeridos: {', '.join(documentos_faltantes)}"
                                        }
                                        return JsonResponse(response_data, status=400)

                                    # Procesar y copiar los archivos según el tipo
                                    for archivo in archivos_data:
                                        tipo_archivo = archivo.get('Tipo')
                                        ruta_origen_relative = unquote(archivo.get('RutaArchivo'))
                                        ruta_origen_relative = ruta_origen_relative.replace(settings.MEDIA_URL, "").lstrip('/')
                                        ruta_origen = os.path.normpath(os.path.join(settings.MEDIA_ROOT, ruta_origen_relative))

                                        if tipo_archivo == 'FACTURA':
                                            nombre_archivo = f"{prefijo}{factura_numero}.pdf"
                                        else:
                                            if tipo_archivo == 'COMPROBANTE':
                                                sop = 'SOP_1'
                                            elif tipo_archivo == 'AUTORIZACION':
                                                sop = 'SOP_2'
                                            elif tipo_archivo == 'ORDEN':
                                                sop = 'SOP_3'
                                            elif tipo_archivo == 'ADICIONALES':
                                                sop = 'SOP_4'
                                            elif tipo_archivo == 'RESULTADO':
                                                sop = 'SOP_5'
                                            elif tipo_archivo == 'HCNEURO':
                                                sop = 'SOP_6'
                                            else:
                                                sop = 'OTRO'  # Otra opción si no se encuentra el tipo de documento

                                            nombre_archivo = f"{prefijo}{factura_numero}_{sop}.pdf"

                                        print("Nombre de archivo:", nombre_archivo)

                                        # Verificar y ajustar la ruta si contiene duplicaciones de 'media'
                                        if 'media/media' in ruta_origen:
                                            ruta_origen = ruta_origen.replace('media/media', 'media')

                                        print(f'Ruta formada para {tipo_archivo}: {ruta_origen}')

                                        if os.path.exists(ruta_origen):
                                            ruta_destino = os.path.join(carpeta_path, nombre_archivo)
                                            shutil.copy(ruta_origen, ruta_destino)
                                            print("Archivo copiado exitosamente.")
                                        else:
                                            raise FileNotFoundError(f"La ruta de origen '{ruta_origen}' no es válida")

                                    # Verificar registros antes de la actualización
                                    print(f"Registros encontrados para actualizar: {archivos_a_verificar.count()}")
                                    for archivo in archivos_a_verificar:
                                        print(f"Antes de la actualización - IdArchivo: {archivo.IdArchivo}, Radicado: {archivo.Radicado}")

                                    # Actualizar el campo Radicado en la tabla archivos
                                    actualizados = archivos_a_verificar.update(Radicado=True)
                                    print(f"Registros actualizados a Radicado=True: {actualizados}")

                                    # Verificar registros después de la actualización
                                    archivos_actualizados = ArchivoFacturacion.objects.filter(Admision_id=numero_admision, Radicado=True)
                                    for archivo in archivos_actualizados:
                                        print(f"Después de la actualización - IdArchivo: {archivo.IdArchivo}, Radicado: {archivo.Radicado}")

                                    response_data = {
                                        "success": True,
                                        "detail": f"Archivos copiados y carpetas creadas para la admisión con número {numero_admision}"
                                    }
                                    return JsonResponse(response_data, status=200)
                                else:
                                    raise ValueError("La respuesta de archivos no contiene una lista de datos válida.")
                            else:
                                raise ValueError("La respuesta de archivos no contiene datos válidos.")
                        else:
                            return archivos_response
                    else:
                        raise ValueError("La admisión no tiene el número de factura.")
                else:
                    raise ValueError("Los datos de admisión no están en el formato esperado.")
            else:
                raise ValueError("La respuesta de admisión no contiene datos válidos.")
        else:
            return admision_response
    except ArchivoFacturacion.DoesNotExist:
        response_data = {
            "success": False,
            "detail": f"No se encontraron archivos para la admisión con número {numero_admision}"
        }
        return JsonResponse(response_data, status=404)
    except Exception as e:
        response_data = {
            "success": False,
            "detail": str(e)
        }
        return JsonResponse(response_data, status=500)

      
      
##### MEDISANITAS###
@api_view(['GET'])
@permission_classes([AllowAny])  # Permitir acceso a cualquier usuario
def radicar_mes01_view(request, numero_admision, idusuario):
    try:
        # Verificar si ya está radicado
        archivos_a_verificar = ArchivoFacturacion.objects.filter(Admision_id=numero_admision)
        if archivos_a_verificar.exists() and archivos_a_verificar.filter(Radicado=True).exists():
            response_data = {
                "success": False,
                "detail": f"La admisión con número {numero_admision} ya está radicada."
            }
            return JsonResponse(response_data, status=400)

        # Obtener los datos de admisión
        admision_response = GeDocumentalView().get(request._request, consecutivo=numero_admision)
        if admision_response.status_code == 200:
            admision_data = admision_response.data.get('data')
            factura_numero = admision_data.get('FacturaNo')
            prefijo = admision_data.get('Prefijo') or ''  # Usa un valor predeterminado si es None

            if factura_numero is not None:
                # Obtener los archivos de la admisión
                archivos_response = archivos_por_admision_radicacion(request._request, numero_admision)
                if archivos_response.status_code == 200:
                    archivos_data = archivos_response.data.get('data', [])

                    # Verificar si el usuario existe y obtener el nombre
                    try:
                        user = CustomUser.objects.get(id=idusuario)
                        nombre_usuario = user.username  # Obtener el nombre del usuario para usar en la carpeta
                        # Sanitizar el nombre del usuario si es necesario
                        nombre_usuario = "".join(c for c in nombre_usuario if c.isalnum() or c in (' ', '.', '_')).rstrip()
                        print(f"Nombre del usuario sanitizado para crear carpeta: {nombre_usuario}")
                    except CustomUser.DoesNotExist:
                        response_data = {
                            "success": False,
                            "detail": "Usuario no encontrado."
                        }
                        return JsonResponse(response_data, status=404)

                    # Obtener la fecha de hoy para la carpeta
                    fecha_hoy = datetime.now().strftime('%Y-%m-%d')

                    # Crear la ruta completa usando el nombre de usuario
                    carpeta_path = os.path.join(settings.MEDIA_ROOT, 'gdocumental', 'Radicacion', 'MEDISANITAS', fecha_hoy, nombre_usuario)
                    if not os.path.exists(carpeta_path):
                        os.makedirs(carpeta_path)

                    # Definir los tipos de archivos requeridos
                    documentos_requeridos = {'FACTURA', 'RESULTADO', 'AUTORIZACION', 'COMPROBANTE', 'ORDEN'}
                    
                    # Verificar la presencia de todos los documentos requeridos
                    tipos_archivos_presentes = {archivo.get('Tipo') for archivo in archivos_data}
                    documentos_faltantes = documentos_requeridos - tipos_archivos_presentes

                    if documentos_faltantes:
                        response_data = {
                            "success": False,
                            "detail": f"Faltan los siguientes documentos requeridos: {', '.join(documentos_faltantes)}"
                        }
                        return JsonResponse(response_data, status=400)

                    # Procesar y copiar los archivos según el tipo
                    for archivo in archivos_data:
                        tipo_archivo = archivo.get('Tipo')
                        ruta_origen_relative = unquote(archivo.get('RutaArchivo'))
                        ruta_origen_relative = ruta_origen_relative.replace(settings.MEDIA_URL, "").lstrip('/')
                        ruta_origen = os.path.normpath(os.path.join(settings.MEDIA_ROOT, ruta_origen_relative))

                        if tipo_archivo == 'FACTURA':
                            nombre_archivo = f"{prefijo}{factura_numero}.pdf"
                        else:
                            if tipo_archivo == 'COMPROBANTE':
                                sop = 'SOP_1'
                            elif tipo_archivo == 'AUTORIZACION':
                                sop = 'SOP_2'
                            elif tipo_archivo == 'ORDEN':
                                sop = 'SOP_3'
                            elif tipo_archivo == 'ADICIONALES':
                                sop = 'SOP_4'
                            elif tipo_archivo == 'RESULTADO':
                                sop = 'SOP_5'
                            elif tipo_archivo == 'HCNEURO':
                                sop = 'SOP_6'
                            else:
                                sop = 'OTRO'  # Otra opción si no se encuentra el tipo de documento

                            nombre_archivo = f"{prefijo}{factura_numero}_{sop}.pdf"

                        print("Nombre de archivo:", nombre_archivo)

                        # Verificar y ajustar la ruta si contiene duplicaciones de 'media'
                        if 'media/media' in ruta_origen:
                            ruta_origen = ruta_origen.replace('media/media', 'media')

                        print(f'Ruta formada para {tipo_archivo}: {ruta_origen}')

                        if os.path.exists(ruta_origen):
                            ruta_destino = os.path.join(carpeta_path, nombre_archivo)
                            shutil.copy(ruta_origen, ruta_destino)
                            print("Archivo copiado exitosamente.")
                        else:
                            raise FileNotFoundError(f"La ruta de origen '{ruta_origen}' no es válida")

                    # Verificar registros antes de la actualización
                    print(f"Registros encontrados para actualizar: {archivos_a_verificar.count()}")
                    for archivo in archivos_a_verificar:
                        print(f"Antes de la actualización - IdArchivo: {archivo.IdArchivo}, Radicado: {archivo.Radicado}")

                    # Actualizar el campo Radicado en la tabla archivos
                    actualizados = archivos_a_verificar.update(Radicado=True)
                    print(f"Registros actualizados a Radicado=True: {actualizados}")

                    # Verificar registros después de la actualización
                    archivos_actualizados = ArchivoFacturacion.objects.filter(Admision_id=numero_admision, Radicado=True)
                    for archivo in archivos_actualizados:
                        print(f"Después de la actualización - IdArchivo: {archivo.IdArchivo}, Radicado: {archivo.Radicado}")

                    response_data = {
                        "success": True,
                        "detail": f"Archivos copiados y carpetas creadas para la admisión con número {numero_admision}"
                    }
                    return JsonResponse(response_data, status=200)
                else:
                    return archivos_response
            else:
                raise ValueError("La admisión no tiene el número de factura.")
        else:
            return admision_response
    except ArchivoFacturacion.DoesNotExist:
        response_data = {
            "success": False,
            "detail": f"No se encontraron archivos para la admisión con número {numero_admision}"
        }
        return JsonResponse(response_data, status=404)
    except Exception as e:
        response_data = {
            "success": False,
            "detail": str(e)
        }
        return JsonResponse(response_data, status=500)

      
      
    
#### CAPITAL SALUD ###############################################################################################
@api_view(['GET'])
@permission_classes([AllowAny])  # Permitir acceso a cualquier usuario
def radicar_capitalsalud_view(request, numero_admision, idusuario):
    try:
        # Verificar si ya está radicado
        archivos_a_verificar = ArchivoFacturacion.objects.filter(Admision_id=numero_admision)
        if archivos_a_verificar.exists() and archivos_a_verificar.filter(Radicado=True).exists():
            response_data = {
                "success": False,
                "detail": f"La admisión con número {numero_admision} ya está radicada."
            }
            return JsonResponse(response_data, status=400)

        # Obtener los datos de admisión
        admision_response = GeDocumentalView().get(request._request, consecutivo=numero_admision)
        if admision_response.status_code == 200:
            admision_data = admision_response.data.get('data')
            factura_numero = admision_data.get('FacturaNo')
            prefijo = admision_data.get('Prefijo')

            if factura_numero is not None:
                # Obtener los archivos de la admisión
                archivos_response = archivos_por_admision_radicacion(request._request, numero_admision)
                if archivos_response.status_code == 200:
                    archivos_data = archivos_response.data.get('data', [])

                    # Definir los tipos de archivos requeridos
                    documentos_requeridos = {'FACTURA', 'COMPROBANTE', 'AUTORIZACION', 'ORDEN', 'RESULTADO', 'HCNEURO'}
                    
                    # Verificar la presencia de los documentos clave
                    tipos_archivos_presentes = {archivo.get('Tipo') for archivo in archivos_data}
                    documentos_clave = {'FACTURA', 'RESULTADO'}
                    documentos_faltantes = documentos_clave - tipos_archivos_presentes

                    # Si falta resultado pero existe HCNEURO, considerarlo como válido
                    if 'RESULTADO' in documentos_faltantes and 'HCNEURO' in tipos_archivos_presentes:
                        documentos_faltantes.remove('RESULTADO')  # Consideramos HCNEURO en lugar de RESULTADO

                    # Verificar si faltan documentos obligatorios
                    if 'FACTURA' in documentos_faltantes:
                        response_data = {
                            "success": False,
                            "detail": "Falta el documento de FACTURA."
                        }
                        return JsonResponse(response_data, status=400)

                    # Verificar si el usuario existe y obtener el nombre
                    try:
                        user = CustomUser.objects.get(id=idusuario)
                        nombre_usuario = user.username  # Obtener el nombre del usuario para usar en la carpeta
                        # Sanitizar el nombre del usuario si es necesario
                        nombre_usuario = "".join(c for c in nombre_usuario if c.isalnum() or c in (' ', '.', '_')).rstrip()
                        print(f"Nombre del usuario sanitizado para crear carpeta: {nombre_usuario}")
                    except CustomUser.DoesNotExist:
                        response_data = {
                            "success": False,
                            "detail": "Usuario no encontrado."
                        }
                        return JsonResponse(response_data, status=404)

                    # Crear un nuevo documento PDF
                    merger = PdfMerger()

                    # Orden de los documentos: Factura, Comprobante, Autorización, Orden, Resultado (o HCNeuro)
                    orden_documentos = ['FACTURA', 'COMPROBANTE', 'AUTORIZACION', 'ORDEN', 'ADICIONALES','RESULTADO', 'HCNEURO']

                    # Procesar y agregar los archivos en el orden requerido
                    for tipo_documento in orden_documentos:
                        if tipo_documento in tipos_archivos_presentes:
                            # Si no hay Resultado pero hay HCNEURO, se usa HCNEURO
                            if tipo_documento == 'RESULTADO' and 'RESULTADO' not in tipos_archivos_presentes:
                                continue  # Si no está RESULTADO, pero se agrega HCNEURO después
                            
                            # Obtener el archivo correspondiente al tipo de documento
                            archivo = next(archivo for archivo in archivos_data if archivo.get('Tipo') == tipo_documento)
                            ruta_origen_relative = unquote(archivo.get('RutaArchivo'))
                            ruta_origen = os.path.normpath(os.path.join(settings.MEDIA_ROOT, ruta_origen_relative.replace(settings.MEDIA_URL, "")))

                            if os.path.exists(ruta_origen):
                                merger.append(ruta_origen)
                            else:
                                raise FileNotFoundError(f"No se encontró el archivo {tipo_documento} en {ruta_origen}")

                    # Obtener el régimen de la admisión desde el primer archivo asociado
                    archivo_facturacion = ArchivoFacturacion.objects.filter(Admision_id=numero_admision).first()
                    if not archivo_facturacion:
                        raise FileNotFoundError(f"No se encontró el archivo de facturación para la admisión {numero_admision}")

                    regimen = archivo_facturacion.Regimen
                    if regimen == 'C':
                        carpeta_tipo_archivo = 'CONTRIBUTIVO'
                    elif regimen == 'S':
                        carpeta_tipo_archivo = 'SUBSIDIADO'
                    else:
                        raise ValueError(f"Regimen desconocido: {regimen}")

                    # Crear la ruta completa del archivo destino usando el nombre del usuario
                    fecha_hoy = datetime.now().strftime('%Y-%m-%d')
                    carpeta_nombre_archivo = os.path.join(settings.MEDIA_ROOT, 'gdocumental', 'Radicacion', 'CAPITALSALUD', carpeta_tipo_archivo, fecha_hoy, nombre_usuario)
                    if not os.path.exists(carpeta_nombre_archivo):
                        os.makedirs(carpeta_nombre_archivo)

                    ruta_destino_merged = os.path.join(carpeta_nombre_archivo, f"{prefijo}{factura_numero}.pdf")
                    merger.write(ruta_destino_merged)
                    merger.close()

                    # Actualizar el campo Radicado en la tabla archivos
                    actualizados = archivos_a_verificar.update(Radicado=True)

                    response_data = {
                        "success": True,
                        "detail": f"Archivos combinados en un solo documento y guardados en {ruta_destino_merged}"
                    }
                    return JsonResponse(response_data, status=200)
                else:
                    return archivos_response
            else:
                raise ValueError("La admisión no tiene el número de factura.")
        else:
            return admision_response
    except ArchivoFacturacion.DoesNotExist:
        response_data = {
            "success": False,
            "detail": f"No se encontraron archivos para la admisión con número {numero_admision}"
        }
        return JsonResponse(response_data, status=404)
    except Exception as e:
        response_data = {
            "success": False,
            "detail": str(e)
        }
        return JsonResponse(response_data, status=500)


###### RADICAR SAN02#####

@api_view(['GET'])
@permission_classes([AllowAny])  # Permitir acceso a cualquier usuario
def radicar_san02_view(request, numero_admision, idusuario):
    try:
        # Verificar si el idusuario existe en la base de datos y obtener el nombre de usuario
        try:
            user = CustomUser.objects.get(id=idusuario)
            nombre_usuario = user.username  # Obtener el nombre del usuario para usar en la carpeta
        except CustomUser.DoesNotExist:
            response_data = {
                "success": False,
                "detail": "Usuario no encontrado."
            }
            return JsonResponse(response_data, status=404)

        # Verificar si ya está radicado
        archivos_a_verificar = ArchivoFacturacion.objects.filter(Admision_id=numero_admision)
        if archivos_a_verificar.exists() and archivos_a_verificar.filter(Radicado=True).exists():
            response_data = {
                "success": False,
                "detail": f"La admisión con número {numero_admision} ya está radicada."
            }
            return JsonResponse(response_data, status=400)

        # Obtener los datos de admisión
        admision_response = GeDocumentalView().get(request._request, consecutivo=numero_admision)
        if admision_response.status_code == 200:
            admision_data = admision_response.data.get('data')
            factura_numero = admision_data.get('FacturaNo')
            prefijo = admision_data.get('Prefijo')
            codigo_entidad = admision_data.get('CodigoEntidad')

            if factura_numero is not None:
                # Obtener los archivos de la admisión
                archivos_response = archivos_por_admision_radicacion(request._request, numero_admision)
                if archivos_response.status_code == 200:
                    archivos_data = archivos_response.data.get('data', [])
                    factura_archivo = next((archivo for archivo in archivos_data if archivo.get('Tipo') == 'FACTURA'), None)

                    if factura_archivo:
                        ruta_origen_relative = unquote(factura_archivo.get('RutaArchivo'))
                        ruta_origen = os.path.normpath(os.path.join(settings.MEDIA_ROOT, ruta_origen_relative.replace(settings.MEDIA_URL, "")))
                        print(f"Ruta del archivo de factura: {ruta_origen}")

                        if not os.path.exists(ruta_origen):
                            response_data = {
                                "success": False,
                                "detail": f"No se encontró el archivo de tipo FACTURA en {ruta_origen}"
                            }
                            return JsonResponse(response_data, status=404)

                        # Crear un nuevo documento PDF
                        merger = PdfMerger()
                        merger.append(ruta_origen)

                        # Agregar los demás archivos al nuevo documento
                        tipos_requeridos = ['COMPROBANTE', 'ORDEN', 'HCNEURO', 'AUTORIZACION', 'ADICIONALES', 'RESULTADO']
                        for tipo in tipos_requeridos:
                            for archivo in archivos_data:
                                if archivo.get('Tipo') == tipo:
                                    ruta_origen_relative = unquote(archivo.get('RutaArchivo'))
                                    ruta_origen = os.path.normpath(os.path.join(settings.MEDIA_ROOT, ruta_origen_relative.replace(settings.MEDIA_URL, "")))
                                    print(f"Ruta del archivo {archivo.get('Tipo')}: {ruta_origen}")

                                    if os.path.exists(ruta_origen):
                                        merger.append(ruta_origen)
                                    else:
                                        print(f"No se encontró el archivo {archivo.get('Tipo')} en {ruta_origen}")

                        # Obtener el régimen de la admisión desde el primer archivo asociado
                        archivo_facturacion = ArchivoFacturacion.objects.filter(Admision_id=numero_admision).first()
                        if not archivo_facturacion:
                            response_data = {
                                "success": False,
                                "detail": f"No se encontró el archivo de facturación para la admisión {numero_admision}"
                            }
                            return JsonResponse(response_data, status=404)

                        regimen = archivo_facturacion.Regimen
                        if regimen == 'C':
                            carpeta_tipo_archivo = 'CONTRIBUTIVO'
                        elif regimen == 'S':
                            carpeta_tipo_archivo = 'SUBSIDIADO'
                        else:
                            response_data = {
                                "success": False,
                                "detail": f"Régimen desconocido: {regimen}"
                            }
                            return JsonResponse(response_data, status=400)

                        # Crear la ruta completa del archivo destino
                        fecha_hoy = datetime.now().strftime('%Y-%m-%d')
                        carpeta_nombre_archivo = os.path.join(settings.MEDIA_ROOT, 'gdocumental', 'Radicacion', 'SAN02', carpeta_tipo_archivo, nombre_usuario)
                        if not os.path.exists(carpeta_nombre_archivo):
                            os.makedirs(carpeta_nombre_archivo)

                        ruta_destino_merged = os.path.join(carpeta_nombre_archivo, f"{prefijo}{factura_numero}.pdf")
                        merger.write(ruta_destino_merged)
                        merger.close()

                        # Verificar registros antes de la actualización
                        print(f"Registros encontrados para actualizar: {archivos_a_verificar.count()}")
                        for archivo in archivos_a_verificar:
                            print(f"Antes de la actualización - IdArchivo: {archivo.IdArchivo}, Radicado: {archivo.Radicado}")

                        # Actualizar el campo Radicado en la tabla archivos
                        actualizados = archivos_a_verificar.update(Radicado=True)
                        print(f"Registros actualizados a Radicado=True: {actualizados}")

                        # Verificar registros después de la actualización
                        archivos_actualizados = ArchivoFacturacion.objects.filter(Admision_id=numero_admision, Radicado=True)
                        for archivo in archivos_actualizados:
                            print(f"Después de la actualización - IdArchivo: {archivo.IdArchivo}, Radicado: {archivo.Radicado}")

                        response_data = {
                            "success": True,
                            "detail": f"Archivos combinados en un solo documento y guardados en {ruta_destino_merged}"
                        }
                        return JsonResponse(response_data, status=200)
                    else:
                        response_data = {
                            "success": False,
                            "detail": "No se encontró el archivo de tipo FACTURA para la admisión"
                        }
                        return JsonResponse(response_data, status=404)
                else:
                    return archivos_response
            else:
                response_data = {
                    "success": False,
                    "detail": "La admisión no tiene el número de factura o el tipo de régimen"
                }
                return JsonResponse(response_data, status=400)
        else:
            return admision_response
    except ArchivoFacturacion.DoesNotExist:
        response_data = {
            "success": False,
            "detail": f"No se encontraron archivos para la admisión con número {numero_admision}"
        }
        return JsonResponse(response_data, status=404)
    except Exception as e:
        response_data = {
            "success": False,
            "detail": str(e)
        }
        return JsonResponse(response_data, status=500)
##### OTROS #############

def limpiar_nombre_archivo(nombre):
    nombre = unquote(nombre)  # Decodificar URL
    nombre = nombre.replace("%20", " ")  # Reemplazar codificaciones de espacio por espacios
    return nombre

@api_view(['GET'])
@permission_classes([AllowAny])  # Permitir acceso a cualquier usuario
def radicar_other_view(request, numero_admision, idusuario):
    try:
        # Verificar si ya está radicado
        archivos_a_verificar = ArchivoFacturacion.objects.filter(Admision_id=numero_admision)
        if archivos_a_verificar.exists() and archivos_a_verificar.filter(Radicado=True).exists():
            response_data = {
                "success": False,
                "detail": f"La admisión con número {numero_admision} ya está radicada."
            }
            return JsonResponse(response_data, status=400)

        # Obtener los datos de admisión
        admision_response = GeDocumentalView().get(request._request, consecutivo=numero_admision)
        if admision_response.status_code != 200:
            return admision_response

        admision_data = admision_response.data.get('data')
        factura_numero = admision_data.get('FacturaNo')
        prefijo = admision_data.get('Prefijo')
        codigo_entidad = admision_data.get('CodigoEntidad')

        if factura_numero is not None:
            # Obtener los archivos de la admisión
            archivos_response = archivos_por_admision_radicacion(request._request, numero_admision)
            if archivos_response.status_code != 200:
                return archivos_response

            archivos_data = archivos_response.data.get('data', [])

            # Validar la presencia de los archivos requeridos
            documentos_requeridos = {'FACTURA', 'RESULTADO'}
            tipos_archivos_presentes = {archivo.get('Tipo') for archivo in archivos_data}
            documentos_faltantes = documentos_requeridos - tipos_archivos_presentes

            if documentos_faltantes:
                response_data = {
                    "success": False,
                    "detail": f"Faltan los siguientes documentos requeridos: {', '.join(documentos_faltantes)}"
                }
                return JsonResponse(response_data, status=400)

            # Verificar si el usuario existe y obtener el nombre
            try:
                user = CustomUser.objects.get(id=idusuario)
                nombre_usuario = user.username  # Obtener el nombre del usuario para usar en la carpeta
                # Sanitizar el nombre del usuario si es necesario
                nombre_usuario = "".join(c for c in nombre_usuario if c.isalnum() or c in (' ', '.', '_')).rstrip()
                print(f"Nombre del usuario sanitizado para crear carpeta: {nombre_usuario}")
            except CustomUser.DoesNotExist:
                response_data = {
                    "success": False,
                    "detail": "Usuario no encontrado."
                }
                return JsonResponse(response_data, status=404)

            # Procesar y combinar los archivos en un PDF
            merger = PdfMerger()

            for archivo in archivos_data:
                tipo_archivo = archivo.get('Tipo')
                ruta_origen_relative = unquote(archivo.get('RutaArchivo'))
                ruta_origen_relative = ruta_origen_relative.replace(settings.MEDIA_URL, "").lstrip('/')
                ruta_origen = os.path.normpath(os.path.join(settings.MEDIA_ROOT, ruta_origen_relative))

                print(f'Ruta formada para {tipo_archivo}: {ruta_origen}')

                if os.path.exists(ruta_origen):
                    merger.append(ruta_origen)
                else:
                    raise FileNotFoundError(f"No se encontró el archivo {tipo_archivo} en {ruta_origen}")

            # Definir la carpeta de destino basada en el código de la entidad
            carpetas_entidades = {
                "POL12": "POL12",
                "PML01": "PML01",
                "CAJACO": "CAJACO",
                "CAJASU": "CAJASU",
                "UNA01": "UNA01",
                "DM02": "DM02",
                "EQV01": "EQV01",
                "PAR01": "PAR01",
                "CHM05": "CHM05",
                "COL01": "COL01",
                "MES01": "MES01",
                "POL11": "POL11",
                "CHM02": "CHM02",
                "UNA02": "UNA02",
                "MUL01": "MUL01",
                "FOM01": "FOM01",
                "IPSOL1": "IPSOL1",
                "AIR01": "AIR01",
                "AXA01": "AXA01",
                "POL13": "POL13",
                "BOL01": "BOL01",
                    
            }
            entidad_carpeta = carpetas_entidades.get(codigo_entidad, "OTRO")

            # Crear la ruta completa del archivo destino usando el nombre del usuario
            fecha_hoy = datetime.now().strftime('%Y-%m-%d')
            carpeta_nombre_archivo = os.path.join(settings.MEDIA_ROOT, 'gdocumental', 'Radicacion', entidad_carpeta, fecha_hoy, nombre_usuario)
            if not os.path.exists(carpeta_nombre_archivo):
                os.makedirs(carpeta_nombre_archivo)

            ruta_destino_merged = os.path.join(carpeta_nombre_archivo, f"{prefijo}{factura_numero}.pdf")
            merger.write(ruta_destino_merged)
            merger.close()

            # Verificar registros antes de la actualización
            print(f"Registros encontrados para actualizar: {archivos_a_verificar.count()}")
            for archivo in archivos_a_verificar:
                print(f"Antes de la actualización - IdArchivo: {archivo.IdArchivo}, Radicado: {archivo.Radicado}")

            # Actualizar el campo Radicado en la tabla archivos
            actualizados = archivos_a_verificar.update(Radicado=True)
            print(f"Registros actualizados a Radicado=True: {actualizados}")

            # Verificar registros después de la actualización
            archivos_actualizados = ArchivoFacturacion.objects.filter(Admision_id=numero_admision, Radicado=True)
            for archivo in archivos_actualizados:
                print(f"Después de la actualización - IdArchivo: {archivo.IdArchivo}, Radicado: {archivo.Radicado}")

            response_data = {
                "success": True,
                "detail": f"Archivos combinados en un solo documento y guardados en {ruta_destino_merged}"
            }
            return JsonResponse(response_data, status=200)
        else:
            raise ValueError("La admisión no tiene el número de factura.")
    except ArchivoFacturacion.DoesNotExist:
        response_data = {
            "success": False,
            "detail": f"No se encontraron archivos para la admisión con número {numero_admision}"
        }
        return JsonResponse(response_data, status=404)
    except Exception as e:
        response_data = {
            "success": False,
            "detail": str(e)
        }
        return JsonResponse(response_data, status=500)




########## PUNTEO APP###########class AdmisionesPorFechaYUsuario(APIView):

class AdmisionesPorFechaYUsuario(APIView):
    def get(self, request, format=None):
        fecha_creacion_archivo = request.GET.get('FechaCreacionAntares')
        usuario_id = request.GET.get('UsuarioId')

        if fecha_creacion_archivo and usuario_id:
            try:
                # Filtrar las admisiones por fecha de creación y usuario, ordenar y agrupar por Admision_id
                admisiones_queryset = (ArchivoFacturacion.objects
                                       .filter(FechaCreacionAntares__date=fecha_creacion_archivo, Usuario_id=usuario_id)
                                       .values('Admision_id')
                                       .annotate(cantidad=Count('Admision_id'))
                                       .order_by('Admision_id'))  # Ordenar por Admision_id

                admisiones_count = admisiones_queryset.count()

                admisiones_list = []
                for admision in admisiones_queryset:
                    admision_dict = {
                        'Consecutivo': admision['Admision_id'],
                    }
                    admisiones_list.append(admision_dict)

                response_data = {
                    "success": True,
                    "detail": "Admisiones encontradas.",
                    "cantidad": admisiones_count,
                    "data": admisiones_list
                }
                return JsonResponse(response_data)
            except Exception as e:
                response_data = {
                    "success": False,
                    "detail": f"Error al buscar admisiones: {str(e)}",
                    "cantidad": None,
                    "data": None
                }
                return JsonResponse(response_data, status=500)
        else:
            response_data = {
                "success": False,
                "detail": "Faltan parámetros: FechaCreacionArchivo y/o UsuarioId.",
                "cantidad": None,
                "data": None
            }
            return JsonResponse(response_data, status=400)
        


########## FILTRO DE PUNTEO ADMISIONES ####

class AdmisionesPorFechaYFacturado(APIView):
    def get(self, request, format=None):
        fecha = request.GET.get('Fecha')
        creado_por = request.GET.get('CreadoPor')

        if fecha and creado_por:
            try:
                with connections['datosipsndx'].cursor() as cursor:
                    query_count = '''
                    SELECT COUNT(*) as cantidad
                    FROM admisiones
                    WHERE DATE(FechaCreado) = %s AND CreadoPor = %s
                    '''
                    cursor.execute(query_count, [fecha, creado_por])
                    admisiones_count = cursor.fetchone()[0]

                    query_details = '''
                    SELECT *
                    FROM admisiones
                    WHERE DATE(FechaCreado) = %s AND CreadoPor = %s
                    '''
                    cursor.execute(query_details, [fecha, creado_por])
                    admisiones_data = cursor.fetchall()

                    admisiones_list = []
                    for admision_data in admisiones_data:
                        consecutivo = admision_data[0]
                        admision_dict = {
                            'Consecutivo': consecutivo,
                        }

                        # Obtener el prefijo de la tabla facturas
                        query_facturas = '''
                        SELECT prefijo
                        FROM facturas
                        WHERE AdmisionNo = %s
                        '''
                        cursor.execute(query_facturas, [consecutivo])
                        prefijo = cursor.fetchone()

                        if prefijo:
                            admision_dict['Prefijo'] = prefijo[0]
                        else:
                            admision_dict['Prefijo'] = None

                        admisiones_list.append(admision_dict)

                response_data = {
                    "success": True,
                    "detail": "Admisiones encontradas.",
                    "cantidad": admisiones_count,
                    "data": admisiones_list
                }
                return JsonResponse(response_data)
            except Exception as e:
                response_data = {
                    "success": False,
                    "detail": f"Error al buscar admisiones: {str(e)}",
                    "cantidad": None,
                    "data": None
                }
                return JsonResponse(response_data, status=500)
        else:
            response_data = {
                "success": False,
                "detail": "Faltan parámetros: fecha y/o facturado_por.",
                "cantidad": None,
                "data": None
            }
            return JsonResponse(response_data, status=400)


###### PUNTEO SUBDIRECCION DE PROCESOS Y DIRECCION ####


class PunteoNeurodxSubdireccion(APIView):
    def get(self, request, format=None):
        fecha_inicio = request.GET.get('FechaInicio')
        fecha_fin = request.GET.get('FechaFin')
        usuario_id = request.GET.get('UsuarioId')

        if fecha_inicio and fecha_fin and usuario_id:
            try:
                # Filtrar las admisiones por el rango de fechas y usuario, ordenar y agrupar por Admision_id
                admisiones_queryset = (ArchivoFacturacion.objects
                                       .filter(FechaCreacionAntares__date__range=[fecha_inicio, fecha_fin], 
                                               Usuario_id=usuario_id)
                                       .values('Admision_id')
                                       .annotate(cantidad=Count('Admision_id'))
                                       .order_by('Admision_id'))  # Ordenar por Admision_id

                admisiones_count = admisiones_queryset.count()

                admisiones_list = []
                for admision in admisiones_queryset:
                    admision_dict = {
                        'Consecutivo': admision['Admision_id'],
                    }
                    admisiones_list.append(admision_dict)

                response_data = {
                    "success": True,
                    "detail": "Admisiones encontradas.",
                    "cantidad": admisiones_count,
                    "data": admisiones_list
                }
                return JsonResponse(response_data)
            except Exception as e:
                response_data = {
                    "success": False,
                    "detail": f"Error al buscar admisiones: {str(e)}",
                    "cantidad": None,
                    "data": None
                }
                return JsonResponse(response_data, status=500)
        else:
            response_data = {
                "success": False,
                "detail": "Faltan parámetros: FechaInicio, FechaFin y/o UsuarioId.",
                "cantidad": None,
                "data": None
            }
            return JsonResponse(response_data, status=400)


##### PUNTEO ADMISIONES ANTARES, SUBDIRECCION ####
class PunteoAntaresSubdireccion(APIView):
    def get(self, request, format=None):
        fecha_inicio = request.GET.get('FechaInicio')
        fecha_fin = request.GET.get('FechaFin')
        creado_por = request.GET.get('CreadoPor')

        if fecha_inicio and fecha_fin and creado_por:
            try:
                with connections['datosipsndx'].cursor() as cursor:
                    query_count = '''
                    SELECT COUNT(*) as cantidad
                    FROM admisiones
                    WHERE DATE(FechaCreado) BETWEEN %s AND %s AND CreadoPor = %s
                    '''
                    cursor.execute(query_count, [fecha_inicio, fecha_fin, creado_por])
                    admisiones_count = cursor.fetchone()[0]

                    query_details = '''
                    SELECT *
                    FROM admisiones
                    WHERE DATE(FechaCreado) BETWEEN %s AND %s AND CreadoPor = %s
                    '''
                    cursor.execute(query_details, [fecha_inicio, fecha_fin, creado_por])
                    admisiones_data = cursor.fetchall()

                    admisiones_list = []
                    for admision_data in admisiones_data:
                        consecutivo = admision_data[0]
                        admision_dict = {
                            'Consecutivo': consecutivo,
                        }

                        # Obtener el prefijo de la tabla facturas
                        query_facturas = '''
                        SELECT prefijo
                        FROM facturas
                        WHERE AdmisionNo = %s
                        '''
                        cursor.execute(query_facturas, [consecutivo])
                        prefijo = cursor.fetchone()

                        if prefijo:
                            admision_dict['Prefijo'] = prefijo[0]
                        else:
                            admision_dict['Prefijo'] = None

                        admisiones_list.append(admision_dict)

                response_data = {
                    "success": True,
                    "detail": "Admisiones encontradas.",
                    "cantidad": admisiones_count,
                    "data": admisiones_list
                }
                return JsonResponse(response_data)
            except Exception as e:
                response_data = {
                    "success": False,
                    "detail": f"Error al buscar admisiones: {str(e)}",
                    "cantidad": None,
                    "data": None
                }
                return JsonResponse(response_data, status=500)
        else:
            response_data = {
                "success": False,
                "detail": "Faltan parámetros: FechaInicio, FechaFin y/o CreadoPor.",
                "cantidad": None,
                "data": None
            }
            return JsonResponse(response_data, status=400)
        

### FILTRO POR TIPO DE DOCUMENTO######
class AdmisionesConTiposDeDocumento(APIView):
    def get(self, request, format=None):
        # Recuperar parámetros de la solicitud
        fecha_inicio = request.GET.get('FechaInicio')
        fecha_fin = request.GET.get('FechaFin')
        usuario_id = request.GET.get('UsuarioId')

        # Verificar la existencia de los parámetros requeridos
        if fecha_inicio and fecha_fin and usuario_id:
            try:
                # Filtrar admisiones por el rango de fechas de FechaCreacionAntares y el usuario
                admisiones_queryset = (
                    ArchivoFacturacion.objects
                    .filter(
                        FechaCreacionAntares__date__range=[fecha_inicio, fecha_fin],
                        Usuario_id=usuario_id
                    )
                    .values('Admision_id', 'FechaCreacionAntares')
                    .annotate(cantidad=Count('Admision_id'))
                    .order_by('Admision_id')
                )

                # Orden deseado para los tipos de documentos
                tipos_documento_ordenados = [
                    'FACTURA', 'COMPROBANTE', 'AUTORIZACION', 'ORDEN',
                    'ADICIONALES', 'RESULTADO', 'HCNEURO', 'HCLINICA'
                ]

                admisiones_list = []
                for admision in admisiones_queryset:
                    admision_id = admision['Admision_id']
                    fecha_creacion_antares = admision['FechaCreacionAntares']

                    # Formatear FechaCreacionAntares a solo incluir año, mes, día
                    fecha_creacion_antares_str = fecha_creacion_antares.strftime('%Y-%m-%d') if fecha_creacion_antares else None

                    # Recuperar el 'CodigoEntidad' asociado con el 'Admision_id'
                    codigo_entidad = None
                    try:
                        with connections['datosipsndx'].cursor() as cursor:
                            query_entidad = 'SELECT CodigoEntidad FROM admisiones WHERE Consecutivo = %s'
                            cursor.execute(query_entidad, [admision_id])
                            entidad_info = cursor.fetchone()
                            codigo_entidad = entidad_info[0] if entidad_info else None
                    except Exception as e:
                        # Registrar o manejar error si no se puede recuperar el CodigoEntidad
                        pass

                    # Obtener y verificar los tipos de documentos asociados a la admisión
                    tipos_documento = (
                        ArchivoFacturacion.objects
                        .filter(Admision_id=admision_id)
                        .values('Tipo')
                    )
                    tipos_documento_list = [tipo['Tipo'] for tipo in tipos_documento]

                    # Inicializar un diccionario con valores en blanco para cada tipo esperado
                    tipos_documento_dict = {tipo: '' for tipo in tipos_documento_ordenados}

                    # Verificar y completar el diccionario con valores reales desde los documentos obtenidos
                    for tipo in tipos_documento_list:
                        if tipo in tipos_documento_dict:
                            tipos_documento_dict[tipo] = tipo

                    # Convertir el diccionario a una lista siguiendo el orden deseado
                    tipos_documento_list_sorted = [tipos_documento_dict[tipo] for tipo in tipos_documento_ordenados]

                    admision_dict = {
                        'Consecutivo': admision_id,
                        'FechaCreacionAntares': fecha_creacion_antares_str,
                        'CodigoEntidad': codigo_entidad,
                        'TiposDeDocumento': tipos_documento_list_sorted,
                    }
                    admisiones_list.append(admision_dict)

                response_data = {
                    "success": True,
                    "detail": "Admisiones encontradas.",
                    "cantidad": len(admisiones_list),
                    "data": admisiones_list
                }
                return JsonResponse(response_data)

            except Exception as e:
                response_data = {
                    "success": False,
                    "detail": f"Error al buscar admisiones: {str(e)}",
                    "cantidad": None,
                    "data": None
                }
                return JsonResponse(response_data, status=500)

        else:
            response_data = {
                "success": False,
                "detail": "Faltan parámetros: FechaInicio, FechaFin y/o UsuarioId.",
                "cantidad": None,
                "data": None
            }
            return JsonResponse(response_data, status=400)

        

class ActualizarRegimenArchivosView(APIView):
    def post(self, request, consecutivo, format=None):
        regimen = request.data.get('regimen')
        
        if not regimen or regimen not in ['C', 'S']:
            return Response({"success": False, "message": "Regimen inválido"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with transaction.atomic():
                archivos_actualizados = ArchivoFacturacion.objects.filter(Admision_id=consecutivo).update(Regimen=regimen)
                
                if archivos_actualizados == 0:
                    return Response({"success": False, "message": f"No se encontraron archivos para la admisión {consecutivo}"}, status=status.HTTP_404_NOT_FOUND)
                
                return Response({"success": True, "message": f"Regimen actualizado a {regimen} para {archivos_actualizados} archivos de la admisión {consecutivo}"}, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({"success": False, "message": "Error interno del servidor", "error_details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


### CREAR OBSERVACIONES SIN ARCHIVO PARA LOS RESULTADOS QUE NO ESTAN CARGADOS !
class AgregarObservacionSinArchivoView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = ObservacionSinArchivoSerializer(data=request.data)
        if serializer.is_valid():
            observacion = serializer.save()
            response_data = {
                "id": observacion.id,
                "AdmisionId": observacion.AdmisionId,
                "Descripcion": observacion.Descripcion,
                "FechaObservacion": observacion.FechaObservacion,
                "Revisada": observacion.Revisada,
                "Usuario": observacion.Usuario.id
            }
            return Response({"success": True, "message": "Observación sin archivo agregada correctamente", "data": response_data}, status=status.HTTP_201_CREATED)
        return Response({"success": False, "message": "Error de validación", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    


#### ADMISION SIN ARCHIVO#####
class ObservacionesPorUsuario(APIView):
    def get(self, request, user_id):
        try:
            # Filtrar las observaciones por usuario
            observaciones = ObservacionSinArchivo.objects.filter(Usuario_id=user_id)
            print(f"Usuario_id: {user_id}, Observaciones count: {observaciones.count()}")  # Debugging line
            
            # Filtrar las observaciones que están asociadas a una admisión donde no todos los archivos tienen RevisionPrimera en True
            observaciones_filtradas = []
            for observacion in observaciones:
                admision_id = observacion.AdmisionId
                archivos = ArchivoFacturacion.objects.filter(Admision_id=admision_id)
                
                # Agrega la observación a la lista si no todos los archivos tienen RevisionPrimera en True
                if archivos.exists() and not archivos.filter(RevisionPrimera=True).count() == archivos.count():
                    observaciones_filtradas.append(observacion)
            
            if not observaciones_filtradas:
                return Response({'error': 'Observaciones no encontradas para este usuario'}, status=404)

            # Serializar las observaciones filtradas
            serializer = ObservacionSinArchivoSerializer(observaciones_filtradas, many=True)
            return Response(serializer.data, status=200)

        except Exception as e:
            response_data = {
                "success": False,
                "detail": "Error interno del servidor",
                "error_details": str(e)
            }
            return JsonResponse(response_data, status=500)


        

####  MODIFICACION REALIZADA ADMISON SIN ARCHIVO #####
class RevisarObservacion(APIView):
    def patch(self, request, admision_id):
        # Obtener todas las observaciones con el AdmisionId dado
        observaciones = ObservacionSinArchivo.objects.filter(AdmisionId=admision_id)
        if not observaciones.exists():
            return Response({'error': 'Observación no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        # Buscar un archivo con un UsuarioCuentasMedicas_id asociado
        try:
            archivo = ArchivoFacturacion.objects.filter(
                Admision_id=admision_id,
                UsuarioCuentasMedicas__isnull=False
            ).order_by('-FechaCreacionArchivo').first()

            if archivo is None:
                return Response({'error': 'No se encontró archivo con UsuarioCuentasMedicas asociado con la admisión'}, status=status.HTTP_404_NOT_FOUND)
            
            id_revisor = archivo.UsuarioCuentasMedicas_id  # Tomar el Id del UsuarioCuentasMedicas

            print(f"Archivo encontrado: {archivo}")
            print(f"UsuarioCuentasMedicas asociado: {archivo.UsuarioCuentasMedicas}")
            print(f"IdRevisor (UsuarioCuentasMedicas_id) obtenido: {id_revisor}")

        except ArchivoFacturacion.DoesNotExist:
            return Response({'error': 'Revisor no encontrado'}, status=status.HTTP_404_NOT_FOUND)

        # Iterar sobre todas las observaciones encontradas y actualizarlas
        for observacion in observaciones:
            request_data = request.data.copy()
            request_data['IdRevisor'] = id_revisor
            request_data['Revisada'] = True

            serializer = ObservacionSinArchivoSerializer(observacion, data=request_data, partial=True)
            if serializer.is_valid():
                serializer.save()
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response({'status': 'Observaciones actualizadas correctamente'}, status=status.HTTP_200_OK)




import logging
logger = logging.getLogger(__name__)
@api_view(['POST'])
def actualizar_modificado_revisor(request):
    data = request.data
    admision_id = data.get('admision_id')
    tipo_revisor = data.get('tipo_revisor')

    print(f"Datos recibidos: admision_id={admision_id}, tipo_revisor={tipo_revisor}")

    try:
        with transaction.atomic():
            archivos = ArchivoFacturacion.objects.filter(Admision_id=admision_id)
            if not archivos.exists():
                print(f"No se encontraron archivos para la admisión {admision_id}")
                return JsonResponse({"success": False, "detail": "Archivo no encontrado"}, status=404)

            for archivo in archivos:
                print(f"Procesando archivo con IdArchivo: {archivo.IdArchivo}")

                # Asignar idRevisor basado en tipo_revisor
                if tipo_revisor == "cuentas_medicas":
                    if archivo.UsuarioCuentasMedicas_id:
                        archivo.IdRevisor = archivo.UsuarioCuentasMedicas_id
                        print(f"Asignado UsuarioCuentasMedicas_id: {archivo.UsuarioCuentasMedicas_id} a IdRevisor")
                    else:
                        print("UsuarioCuentasMedicas_id es None")
                elif tipo_revisor == "tesoreria":
                    if archivo.UsuariosTesoreria_id:
                        archivo.IdRevisor = archivo.UsuariosTesoreria_id
                        print(f"Asignado UsuariosTesoreria_id: {archivo.UsuariosTesoreria_id} a IdRevisor")
                    else:
                        print("UsuariosTesoreria_id es None")

                print(f"IdRevisor asignado: {archivo.IdRevisor}")

                # Actualizar los campos de modificado
                if archivo.Modificado1 is None:
                    archivo.Modificado1 = 1
                    print("Modificado1 actualizado a 1")
                elif archivo.Modificado1 == 1 and archivo.Modificado2 is None:
                    archivo.Modificado2 = 1
                    print("Modificado2 actualizado a 1")
                elif archivo.Modificado2 == 1 and archivo.Modificado3 is None:
                    archivo.Modificado3 = 1
                    print("Modificado3 actualizado a 1")

                archivo.save()
                print(f"Archivo guardado con IdArchivo: {archivo.IdArchivo}, Modificado1: {archivo.Modificado1}, Modificado2: {archivo.Modificado2}, Modificado3: {archivo.Modificado3}, IdRevisor: {archivo.IdRevisor}")

            return JsonResponse({"success": True, "detail": "Archivos actualizados correctamente"})

    except Exception as e:
        print(f"Error al actualizar archivos: {str(e)}")
        return JsonResponse({"success": False, "detail": str(e)}, status=500)


######## admisiones ya modofocadas para cuentas medicas o tesoreria 

def admisiones_con_id_revisor(request, id_revisor):
    try:
        # Filtrar registros de ArchivoFacturacion para el revisor dado
        archivos = ArchivoFacturacion.objects.filter(IdRevisor=id_revisor)

        # Obtener los Ids de las admisiones con los archivos filtrados
        admisiones_ids = archivos.values_list('Admision_id', flat=True).distinct()

        # Filtrar registros de AuditoriaCuentasMedicas con la condición especificada (solo con IdRevisor)
        admisiones_con_revisor = AuditoriaCuentasMedicas.objects.filter(
            AdmisionId__in=admisiones_ids
        )

        admisiones_data = []
        with connections['datosipsndx'].cursor() as cursor:
            for auditoria in admisiones_con_revisor:
                # Verificar si hay algún archivo asociado con RevisionPrimera=False
                archivos_admision = ArchivoFacturacion.objects.filter(Admision_id=auditoria.AdmisionId)
                if not archivos_admision.filter(RevisionPrimera=False).exists():
                    continue

                # Obtener datos de la admisión
                query_admision = '''
                    SELECT Consecutivo, IdPaciente, CodigoEntidad, NombreResponsable, FacturaNo
                    FROM admisiones
                    WHERE Consecutivo = %s
                '''
                cursor.execute(query_admision, [auditoria.AdmisionId])
                admision_data = cursor.fetchone()

                if admision_data:
                    # Consulta para obtener el prefijo de la factura asociada a la admisión
                    query_factura = 'SELECT Prefijo FROM facturas WHERE AdmisionNo = %s'
                    cursor.execute(query_factura, [auditoria.AdmisionId])
                    factura_info = cursor.fetchone()

                    prefijo = factura_info[0] if factura_info else ''
                    numero_factura = admision_data[4] if len(admision_data) > 4 else ''
                    factura_completa = f"{prefijo}{numero_factura}"

                    transformed_data = {
                        'Consecutivo': admision_data[0],
                        'IdPaciente': admision_data[1],
                        'CodigoEntidad': admision_data[2],
                        'NombreResponsable': admision_data[3],
                        'FacturaNo': factura_completa,
                    }
                    admisiones_data.append(transformed_data)

        response_data = {
            "success": True,
            "detail": f"Admisiones con el revisor ID {id_revisor} encontradas",
            "data": admisiones_data
        }

        return JsonResponse(response_data, status=200)

    except AuditoriaCuentasMedicas.DoesNotExist:
        response_data = {
            "success": False,
            "detail": f"No se encontraron admisiones con el revisor ID {id_revisor}",
            "data": None
        }

        return JsonResponse(response_data, status=404)

    except Exception as e:
        response_data = {
            "success": False,
            "detail": "Error interno del servidor",
            "error_details": str(e)
        }

        return JsonResponse(response_data, status=500)
      
      
      
# ELIMINACION DE ARCHIVOS 
class ArchivoFacturacionDeleteView(APIView):
    def delete(self, request):
        archivo_id = request.query_params.get('archivo_id', None)
        print(f"Received request to delete archivo_id: {archivo_id}")

        if not archivo_id:
            print("archivo_id is missing in the request")
            return Response({"error": "archivo_id is required"}, status=400)

        try:
            archivo = ArchivoFacturacion.objects.get(pk=archivo_id)
            print(f"Archivo encontrado: {archivo}")
            ruta_archivo = archivo.RutaArchivo.path if archivo.RutaArchivo else None
            print(f"Ruta del archivo: {ruta_archivo}")

            # Eliminar el archivo de la base de datos
            archivo.delete()
            print(f"Archivo {archivo_id} eliminado de la base de datos")

            # Verificar si el archivo existe en el sistema de archivos antes de eliminarlo
            if ruta_archivo and os.path.exists(ruta_archivo):
                os.remove(ruta_archivo)
                print(f"Archivo {ruta_archivo} eliminado del sistema de archivos")

            return Response(status=status.HTTP_204_NO_CONTENT)
        except ArchivoFacturacion.DoesNotExist:
            print(f"Archivo con ID {archivo_id} no encontrado")
            return Response({"detail": "Archivo no encontrado"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(f"Error al eliminar el archivo: {str(e)}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
          
          
######## ADMISIONES REVISADAS DE CUENTAS MEDICAS A TESORERIA 

def admisiones_revisada_cm(request, idusuariorevisor):
    try:
        # Filtrar registros de ArchivoFacturacion para el revisor dado
        archivos = ArchivoFacturacion.objects.filter(IdRevisor=idusuariorevisor)

        # Obtener los Ids de las admisiones con los archivos filtrados
        admisiones_ids = archivos.values_list('Admision_id', flat=True).distinct()

        # Filtrar registros de AuditoriaCuentasMedicas con la condición especificada (solo con IdRevisor)
        admisiones_con_revisor = AuditoriaCuentasMedicas.objects.filter(
            AdmisionId__in=admisiones_ids
        )

        admisiones_data = []
        with connections['datosipsndx'].cursor() as cursor:
            for auditoria in admisiones_con_revisor:
                # Verificar si hay algún archivo asociado con RevisionPrimera=False
                archivos_admision = ArchivoFacturacion.objects.filter(Admision_id=auditoria.AdmisionId)
                if not archivos_admision.filter(RevisionPrimera=False).exists():
                    continue

                # Obtener datos de la admisión
                query_admision = '''
                    SELECT Consecutivo, IdPaciente, CodigoEntidad, NombreResponsable, FacturaNo
                    FROM admisiones
                    WHERE Consecutivo = %s
                '''
                cursor.execute(query_admision, [auditoria.AdmisionId])
                admision_data = cursor.fetchone()

                if admision_data:
                    # Consulta para obtener el prefijo de la factura asociada a la admisión
                    query_factura = 'SELECT Prefijo FROM facturas WHERE AdmisionNo = %s'
                    cursor.execute(query_factura, [auditoria.AdmisionId])
                    factura_info = cursor.fetchone()

                    prefijo = factura_info[0] if factura_info else ''
                    numero_factura = admision_data[4] if len(admision_data) > 4 else ''
                    factura_completa = f"{prefijo}{numero_factura}"

                    transformed_data = {
                        'Consecutivo': admision_data[0],
                        'IdPaciente': admision_data[1],
                        'CodigoEntidad': admision_data[2],
                        'NombreResponsable': admision_data[3],
                        'FacturaNo': factura_completa,
                    }
                    admisiones_data.append(transformed_data)

        response_data = {
            "success": True,
            "detail": f"Admisiones con el revisor ID {idusuariorevisor} encontradas",
            "data": admisiones_data
        }

        return JsonResponse(response_data, status=200)

    except AuditoriaCuentasMedicas.DoesNotExist:
        response_data = {
            "success": False,
            "detail": f"No se encontraron admisiones con el revisor ID {idusuariorevisor}",
            "data": None
        }

        return JsonResponse(response_data, status=404)

    except Exception as e:
        response_data = {
            "success": False,
            "detail": "Error interno del servidor",
            "error_details": str(e)
        }

        return JsonResponse(response_data, status=500)



logger = logging.getLogger(__name__)

@api_view(['POST'])
def actualizar_correciones_cm(request):
    data = request.data
    admision_id = data.get('admision_id')
    user_id = data.get('user_id')

    print(f"Datos recibidos: admision_id={admision_id}, user_id={user_id}")

    try:
        with transaction.atomic():
            archivos = ArchivoFacturacion.objects.filter(Admision_id=admision_id)
            if not archivos.exists():
                print(f"No se encontraron archivos para la admisión {admision_id}")
                return JsonResponse({"success": False, "detail": "Archivo no encontrado"}, status=404)

            for archivo in archivos:
                print(f"Procesando archivo con IdArchivo: {archivo.IdArchivo}")

                # Asignar IdRevisor basado en user_id
                archivo.IdRevisor = user_id
                print(f"Asignado user_id: {user_id} a IdRevisor")

                # Actualizar los campos de modificado
                if archivo.Modificado1 is None:
                    archivo.Modificado1 = 1
                    print("Modificado1 actualizado a 1")
                elif archivo.Modificado1 == 1 and archivo.Modificado2 is None:
                    archivo.Modificado2 = 1
                    print("Modificado2 actualizado a 1")
                elif archivo.Modificado2 == 1 and archivo.Modificado3 is None:
                    archivo.Modificado3 = 1
                    print("Modificado3 actualizado a 1")

                archivo.save()
                print(f"Archivo guardado con IdArchivo: {archivo.IdArchivo}, Modificado1: {archivo.Modificado1}, Modificado2: {archivo.Modificado2}, Modificado3: {archivo.Modificado3}, IdRevisor: {archivo.IdRevisor}")

            return JsonResponse({"success": True, "detail": "Archivos actualizados correctamente"})

    except Exception as e:
        print(f"Error al actualizar archivos: {str(e)}")
        return JsonResponse({"success": False, "detail": str(e)}, status=500)

########## ENVIAR A TESORERIA ADMISIONES QUE AFECTAN CAJA##############
logger = logging.getLogger(__name__)

@api_view(['POST'])
def idrevisor_tesoreria(request):
    data = request.data
    admision_id = data.get('admision_id')
    user_id = data.get('user_id')

    print(f"Datos recibidos: admision_id={admision_id}, user_id={user_id}")

    try:
        with transaction.atomic():
            archivos = ArchivoFacturacion.objects.filter(Admision_id=admision_id)
            if not archivos.exists():
                print(f"No se encontraron archivos para la admisión {admision_id}")
                return JsonResponse({"success": False, "detail": "Archivo no encontrado"}, status=404)

            for archivo in archivos:
                print(f"Procesando archivo con IdArchivo: {archivo.IdArchivo}")

                # Asignar IdRevisor basado en user_id
                archivo.IdRevisorTesoreria = user_id
                print(f"Asignado user_id: {user_id} a IdRevisorTesoreria")

                # Actualizar los campos de modificado
                if archivo.Modificado1 is None:
                    archivo.Modificado1 = 1
                    print("Modificado1 actualizado a 1")
                elif archivo.Modificado1 == 1 and archivo.Modificado2 is None:
                    archivo.Modificado2 = 1
                    print("Modificado2 actualizado a 1")
                elif archivo.Modificado2 == 1 and archivo.Modificado3 is None:
                    archivo.Modificado3 = 1
                    print("Modificado3 actualizado a 1")

                archivo.save()
                print(f"Archivo guardado con IdArchivo: {archivo.IdArchivo}, Modificado1: {archivo.Modificado1}, Modificado2: {archivo.Modificado2}, Modificado3: {archivo.Modificado3}, IdRevisorTesoreria: {archivo.IdRevisorTesoreria}")

            return JsonResponse({"success": True, "detail": "Archivos actualizados correctamente"})

    except Exception as e:
        print(f"Error al actualizar archivos: {str(e)}")
        return JsonResponse({"success": False, "detail": str(e)}, status=500)

##### TRAE LAS ADMISIONES QUE HAN SIDO REVISDAS POR CM Y SON ENVIADAS A TESORERIA
@api_view(['GET'])
@permission_classes([AllowAny])
def admisiones_revision_para_cm(request, id_revisor):
    try:
        # Filtrar registros de ArchivoFacturacion para el revisor dado
        archivos = ArchivoFacturacion.objects.filter(IdRevisorTesoreria=id_revisor)

        # Obtener los Ids de las admisiones con los archivos filtrados
        admisiones_ids = archivos.values_list('Admision_id', flat=True).distinct()

        # Filtrar registros de AuditoriaCuentasMedicas con la condición especificada (solo con IdRevisor)
        admisiones_con_revisor = AuditoriaCuentasMedicas.objects.filter(
            AdmisionId__in=admisiones_ids
        )

        admisiones_data = []
        with connections['datosipsndx'].cursor() as cursor:
            for auditoria in admisiones_con_revisor:
                # Obtener datos de la admisión, incluyendo FechaCreado
                query_admision = '''
                    SELECT Consecutivo, IdPaciente, CodigoEntidad, NombreResponsable, FacturaNo, FechaCreado
                    FROM admisiones
                    WHERE Consecutivo = %s
                '''
                cursor.execute(query_admision, [auditoria.AdmisionId])
                admision_data = cursor.fetchone()

                if admision_data:
                    # Consulta para obtener el prefijo de la factura asociada a la admisión
                    query_factura = 'SELECT Prefijo FROM facturas WHERE AdmisionNo = %s'
                    cursor.execute(query_factura, [auditoria.AdmisionId])
                    factura_info = cursor.fetchone()

                    prefijo = factura_info[0] if factura_info else ''
                    numero_factura = admision_data[4] if len(admision_data) > 4 else ''
                    factura_completa = f"{prefijo}{numero_factura}"

                    # Formatear la FechaCreado para enviar solo año-mes-día
                    fecha_creado = admision_data[5].strftime('%Y-%m-%d') if admision_data[5] else None

                    # Obtener observaciones con archivos relacionados a la admisión
                    observaciones_archivos = ObservacionesArchivos.objects.filter(
                        IdArchivo__Admision_id=auditoria.AdmisionId
                    ).select_related('IdArchivo')

                    # Obtener observaciones sin archivos relacionadas a la admisión
                    observaciones_sin_archivo = ObservacionSinArchivo.objects.filter(
                        AdmisionId=auditoria.AdmisionId
                    ).select_related('Usuario')

                    # Listar las observaciones con archivos
                    observaciones_archivo_list = list(observaciones_archivos.values('IdObservacion', 'Descripcion', 'FechaObservacion'))

                    # Listar las observaciones sin archivos
                    observaciones_sin_archivo_list = list(observaciones_sin_archivo.values('id', 'Descripcion', 'FechaObservacion'))

                    # Obtener los nombres de los usuarios asociados a las observaciones
                    usuarios_con_observacion_archivo_ids = set(
                        observaciones_archivos.values_list('IdArchivo__Usuario_id', flat=True).distinct()
                    )

                    usuarios_con_observacion_sin_archivo_ids = set(
                        observaciones_sin_archivo.values_list('Usuario_id', flat=True).distinct()
                    )

                    # Combinar todos los usuarios que tienen observaciones
                    usuario_ids = list(usuarios_con_observacion_archivo_ids.union(usuarios_con_observacion_sin_archivo_ids))

                    # Consultar los nombres de los usuarios basados en los IDs
                    usuarios = CustomUser.objects.filter(id__in=usuario_ids).values_list('nombre', flat=True) 
                    usuarios_list = list(usuarios)  # Convertir QuerySet a lista

                    # Añadir los datos y observaciones al diccionario de respuesta
                    transformed_data = {
                        'Consecutivo': admision_data[0],
                        'IdPaciente': admision_data[1],
                        'CodigoEntidad': admision_data[2],
                        'NombreResponsable': admision_data[3],
                        'FacturaNo': factura_completa,
                        'FechaCreado': fecha_creado,  # Formatear FechaCreado a año-mes-día
                        'Usuarios': usuarios_list,
                        'ObservacionesArchivos': observaciones_archivo_list,
                        'ObservacionesSinArchivos': observaciones_sin_archivo_list
                    }
                    admisiones_data.append(transformed_data)

        response_data = {
            "success": True,
            "detail": f"Admisiones con el revisor ID {id_revisor} encontradas",
            "data": admisiones_data
        }

        return JsonResponse(response_data, status=200)

    except AuditoriaCuentasMedicas.DoesNotExist:
        response_data = {
            "success": False,
            "detail": f"No se encontraron admisiones con el revisor ID {id_revisor}",
            "data": None
        }

        return JsonResponse(response_data, status=404)

    except Exception as e:
        response_data = {
            "success": False,
            "detail": "Error interno del servidor",
            "error_details": str(e)
        }

        return JsonResponse(response_data, status=500)
#####

@api_view(['POST'])
def quitar_revisor_admision(request, numero_admision):
    try:
        # Filtrar registros de la admisión en la tabla ArchivoFacturacion
        archivos_a_modificar = ArchivoFacturacion.objects.filter(Admision_id=numero_admision)

        # Verificar si existen registros con ese número de admisión y un revisor asignado
        if not archivos_a_modificar.exists():
            return JsonResponse(
                {"success": False, "detail": f"No se encontraron registros para la admisión con número {numero_admision}."},
                status=404
            )

        # Actualizar el campo IdRevisor a 0 para desasociar del revisor actual
        archivos_a_modificar.update(IdRevisorTesoreria=0)

        response_data = {
            "success": True,
            "detail": f"El revisor ha sido desasociado de la admisión con número {numero_admision}."
        }

        return JsonResponse(response_data, status=200)

    except Exception as e:
        response_data = {
            "success": False,
            "detail": "Error interno del servidor",
            "error_details": str(e)
        }

        return JsonResponse(response_data, status=500)