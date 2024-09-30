from datetime import datetime
from django.shortcuts import render
from django.http import JsonResponse
from django.utils.dateparse import parse_datetime
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.db import connections
from django.utils.dateparse import parse_date
from gedocumental.models import ArchivoFacturacion, AuditoriaCuentasMedicas, ObservacionSinArchivo, ObservacionesArchivos
from collections import defaultdict
from django.utils import timezone
from django.shortcuts import get_object_or_404
from login.models import CustomUser
from rest_framework.views import APIView
from django.db.models import Count, Q, F
from rest_framework import status
from django.contrib.auth import get_user_model



class AdmisionesPorUsuario(APIView):
    def get(self, request):
        # Obtener los parámetros de la solicitud
        usuario_ids = request.query_params.getlist('usuario_ids', None)
        fecha_inicio_str = request.query_params.get('fecha_inicio', None)
        fecha_fin_str = request.query_params.get('fecha_fin', None)

        # Verificar que los parámetros requeridos estén presentes
        if not usuario_ids or not fecha_inicio_str or not fecha_fin_str:
            return Response({'error': 'Se requieren usuario_ids, fecha_inicio y fecha_fin'}, status=400)

        try:
            # Convertir las cadenas de fechas en objetos datetime
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d')
            fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d')
          
            # Asegurarse de que las fechas estén en el timezone correcto
            if timezone.is_naive(fecha_inicio):
                fecha_inicio = timezone.make_aware(fecha_inicio, timezone.get_current_timezone())
            if timezone.is_naive(fecha_fin):
                fecha_fin = timezone.make_aware(fecha_fin, timezone.get_current_timezone())
        except ValueError:
            return Response({'error': 'Formato de fecha no válido. Use YYYY-MM-DD.'}, status=400)

        try:
            # Filtrar los usuarios por ID
            usuarios = CustomUser.objects.filter(id__in=usuario_ids)
            if not usuarios.exists():
                return Response({'error': 'Usuarios no encontrados'}, status=404)

            response_data = {}

            for usuario in usuarios:
                # Filtra las admisiones que cumplan con cualquiera de las dos fechas
                admisiones_queryset = ArchivoFacturacion.objects.filter(
                    Usuario=usuario
                ).filter(
                    Q(FechaCreacionArchivo__range=(fecha_inicio, fecha_fin)) |
                    Q(FechaCreacionAntares__range=(fecha_inicio, fecha_fin))
                ).values('NumeroAdmision').distinct()

                admisiones_list = [admision['NumeroAdmision'] for admision in admisiones_queryset]

                entidad_count = {}
                if admisiones_list:
                    with connections['datosipsndx'].cursor() as cursor:
                        # Realizar la consulta SQL con los argumentos correctos
                        cursor.execute('''
                            SELECT CodigoEntidad, COUNT(*) as cantidad
                            FROM admisiones
                            WHERE Consecutivo IN %s
                            GROUP BY CodigoEntidad
                        ''', [tuple(admisiones_list)])

                        results = cursor.fetchall()
                        for codigo_entidad, cantidad in results:
                            entidad_count[codigo_entidad] = cantidad

                response_data[usuario.username] = {
                    "cantidad_admisiones": len(admisiones_list),
                    "entidad_count": entidad_count
                }

            return Response(response_data, status=200)
        except CustomUser.DoesNotExist:
            return Response({'error': 'Usuario no encontrado'}, status=404)
        except ValueError:
            return Response({'error': 'Formato de fecha no válido. Use YYYY-MM-DD.'}, status=400)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
        


class ArchivosRevisadosPorCM(APIView):
    def get(self, request):
        # Obtener los parámetros de la solicitud
        usuario_id = request.query_params.get('usuario_id')
        fecha_inicio_str = request.query_params.get('fecha_inicio', None)
        fecha_fin_str = request.query_params.get('fecha_fin', None)

        # Verificar que los parámetros requeridos estén presentes
        if not usuario_id or not fecha_inicio_str or not fecha_fin_str:
            return Response({'error': 'Se requieren usuario_id, fecha_inicio y fecha_fin'}, status=400)

        try:
            # Convertir las cadenas de fechas en objetos datetime
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d')
            fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d')

            # Asegurarse de que las fechas estén en el timezone correcto
            if timezone.is_naive(fecha_inicio):
                fecha_inicio = timezone.make_aware(fecha_inicio, timezone.get_current_timezone())
            if timezone.is_naive(fecha_fin):
                fecha_fin = timezone.make_aware(fecha_fin, timezone.get_current_timezone())
        except ValueError:
            return Response({'error': 'Formato de fecha no válido. Use YYYY-MM-DD.'}, status=400)

        try:
            # Validar que el usuario exista utilizando CustomUser
            usuario = CustomUser.objects.get(pk=usuario_id)
        except CustomUser.DoesNotExist:
            return Response({'error': 'Usuario no encontrado.'}, status=404)

        try:
            # Filtrar los archivos según el usuario y el rango de fechas
            archivos_revisados = ArchivoFacturacion.objects.filter(
                UsuarioCuentasMedicas=usuario,
                RevisionPrimera=True,
                FechaRevisionPrimera__range=(fecha_inicio, fecha_fin)
            ).values('Admision_id', 'FechaRevisionPrimera')

            if not archivos_revisados.exists():
                return Response({'error': 'No se encontraron admisiones revisadas para este usuario en el rango de fechas proporcionado.'}, status=404)

            # Diccionario para almacenar información única por admisión
            admisiones_unicas = {}

            # Obtener información adicional de cada admisión
            with connections['datosipsndx'].cursor() as cursor:
                for archivo in archivos_revisados:
                    consecutivo = archivo['Admision_id']

                    # Consulta para obtener la información de la admisión
                    cursor.execute('''
                        SELECT Consecutivo, IdPaciente, CodigoEntidad, NombreResponsable, FacturaNo, CedulaResponsable
                        FROM admisiones
                        WHERE Consecutivo = %s
                    ''', [consecutivo])
                    admision_data = cursor.fetchone()

                    if admision_data and consecutivo not in admisiones_unicas:
                        # Obtener el primer archivo de facturación que coincide con la admisión
                        archivo_facturacion = ArchivoFacturacion.objects.filter(Admision_id=consecutivo).first()

                        # Construir el JSON de respuesta para esta admisión
                        data = {
                            'AdmisionId': consecutivo,
                            'FechaRevisionPrimera': archivo['FechaRevisionPrimera'].strftime('%Y-%m-%d'),
                            'Consecutivo': admision_data[0],
                            'IdPaciente': admision_data[1],
                            'CodigoEntidad': admision_data[2],
                            'NombreResponsable': admision_data[3],
                            'FacturaNo': admision_data[4] if len(admision_data) > 3 else None,
                            'FechaCreacionAntares': archivo_facturacion.FechaCreacionAntares.strftime('%Y-%m-%d') if archivo_facturacion and archivo_facturacion.FechaCreacionAntares else None,
                            
                        }

                        # Almacenar la información en el diccionario para evitar duplicados
                        admisiones_unicas[consecutivo] = data

            # Convertir el diccionario a una lista para la respuesta
            response_data = list(admisiones_unicas.values())

            return Response(response_data, status=200)
        except Exception as e:
            return Response({'error': str(e)}, status=500)



CustomUser = get_user_model()

class AdmisionesConObservacionesView(APIView):
    def get(self, request):
        # Crear una lista para almacenar la respuesta
        response_data = []

        # Filtrar las admisiones que no tienen todos los archivos con RevisionPrimera en True
        admisiones_filtradas = ArchivoFacturacion.objects.annotate(
            total_archivos=Count('Admision_id'),
            total_revision_primera=Count('Admision_id', filter=Q(RevisionPrimera=True))
        ).filter(
            total_archivos__gt=F('total_revision_primera')
        ).values_list('Admision_id', flat=True).distinct()

        # Prefetch de observaciones y usuarios relacionados
        observaciones_archivos_qs = ObservacionesArchivos.objects.filter(
            IdArchivo__Admision_id__in=admisiones_filtradas
        ).select_related('IdArchivo__Usuario')
        
        observaciones_sin_archivo_qs = ObservacionSinArchivo.objects.filter(
            AdmisionId__in=admisiones_filtradas
        ).select_related('Usuario')

        # Iterar sobre las admisiones filtradas
        for admision_id in admisiones_filtradas:
            # Filtrar observaciones por admisión
            observaciones_archivos = observaciones_archivos_qs.filter(IdArchivo__Admision_id=admision_id)
            usuarios_con_observacion_archivo_ids = set(
                observaciones_archivos.values_list('IdArchivo__Usuario_id', flat=True).distinct()
            )

            observaciones_sin_archivo = observaciones_sin_archivo_qs.filter(AdmisionId=admision_id)
            usuarios_con_observacion_sin_archivo_ids = set(
                observaciones_sin_archivo.values_list('Usuario_id', flat=True).distinct()
            )

            # Combinar todos los usuarios que tienen observaciones
            usuario_ids = list(usuarios_con_observacion_archivo_ids.union(usuarios_con_observacion_sin_archivo_ids))

            # Consultar los nombres de los usuarios basados en los IDs
            usuarios = CustomUser.objects.filter(id__in=usuario_ids).values_list('username', flat=True)
            usuarios_list = list(usuarios)  # Convertir QuerySet a lista

            # Obtener la fecha de creación de Antares del primer archivo de la admisión
            fecha_creacion_antares = ArchivoFacturacion.objects.filter(
                Admision_id=admision_id
            ).values_list('FechaCreacionAntares', flat=True).first()

            # Añadir los usuarios al diccionario de respuesta
            data = {
                'AdmisionId': admision_id,
                'FechaCreacionAntares': fecha_creacion_antares,
                'Usuarios': usuarios_list  # Incluimos la lista de usuarios
            }

            response_data.append(data)

        return Response(response_data, status=status.HTTP_200_OK)