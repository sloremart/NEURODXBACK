def obtener_tipos_documentos_por_codigo_entidad():
    tipos_documentos_por_codigo_entidad = {
        'SAN01': [ 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION','VALIDADOR','RESULTADO', ],
        'SAN02': [ 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION','VALIDADOR', 'RESULTADO', ],
        'POL11': [ 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION','VALIDADOR', 'RESULTADO', ],
        'POL12': [ 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION','VALIDADOR', 'RESULTADO', ],
        'PML01': [ 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION','VALIDADOR', 'RESULTADO', ],
        'COM01': [ 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION','VALIDADOR', 'RESULTADO', ],
        'CAJACO': [ 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION','VALIDADOR', 'RESULTADO', ],
        'CAJASU': [ 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION','VALIDADOR', 'RESULTADO', ],
        'SAL01': [ 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION','VALIDADOR', 'RESULTADO', ],
        'CAP01': [ 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION','VALIDADOR', 'RESULTADO', ],
        'UNA01': [ 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION','VALIDADOR', 'RESULTADO', ],
        'DM02': [ 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION','VALIDADOR', 'RESULTADO', ],
        'EQV01': [ 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION','VALIDADOR', 'RESULTADO', ],
        'PAR01': [ 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION','VALIDADOR', 'RESULTADO', ],
        'CHM01': [ 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION','VALIDADOR', 'RESULTADO', ],
        'CHM02': [ 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION','VALIDADOR', 'RESULTADO', ],
    }
    return tipos_documentos_por_codigo_entidad

def obtener_tipos_documentos_por_entidad(codigo_entidad):
    tipos_documentos_por_codigo_entidad = obtener_tipos_documentos_por_codigo_entidad()
    return tipos_documentos_por_codigo_entidad.get(codigo_entidad, [])

# Ejemplo de uso:
codigo_entidad = "DM02"
tipos_documentos = obtener_tipos_documentos_por_entidad(codigo_entidad)
print("Tipos de documentos para la entidad", codigo_entidad, ":", tipos_documentos)
