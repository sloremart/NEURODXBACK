from datetime import date, timedelta, datetime
from django.db import IntegrityError, transaction
import logging
from sqlite3 import IntegrityError
from django.db import connections
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import api_view
from django.http import FileResponse
from .serializers import ArchivoFacturacionSerializer
from django.http import Http404
from .models import ArchivoFacturacion
from .modelsFacturacion import Admisiones





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

                
                transformed_data = {
                    'Consecutivo': admision_data[0],
                    'IdPaciente': admision_data[1],
                    'CodigoEntidad': admision_data[2],
                    'NombreResponsable': admision_data[3],
                    'FacturaNo': admision_data[4] if len(admision_data) > 4 else None,
                    'Prefijo': factura_info[0] if factura_info else None,
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



# views.py


from django.conf import settings
import os


class ArchivoUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, consecutivo, format=None):
        print(f"Consecutivo recibido en la vista: {consecutivo}")
        try:
            with transaction.atomic():
                # Obtener la admisión asociada al consecutivo
                admision = Admisiones.objects.using('datosipsndx').get(Consecutivo=consecutivo)

                # Crear la carpeta con el nombre del número de admisión
                folder_path = os.path.join(settings.MEDIA_ROOT, 'GeDocumental', 'archivosFacturacion', str(admision.Consecutivo))
                os.makedirs(folder_path, exist_ok=True)

                # Obtener la lista de archivos desde la solicitud
                archivos = request.FILES.getlist('files')
                print("Archivos recibidos en la vista:", archivos)
                archivos_guardados = []

                for archivo in archivos:
                    # Construir la ruta del archivo dentro de la carpeta de la admisión
                    archivo_path = os.path.join(folder_path, archivo.name)

                    archivo_obj = ArchivoFacturacion(
                         Admision=admision.Consecutivo,  # Utilizar el consecutivo de Admision
                         Tipo='TipoArchivo',
    RutaArchivo=archivo_path
)
                    try:
                        archivo_obj.NumeroAdmision = admision.Consecutivo 
                        archivo_obj.save()
                        archivos_guardados.append({
                            "id": archivo_obj.IdArchivo,
                            "ruta": archivo_obj.RutaArchivo.url
                        })

                        # Guardar el archivo físicamente en la nueva ruta
                        with open(archivo_path, 'wb') as file:
                            for chunk in archivo.chunks():
                                file.write(chunk)

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






############# cargar archivos ############################
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
    

from django.shortcuts import redirect
from django.http import FileResponse

@api_view(['GET'])
def donwloadFile(request, id_archivo):
    try:
        # Buscar el archivo por id
        archivo = ArchivoFacturacion.objects.get(IdArchivo=id_archivo)

        # Construir la ruta completa del archivo
        archivo_path = os.path.join(settings.ROOT_PATH_FILES_STORAGE,'/',settings.MEDIA_ROOT, '/',str(archivo.RutaArchivo))

        # Verificar si el archivo realmente existe
        if not os.path.exists(archivo_path):
            raise Http404("El archivo no existe")

        # Redireccionar la respuesta a una nueva ventana
        response = FileResponse(open(archivo_path, 'rb'))
        response['Content-Disposition'] = 'inline; filename=' + os.path.basename(archivo_path)
        return response
    except ArchivoFacturacion.DoesNotExist:
        raise Http404("El archivo no existe")
