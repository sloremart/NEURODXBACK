from datetime import datetime
from django.utils import timezone
from django.utils.timezone import make_aware
from django.db import IntegrityError, transaction
from django.db.models.functions import TruncDate
from sqlite3 import IntegrityError
from django.db import connections
from django.http import HttpResponse, JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import api_view
from gedocumental.modelsFacturacion import Admisiones
from gedocumental.utils.codigoentidad import obtener_tipos_documentos_por_entidad
from neurodx.settings import MEDIA_ROOT
from .serializers import   ArchivoFacturacionSerializer, RevisionCuentaMedicaSerializer
from django.http import Http404
from .models import ArchivoFacturacion, AuditoriaCuentasMedicas, ObservacionesArchivos

from django.conf import settings
import os



class GeDocumentalView(APIView):
    def get(self, request, consecutivo, format=None):
        with connections['datosipsndx'].cursor() as cursor:
            # Consulta para obtener la información de la admisión
            query_admision = '''
                SELECT Consecutivo, IdPaciente, CodigoEntidad, NombreResponsable, FacturaNo
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


                
                transformed_data = {
                    'Consecutivo': admision_data[0],
                    'IdPaciente': admision_data[1],
                    'CodigoEntidad': admision_data[2],
                    'NombreResponsable': admision_data[3],
                    'FacturaNo': admision_data[4] if len(admision_data) > 4 else None,
                    'Prefijo': factura_info[0] if factura_info else None,
                    'TiposDocumentos': tipos_documentos
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
        print(f"Consecutivo recibido en la vista: {consecutivo}")
        try:
            # Obtener la admisión asociada al consecutivo
            admision = Admisiones.objects.using('datosipsndx').get(Consecutivo=consecutivo)

            # Crear la carpeta con el nombre del número de admisión
            base_path = settings.ROOT_PATH_FILES_STORAGE
            if not os.path.exists(base_path):
                return JsonResponse({
                    "success": False,
                    "detail": f"El directorio base {base_path} no existe.",
                    "data": None
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            folder_path = os.path.join(MEDIA_ROOT, 'GeDocumental', 'archivosFacturacion', str(admision.Consecutivo))
            os.makedirs(folder_path, exist_ok=True)

            # Obtener la lista de archivos desde la solicitud
            archivos = request.FILES.getlist('files')
            print("Archivos recibidos en la vista:", archivos)
            archivos_guardados = []

            for archivo in archivos:
                archivo_path = os.path.join(folder_path, archivo.name)
                print(archivo_path)

                try:
                    # Guardar el archivo físicamente en la nueva ruta
                    with open(archivo_path, 'wb') as file:
                        for chunk in archivo.chunks():
                            file.write(chunk)

                    # Crear registro en ArchivoFacturacion
                    archivo_obj = ArchivoFacturacion(
                        Admision_id=admision.Consecutivo,
                        Tipo=request.data.get('tipoDocumentos', None),  
                        RutaArchivo=archivo_path
                    )

                    archivo_obj.NumeroAdmision = admision.Consecutivo
                    archivo_obj.save()
                    archivos_guardados.append({
                        "id": archivo_obj.IdArchivo,
                        "ruta": archivo_obj.RutaArchivo.url
                    })

                except IntegrityError as e:
                    return JsonResponse({
                        "success": False,
                        "detail": f"Error de integridad al guardar el archivo: {e}",
                        "data": None
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                except Exception as e:
                    return JsonResponse({
                        "success": False,
                        "detail": f"Error desconocido al guardar el archivo: {e}",
                        "data": None
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            response_data = {
                "success": True,
                "detail": f"Archivos guardados exitosamente para la admisión con consecutivo {consecutivo}",
                "data": archivos_guardados
            }

            return JsonResponse(response_data, status=status.HTTP_201_CREATED)

        except Admisiones.objects.using('datosipsndx').DoesNotExist:
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
                archivo.NombreArchivo = archivo_nuevo.name  # Actualizar el nombre del archivo
                archivo.RutaArchivo = archivo_nuevo  # Actualizar la ruta del archivo
                archivo.save(update_fields=['NombreArchivo', 'RutaArchivo'])  # Guardar solo los campos modificados

                # Actualizar la fecha de carga del archivo en la tabla de auditoría
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

        
############# archivos ############################
@api_view(['GET'])
def archivos_por_admision(request, numero_admision):
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

        try:
            with transaction.atomic():
                for archivo_data in archivos:
                    archivo_id = archivo_data.get('IdArchivo')
                    try:
                        archivo_existente = ArchivoFacturacion.objects.get(IdArchivo=archivo_id)
                        archivo_serializer = RevisionCuentaMedicaSerializer(archivo_existente, data=archivo_data, partial=True)

                        if archivo_serializer.is_valid():
                            archivo_serializer.save()
                        else:
                            errors = archivo_serializer.errors
                            return Response({"success": False, "message": "Error de validación en los datos del archivo", "error_details": errors}, status=status.HTTP_400_BAD_REQUEST)

                        observacion = archivo_data.get('Observacion')
                        if observacion is not None and observacion.strip():
                            observacion_obj = ObservacionesArchivos.objects.create(IdArchivo=archivo_existente, Descripcion =observacion)
                            print("Observación creada:", observacion_obj)

                    except ArchivoFacturacion.DoesNotExist:
                        return Response({"success": False, "message": f"Archivo con ID {archivo_id} no encontrado"}, status=status.HTTP_404_NOT_FOUND)

                admision_ids = [archivo_data.get('Admision_id') for archivo_data in archivos]

                auditoria_cuentas_medicas = AuditoriaCuentasMedicas.objects.filter(AdmisionId__in=admision_ids)
                todos_revision_primera_true = all(archivo_data.get('RevisionPrimera', False) for archivo_data in archivos)

                auditoria_cuentas_medicas.update(RevisionCuentasMedicas=todos_revision_primera_true)

                return Response({"success": True, "message": "Datos guardados correctamente"}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"success": False, "message": "Error interno del servidor", "error_details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

####### FILTRO DE ADMISIONES Y ARCHIVOS POR FECHA ####


class FiltroAuditoriaCuentasMedicas(APIView):
    def get(self, request):
        fecha_creacion_str = request.query_params.get('FechaCreacion', None)
        revision_cuentas_medicas = request.query_params.get('RevisionCuentasMedicas', None)

        queryset = AuditoriaCuentasMedicas.objects.all()

        if fecha_creacion_str:
            fecha_creacion = datetime.strptime(fecha_creacion_str, '%Y-%m-%d').date()
            queryset = queryset.annotate(creacion_date=TruncDate('FechaCreacion')).filter(creacion_date=fecha_creacion)

        if revision_cuentas_medicas is not None:
            queryset = queryset.filter(RevisionCuentasMedicas=bool(int(revision_cuentas_medicas)))

        response_data = []

        with connections['datosipsndx'].cursor() as cursor:
            for auditoria in queryset:
                cursor.execute('''
                    SELECT Consecutivo, IdPaciente, CodigoEntidad, NombreResponsable, FacturaNo
                    FROM admisiones
                    WHERE Consecutivo = %s
                ''', [auditoria.AdmisionId])
                admision_data = cursor.fetchone()

                if admision_data:
                    data = {
                        'AdmisionId': auditoria.AdmisionId,
                        'FechaCreacion': auditoria.FechaCreacion.isoformat(),
                        'FechaCargueArchivo': auditoria.FechaCargueArchivo.isoformat(),
                        'Observacion': auditoria.Observacion,
                        'RevisionCuentasMedicas': auditoria.RevisionCuentasMedicas,
                        'RevisionTesoreria': auditoria.RevisionTesoreria,
                        'Consecutivo': admision_data[0],
                        'IdPaciente': admision_data[1],
                        'CodigoEntidad': admision_data[2],
                        'NombreResponsable': admision_data[3],
                        'CedulaResponsable': admision_data[4],
                        'FacturaNo': admision_data[5] if len(admision_data) > 5 else None,
                    }
                    response_data.append(data)

        return Response(response_data)