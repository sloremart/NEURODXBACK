from rest_framework import serializers
from datetime import datetime, timedelta
from controlfacturacion.serializers import CodigoSoatSerializer, DetalleFacturaSerializer
from .models import DetalleFactura, CodigoSoat
from rest_framework import generics
from rest_framework import serializers
from rest_framework.views import APIView
from .models import DetalleFactura
from django.db import connections
from rest_framework import status
from rest_framework.response import Response
from collections import defaultdict
class DateSerializerField(serializers.Field):
    
    def to_representation(self, value):
        return value.date()

class DetalleFacturaSerializer(serializers.ModelSerializer):
    FechaServicio = DateSerializerField(read_only=True)

    class Meta:
        model = DetalleFactura
        fields = '__all__'
from datetime import datetime


        






class FiltroDetalleFacturaPorFecha(APIView):       

    def get(self, request):
        fecha_servicio_str = request.query_params.get('FechaServicio', None)
        
        if fecha_servicio_str:
            try:
                fecha_servicio = datetime.strptime(fecha_servicio_str, '%Y-%m-%d')
                fecha_inicio = fecha_servicio.replace(hour=0, minute=0, second=0)
                fecha_fin = fecha_inicio + timedelta(days=1) - timedelta(seconds=1)

                # Consulta a la otra base de datos usando conexiones
                detalles_factura = []
                with connections['datosipsndx'].cursor() as cursor:
                    cursor.execute('''
                        SELECT AdmisionNo, FechaServicio, IDServicio, CodigoCUPS, CodigoSOAT, CodigoISS,
                               Cantidad, ValorUnitario, FacturaNo, RegistroGlosa, IdEspecialista, CreadoPor,
                               ModificadoPor, FechaCreado, FechaModificado, VrUnitarioCompartido, VrPorCopago,
                               VrPorCuota, OrdenNo, Ccosto
                        FROM detallefactura
                        WHERE FechaServicio BETWEEN %s AND %s
                    ''', [fecha_inicio, fecha_fin])
                    detalles_factura = cursor.fetchall()

                # Convertir las fechas a strings solo si no son None
                data = [{
                    'AdmisionNo': detalle[0],
                    'FechaServicio': detalle[1].strftime('%Y-%m-%d') if detalle[1] is not None else None,
                    'IDServicio': detalle[2],
                    'CodigoCUPS': detalle[3],
                    'CodigoSOAT': detalle[4],
                    'CodigoISS': detalle[5],
                    'Cantidad': detalle[6],
                    'ValorUnitario': detalle[7],
                    'FacturaNo': detalle[8],
                    'RegistroGlosa': detalle[9],
                    'IdEspecialista': detalle[10],
                    'CreadoPor': detalle[11],
                    'ModificadoPor': detalle[12],
                    'FechaCreado': detalle[13].strftime('%Y-%m-%d') if detalle[13] is not None else None,
                    'FechaModificado': detalle[14].strftime('%Y-%m-%d') if detalle[14] is not None else None,
                    'VrUnitarioCompartido': detalle[15],
                    'VrPorCopago': detalle[16],
                    'VrPorCuota': detalle[17],
                    'OrdenNo': detalle[18],
                    'Ccosto': detalle[19]
                } for detalle in detalles_factura]

                return Response(data)
            except ValueError:
                return Response({'error': 'Formato de fecha incorrecto. Use el formato YYYY-MM-DD.'}, status=400)
        else:
            return Response({'error': 'Se necesita proporcionar una fecha de servicio.'}, status=400)


class FiltroFacturaPorFecha(APIView):       

    def get(self, request):
        fecha_servicio_str = request.query_params.get('Fecha', None)
        
        if fecha_servicio_str:
            try:
                fecha_servicio = datetime.strptime(fecha_servicio_str, '%Y-%m-%d')
                fecha_inicio = fecha_servicio.replace(hour=0, minute=0, second=0)
                fecha_fin = fecha_inicio + timedelta(days=1) - timedelta(seconds=1)

                # Consulta a la otra base de datos usando conexiones
                factura = []
                with connections['datosipsndx'].cursor() as cursor:
                    cursor.execute('''
                        SELECT AdmisionNo, Fecha,TotalFactura, FacturaNo, TotalTerceros, FechaAdmision 
                           
                        FROM facturas
                        WHERE Fecha BETWEEN %s AND %s
                    ''', [fecha_inicio, fecha_fin])
                    factura = cursor.fetchall()

                # Convertir las fechas a strings solo si no son None
                data = [{
                    'AdmisionNo': detalle[0],
                    'Fecha': detalle[1].strftime('%Y-%m-%d') if detalle[1] is not None else None,
                    'TotalFactura': detalle[2],
                    'FacturaNo': detalle[3],
                    'TotalTerceros': detalle[4],
                    'FechaAdmision': detalle[5].strftime('%Y-%m-%d') if isinstance(detalle[5], datetime) else None,
                } for detalle in factura]

                return Response(data)
            except ValueError:
                return Response({'error': 'Formato de fecha incorrecto. Use el formato YYYY-MM-DD.'}, status=400)
        else:
            return Response({'error': 'Se necesita proporcionar una fecha de servicio.'}, status=400)
        
class CitasPxApiView(APIView):
    def get(self, request, format=None):
        fecha_inicio_str = request.GET.get('fecha_inicio', None)
        fecha_fin_str = request.GET.get('fecha_fin', None)
        
        if fecha_inicio_str and fecha_fin_str:
            try:
                fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
                fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({"error": "Formato de fecha inválido"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": "Se requieren las fechas de inicio y fin"}, status=status.HTTP_400_BAD_REQUEST)
        
        citas_por_rango = {}
        delta = timedelta(days=1)
        fecha_actual = fecha_inicio
        while fecha_actual <= fecha_fin:
            citas_por_rango[fecha_actual.strftime('%Y-%m-%d')] = self.get_citas_por_dia(fecha_actual)
            fecha_actual += delta

        response_data = {
            "success": True,
            "detail": "Las citas programadas por día en el rango de fechas son las siguientes",
            "data": citas_por_rango
        }

        return Response(response_data, status=status.HTTP_200_OK)

    def get_citas_por_dia(self, fecha):
        fecha_inicio = datetime.combine(fecha, datetime.min.time())
        fecha_fin = datetime.combine(fecha, datetime.max.time())
        with connections['datosipsndx'].cursor() as cursor:
            query = '''
                SELECT DISTINCT cita.IdCita, pxcita.VrUnitario, pxcita.Cantidad, pxcita.CUPS, cups.RegistroNo,
                cups.Servicio, soat.DescripcionCUPS, cita.Entidad
                FROM citas AS cita
                JOIN pxcita ON cita.IdCita = pxcita.IdCita
                LEFT JOIN cupsxservicio AS cups ON pxcita.CUPS = cups.CUPS
                LEFT JOIN codigossoat AS soat ON pxcita.CUPS = soat.CodigoCUPS
                WHERE cita.FeCita BETWEEN %s AND %s AND cita.Cancelada = 0
                AND cita.Entidad = 'SAN02' AND pxcita.CUPS IN ('890274', '890374')
            '''

            cursor.execute(query, [fecha_inicio, fecha_fin])
            rows = cursor.fetchall()

            citas_data = []

            for row in rows:
                cita = {
                    'IdCita': row[0],
                    'VrUnitario': row[1],
                    'Cantidad': row[2],
                    'CUPS': row[3],
                    'RegistroNo': row[4],
                    'Servicio': row[5],
                    'DescripcionCUPS': row[6],
                    'Entidad': row[7],
                    'ValorTotal': row[1] * row[2]
                }
                citas_data.append(cita)

        # Filtrar citas duplicadas por IdCita y CUPS
        citas_data = self.filter_duplicate_citas(citas_data)

        # Aplicar ajuste de precios a las citas
        citas_ajustadas = self.adjust_prices(citas_data)

        return citas_ajustadas

    def filter_duplicate_citas(self, citas):
        unique_citas = {}
        for cita in citas:
            key = (cita['IdCita'], cita['CUPS'])
            if key not in unique_citas:
                unique_citas[key] = cita
        return list(unique_citas.values())

    def adjust_prices(self, citas):
        CANTIDAD_MINIMA = 325
        CANTIDAD_REFERENCIA = 361
        CANTIDAD_MAXIMA = 397
        VALOR_TOTAL_REFERENCIA = 19335160

        # Ordenar las citas por IdCita o cualquier otro criterio si es necesario
        citas.sort(key=lambda x: x['IdCita'])

        # Calcular los nuevos valores unitarios para las citas
        for i, cita in enumerate(citas, start=1):
            if i <= CANTIDAD_MINIMA:
                cita['VrUnitario'] = VALOR_TOTAL_REFERENCIA / CANTIDAD_MINIMA
            elif i <= CANTIDAD_REFERENCIA:
                cita['VrUnitario'] = VALOR_TOTAL_REFERENCIA / CANTIDAD_REFERENCIA
            elif i <= CANTIDAD_MAXIMA:
                cita['VrUnitario'] = VALOR_TOTAL_REFERENCIA / CANTIDAD_MAXIMA
            else:
                # En caso de que las citas superen la cantidad máxima, mantenemos el valor más bajo calculado
                cita['VrUnitario'] = VALOR_TOTAL_REFERENCIA / CANTIDAD_MAXIMA

            # Actualizar el valor total basado en la nueva tarifa
            cita['ValorTotal'] = cita['VrUnitario'] * cita['Cantidad']
            print(f"Índice: {i}, IdCita: {cita['IdCita']}, VrUnitario: {cita['VrUnitario']}, ValorTotal: {cita['ValorTotal']}")

        return citas




class CiPxApiView(APIView):
    def get(self, request, format=None):
        fecha_inicio_str = request.GET.get('fecha_inicio', None)
        fecha_fin_str = request.GET.get('fecha_fin', None)
        
        if fecha_inicio_str and fecha_fin_str:
            try:
                fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
                fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({"error": "Formato de fecha inválido"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": "Se requieren las fechas de inicio y fin"}, status=status.HTTP_400_BAD_REQUEST)
        
        citas_por_rango = {}
        delta = timedelta(days=1)
        fecha_actual = fecha_inicio
        while fecha_actual <= fecha_fin:
            citas_por_rango[fecha_actual.strftime('%Y-%m-%d')] = self.get_citas_por_dia(fecha_actual)
            fecha_actual += delta

        consolidated_data = self.calculate_consolidated_data(citas_por_rango)

        response_data = {
            "success": True,
            "detail": "Las citas programadas por día en el rango de fechas son las siguientes",
            "data": citas_por_rango,
            "consolidated_data": consolidated_data
        }

        return Response(response_data, status=status.HTTP_200_OK)

    def get_citas_por_dia(self, fecha):
        fecha_inicio = datetime.combine(fecha, datetime.min.time())
        fecha_fin = datetime.combine(fecha, datetime.max.time())
        with connections['datosipsndx'].cursor() as cursor:
            query = '''
                SELECT DISTINCT cita.IdCita, pxcita.VrUnitario, pxcita.Cantidad, pxcita.CUPS, cups.RegistroNo, cups.Servicio, soat.DescripcionCUPS
                FROM citas AS cita
                JOIN pxcita ON cita.IdCita = pxcita.IdCita
                LEFT JOIN cupsxservicio AS cups ON pxcita.CUPS = cups.CUPS
                LEFT JOIN codigossoat AS soat ON pxcita.CUPS = soat.CodigoCUPS
                WHERE cita.FeCita BETWEEN %s AND %s AND cita.Cancelada = 0
            '''

            cursor.execute(query, [fecha_inicio, fecha_fin])
            rows = cursor.fetchall()

            citas_data = []

            for row in rows:
                cita = {
                    'IdCita': row[0],
                    'VrUnitario': row[1],
                    'Cantidad': row[2],
                    'CUPS': row[3],
                    'RegistroNo': row[4],
                    'Servicio': row[5],
                    'DescripcionCUPS': row[6],
                    'ValorTotal': row[1] * row[2]
                }
                citas_data.append(cita)
        
        # Procesamiento adicional para filtrar los CUPS duplicados por cada cita
        citas_data_filtered = []
        processed_ids = set()  # Para realizar seguimiento de los IdCita procesados

        for cita in citas_data:
            id_cita = cita['IdCita']
            cups = cita['CUPS']
            if id_cita not in processed_ids:
                citas_data_filtered.append(cita)
                processed_ids.add(id_cita)
            else:
                # Verificar si el CUPS ya ha sido registrado para esta cita
                cups_set = set(cita['CUPS'] for cita in citas_data_filtered if cita['IdCita'] == id_cita)
                if cups not in cups_set:
                    citas_data_filtered.append(cita)

        return citas_data_filtered
    
    def calculate_consolidated_data(self, citas_por_rango):
        consolidated_data = defaultdict(int)
        servicio_categoria = {
            "1": "Radiografia",
            "2": "Ultrasonografia",
            "3": "Doppler",
            "4": "Electroencefalograma",
            "5": "Electromiografia",
            "6": "EstudioPoliSinOximetria",
            "7": "EstudioPoliConOximetria",
            "8": "Monitorizacion",
            "9": "Neuroconduccion",
            "10": "PolisonografiaTitulacion",
            "11": "Potenciales",
            "14": "Neurologia",
            "15": "ServicioRadiologia",
            "16": "InyeccionMiorelajante",
            "17": "Fisiatria",
            "18": "Infiltraciones",
            "19": "BloqueoFisiatria",
            "20": "Bloqueoneurologia",
            "21": "TomografiaContrastada",
            "22": "TomografiaSimple",
            "23": "InsumoTomografia",
            "24": "MedicamentoTac"
        }
        for categoria in servicio_categoria.values():
         consolidated_data[categoria] = 0
        

        for fecha, citas in citas_por_rango.items():
            for cita in citas:
                categoria = servicio_categoria.get(cita['Servicio'], 'Otros')
                consolidated_data[categoria] += cita['ValorTotal']

        return consolidated_data


class CitasSubcentroApiView(APIView):
    def get(self, request, format=None):
        fecha_inicio_str = request.GET.get('fecha_inicio', None)
        fecha_fin_str = request.GET.get('fecha_fin', None)
        
        if fecha_inicio_str and fecha_fin_str:
            try:
                fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
                fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({"error": "Formato de fecha inválido"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": "Se requieren las fechas de inicio y fin"}, status=status.HTTP_400_BAD_REQUEST)
        
        citas_por_rango = {}
        delta = timedelta(days=1)
        fecha_actual = fecha_inicio
        while fecha_actual <= fecha_fin:
            citas_por_rango[fecha_actual.strftime('%Y-%m-%d')] = self.get_citas_por_dia(fecha_actual)
            fecha_actual += delta

        consolidated_data = self.calculate_consolidated_data(citas_por_rango)

        response_data = {
            "success": True,
            "detail": "Las citas programadas por día en el rango de fechas son las siguientes",
            "data": citas_por_rango,
            "consolidated_data": consolidated_data
        }

        return Response(response_data, status=status.HTTP_200_OK)

    def get_citas_por_dia(self, fecha):
        fecha_inicio = datetime.combine(fecha, datetime.min.time())
        fecha_fin = datetime.combine(fecha, datetime.max.time())
        with connections['datosipsndx'].cursor() as cursor:
            query = '''
                SELECT DISTINCT cita.IdCita, pxcita.VrUnitario, pxcita.Cantidad, pxcita.CUPS, cups.RegistroNo, cups.Servicio, soat.DescripcionCUPS
                FROM citas AS cita
                JOIN pxcita ON cita.IdCita = pxcita.IdCita
                LEFT JOIN cupsxservicio AS cups ON pxcita.CUPS = cups.CUPS
                LEFT JOIN codigossoat AS soat ON pxcita.CUPS = soat.CodigoCUPS
                WHERE cita.FeCita BETWEEN %s AND %s AND cita.Cancelada = 0
            '''

            cursor.execute(query, [fecha_inicio, fecha_fin])
            rows = cursor.fetchall()

            citas_data = []

            for row in rows:
                cita = {
                    'IdCita': row[0],
                    'VrUnitario': row[1],
                    'Cantidad': row[2],
                    'CUPS': row[3],
                    'RegistroNo': row[4],
                    'Servicio': row[5],
                    'DescripcionCUPS': row[6],
                    'ValorTotal': row[1] * row[2]
                }
                citas_data.append(cita)
        
        # Procesamiento adicional para filtrar los CUPS duplicados por cada cita
        citas_data_filtered = []
        processed_ids = set()  # Para realizar seguimiento de los IdCita procesados

        for cita in citas_data:
            id_cita = cita['IdCita']
            cups = cita['CUPS']
            if id_cita not in processed_ids:
                citas_data_filtered.append(cita)
                processed_ids.add(id_cita)
            else:
                # Verificar si el CUPS ya ha sido registrado para esta cita
                cups_set = set(cita['CUPS'] for cita in citas_data_filtered if cita['IdCita'] == id_cita)
                if cups not in cups_set:
                    citas_data_filtered.append(cita)

        return citas_data_filtered
    
    def calculate_consolidated_data(self, citas_por_rango):
        consolidated_data = defaultdict(int)
        servicio_categoria = {
            "1": "ImagenesBajaComplejidad",
            "2": "ImagenesBajaComplejidad",
            "3": "ImagenesBajaComplejidad",
            "4": "EstudioSueño",
            "6": "EstudioSueño",
            "7": "EstudioSueño",
            "8": "EstudioSueño",
            "10": "EstudioSueño",
            "14": "Neurologia",
            "16": "Neurologia",
            "20": "Neurologia",
            "21": "AltaComplejidad",
            "22": "AltaComplejidad",
            "23": "AltaComplejidad",
            "24": "AltaComplejidad",
            "5": "Fisiatria",
            "9": "Fisiatria",
            "11": "Fisiatria",
            "17": "Fisiatria",
            "18": "Fisiatria",
            "19": "Fisiatria"
        }

        for fecha, citas in citas_por_rango.items():
            for cita in citas:
                categoria = servicio_categoria.get(cita['Servicio'], 'Otros')
                consolidated_data[categoria] += cita['ValorTotal']

        return consolidated_data
    


##### SERVICIO PARA AGENDAS#######
class AgendasView(APIView):
    def get(self, request, format=None):
        fecha_inicio_str = request.GET.get('fecha_inicio', None)
        fecha_fin_str = request.GET.get('fecha_fin', None)
        
        if fecha_inicio_str and fecha_fin_str:
            try:
                fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
                fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({"error": "Formato de fecha inválido"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": "Se requieren las fechas de inicio y fin"}, status=status.HTTP_400_BAD_REQUEST)
        
        citas_por_rango = {}
        delta = timedelta(days=1)
        fecha_actual = fecha_inicio
        while fecha_actual <= fecha_fin:
            citas_por_rango[fecha_actual.strftime('%Y-%m-%d')] = self.get_citas_por_dia(fecha_actual)
            fecha_actual += delta

        consolidated_data = self.calculate_consolidated_data(citas_por_rango)

        response_data = {
            "success": True,
            "detail": "Las citas programadas por día en el rango de fechas son las siguientes",
            "data": citas_por_rango,
            "consolidated_data": consolidated_data
        }

        return Response(response_data, status=status.HTTP_200_OK)

    def get_citas_por_dia(self, fecha):
        fecha_inicio = datetime.combine(fecha, datetime.min.time())
        fecha_fin = datetime.combine(fecha, datetime.max.time())
        with connections['datosipsndx'].cursor() as cursor:
            query = '''
                SELECT DISTINCT cita.IdCita, cita.Agenda, pxcita.VrUnitario, pxcita.Cantidad, pxcita.CUPS, 
                cups.RegistroNo, cups.Servicio, soat.DescripcionCUPS, 
                FROM citas AS cita
                JOIN pxcita ON cita.IdCita = pxcita.IdCita
                LEFT JOIN cupsxservicio AS cups ON pxcita.CUPS = cups.CUPS
                LEFT JOIN codigossoat AS soat ON pxcita.CUPS = soat.CodigoCUPS
                WHERE cita.FeCita BETWEEN %s AND %s AND cita.Cancelada = 0
            '''

            cursor.execute(query, [fecha_inicio, fecha_fin])
            rows = cursor.fetchall()

            citas_data = []

            for row in rows:
                cita = {
                    'IdCita': row[0],
                    'VrUnitario': row[1],
                    'Cantidad': row[2],
                    'Agenda': row[3],
                    'CUPS': row[4],
                    'RegistroNo': row[5],
                    'Servicio': row[6],
                    'DescripcionCUPS': row[7],
                    'ValorTotal': row[1] * row[2]
                }
                citas_data.append(cita)
        
        # Procesamiento adicional para filtrar los CUPS duplicados por cada cita
        citas_data_filtered = []
        processed_ids = set()  # Para realizar seguimiento de los IdCita procesados

        for cita in citas_data:
            id_cita = cita['IdCita']
            cups = cita['CUPS']
            if id_cita not in processed_ids:
                citas_data_filtered.append(cita)
                processed_ids.add(id_cita)
            else:
                # Verificar si el CUPS ya ha sido registrado para esta cita
                cups_set = set(cita['CUPS'] for cita in citas_data_filtered if cita['IdCita'] == id_cita)
                if cups not in cups_set:
                    citas_data_filtered.append(cita)

        return citas_data_filtered
    
    def calculate_consolidated_data(self, citas_por_rango):
        consolidated_data = defaultdict(int)
        servicio_categoria = {
            "1": "ImagenesBajaComplejidad",
            "2": "ImagenesBajaComplejidad",
            "3": "ImagenesBajaComplejidad",
            "4": "EstudioSueño",
            "6": "EstudioSueño",
            "7": "EstudioSueño",
            "8": "EstudioSueño",
            "10": "EstudioSueño",
            "14": "Neurologia",
            "16": "Neurologia",
            "20": "Neurologia",
            "21": "AltaComplejidad",
            "22": "AltaComplejidad",
            "23": "AltaComplejidad",
            "24": "AltaComplejidad",
            "5": "Fisiatria",
            "9": "Fisiatria",
            "11": "Fisiatria",
            "17": "Fisiatria",
            "18": "Fisiatria",
            "19": "Fisiatria"
        }

        for fecha, citas in citas_por_rango.items():
            for cita in citas:
                categoria = servicio_categoria.get(cita['Servicio'], 'Otros')
                consolidated_data[categoria] += cita['ValorTotal']

        return consolidated_data
    



class CodigoSoatList(APIView):
    def get(self, request, tarifa_number, format=None):
        with connections['datosipsndx'].cursor() as cursor:
            tarifa_field = f'Tarifa{tarifa_number:02d}'
            query = f'''
                SELECT CodigoCUPS, DescripcionCUPS, {tarifa_field} 
                FROM codigossoat 
                WHERE {tarifa_field} <> 0
            '''
            cursor.execute(query)
            rows = cursor.fetchall()
            data = [{'CodigoCUPS': row[0],  'DescripcionCUPS': row[1],'Tarifa': row[2]} for row in rows]

        return Response(data)
    




class ContratoTarifaListView(APIView):
    def get(self, request, format=None):
        codigos = [
            { "id": 1, "label": "POLICIA ELECTRODIAGNOSTIC" },
            { "id": 2, "label": "EQUIVIDA" },
            { "id": 3, "label": "1 ENTIDAD PROMOTORA DE SALUD SANITAS S.A.S – EN INTERVENCIÓN BAJO LA MEDIDA DE TOMA DE POSESIÓN" },
            { "id": 4, "label": "POL 04 FISIATRIA 2022" },
            { "id": 5, "label": "INV META CAPITAL SALUD" },
            { "id": 6, "label": "POL09_FISATRIA" },
            { "id": 7, "label": "POL10_ELECTRO" },
            { "id": 8, "label": "POL 03" },
            { "id": 9, "label": "SALUD TOTAL" },
            { "id": 10, "label": "INV META PARTICULAR" },
            { "id": 11, "label": "UNAAC" },
            { "id": 12, "label": "DMORI2023" },
            { "id": 13, "label": "INV META COMPARTA" },
            { "id": 14, "label": "NV META SEGUROS DEL ESTA" },
            { "id": 15, "label": "INV META CAJACOPI" },
            { "id": 16, "label": "DISPENSARIO MEDICO" },
            { "id": 17, "label": "POLICIA FISIATRIA 2" },
            { "id": 18, "label": "INV META SEGUROS BOLIVAR" },
            { "id": 19, "label": "INV META COLSANITAS" },
            { "id": 20, "label": "CENTRO DE CUIDADO CLINICO" },
            { "id": 21, "label": "COLMEDICA" },
            { "id": 22, "label": "NUEVA CLINICA BARZAL" },
            { "id": 23, "label": "CONSULTORIO IPS" },
            { "id": 24, "label": "INV META COMPENSAR" },
            { "id": 25, "label": "INV META COLMEDICA" },
            { "id": 26, "label": "MEDISANITAS" },
            { "id": 27, "label": "FISIATRIA POL05" },
            { "id": 28, "label": "CLINICA META" },
            { "id": 29, "label": "CHM MEDIMAS IMG DX" },
            { "id": 30, "label": "POL11" },
            { "id": 31, "label": "MEDIMAS" },
            { "id": 32, "label": "CAJACOPI" },
            { "id": 33, "label": "INVENTARIO" },
            { "id": 34, "label": "COMPENSAR" },
            { "id": 35, "label": "ENTIDAD PROMOTORA DE SALUD SANITAS S.A.S – EN INTERVENCIÓN BAJO LA MEDIDA DE TOMA DE POSESIÓN" },
            { "id": 36, "label": "PARTICULAR" },
            { "id": 37, "label": "PIJAOS" },
            { "id": 38, "label": "CAPITAL SALUD" },
            { "id": 39, "label": "NUEVA CLINICA SOAT" },
            { "id": 40, "label": "COLSANITAS" }
        ]
        return Response(codigos)