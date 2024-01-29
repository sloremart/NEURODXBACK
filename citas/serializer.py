from rest_framework import serializers
from .models import Citas
from .models import Pacientes

# Convertir los objetos a un JSOn

class PacienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pacientes
        fields = ['Nombre1', 'Nombre2', 'Apellido1', 'Apellido2', 'IDPaciente', 'Telefono']

class CitaSerializer(serializers.ModelSerializer):
    paciente = PacienteSerializer(source='NumeroPaciente', read_only=True)
    class Meta:
        
        model = Citas
        fields = ['FechaCita', 'NumeroPaciente', 'paciente']   

