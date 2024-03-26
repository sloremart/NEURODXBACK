from rest_framework import serializers

from gedocumental.modelsFacturacion import Admisiones
from .models import ArchivoFacturacion, AuditoriaCuentasMedicas, ObservacionesArchivos
from django.contrib.auth import authenticate


class ObservacionesArchivosSerializer(serializers.ModelSerializer):
    class Meta:
        model = ObservacionesArchivos
        fields = '__all__'

class ArchivoFacturacionSerializer(serializers.ModelSerializer):
    Observaciones = ObservacionesArchivosSerializer(many=True, read_only=True)

    class Meta:
        model = ArchivoFacturacion
        fields = '__all__'

class AdmisionConArchivosSerializer(serializers.ModelSerializer):
    archivos_facturacion = ArchivoFacturacionSerializer(many=True, read_only=True)
    observaciones = ObservacionesArchivosSerializer(many=True, read_only=True)

    class Meta:
        model = ArchivoFacturacion
        fields = ['Admision_id', 'FechaCreacionArchivo', 'archivos_facturacion', 'observaciones']

class RevisionCuentaMedicaSerializer(serializers.ModelSerializer):
    archivos_facturacion = ArchivoFacturacionSerializer(many=True, read_only=True)

    class Meta:
        model = ArchivoFacturacion
        fields = ['Admision_id', 'FechaCreacionArchivo', 'archivos_facturacion', 'RevisionPrimera',  'RevisionSegunda']

class AuditoriaCuentasMedicasSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditoriaCuentasMedicas
        fields = '__all__'


class AdmisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Admisiones
        fields = '__all__'