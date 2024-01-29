# registroViews.py

from rest_framework import generics, permissions
from rest_framework.response import Response

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token

from .models import CustomUser
from .serializer import LoginSerializer, UserSerializer  # Importar Token aquí

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

        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)

        user_serializer = UserSerializer(user)
        response_data = {
            'token': token.key,
            'user': user_serializer.data,
        }

        return Response(response_data, status=status.HTTP_200_OK)
