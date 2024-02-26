def obtener_tipos_documentos_por_codigo_entidad():
    tipos_documentos_por_codigo_entidad = {
        'SAN01': ['CEDULA', 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION', 'RESULTADO', ],
        'SAN02': ['CEDULA', 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION', 'RESULTADO', ],
        'POL11': ['CEDULA', 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION', 'RESULTADO', ],
        'POL12': ['CEDULA', 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION', 'RESULTADO', ],
        'PML01': ['CEDULA', 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION', 'RESULTADO', ],
        'COM01': ['CEDULA', 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION', 'RESULTADO', ],
        'CAJACO': ['CEDULA', 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION', 'RESULTADO', ],
        'CAJASU': ['CEDULA', 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION', 'RESULTADO', ],
        'SAL01': ['CEDULA', 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION', 'RESULTADO', ],
        'CAP01': ['CEDULA', 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION', 'RESULTADO', ],
        'UNA01': ['CEDULA', 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION', 'RESULTADO', ],
        'DM02': ['CEDULA', 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION', 'RESULTADO', ],
        'EQV01': ['CEDULA', 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION', 'RESULTADO', ],
        'PAR01': ['CEDULA', 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION', 'RESULTADO', ],
        'CHM01': ['CEDULA', 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION', 'RESULTADO', ],
        'CHM02': ['CEDULA', 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION', 'RESULTADO', ],
    }
    return tipos_documentos_por_codigo_entidad

def obtener_tipos_documentos_por_entidad(codigo_entidad):
    tipos_documentos_por_codigo_entidad = obtener_tipos_documentos_por_codigo_entidad()
    return tipos_documentos_por_codigo_entidad.get(codigo_entidad, [])

# Ejemplo de uso:
codigo_entidad = "DM02"
tipos_documentos = obtener_tipos_documentos_por_entidad(codigo_entidad)
print("Tipos de documentos para la entidad", codigo_entidad, ":", tipos_documentos)