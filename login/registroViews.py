# registroViews.py

from rest_framework import generics, permissions
from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from django_filters.rest_framework import DjangoFilterBackend
from .models import CustomUser
from .serializer import LoginSerializer, UserSerializer

class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        email = serializer.validated_data['email']
        username = email.split('@')[0]

        if CustomUser.objects.filter(username=username).exists():
            username = f"{username}_{CustomUser.objects.count() + 1}"

        serializer.validated_data['username'] = username

        instance = serializer.save()
        instance.set_password(instance.password)
        instance.save()

        return Response(serializer.data)

class LoginView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data['username']
        password = serializer.validated_data['password']

        user = authenticate(username=username, password=password)

        if user is not None:
            token, created = Token.objects.get_or_create(user=user)
            user_serializer = UserSerializer(user)
            response_data = {
                'token': token.key,
                'user': user_serializer.data,
            }

            # Imprimir el token generado para verificar
            print("Token generado:", token.key)

            return Response(response_data, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Nombre de usuario o contraseña incorrectos.'}, status=status.HTTP_400_BAD_REQUEST)
        

class CustomUserListView(generics.ListAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['cargo'] 