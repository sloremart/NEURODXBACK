from datetime import datetime
from django.shortcuts import render
from django.http import JsonResponse
from django.utils.dateparse import parse_datetime
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.db import connections
from django.utils.dateparse import parse_date
from gedocumental.models import ArchivoFacturacion, AuditoriaCuentasMedicas, ObservacionSinArchivo, ObservacionesArchivos, OrdenMedica
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



class AdmisionesConObservacionesView(APIView):
    def get(self, request):
        # Obtener los parámetros de fecha del request
        fechainicio = request.query_params.get('fechainicio')
        fechafin = request.query_params.get('fechafin')

        # Validar y convertir las fechas
        try:
            if fechainicio:
                fechainicio = datetime.strptime(fechainicio, '%Y-%m-%d')
            if fechafin:
                fechafin = datetime.strptime(fechafin, '%Y-%m-%d')
        except ValueError:
            return Response({'error': 'Formato de fecha incorrecto. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

        # Crear una lista para almacenar la respuesta
        response_data = []

        # Traer todas las admisiones
        admisiones_filtradas = ArchivoFacturacion.objects.all()

        # Aplicar filtros de fecha si están presentes
        if fechainicio:
            admisiones_filtradas = admisiones_filtradas.filter(FechaCreacionAntares__gte=fechainicio)
        if fechafin:
            admisiones_filtradas = admisiones_filtradas.filter(FechaCreacionAntares__lte=fechafin)

        # Obtener la lista de IDs de admisiones únicas
        admisiones_filtradas = admisiones_filtradas.values_list('Admision_id', flat=True).distinct()

        # Prefetch de observaciones y archivos relacionados
        observaciones_archivos_qs = ObservacionesArchivos.objects.filter(
            IdArchivo__Admision_id__in=admisiones_filtradas
        ).select_related('IdArchivo')
        
        observaciones_sin_archivo_qs = ObservacionSinArchivo.objects.filter(
            AdmisionId__in=admisiones_filtradas
        ).select_related('Usuario')

        # Iterar sobre las admisiones filtradas
        for admision_id in admisiones_filtradas:
            # Filtrar observaciones por admisión
            observaciones_archivos = observaciones_archivos_qs.filter(IdArchivo__Admision_id=admision_id)
            observaciones_sin_archivo = observaciones_sin_archivo_qs.filter(AdmisionId=admision_id)

            # Obtener usuarios asociados a las observaciones (si existen)
            usuarios_con_observacion_archivo_ids = set(
                observaciones_archivos.values_list('IdArchivo__Usuario_id', flat=True).distinct()
            )
            usuarios_con_observacion_sin_archivo_ids = set(
                observaciones_sin_archivo.values_list('Usuario_id', flat=True).distinct()
            )
            usuario_ids = list(usuarios_con_observacion_archivo_ids.union(usuarios_con_observacion_sin_archivo_ids))
            usuarios = CustomUser.objects.filter(id__in=usuario_ids).values_list('nombre', flat=True)
            usuarios_list = list(usuarios)

            # Obtener las observaciones de ambas tablas
            observaciones_archivo_list = list(observaciones_archivos.values('IdObservacion', 'Descripcion', 'FechaObservacion'))
            observaciones_sin_archivo_list = list(observaciones_sin_archivo.values('id', 'Descripcion', 'FechaObservacion'))

            # Obtener los archivos de la admisión para agregar tipo de documento y radicado
            archivos_admision = ArchivoFacturacion.objects.filter(Admision_id=admision_id)
            archivos_list = list(archivos_admision.values('Tipo', 'Radicado'))

            # Obtener la fecha de creación de Antares del primer archivo de la admisión
            fecha_creacion_antares = archivos_admision.values_list('FechaCreacionAntares', flat=True).first()

            # Añadir la información al diccionario de respuesta
            data = {
                'AdmisionId': admision_id,
                'FechaCreacionAntares': fecha_creacion_antares,
                'Usuarios': usuarios_list,  # Lista de usuarios que tienen observaciones
                'ObservacionesArchivos': observaciones_archivo_list,  # Observaciones de la tabla ObservacionesArchivos
                'ObservacionesSinArchivos': observaciones_sin_archivo_list,  # Observaciones de la tabla ObservacionSinArchivo
                'Archivos': archivos_list  # Tipos de documento y radicado
            }

            response_data.append(data)

        return Response(response_data, status=status.HTTP_200_OK)


from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.db import connections

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.db import connections
from rest_framework import status
from datetime import datetime

class LargeDataPagination(PageNumberPagination):
    page_size = 100  # Número de registros por página
    page_size_query_param = 'page_size'
    max_page_size = 1000

class ProcessedXMLView(APIView):
    pagination_class = LargeDataPagination

    def get(self, request, format=None):
        # Obtener parámetros de fecha de la solicitud
        fecha_inicio_str = request.GET.get('fecha_inicio', None)
        fecha_fin_str = request.GET.get('fecha_fin', None)

        # Validación de las fechas proporcionadas
        if fecha_inicio_str and fecha_fin_str:
            try:
                # Convertir las cadenas en objetos de tipo datetime
                fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d')
                fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d')
            except ValueError:
                return Response({"error": "Formato de fecha inválido. El formato correcto es AAAA-MM-DD."},
                                status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": "Se requieren las fechas de inicio y fin."},
                            status=status.HTTP_400_BAD_REQUEST)

        paginator = self.pagination_class()

        # Consulta SQL con filtro de rango de fechas en FechaCreado
        with connections['datosipsndx'].cursor() as cursor:
            query = '''
                SELECT 
                    Id,
                    texto,
                    direccion,
                    FechaCreado,
                    IpOrigen,
                    Procesado,
                    RtaLumier
                FROM tblxmlprocesados
                WHERE FechaCreado BETWEEN %s AND %s
            '''
            cursor.execute(query, [fecha_inicio, fecha_fin])
            rows = cursor.fetchall()

            data = []
            for row in rows:
                record = {
                    'Id': row[0],
                    'Texto': row[1],
                    'Direccion': row[2],
                    'FechaCreado': row[3],
                    'IpOrigen': row[4],
                    'Procesado': row[5],
                    'RtaLumier': row[6]
                }
                data.append(record)

        paginated_data = paginator.paginate_queryset(data, request)
        return paginator.get_paginated_response(paginated_data)
    
import xml.etree.ElementTree as ET
from io import BytesIO
from django.http import HttpResponse, JsonResponse
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
import os
from django.conf import settings
import ftfy  # Librería para corregir caracteres corruptos
from reportlab.graphics.shapes import Drawing, Line
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from django.db import connections
from datetime import datetime
from reportlab.lib.utils import ImageReader
from PIL import Image as PILImage
# Registrar la fuente Arial y su versión en negrilla
pdfmetrics.registerFont(TTFont('Arial', os.path.join(settings.BASE_DIR, 'fonts', 'Arial.ttf')))
pdfmetrics.registerFont(TTFont('Arial_Bold', os.path.join(settings.BASE_DIR, 'fonts', 'Arial_Bold.ttf')))
import io

# Función para corregir caracteres corruptos usando ftfy
def limpiar_caracteres_corruptos(texto):
    return ftfy.fix_text(texto)

# Función para buscar la orden en la base de datos por OrdenHis y Dirección "E"
def buscar_orden_por_ordenhis(ordenhis):
    with connections['datosipsndx'].cursor() as cursor:
        query = """
            SELECT texto 
            FROM tblxmlprocesados 
            WHERE texto LIKE %s 
              AND Direccion = 'E'
        """
        cursor.execute(query, [f'%<OrdenHis>{ordenhis}</OrdenHis>%'])
        result = cursor.fetchone()
    
    # Si se obtiene resultado, aplicar la función de limpieza de caracteres
    if result:
        texto_xml = result[0]
        texto_xml = limpiar_caracteres_corruptos(texto_xml)
        return texto_xml
    else:
        return None

# Función para buscar detalles de admisión en la base de datos por OrdenHis
def buscar_admision_por_ordenhis(ordenhis):
    with connections['datosipsndx'].cursor() as cursor:
        query = """
            SELECT CodigoEntidad, FechaCreado 
            FROM admisiones
            WHERE Consecutivo = %s
        """
        cursor.execute(query, [ordenhis])
        result = cursor.fetchone()
    
    if result:
        codigo_entidad, fecha_creado = result
        return {"CodigoEntidad": codigo_entidad, "FechaCreado": fecha_creado}
    else:
        return None

# Función para buscar detalles del paciente usando Documento como IDPaciente
def buscar_paciente_por_documento(documento):
    with connections['datosipsndx'].cursor() as cursor:
        query = """
            SELECT FechaNacimiento 
            FROM pacientes
            WHERE IDPaciente = %s
        """
        cursor.execute(query, [documento])
        result = cursor.fetchone()

    if result:
        fecha_nacimiento = result[0]
        return {"FechaNacimiento": fecha_nacimiento}
    else:
        return None

# Función para calcular la edad a partir de la fecha de nacimiento
def calcular_edad(fecha_nacimiento):
    if isinstance(fecha_nacimiento, str):
        fecha_nacimiento = datetime.strptime(fecha_nacimiento, "%Y-%m-%d").date()
    hoy = datetime.now().date()
    edad = hoy.year - fecha_nacimiento.year - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))
    return edad

# Función para extraer datos relevantes del XML
def extraer_datos_desde_xml(texto_xml):
    try:
        root = ET.fromstring(texto_xml)
    except ET.ParseError as e:
        print(f"Error al parsear XML: {e}")
        return None

    # Extraer las observaciones
    observaciones = root.findtext('.//Analito/Observaciones', default='No se encontraron observaciones')
    
    # Reemplazar todas las versiones de 'br' con saltos de línea reales
    observaciones = observaciones.replace('..br..', '\n').replace('<br>', '\n').replace('br', '\n')

    # Remover saltos de línea consecutivos para evitar espacios excesivos
    observaciones = '\n'.join([line.strip() for line in observaciones.split('\n') if line.strip()])

    datos = {
        "OrdenHis": root.findtext('.//OrdenHis', default=''),
        "Nombre": root.findtext('.//NombreUsuario', default=''),
        "Apellido": root.findtext('.//ApellidoUsuario', default=''),
        "Documento": root.findtext('.//Documento', default=''),
        "CUPS": root.findtext('.//CodigoServicio', default=''),
        "NombreServicio": root.findtext('.//NombreServicio', default=''),
        "Observaciones": observaciones,
        "NombreProfesional": root.findtext('.//NombreProfesional', default='N/A')  # Extraer nombre del médico
    }
    return datos

# Función para buscar el registro médico del profesional en la base de datos contabilidadndx
def buscar_registro_medico(nombre_profesional):
    with connections['contabilidadndx'].cursor() as cursor:
        query = """
            SELECT RegMedico 
            FROM usuarios
            WHERE NombreReal = %s
        """
        cursor.execute(query, [nombre_profesional])
        result = cursor.fetchone()

    if result:
        reg_medico = result[0]
        return reg_medico
    else:
        return "N/A"

def obtener_firma_profesional(identificacion_profesional):
    # Conectar a la base de datos `contabilidadndx`
    with connections['contabilidadndx'].cursor() as cursor:
        query = """
            SELECT ImgFirma 
            FROM usuarios 
            WHERE Cedula = %s
        """
        cursor.execute(query, [identificacion_profesional])
        result = cursor.fetchone()

    if result and result[0]:
        # Convertir los datos binarios de la firma en un objeto BytesIO
        firma_binaria = result[0]
        try:
            # Verificar si los datos binarios son una imagen válida y convertir si es BMP
            img = PILImage.open(io.BytesIO(firma_binaria))
            
            # Si la imagen es un BMP, convertirla a PNG
            if img.format == 'BMP':
                with io.BytesIO() as output:
                    img.save(output, format="PNG")
                    firma_binaria = output.getvalue()
            
            # Retornar los datos binarios de la firma convertida
            return BytesIO(firma_binaria)
        except Exception as e:
            print(f"Error al cargar o convertir la imagen de la firma: {e}")
            return None
    else:
        return None


# Función para generar el PDF con la información del paciente
def generar_pdf_orden(orden_datos, admision_datos, paciente_datos, medico_datos):
    buffer = BytesIO()  
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=10)  # Ajustar márgenes si es necesario
    story = []
    styles = getSampleStyleSheet()
    
    # Crear estilos de texto
    styles.add(ParagraphStyle(name='Arial', fontName='Arial', fontSize=8))
    bold_header_style = ParagraphStyle(name='BoldHeaderStyle', fontName='Arial_Bold', fontSize=9, alignment=TA_LEFT)
    observations_style = ParagraphStyle(name='Observations', fontName='Arial', fontSize=10, leading=14, leftIndent=0, spaceAfter=6)  # Ajuste sin sangría y ajuste de espaciado entre párrafos
    note_style = ParagraphStyle(name='NoteStyle', fontName='Arial', fontSize=7, leading=8)

    # Añadir la imagen al encabezado (parte superior izquierda) y texto al centro
    logo_path = os.path.join(settings.BASE_DIR, 'media', 'logo.png')  # Cambia la ruta según la ubicación de tu imagen
    logo = None
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=1.0 * inch, height=0.75 * inch)  # Tamaño reducido
        logo.hAlign = 'LEFT'  # Alineación a la izquierda

    # Crear la tabla para el encabezado con el logo y "DIAGNOSTICO RIS"
    header_data = [
        [logo, Paragraph("<b>Diagnostico RIS</b>", ParagraphStyle(name='Header', fontName='Arial_Bold', fontSize=8, alignment=TA_CENTER))]
    ]

    header_table = Table(header_data, colWidths=[1.5 * inch, 5.5 * inch])  # Ajustar ancho de columnas
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),  # Alinear logo a la izquierda
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),  # Alinear texto al centro
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Alinear verticalmente al medio
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),  # Quitar padding inferior
    ]))

    # Añadir la tabla del encabezado al documento
    story.append(header_table)
    story.append(Spacer(1, 12))  # Espacio debajo del encabezado

    # Calcular la edad del paciente
    edad = calcular_edad(paciente_datos['FechaNacimiento'])

    # Ajustar las filas de la tabla con 3 columnas y ajustar los spans para las celdas que deben abarcar más columnas
    paciente_data = [
        [Paragraph(f"<b>Nombre Paciente:</b> {orden_datos['Nombre']} - {orden_datos['Apellido']}", bold_header_style), '', Paragraph(f"<b>Fecha Nacimiento:</b>", bold_header_style)],
        [Paragraph(f"<b>ID Paciente:</b> CC {orden_datos['Documento']}", bold_header_style), '', Paragraph(f"{paciente_datos['FechaNacimiento']} / {edad} Años", bold_header_style)],
        [Paragraph(f"<b>Contrato:</b> {admision_datos['CodigoEntidad']}", bold_header_style), Paragraph(f"<b>Procedencia:</b> Ambulatorio", bold_header_style), ''],
        [Paragraph(f"<b>Procedimientos:</b> {orden_datos['CUPS']} - {orden_datos['NombreServicio']}", bold_header_style), '', Paragraph(f"<b>Fecha Cita:</b> {admision_datos['FechaCreado'].date()}", bold_header_style)]
    ]

    # Definir el tamaño de las columnas para que el nombre del paciente ocupe dos columnas adecuadamente
    table = Table(paciente_data, colWidths=[2.5 * inch, 2.5 * inch, 2.5 * inch])
    table.setStyle(TableStyle([
        ('SPAN', (0, 0), (1, 0)),  # Span for "Nombre Paciente" to occupy first two columns
        ('SPAN', (0, 3), (1, 3)),  # Span for "Procedimientos" to occupy first two columns
        ('LINEABOVE', (0, 0), (-1, 0), 1, colors.black),
        ('LINEBELOW', (0, -1), (-1, -1), 1, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Arial'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),  # Reducir el padding inferior para menor espacio
        ('TOPPADDING', (0, 0), (-1, -1), 2),  # Reducir padding superior para ajustar mejor
    ]))

    # Añadir la tabla al documento
    story.append(table)
    story.append(Spacer(1, 6))  # Reducir el espacio entre la tabla y el siguiente elemento para alineación

    # Añadir las observaciones respetando los saltos de línea
    story.append(Paragraph("<b>Observaciones:</b>", bold_header_style))  # Añadir título de observaciones
    story.append(Spacer(1, 6))  # Añadir un pequeño espacio después del título

    # Convertir las observaciones en párrafos separados por saltos de línea
    for line in orden_datos['Observaciones'].split('\n'):
        if line.strip():  # Ignorar líneas en blanco
            story.append(Paragraph(line, observations_style))  # Usar estilo con menor espaciado entre líneas
            story.append(Spacer(1, 4))  # Espacio reducido entre cada línea para una mejor legibilidad
    
    # Añadir la nota después de las observaciones
    nota_texto = """<b>NOTA:</b> En la realización del estudio se adoptan los protocolos y guías de atención establecidos para la prevención del <b>SARS-COV 2/COVID 19</b> que incluye lavado de manos según las recomendaciones de la OMS; además de la utilización de equipo de protección personal y las medidas de protección del paciente; así como limpieza y desinfección de los equipos después de la atención que cada usuario."""
    story.append(Spacer(1, 12))
    story.append(Paragraph(nota_texto, note_style))

    # Obtener la firma del médico
    identificacion_profesional = orden_datos.get('IdentificacionProfesional')
    firma_binaria = obtener_firma_profesional(identificacion_profesional)

    # Si la firma existe, agregarla
    if firma_binaria:
        firma_img = ImageReader(firma_binaria)
        firma = Image(firma_img, width=2.0 * inch, height=0.5 * inch)
        firma.hAlign = 'CENTER'  # Centrar la firma en la página
        story.append(firma)
        story.append(Spacer(1, 6))

    # Añadir el nombre del médico antes de la nota "RECUERDE"
    medico_nombre = medico_datos.get('NombreProfesional', 'N/A')
    reg_medico = buscar_registro_medico(medico_nombre)
    story.append(Paragraph(f"<b>Realizado por:</b> {medico_nombre}", bold_header_style))
    story.append(Paragraph(f"<b>Registro Médico:</b> {reg_medico}", bold_header_style))

    # Añadir la nota "RECUERDE" después del nombre del médico
    nota_texto_recuerde = """<b>RECUERDE:</b> que los exámenes de imagenología son un apoyo diagnóstico, y su importancia radica en que deben ser analizados e interpretados por su médico tratante, teniendo en cuenta su cuadro clínico, si hay una discrepancia entre su impresión clínica y nuestro informe, por favor póngase en contacto con nosotros."""
    story.append(Spacer(1, 12))
    story.append(Paragraph(nota_texto_recuerde, note_style))
    
    # Añadir la línea horizontal al final del documento
    story.append(Spacer(1, 12))  # Añadir espacio antes de la línea

    # Crear una línea usando Drawing
    line = Drawing(500, 1)
    line.add(Line(0, 0, 530, 0))  # Crear línea horizontal con largo 500 puntos
    story.append(line)  # Añadir la línea al final del documento

    # Generar el PDF
    doc.build(story)
    buffer.seek(0)

    # Crear la carpeta para almacenar el PDF
    output_dir = os.path.join(settings.MEDIA_ROOT, 'pdf', f"orden_{orden_datos['OrdenHis']}")
    os.makedirs(output_dir, exist_ok=True)

    # Guardar el PDF en la carpeta
    pdf_filename = f"informe_orden_{orden_datos['OrdenHis']}.pdf"
    pdf_path = os.path.join(output_dir, pdf_filename)
    with open(pdf_path, 'wb') as f:
        f.write(buffer.getvalue())

    return buffer
# Vista que recibe la OrdenHis y genera el PDF automáticamente
def generar_pdf_orden_view(request, orden_id):
    orden_texto = buscar_orden_por_ordenhis(orden_id)
    if not orden_texto:
        return JsonResponse({"error": "Orden no encontrada o la dirección no es 'E'"}, status=404)

    datos_orden = extraer_datos_desde_xml(orden_texto)
    if datos_orden is None:
        return JsonResponse({"error": "Error al procesar el XML"}, status=500)

    admision_datos = buscar_admision_por_ordenhis(orden_id)
    if admision_datos is None:
        return JsonResponse({"error": "Datos de admisión no encontrados"}, status=404)

    paciente_datos = buscar_paciente_por_documento(datos_orden['Documento'])
    if paciente_datos is None:
        return JsonResponse({"error": "Datos del paciente no encontrados"}, status=404)

    # Extraer datos del médico del XML
    medico_datos = {
        "NombreProfesional": datos_orden.get('NombreProfesional', 'N/A')
    }

    # Generar el PDF pasando la información del médico
    pdf_buffer = generar_pdf_orden(datos_orden, admision_datos, paciente_datos, medico_datos)

    # Devolver el PDF como respuesta
    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="informe_orden_{orden_id}.pdf"'
    return response
