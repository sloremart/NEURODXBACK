from rest_framework import serializers

from controlfacturacion.models import DetalleFactura

class DateSerializerField(serializers.Field):
    def to_representation(self, value):
        return value.date()

class DetalleFacturaSerializer(serializers.ModelSerializer):
    FechaServicio = DateSerializerField()

    class Meta:
        model = DetalleFactura
        fields = '__all__'