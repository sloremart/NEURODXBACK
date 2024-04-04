

from gedocumental.modelsFacturacion import Admisiones
from django.db import connections

def obtener_informacion_admision(numero_admision):
    try:
        # Aquí cambia 'datosipsndx' al nombre de la conexión de la base de datos que necesites
        with connections['datosipsndx'].cursor() as cursor:
            cursor.execute('SELECT * FROM Admisiones WHERE Consecutivo = %s', [numero_admision])
            row = cursor.fetchone()

            if row:
                return {
                    'Consecutivo': row[0],
                    'IdPaciente': row[1],
                    'CodigoEntidad': row[2],
                    'NombreResponsable': row[3],
                    'FacturaNo': row[4],
                    'tRegimen': row[5],
                    # Otros campos de la admisión que necesites
                }
            else:
                return None
    except Admisiones.DoesNotExist:
        return None