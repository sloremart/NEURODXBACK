from rest_framework import serializers
from .models import ArchivoFacturacion
from django.contrib.auth import authenticate


class ArchivoFacturacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArchivoFacturacion
        fields = '__all__'

class AdmisionConArchivosSerializer(serializers.ModelSerializer):
    archivos_facturacion = ArchivoFacturacionSerializer(many=True, read_only=True)

    class Meta:
        model = ArchivoFacturacion
        fields = ['Admision_id', 'FechaCreacionArchivo', 'archivos_facturacion']

class RevisionCuentaMedicaSerializer(serializers.ModelSerializer):
    archivos_facturacion = ArchivoFacturacionSerializer(many=True, read_only=True)

    class Meta:
        model = ArchivoFacturacion
        fields = ['Admision_id', 'FechaCreacionArchivo', 'archivos_facturacion', 'RevisionPrimera',]


