
from django.conf import settings
from django.contrib import admin
from django.urls import path
from django.conf.urls.static import static
from login.registroViews import LoginView, RegisterView
from citas.views import CitasApiView
from gedocumental.views import AdmisionCuentaMedicaView, AdmisionTesoreriaView,  ArchivoEditView, ArchivoUploadView, CodigoListView, FiltroAuditoriaCuentasMedicas, FiltroTesoreria, GeDocumentalView, admisiones_con_observaciones_por_usuario, archivos_por_admision, crear_carpeta_y_copiar_archivos_view,  downloadFile


urlpatterns = [
    path('admin/', admin.site.urls),
    path('lista-citas/', CitasApiView.as_view()),  # CITAS
    path('login/', LoginView.as_view()),
    path('register/', RegisterView.as_view()),
    path('admisiones/<int:consecutivo>/', GeDocumentalView.as_view()),  # ADMISIONES
    path('archivo_upload/<str:consecutivo>/', ArchivoUploadView.as_view()),  # ARCHIVOS
    path('archivos_por_admision/<int:numero_admision>/', archivos_por_admision, name='archivos_por_admision'),
    path('descargar/<int:id_archivo>/', downloadFile, name='descargar_archivo'),
    path('admision_revision/<str:consecutivoConsulta>/', AdmisionCuentaMedicaView.as_view()),  # REV ADMISION CUENTAS MEDICAS 
    path('admision_revision_tesoreria/<str:consecutivoConsulta>/', AdmisionTesoreriaView.as_view()),# REV ADMISION TESORERIA
    path('filtro_auditoria/', FiltroAuditoriaCuentasMedicas.as_view(), name='filtro_auditoria'),
    path('admisiones/<str:consecutivo>/editar/<int:archivo_id>/', ArchivoEditView.as_view(), name='borrar_archivo'),## editar DE ARCHIVOS 
    path('lista_codigo_entidad/', CodigoListView.as_view()),
    path('archivos_por_usuario_observacion/<int:usuario_id>/', admisiones_con_observaciones_por_usuario, name='archivos_por_usuario'),
    path('filtro_tesoreria/', FiltroTesoreria.as_view(), name='filtro_tesoreria'),
    path('radicar_cuentamedica/<int:numero_admision>/', crear_carpeta_y_copiar_archivos_view, name='informacion_admision_y_archivos'),  # Agrega la nueva ruta


]




if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
