def obtener_tipos_documentos_por_codigo_entidad():
    tipos_documentos_por_codigo_entidad = {
        'SAN01': [ 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION','VALIDADOR','RESULTADO','HISTORIACLINICA',  ],
        'SAN02': [ 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION','VALIDADOR', 'RESULTADO','HISTORIACLINICA',   ],
        'POL11': [ 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION','VALIDADOR', 'RESULTADO','HISTORIACLINICA',  ],
        'POL12': [ 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION','VALIDADOR', 'RESULTADO','HISTORIACLINICA',  ],
        'PML01': [ 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION','VALIDADOR', 'RESULTADO','HISTORIACLINICA',  ],
        'COM01': [ 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION','VALIDADOR', 'RESULTADO', 'HISTORIACLINICA', ],
        'CAJACO': [ 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION','VALIDADOR', 'RESULTADO','HISTORIACLINICA',  ],
        'CAJASU': [ 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION','VALIDADOR', 'RESULTADO', 'HISTORIACLINICA', ],
        'SAL01': [ 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION','VALIDADOR', 'RESULTADO', 'HISTORIACLINICA', ],
        'CAP01': [ 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION','VALIDADOR', 'RESULTADO', 'HISTORIACLINICA', ],
        'UNA01': [ 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION','VALIDADOR', 'RESULTADO', 'HISTORIACLINICA', ],
        'DM02': [ 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION','VALIDADOR', 'RESULTADO', 'HISTORIACLINICA', ],
        'EQV01': [ 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION','VALIDADOR', 'RESULTADO','HISTORIACLINICA',  ],
        'PAR01': [ 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION','VALIDADOR', 'RESULTADO','HISTORIACLINICA',  ],
        'CHM01': [ 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION','VALIDADOR', 'RESULTADO','HISTORIACLINICA',  ],
        'CHM02': [ 'ORDEN', 'FACTURA', 'COMPROBANTE','AUTORIZACION','VALIDADOR', 'RESULTADO','HISTORIACLINICA',  ],
    }
    return tipos_documentos_por_codigo_entidad

def obtener_tipos_documentos_por_entidad(codigo_entidad):
    tipos_documentos_por_codigo_entidad = obtener_tipos_documentos_por_codigo_entidad()
    return tipos_documentos_por_codigo_entidad.get(codigo_entidad, [])

# Ejemplo de uso:
codigo_entidad = "DM02"
tipos_documentos = obtener_tipos_documentos_por_entidad(codigo_entidad)
print("Tipos de documentos para la entidad", codigo_entidad, ":", tipos_documentos)
