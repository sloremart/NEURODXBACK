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

from .models import ArchivoFacturacion,Admisiones





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

                # Transformar la estructura de datos antes de enviar la respuesta
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


class ArchivoUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, consecutivo, format=None):
        try:
            with transaction.atomic():
                # Obtener la admisión asociada al consecutivo
                admision = Admisiones.objects.get(Consecutivo=consecutivo)

                # Obtener la lista de archivos desde la solicitud
                archivos = request.FILES.getlist('files')
                archivos_guardados = []

                for archivo in archivos:
                    archivo_obj = ArchivoFacturacion(Admision=admision, RutaArchivo=archivo)
                    try:
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

        except Admisiones.DoesNotExist:
            response_data = {
                "success": False,
                "detail": f"No se encontró la admisión con consecutivo {consecutivo}",
                "data": None
            }
            return JsonResponse(response_data, status=status.HTTP_404_NOT_FOUND)

