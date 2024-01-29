from datetime import date, timedelta, datetime
from urllib.request import Request
from django.shortcuts import render
from django.db import connections
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class CitasApiView(APIView):
    def get(self, request, format=None):
        fecha_inicio = datetime.strptime('2024-01-29 07:00', '%Y-%m-%d %H:%M')
        fecha_fin = datetime.strptime('2024-01-29 22:00', '%Y-%m-%d %H:%M')
        today = date.today()
        tomorrow = today + timedelta(days=1)

        # Definir la hora de inicio y fin para las citas (7 am y 1 pm)
        start_time = datetime.strptime('07:00', '%H:%M').time()
        end_time = datetime.strptime('19:00', '%H:%M').time()

        start_datetime = datetime.combine(tomorrow, start_time)
        end_datetime = datetime.combine(tomorrow, end_time)

        with connections['datosipsndx'].cursor() as cursor:
            query = '''
                SELECT FechaCita, NumeroPaciente, IdMedico
                FROM citas
                WHERE FechaCita != "" 
                AND FechaCita BETWEEN %s AND %s
                AND FechaCancelacion IS NULL
              
            '''
            
            print("Consulta SQL:", query, [fecha_inicio.strftime('%Y%m%d%H%M'), fecha_fin.strftime('%Y%m%d%H%M')])
            cursor.execute(query, [fecha_inicio.strftime('%Y%m%d%H%M'), fecha_fin.strftime('%Y%m%d%H%M')])
            citas_data = [
                {
                    'FechaCita': self.format_char_date(row[0]),
                    'NumeroPaciente': row[1],
                    'IdMedico':row[2],                    
                    'PacienteInfo': self.get_paciente_info(row[1]),

                }
                 for row in cursor.fetchall()
            ]

        # Transformar la estructura de datos antes de enviar la respuesta
        transformed_data = [
            {
                "name": f"{cita['PacienteInfo']['Nombre1']} {cita['PacienteInfo']['Nombre2']} {cita['PacienteInfo']['Apellido1']} {cita['PacienteInfo']['Apellido2']}",
                "phone": f"57{cita['PacienteInfo']['Telefono']}", 
                "fecha_cita": cita['FechaCita'],
                "id_medico": cita['IdMedico'],
                "nueva_sede": self.get_nueva_sede(cita["IdMedico"])
            }
            for cita in citas_data
        ]
        transformed_data.sort(key=lambda x: x["id_medico"])

        response_data = {
            "success": True,
            "detail": "Las citas programadas son las siguientes",
            "data": transformed_data
        }

        return Response(response_data, status=status.HTTP_200_OK)

    def format_char_date(self, char_date):
        try:
            datetime_obj = datetime.strptime(char_date, '%Y%m%d%H%M')
            formatted_date = datetime_obj.strftime('%Y/%m/%d - %H:%M')
            return formatted_date
        except ValueError as e:
            print(f"Error al convertir la fecha {char_date}: {e}")
            return None

    def get_paciente_info(self, numero_paciente):
        with connections['datosipsndx'].cursor() as cursor:
            paciente_query = 'SELECT Nombre1, Nombre2, Apellido1, Apellido2, IDPaciente, Telefono FROM pacientes WHERE NumeroPaciente = %s'
            cursor.execute(paciente_query, [numero_paciente])
            paciente_info = cursor.fetchone()
            if paciente_info:
                return {
                    'Nombre1': paciente_info[0],
                    'Nombre2': paciente_info[1],
                    'Apellido1': paciente_info[2],
                    'Apellido2': paciente_info[3],
                    'IDPaciente': paciente_info[4],
                    'Telefono': paciente_info[5],
                }
            else:
                return {
                    'Nombre1': None,
                    'Nombre2': None,
                    'Apellido1': None,
                    'Apellido2': None,
                    'IDPaciente': None,
                    'Telefono': None,
                }
    def get_nueva_sede(self, id_medico):
        tercer_piso = ["1018424262", "72200727", "1121830894", "79428720", "72199429", "1121833421", "1116240264", "79683666", "7178922"]
        barzal_medicos = ["1010197455", "52477075", "80221101", "52932022", "7827416", "17417997"]

        if id_medico in barzal_medicos:
            return "barzal"
        elif id_medico in tercer_piso:
            return "tercer_piso"
        else:
            return None
            
######################## plataforma WOTNOT ##############################
            

    def post(self, request, format=None):
        try:
            # Obtener los datos del cuerpo de la solicitud POST
            
            telefono = request.data.get('phone', '')
           

            # Validar que el número de teléfono no esté vacío
            if not telefono:
                return Response({"success": False, "detail": "El número de teléfono es obligatorio"}, status=status.HTTP_400_BAD_REQUEST)

            # Datos para la plataforma en formato de matriz
            platform_data = [{
                'phone': telefono,
            }]

            # URL y token de autenticación de la plataforma
            webhook_url = 'https://outbound.wotnot.io/api/v1/outbound/RsrdVNcpmg8H212739409455mvF516UZ/campaign/9oZEhKnWbYMd1603279423311fcTaDjT'
            webhook_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2NvdW50X2lkIjo1NDA1NX0.4VCQXQiVlekh62a91aMP7fWQzK5eGCVj4MuWLkf1iUY'

            # Encabezados con el token de autorización y tipo de contenido
            headers = {
                'Authorization': f'Bearer {webhook_token}',
                'Content-Type': 'application/json',
            }

            # Enviar solicitud POST a la plataforma
            response = Request.post(webhook_url, json=platform_data, headers=headers)

            if response.status_code == 200:
                return Response({"success": True, "detail": "Datos enviados correctamente"}, status=status.HTTP_200_OK)
            else:
                print(f"Error en la solicitud a la plataforma. Estado: {response.status_code}")
                print(response.text)  # Imprime la respuesta de la plataforma
                return Response({"success": False, "detail": "Error al enviar datos a la plataforma"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            print(f"Excepción durante el procesamiento: {str(e)}")
            return Response({"success": False, "detail": "Error interno en el servidor"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)