
from django.conf import settings
from django.contrib import admin
from django.urls import path
from django.conf.urls.static import static
from login.registroViews import LoginView, RegisterView
from citas.views import CitasApiView
from gedocumental.views import AdmisionCuentaMedicaView, AdmisionTesoreriaView,  ArchivoEditView, ArchivoUploadView, CodigoListView, FiltroAuditoriaCuentasMedicas, FiltroTesoreria, GeDocumentalView, TablaRadicacion, admisiones_con_observaciones_por_usuario, archivos_por_admision, radicar_capitalsalud_view, radicar_colsanitas_view, radicar_compensar_view,  downloadFile, radicar_other_view, radicar_salud_total_view, radicar_sanitas_evento_view
from controlfacturacion.views import CitasPxApiView, FiltroDetalleFacturaPorFecha, FiltroFacturaPorFecha


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
    path('archivos_por_usuario_observacion/<int:usuario_id>/', admisiones_con_observaciones_por_usuario,),
    path('filtro_tesoreria/', FiltroTesoreria.as_view(), name='filtro_tesoreria'),
    path('radicar_compensar/<int:numero_admision>/', radicar_compensar_view, name='radicar_compensar'),
    path('radicar_salud_total/<int:numero_admision>/', radicar_salud_total_view, ),   
    path('radicar_sanitas_evento/<int:numero_admision>/', radicar_sanitas_evento_view, ),  
    path('radicar_colsanitas/<int:numero_admision>/', radicar_colsanitas_view, ),  
    path('radicar_capital_salud/<int:numero_admision>/', radicar_capitalsalud_view, ),  
    path('radicar_otros/<int:numero_admision>/', radicar_other_view, ),  
    path('detallefacturacion/', FiltroDetalleFacturaPorFecha.as_view(), name='facturacion'),
    path('facturacion/', FiltroFacturaPorFecha.as_view(), name='facturacion'),
    path('citaspx/', CitasPxApiView.as_view()),  # CITAS
]




if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
