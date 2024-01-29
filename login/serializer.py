
###### register ###########
from rest_framework import serializers
from .models import CustomUser

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'password', 'nombre', 'email', 'cargo')
        extra_kwargs = {'password': {'write_only': True}}


######## login

from rest_framework import serializers
from django.contrib.auth import authenticate

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')

        if username and password:
            user = authenticate(username=username, password=password)

            if user:
                data['user'] = user
            else:
                raise serializers.ValidationError('Nombre de usuario o contraseña incorrectos.')
        else:
            raise serializers.ValidationError('Se requieren nombre de usuario y contraseña.')

        return data
    