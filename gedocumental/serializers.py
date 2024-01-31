from rest_framework import serializers
from .models import ArchivoFacturacion
from django.contrib.auth import authenticate


class ArchivoFacturacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArchivoFacturacion
        fields = '__all__'

