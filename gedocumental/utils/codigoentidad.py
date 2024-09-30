import os
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import JsonResponse 

def obtener_tipos_documentos_por_codigo_entidad():
    tipos_documentos_por_codigo_entidad = {
        'SAN01':['FACTURA', 'COMPROBANTE','AUTORIZACION','ORDEN','ADICIONALES','RESULTADO','HCNEURO','HCLINICA'],
        'SAN02':['FACTURA', 'COMPROBANTE','AUTORIZACION','ORDEN','ADICIONALES','RESULTADO','HCNEURO', 'HCLINICA'],
        'POL12':['FACTURA', 'COMPROBANTE','AUTORIZACION','ORDEN','ADICIONALES','RESULTADO','HCNEURO', 'HCLINICA'],
        'PML01':['FACTURA', 'COMPROBANTE','AUTORIZACION','ORDEN','ADICIONALES','RESULTADO','HCNEURO','HCLINICA'],
        'COM01': ['FACTURA', 'COMPROBANTE','AUTORIZACION','ORDEN','ADICIONALES','RESULTADO','HCNEURO','HCLINICA'],
        'CAJACO':['FACTURA', 'COMPROBANTE','AUTORIZACION','ORDEN','ADICIONALES','RESULTADO','HCNEURO','HCLINICA'],
        'CAJASU':['FACTURA', 'COMPROBANTE','AUTORIZACION','ORDEN','ADICIONALES','RESULTADO','HCNEURO','HCLINICA'],
        'SAL01':['FACTURA', 'COMPROBANTE','AUTORIZACION','ORDEN','ADICIONALES','RESULTADO','HCNEURO','HCLINICA'],
        'CAP01':['FACTURA', 'COMPROBANTE','AUTORIZACION','ORDEN','ADICIONALES','RESULTADO','HCNEURO','HCLINICA'],
        'UNA01':['FACTURA', 'COMPROBANTE','AUTORIZACION','ORDEN','ADICIONALES','RESULTADO','HCNEURO','HCLINICA'],
        'DM02':['FACTURA', 'COMPROBANTE','AUTORIZACION','ORDEN','ADICIONALES','RESULTADO','HCNEURO','HCLINICA'],
        'EQV01':['FACTURA', 'COMPROBANTE','AUTORIZACION','ORDEN','ADICIONALES','RESULTADO','HCNEURO','HCLINICA'],
        'PAR01':['FACTURA', 'COMPROBANTE','AUTORIZACION','ORDEN','ADICIONALES','RESULTADO','HCNEURO','HCLINICA'],
        'CHM05':['FACTURA', 'COMPROBANTE','AUTORIZACION','ORDEN','ADICIONALES','RESULTADO','HCNEURO','HCLINICA'],
        'CHM02': ['FACTURA', 'COMPROBANTE','AUTORIZACION','ORDEN','ADICIONALES','RESULTADO','HCNEURO','HCLINICA'],
        'COL01':['FACTURA', 'COMPROBANTE','AUTORIZACION','ORDEN','ADICIONALES','RESULTADO','HCNEURO','HCLINICA'],
        'MES01': ['FACTURA', 'COMPROBANTE','AUTORIZACION','ORDEN','ADICIONALES','RESULTADO','HCNEURO','HCLINICA'],
        'POL11':['FACTURA', 'COMPROBANTE','AUTORIZACION','ORDEN','ADICIONALES','RESULTADO','HCNEURO','HCLINICA'],
        'UNA02':['FACTURA', 'COMPROBANTE','AUTORIZACION','ORDEN','ADICIONALES','RESULTADO','HCNEURO','HCLINICA'],
        'MUL01':['FACTURA', 'COMPROBANTE','AUTORIZACION','ORDEN','ADICIONALES','RESULTADO','HCNEURO','HCLINICA'],
        'par01':['FACTURA', 'COMPROBANTE','AUTORIZACION','ORDEN','ADICIONALES','RESULTADO','HCNEURO','HCLINICA'],
        'FOM01':['FACTURA', 'COMPROBANTE','AUTORIZACION','ORDEN','ADICIONALES','RESULTADO','HCNEURO','HCLINICA'],
        'IPSOL1':['FACTURA', 'COMPROBANTE','AUTORIZACION','ORDEN','ADICIONALES','RESULTADO','HCNEURO','HCLINICA'],
        'AIR01':['FACTURA', 'COMPROBANTE','AUTORIZACION','ORDEN','ADICIONALES','RESULTADO','HCNEURO','HCLINICA'],
        'AXA01':['FACTURA', 'COMPROBANTE','AUTORIZACION','ORDEN','ADICIONALES','RESULTADO','HCNEURO','HCLINICA'],
       'POL13':['FACTURA', 'COMPROBANTE','AUTORIZACION','ORDEN','ADICIONALES','RESULTADO','HCNEURO','HCLINICA'],
        'BOL01':['FACTURA', 'COMPROBANTE','AUTORIZACION','ORDEN','ADICIONALES','RESULTADO','HCNEURO','HCLINICA'],
    }
    return tipos_documentos_por_codigo_entidad

def obtener_tipos_documentos_por_entidad(codigo_entidad):
    tipos_documentos_por_codigo_entidad = obtener_tipos_documentos_por_codigo_entidad()
    return tipos_documentos_por_codigo_entidad.get(codigo_entidad, []) 

@api_view(['GET'])
def obtener_hallazgos(request):
    try:
        opciones = [
            {"id": 1, "descripcion": "ERROR DE COPAGO"},
            {"id": 2, "descripcion": "ERROR DE CUOTA MODERADORA"},
            {"id": 3, "descripcion": "NO COBRO DE COPAGO"},
            {"id": 4, "descripcion": "NO COBRO DE CUOTA MODERADORA"},
            {"id": 5, "descripcion": "COBRO DE COPAGO CUANDO NO LE APLICABA"},
            {"id": 6, "descripcion": "COBRO DE CUOTA MODERADORA CUANDO NO LE APLICABA"},
            {"id": 7, "descripcion": "ERROR DE TARIFA"},
            {"id": 8, "descripcion": "COBRO MENOS CANTIDADES"},
            {"id": 9, "descripcion": "COBRO MAS CANTIDADES"},
            {"id": 10, "descripcion": "ERROR DE CONTRATO"},
            {"id": 11, "descripcion": "ERROR DE CUPS"},
            {"id": 12, "descripcion": "AUTORIZACIÓN VENCIDA"},
            {"id": 13, "descripcion": "AUTORIZACIÓN CON TACHONES"},
            {"id": 14, "descripcion": "ERROR NÚMERO DE AUTORIZACIÓN"},
            {"id": 15, "descripcion": "FALTA FIRMA DEL COMPROBANTE"},
            {"id": 16, "descripcion": "ERROR TIPO DOCUMENTO PTE"},
            {"id": 17, "descripcion": "ERROR NÚMERO DOCUMENTO DEL PTE"},
            {"id": 18, "descripcion": "ERROR NOMBRE DEL PTE"},
            {"id": 19, "descripcion": "FALTA SOPORTE / REPORTE / HC"},
            {"id": 20, "descripcion": "SOPORTE / REPORTE / HC ADJUNTO NO CORRESPONDE"},
            {"id": 21, "descripcion": "ERROR EDAD"},
            {"id": 22, "descripcion": "ORDEN MÉDICA VENCIDA"},
            {"id": 23, "descripcion": "DOCUMENTOS ILEGIBLES O MAL ESCANEADOS"},
            {"id": 24, "descripcion": "OTROS"},
        ]
        response_data = {
            "success": True,
            "detail": "Hallazgos obtenidos exitosamente",
            "data": opciones
        }
        return JsonResponse(response_data, status=200)
    except Exception as e:
        response_data = {
            "success": False,
            "detail": "Error interno del servidor",
            "error_details": str(e)
        }
        return JsonResponse(response_data, status=500)



