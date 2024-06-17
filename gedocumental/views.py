from datetime import datetime
from django.utils import timezone
from django.utils.timezone import make_aware
import shutil
from django.db.models import Q, Max
from PyPDF2 import PdfMerger
from urllib.parse import unquote
from django.db import IntegrityError, transaction
from django.db.models.functions import TruncDate
from django.db import connections
from django.http import HttpResponse, JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import api_view
from gedocumental.modelsFacturacion import Admisiones
from gedocumental.utils.codigoentidad import obtener_tipos_documentos_por_entidad
from .serializers import   ArchivoFacturacionSerializer,  RevisionCuentaMedicaSerializer
from django.http import Http404
from .models import ArchivoFacturacion, AuditoriaCuentasMedicas, ObservacionesArchivos
from django.conf import settings
import os
from django.db.models import Count
from django.views.decorators.http import require_GET
from datetime import datetime, timedelta



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

            # Obtener la admisión
            admision = Admisiones.objects.using('datosipsndx').get(Consecutivo=consecutivo)

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
                ruta_relativa = os.path.relpath(archivo_path, settings.MEDIA_ROOT)

                # Crear el objeto ArchivoFacturacion
                fecha_creacion_archivo = datetime.now().replace(second=0, microsecond=0)
                fecha_formateada = fecha_creacion_archivo.strftime('%Y-%m-%d %H:%M:%S')  # Formatear la fecha sin segundos ni milisegundos
                archivo_obj = ArchivoFacturacion(
                    Admision_id=admision.Consecutivo,
                    Tipo=request.data.get('tipoDocumentos', None),
                    RutaArchivo=ruta_relativa,
                    FechaCreacionArchivo=fecha_formateada,
                    Usuario_id=user_id  
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
                        if observacion:
                            observacion_obj = ObservacionesArchivos.objects.create(
                                IdArchivo=archivo_existente,
                                Descripcion=observacion,
                                ObservacionCuentasMedicas=True  
                            )
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

######TESORERIA 

class AdmisionTesoreriaView(APIView):
    def post(self, request, *args, **kwargs):
        print("Datos recibidos en la solicitud:", request.data)
        data = request.data
        archivos = data.get('archivos', [])
        consecutivo_consulta = data.get('consecutivoConsulta')

        try:
            with transaction.atomic():
                for archivo_data in archivos:
                    archivo_id = archivo_data.get('IdArchivo')
                    revision_segunda = archivo_data.get('RevisionSegunda', False)

                    archivo = ArchivoFacturacion.objects.get(IdArchivo=archivo_id)
                    archivo.RevisionSegunda = revision_segunda
                    archivo.save()

                    # Aquí agregamos la lógica para crear la observación
                    observacion = archivo_data.get('Observacion')
                    if observacion:
                        observacion_obj = ObservacionesArchivos.objects.create(IdArchivo=archivo, Descripcion=observacion)
                        print("Observación creada:", observacion_obj)
                        observacion_obj.ObservacionTesoreria = True  # Se establece en True si es para tesorería
                        observacion_obj.save()

                    print(f"Se actualizó el campo RevisionSegunda para el archivo {archivo_id}")

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
        fecha_creacion_str = request.query_params.get('FechaCreacion', None)
        revision_cuentas_medicas = request.query_params.get('RevisionCuentasMedicas', None)
        codigo_entidad = request.query_params.get('CodigoEntidad', None)

        if not user_id:
            return Response({"error": "user_id is required"}, status=400)

        if fecha_creacion_str:
            fecha_creacion = datetime.strptime(fecha_creacion_str, '%Y-%m-%d')
            fecha_inicio = fecha_creacion.replace(hour=0, minute=0, second=0)
            fecha_fin = fecha_inicio + timedelta(days=1) - timedelta(seconds=1)
            archivos_facturacion = ArchivoFacturacion.objects.filter(FechaCreacionArchivo__date=fecha_creacion, Usuario_id=user_id)
            admision_ids = archivos_facturacion.values_list('Admision_id', flat=True)
            queryset = AuditoriaCuentasMedicas.objects.filter(AdmisionId__in=admision_ids)
        else:
            archivos_facturacion = ArchivoFacturacion.objects.filter(Usuario_id=user_id)
            admision_ids = archivos_facturacion.values_list('Admision_id', flat=True)
            queryset = AuditoriaCuentasMedicas.objects.filter(AdmisionId__in=admision_ids)

        response_data = []

        with connections['datosipsndx'].cursor() as cursor:
            for auditoria in queryset:
                cursor.execute('''
                    SELECT Consecutivo, IdPaciente, CodigoEntidad, NombreResponsable, FacturaNo, CedulaResponsable
                    FROM admisiones
                    WHERE Consecutivo = %s
                ''', [auditoria.AdmisionId])
                admision_data = cursor.fetchone()

                if admision_data:
                    if (revision_cuentas_medicas is None) or (bool(int(revision_cuentas_medicas)) == auditoria.RevisionCuentasMedicas):
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
                                'CedulaResponsable': admision_data[4],
                                'FacturaNo': admision_data[4] if len(admision_data) > 4 else None,
                            }
                            response_data.append(data)

        return Response(response_data)



class CodigoListView(APIView):
    def get(self, request, format=None):
        codigos = [
            'SAN01',
            'SAN02',
            'POL11',
            'POL12',
            'PML01',
            'COM01',
            'CAJACO',
            'CAJASU',
            'SAL01',
            'CAP01',
            'UNA01',
            'DM02',
            'EQV01',
            'PAR01',
            'CHM01',
            'CHM02',
            'COL01',
            'MES01',
            'SAL01'
        ]
        return Response(codigos)
    

### FILTRO QUE TRAE LAS ADM QUE TIENEN OBSER CM  ######
def admisiones_con_observaciones_por_usuario(request, usuario_id):
    try:
        # Filtrar registros de ObservacionesArchivos para el usuario dado
        observaciones = ObservacionesArchivos.objects.filter(
            IdArchivo__Usuario_id=usuario_id
        ).filter(
            Q(ObservacionCuentasMedicas=True) | Q(ObservacionTesoreria=True)
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

                    # Obtener la fecha más reciente de observación para la admisión
                    fecha_reciente_observacion = ObservacionesArchivos.objects.filter(
                        IdArchivo__Admision_id=auditoria.AdmisionId
                    ).aggregate(max_fecha=Max('FechaObservacion'))['max_fecha']

                    transformed_data = {
                        'Consecutivo': admision_data[0],
                        'IdPaciente': admision_data[1],
                        'CodigoEntidad': admision_data[2],
                        'NombreResponsable': admision_data[3],
                        'FacturaNo': factura_completa,
                        'FechaRecienteObservacion': fecha_reciente_observacion
                    }
                    admisiones_data.append(transformed_data)

        response_data = {
            "success": True,
            "detail": f"Admisiones con observaciones encontradas para el usuario con ID {usuario_id}",
            "data": admisiones_data
        }

        return JsonResponse(response_data, status=200)

    except AuditoriaCuentasMedicas.DoesNotExist:
        response_data = {
            "success": False,
            "detail": f"No se encontraron admisiones con observaciones para el usuario con ID {usuario_id}",
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

#####FILTRO QUE TRAE LAS ADM QUE TIENEN OBSER CM Y TESOERIA###################
def admisiones_con_revision_tesoreria(request, usuario_id):
    try:
        # Filtrar registros de ObservacionesArchivos para el usuario dado
        observaciones = ObservacionesArchivos.objects.filter(
            IdArchivo__Usuario_id=usuario_id
        ).filter(
            Q(ObservacionCuentasMedicas=True) | Q(ObservacionTesoreria=True)
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
                        # 'Observacion': auditoria.Observacion  # Esto no parece estar en tu modelo, asegúrate de que existe
                    }
                    admisiones_data.append(transformed_data)

        response_data = {
            "success": True,
            "detail": f"Admisiones con revisión de tesorería pendiente encontradas para el usuario con ID {usuario_id}",
            "data": admisiones_data
        }

        return JsonResponse(response_data, status=status.HTTP_200_OK)

    except AuditoriaCuentasMedicas.DoesNotExist:
        response_data = {
            "success": False,
            "detail": f"No se encontraron admisiones con revisión de tesorería pendiente para el usuario con ID {usuario_id}",
            "data": None
        }

        return JsonResponse(response_data, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        response_data = {
            "success": False,
            "detail": "Error interno del servidor",
            "error_details": str(e)
        }

        return JsonResponse(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

###### FILTRO TESORERIA #####

class FiltroTesoreria(APIView):
       def get(self, request):
        fecha_creacion_str = request.query_params.get('FechaCreacion', None)
        revision_cuentas_medicas = request.query_params.get('RevisionCuentasMedicas', None)
        codigo_entidad = request.query_params.get('CodigoEntidad', None)

        queryset = AuditoriaCuentasMedicas.objects.all()

        if codigo_entidad:
            admisiones_codigo = Admisiones.objects.filter(CodigoEntidad=codigo_entidad).values_list('Consecutivo', flat=True)
            queryset = queryset.filter(AdmisionId__in=admisiones_codigo)
        
        response_data = []

        with connections['datosipsndx'].cursor() as cursor:
            for auditoria in queryset:
                cursor.execute('''
                    SELECT Consecutivo, IdPaciente, CodigoEntidad, NombreResponsable, FacturaNo, TipoAfiliado
                    FROM admisiones
                    WHERE Consecutivo = %s
                ''', [auditoria.AdmisionId])
                admision_data = cursor.fetchone()

                if admision_data:
                    if not revision_cuentas_medicas or bool(int(revision_cuentas_medicas)) == auditoria.RevisionCuentasMedicas:
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
                            'FacturaNo': admision_data[5] if len(admision_data) > 5 else None,
                        }
                        response_data.append(data)

        return Response(response_data)


###### RADICACION - CUENTAS MEDICAS #####
def radicar_compensar_view(request, numero_admision):
    try:
        admision_response = GeDocumentalView().get(request=None, consecutivo=numero_admision)
        if admision_response.status_code == 200:
            admision_data = admision_response.data.get('data')
            factura_numero = admision_data.get('FacturaNo')
            t_regimen = admision_data.get('tRegimen')
            if factura_numero is not None and t_regimen is not None:
                archivos_response = archivos_por_admision(request, numero_admision)
                if archivos_response.status_code == 200:
                    archivos_data = archivos_response.data.get('data', [])  
                    for archivo in archivos_data:
                        tipo_archivo = archivo.get('Tipo')
                        ruta_origen_relative = archivo.get('RutaArchivo')  
                        if t_regimen == 1 or t_regimen == 0:
                            carpeta_tipo_archivo = 'CONTRIBUTIVO'
                        elif t_regimen == 2:
                            carpeta_tipo_archivo = 'SUBSIDIADO'
                        else:
                            carpeta_tipo_archivo = tipo_archivo
                        nombre_archivo = f"{tipo_archivo}{factura_numero}.pdf"
                        print("Ruta de origen relativa:", ruta_origen_relative)  
                        ruta_origen = os.path.join(settings.MEDIA_ROOT, ruta_origen_relative[len(settings.MEDIA_URL):])
                        print("Ruta de origen absoluta:", ruta_origen) 
                        print("Ruta de origen:", ruta_origen) 
                       
                        if os.path.exists(ruta_origen):
                            carpeta_path = os.path.join(settings.MEDIA_ROOT, 'gdocumental', 'Radicacion', 'COMPENSAR', carpeta_tipo_archivo)  
                            ruta_destino = os.path.join(carpeta_path, nombre_archivo) 
                            shutil.copy(ruta_origen, ruta_destino)  
                            print("Archivo copiado exitosamente.")  
                        else:
                            raise FileNotFoundError(f"La ruta de origen '{ruta_origen}' no es válida")
                    
                    response_data = {
                        "success": True,
                        "detail": f"Archivos copiados y carpetas creadas para la admisión con número {numero_admision}"
                    }
                    return JsonResponse(response_data, status=200)
                else:
                    return archivos_response
            else:
                raise ValueError("La admisión no tiene el número de factura o el tipo de régimen")
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



######## TABLA RADICACION##############
class TablaRadicacion(APIView):
    def get(self, request):
        codigo_entidad = request.query_params.get('CodigoEntidad', None)

        queryset = AuditoriaCuentasMedicas.objects.all()

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
                    if codigo_entidad and codigo_entidad == admision_data[2] and \
                       auditoria.RevisionCuentasMedicas == 1 and auditoria.RevisionTesoreria == 1:
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
                            'FacturaNo': admision_data[5] if len(admision_data) > 5 else None,
                        }
                        response_data.append(data)

        return Response(response_data)


####### SALUD TOTAL ###
def radicar_salud_total_view(request, numero_admision):
    try:
        admision_response = GeDocumentalView().get(request=None, consecutivo=numero_admision)
        if admision_response.status_code == 200:
            admision_data = admision_response.data.get('data')
            factura_numero = admision_data.get('FacturaNo')
            t_regimen = admision_data.get('tRegimen')
            prefijo = admision_data.get('Prefijo')
            if factura_numero is not None and t_regimen is not None:
                archivos_response = archivos_por_admision(request, numero_admision)
                if archivos_response.status_code == 200:
                    archivos_data = archivos_response.data.get('data', [])
                    
                    if t_regimen == 1 or t_regimen == 0:
                        carpeta_tipo_archivo = 'CONTRIBUTIVO'
                    else:
                        carpeta_tipo_archivo = 'SUBSIDIADO'

                    carpeta_path = os.path.join(settings.MEDIA_ROOT, 'gdocumental', 'Radicacion', 'SALUDTOTAL', carpeta_tipo_archivo)
                    if not os.path.exists(carpeta_path):
                        os.makedirs(carpeta_path)

                    for archivo in archivos_data:
                        tipo_archivo = archivo.get('Tipo')
                        ruta_origen_relative = archivo.get('RutaArchivo')
                        if tipo_archivo == 'FACTURA':
                            numero_tipo_documento = 1
                        elif tipo_archivo == 'AUTORIZACION':
                            numero_tipo_documento = 17
                        elif tipo_archivo == 'ORDEN':
                            numero_tipo_documento = 5
                        elif tipo_archivo == 'RESULTADO':
                            numero_tipo_documento = 7
                        elif tipo_archivo == 'COMPROBANTE':
                            numero_tipo_documento = 15
                        else:
                            numero_tipo_documento = 0  

                        if numero_tipo_documento != 0:
                            nombre_archivo = f"90119103_{prefijo}{factura_numero}_{numero_tipo_documento}_1.pdf"
                            print("Nombre de archivo:", nombre_archivo)
                            ruta_origen = os.path.join(settings.MEDIA_ROOT, ruta_origen_relative[len(settings.MEDIA_URL):])

                            if os.path.exists(ruta_origen):
                                ruta_destino = os.path.join(carpeta_path, nombre_archivo) 
                                shutil.copy(ruta_origen, ruta_destino)  
                                print("Archivo copiado exitosamente.")  
                            else:
                                raise FileNotFoundError(f"La ruta de origen '{ruta_origen}' no es válida")
                        else:
                            raise ValueError(f"No se pudo determinar el número para el tipo de documento {tipo_archivo}")
                    
                    response_data = {
                        "success": True,
                        "detail": f"Archivos copiados y carpetas creadas para la admisión con número {numero_admision}"
                    }
                    return JsonResponse(response_data, status=200)
                else:
                    return archivos_response
            else:
                raise ValueError("La admisión no tiene el número de factura o el tipo de régimen")
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

def radicar_sanitas_evento_view(request, numero_admision):
    try:
        admision_response = GeDocumentalView().get(request=None, consecutivo=numero_admision)
        if admision_response.status_code == 200:
            admision_data = admision_response.data.get('data')
            factura_numero = admision_data.get('FacturaNo')
            t_regimen = admision_data.get('tRegimen')
            prefijo = admision_data.get('Prefijo')
            if factura_numero is not None and t_regimen is not None:
                archivos_response = archivos_por_admision(request, numero_admision)
                if archivos_response.status_code == 200:
                    archivos_data = archivos_response.data.get('data', [])  
                    factura_archivo = next((archivo for archivo in archivos_data if archivo.get('Tipo') == 'FACTURA'), None)

                    if factura_archivo:
                        tipo_archivo = factura_archivo.get('Tipo')
                        ruta_origen_relative = factura_archivo.get('RutaArchivo')
                        ruta_origen = os.path.join(settings.MEDIA_ROOT, ruta_origen_relative[len(settings.MEDIA_URL):])

                        # Crear un nuevo documento PDF
                        merger = PdfMerger()
                        merger.append(ruta_origen)

                        # Agregar los demás archivos al nuevo documento
                        for archivo in archivos_data:
                            if archivo.get('Tipo') != 'FACTURA':
                                ruta_origen_relative = archivo.get('RutaArchivo')
                                ruta_origen = os.path.join(settings.MEDIA_ROOT, ruta_origen_relative[len(settings.MEDIA_URL):])
                                merger.append(ruta_origen)
                            if t_regimen == 1 or t_regimen == 0:
                                carpeta_tipo_archivo = 'CONTRIBUTIVO'
                            else:
                                carpeta_tipo_archivo = 'SUBSIDIADO'
                        
                        carpeta_prefijo_numero_factura = f"{prefijo}{factura_numero}"
                        carpeta_nombre_archivo = os.path.join(settings.MEDIA_ROOT, 'gdocumental', 'Radicacion', 'SANITASEVENTO', carpeta_tipo_archivo, carpeta_prefijo_numero_factura)
                        if not os.path.exists(carpeta_nombre_archivo):
                            os.makedirs(carpeta_nombre_archivo)

                        ruta_destino_merged = os.path.join(carpeta_nombre_archivo, f"{prefijo}{factura_numero}.pdf")
                        merger.write(ruta_destino_merged)
                        merger.close()

                        response_data = {
                            "success": True,
                            "detail": f"Archivos combinados en un solo documento y guardados en {ruta_destino_merged}"
                        }
                        return JsonResponse(response_data, status=200)
                    else:
                        raise FileNotFoundError("No se encontró el archivo de tipo FACTURA para la admisión")
                else:
                    return archivos_response
            else:
                raise ValueError("La admisión no tiene el número de factura o el tipo de régimen")
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

##### COLSANITAS###

def radicar_colsanitas_view(request, numero_admision):
    try:
        admision_response = GeDocumentalView().get(request=None, consecutivo=numero_admision)
        if admision_response.status_code == 200:
            admision_data = admision_response.data.get('data')
            factura_numero = admision_data.get('FacturaNo')
            t_regimen = admision_data.get('tRegimen')
            prefijo = admision_data.get('Prefijo')
            if factura_numero is not None and t_regimen is not None:
                archivos_response = archivos_por_admision(request, numero_admision)
                if archivos_response.status_code == 200:
                    archivos_data = archivos_response.data.get('data', [])
                    
                    carpeta_path = os.path.join(settings.MEDIA_ROOT, 'gdocumental', 'Radicacion', 'COLSANITAS')
                    if not os.path.exists(carpeta_path):
                        os.makedirs(carpeta_path)

                    for archivo in archivos_data:
                        tipo_archivo = archivo.get('Tipo')
                        ruta_origen_relative = archivo.get('RutaArchivo')
                        if tipo_archivo == 'FACTURA':
                            nombre_archivo = f"{prefijo}{factura_numero}.pdf"
                        else:
                            if tipo_archivo == 'COMPROBANTE':
                                sop = 'SOP_1'
                            elif tipo_archivo == 'AUTORIZACION':
                                sop = 'SOP_2'
                            elif tipo_archivo == 'ORDEN':
                                sop ='SOP_3'
                            elif tipo_archivo == 'ADICIONALES':
                                sop = 'SOP_4'
                            elif tipo_archivo == 'RESULTADO':
                                sop = 'SOP_5'
                            elif tipo_archivo == 'HISTORIACLINICA':
                                sop = 'SOP_6'
                            else:
                                sop = 0  # Otra opción si no se encuentra el tipo de documento

                            if sop != 0:
                                nombre_archivo = f"{prefijo}{factura_numero}_{sop}.pdf"
                            else:
                                nombre_archivo = f"{prefijo}{factura_numero}_OTRO.pdf"

                        print("Nombre de archivo:", nombre_archivo)
                        ruta_origen = os.path.join(settings.MEDIA_ROOT, ruta_origen_relative[len(settings.MEDIA_URL):])

                        if os.path.exists(ruta_origen):
                            ruta_destino = os.path.join(carpeta_path, nombre_archivo) 
                            shutil.copy(ruta_origen, ruta_destino)  
                            print("Archivo copiado exitosamente.")  
                        else:
                            raise FileNotFoundError(f"La ruta de origen '{ruta_origen}' no es válida")
                    
                    response_data = {
                        "success": True,
                        "detail": f"Archivos copiados y carpetas creadas para la admisión con número {numero_admision}"
                    }
                    return JsonResponse(response_data, status=200)
                else:
                    return archivos_response
            else:
                raise ValueError("La admisión no tiene el número de factura o el tipo de régimen")
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
    
#### CAPITAL SALUD #####



def radicar_capitalsalud_view(request, numero_admision):
    try:
        admision_response = GeDocumentalView().get(request=None, consecutivo=numero_admision)
        if admision_response.status_code == 200:
            admision_data = admision_response.data.get('data')
            factura_numero = admision_data.get('FacturaNo')
            t_regimen = admision_data.get('tRegimen')
            prefijo = admision_data.get('Prefijo')
            if factura_numero is not None and t_regimen is not None:
                archivos_response = archivos_por_admision(request, numero_admision)
                if archivos_response.status_code == 200:
                    archivos_data = archivos_response.data.get('data', [])  
                    factura_archivo = next((archivo for archivo in archivos_data if archivo.get('Tipo') == 'FACTURA'), None)

                    if factura_archivo:
                        tipo_archivo = factura_archivo.get('Tipo')
                        ruta_origen_relative = factura_archivo.get('RutaArchivo')
                        ruta_origen = os.path.join(settings.MEDIA_ROOT, ruta_origen_relative[len(settings.MEDIA_URL):])

                        # Crear un nuevo documento PDF
                        merger = PdfMerger()
                        merger.append(ruta_origen)

                        # Agregar los demás archivos al nuevo documento
                        for archivo in archivos_data:
                            if archivo.get('Tipo') != 'FACTURA':
                                ruta_origen_relative = archivo.get('RutaArchivo')
                                ruta_origen = os.path.join(settings.MEDIA_ROOT, ruta_origen_relative[len(settings.MEDIA_URL):])
                                merger.append(ruta_origen)
                        
                        ruta_destino_merged = os.path.join(settings.MEDIA_ROOT, 'gdocumental', 'Radicacion', 'CAPITALSALUD', f"{prefijo}{factura_numero}.pdf")
                        merger.write(ruta_destino_merged)
                        merger.close()

                        response_data = {
                            "success": True,
                            "detail": f"Archivos combinados en un solo documento y guardados en {ruta_destino_merged}"
                        }
                        return JsonResponse(response_data, status=200)
                    else:
                        raise FileNotFoundError("No se encontró el archivo de tipo FACTURA para la admisión")
                else:
                    return archivos_response
            else:
                raise ValueError("La admisión no tiene el número de factura o el tipo de régimen")
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

def radicar_other_view(request, numero_admision):
    try:
        admision_response = GeDocumentalView().get(request=None, consecutivo=numero_admision)
        if admision_response.status_code == 200:
            admision_data = admision_response.data.get('data')
            factura_numero = admision_data.get('FacturaNo')
            t_regimen = admision_data.get('tRegimen')
            prefijo = admision_data.get('Prefijo')
            if factura_numero is not None and t_regimen is not None:
                archivos_response = archivos_por_admision(request, numero_admision)
                if archivos_response.status_code == 200:
                    archivos_data = archivos_response.data.get('data', [])  
                    factura_archivo = next((archivo for archivo in archivos_data if archivo.get('Tipo') == 'FACTURA'), None)

                    if factura_archivo:
                        tipo_archivo = factura_archivo.get('Tipo')
                        ruta_origen_relative = factura_archivo.get('RutaArchivo')
                        ruta_origen = os.path.join(settings.MEDIA_ROOT, ruta_origen_relative[len(settings.MEDIA_URL):])

                        # Crear un nuevo documento PDF
                        merger = PdfMerger()
                        merger.append(ruta_origen)

                        # Agregar los demás archivos al nuevo documento
                        for archivo in archivos_data:
                            if archivo.get('Tipo') != 'FACTURA':
                                ruta_origen_relative = archivo.get('RutaArchivo')
                                ruta_origen = os.path.join(settings.MEDIA_ROOT, ruta_origen_relative[len(settings.MEDIA_URL):])
                                merger.append(ruta_origen)
                            if t_regimen == 1 or t_regimen == 0:
                                carpeta_tipo_archivo = 'CONTRIBUTIVO'
                            else:
                                carpeta_tipo_archivo = 'SUBSIDIADO'

                        # Crear la carpeta según el prefijo si no existe
                        carpeta_prefijo = os.path.join(settings.MEDIA_ROOT, 'gdocumental', 'Radicacion', 'CAJACOPI', carpeta_tipo_archivo, prefijo)
                        if not os.path.exists(carpeta_prefijo):
                            os.makedirs(carpeta_prefijo)

                        ruta_destino_merged = os.path.join(carpeta_prefijo, f"{prefijo}{factura_numero}.pdf")
                        merger.write(ruta_destino_merged)
                        merger.close()

                        response_data = {
                            "success": True,
                            "detail": f"Archivos combinados en un solo documento y guardados en {ruta_destino_merged}"
                        }
                        return JsonResponse(response_data, status=200)
                    else:
                        raise FileNotFoundError("No se encontró el archivo de tipo FACTURA para la admisión")
                else:
                    return archivos_response
            else:
                raise ValueError("La admisión no tiene el número de factura o el tipo de régimen")
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
                        admision_dict = {
                            'Consecutivo': admision_data[0],
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
                "detail": "Faltan parámetros: fecha y/o facturado_por.",
                "cantidad": None,
                "data": None
            }
            return JsonResponse(response_data, status=400)
########## PUNTEO APP###########class AdmisionesPorFechaYUsuario(APIView):

class AdmisionesPorFechaYUsuario(APIView):
    def get(self, request, format=None):
        fecha_creacion_archivo = request.GET.get('FechaCreacionArchivo')
        usuario_id = request.GET.get('UsuarioId')

        if fecha_creacion_archivo and usuario_id:
            try:
                # Filtrar las admisiones por fecha de creación y usuario, y agrupar por Admision_id
                admisiones_queryset = (ArchivoFacturacion.objects
                                       .filter(FechaCreacionArchivo__date=fecha_creacion_archivo, Usuario_id=usuario_id)
                                       .values('Admision_id')
                                       .annotate(cantidad=Count('Admision_id')))

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