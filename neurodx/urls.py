"""
URL configuration for neurodx project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.urls import path
from django.conf.urls.static import static
from login.registroViews import LoginView, RegisterView
from gedocumental.views import ArchivoUploadView, GeDocumentalView
from citas.views import CitasApiView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('lista-citas/', CitasApiView.as_view(), name='citas-list'),  # CITAS
    path('login/', LoginView.as_view(), name='login'),
     path('register/', RegisterView.as_view(), name='register'),
    path('admisiones/<int:consecutivo>/', GeDocumentalView.as_view(), name='admisiones'),  # ADMISIONES
    path('archivo-upload/<str:consecutivo>/', ArchivoUploadView.as_view(), name='archivo-upload'),  # ARCHIVOS

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
