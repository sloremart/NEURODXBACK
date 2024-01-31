
from django.conf import settings
from django.contrib import admin
from django.urls import path
from django.conf.urls.static import static
from login.registroViews import LoginView, RegisterView
from citas.views import CitasApiView
from gedocumental.views import ArchivoUploadView, GeDocumentalView, archivos_por_admision, donwloadFile


urlpatterns = [
    path('admin/', admin.site.urls),
    path('lista-citas/', CitasApiView.as_view()),  # CITAS
    path('login/', LoginView.as_view()),
     path('register/', RegisterView.as_view()),
    path('admisiones/<int:consecutivo>/', GeDocumentalView.as_view()),  # ADMISIONES
    path('archivo-upload/<str:consecutivo>/', ArchivoUploadView.as_view()),  # ARCHIVOS
    path('archivos_por_admision/<int:numero_admision>/', archivos_por_admision, name='archivos_por_admision'),
    path('descargar/<int:id_archivo>/', donwloadFile, name='descargar_archivo'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
