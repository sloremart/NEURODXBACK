
from django.conf import settings
from django.contrib import admin
from django.urls import path
from django.conf.urls.static import static
from login.registroViews import LoginView, RegisterView
from citas.views import CitasApiView
from gedocumental.views import AdmisionCuentaMedicaView,  ArchivoEditView, ArchivoUploadView, CodigoListView,  FiltroAuditoriaCuentasMedicas, GeDocumentalView, archivos_por_admision, downloadFile


urlpatterns = [
    path('admin/', admin.site.urls),
    path('lista-citas/', CitasApiView.as_view()),  # CITAS
    path('login/', LoginView.as_view()),
    path('register/', RegisterView.as_view()),
    path('admisiones/<int:consecutivo>/', GeDocumentalView.as_view()),  # ADMISIONES
    path('archivo_upload/<str:consecutivo>/', ArchivoUploadView.as_view()),  # ARCHIVOS
    path('archivos_por_admision/<int:numero_admision>/', archivos_por_admision, name='archivos_por_admision'),
    path('descargar/<int:id_archivo>/', downloadFile, name='descargar_archivo'),
    path('admision_revision/<str:consecutivoConsulta>/', AdmisionCuentaMedicaView.as_view()),  # ADMISION CUENTAS MEDICAS - TALENTO HUMANO
    path('filtro_auditoria/', FiltroAuditoriaCuentasMedicas.as_view(), name='filtro_auditoria'),
    path('admisiones/<str:consecutivo>/editar/<int:archivo_id>/', ArchivoEditView.as_view(), name='borrar_archivo'),## editar DE ARCHIVOS 
    path('lista_codigo_entidad/', CodigoListView.as_view()),

]




if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
