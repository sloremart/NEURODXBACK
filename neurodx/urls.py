
from django.conf import settings
from django.contrib import admin
from django.urls import path
from django.conf.urls.static import static
from login.registroViews import CustomUserListView, LoginView, RegisterView
from citas.views import CitasApiView
from gedocumental.views import ActualizarRegimenArchivosView, AdmisionCuentaMedicaView, AdmisionTesoreriaView, AdmisionesConTiposDeDocumento, AdmisionesPorFechaYFacturado, AdmisionesPorFechaYUsuario, AgregarObservacionSinArchivoView,  ArchivoEditView, ArchivoFacturacionDeleteView, ArchivoUploadView, CodigoListView, FiltroAuditoriaCuentasMedicas, FiltroTesoreria, GeDocumentalView, ObservacionesPorUsuario, PunteoAntaresSubdireccion, PunteoNeurodxSubdireccion, RevisarObservacion, TablaRadicacion, actualizar_correciones_cm, actualizar_modificado_revisor, admisiones_con_id_revisor, admisiones_con_observaciones_por_usuario, admisiones_con_revision_tesoreria, admisiones_revision_para_cm, archivos_por_admision, idrevisor_tesoreria, quitar_revisor_admision,  radicar_capitalsalud_view, radicar_colsanitas_view, radicar_compensar_view,  downloadFile, radicar_mes01_view, radicar_other_view, radicar_salud_total_view, radicar_san02_view, radicar_sanitas_evento_view
from controlfacturacion.views import AgendasView, CiPxApiView, CitasPxApiView, CodigoSoatList, ContratoTarifaListView, FiltroDetalleFacturaPorFecha, FiltroFacturaPorFecha, CitasSubcentroApiView
from gedocumental.utils.codigoentidad import obtener_hallazgos
from login.views import AsistencialListView, CuentasMedicasListView, FacturadorListView, TotalCargosListView
from subdireccionprocesos.views import AdmisionesConObservacionesView, AdmisionesPorUsuario, ArchivosRevisadosPorCM, ProcessedXMLView, generar_pdf_orden, generar_pdf_orden_view



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
    path('archivos_por_usuario_observacion_tesoreria/<int:usuario_id>/', admisiones_con_revision_tesoreria,),
    path('filtro_tesoreria/', FiltroTesoreria.as_view(), name='filtro_tesoreria'),
    path('radicar_compensar/<int:numero_admision>/<str:idusuario>/', radicar_compensar_view, name='radicar_compensar'),
    path('radicar_salud_total/<int:numero_admision>/<str:idusuario>/', radicar_salud_total_view, ),   
    path('radicar_sanitas_evento/<int:numero_admision>/<str:idusuario>/', radicar_sanitas_evento_view, ), 
    path('radicar_mes01_view/<int:numero_admision>/<str:idusuario>/', radicar_mes01_view, ),  
    path('radicar_colsanitas/<int:numero_admision>/<str:idusuario>/', radicar_colsanitas_view, ),  
    path('radicar_capital_salud/<int:numero_admision>/<str:idusuario>/', radicar_capitalsalud_view, ), 
    path('radicar_san02/<int:numero_admision>/<str:idusuario>/', radicar_san02_view, ),   
    path('radicar_otros/<int:numero_admision>/<str:idusuario>/', radicar_other_view, ),  
    path('tabla_radicacion/', TablaRadicacion.as_view(), name='tabla_radicacion'),
    path('detallefacturacion/', FiltroDetalleFacturaPorFecha.as_view(), name='facturacion'),
    path('facturacion/', FiltroFacturaPorFecha.as_view(), name='facturacion'),
    path('citaspx/', CitasPxApiView.as_view()),  
    path('consolidado_especialidad/', CiPxApiView.as_view()),  
    path('consolidado_subcentro/', CitasSubcentroApiView.as_view()),
    path('agenda/', AgendasView.as_view()),
    path('lista_contrato_tarifa/', ContratoTarifaListView.as_view()),
    path('tarifas_contratos/<int:tarifa_number>/', CodigoSoatList.as_view(), name='codigo_soat_list'),
    path('usuarios/', CustomUserListView.as_view(), name='customuser-list'),
    path('punteo/', AdmisionesPorFechaYFacturado.as_view(), name='admisiones_por_fecha_y_facturado'),
    path('punteo_neurodx/', AdmisionesPorFechaYUsuario.as_view(), name='admisiones_neurodx'),
    path('hallazgos/', obtener_hallazgos , ),
    path('punteo_neurodx_subdireccion/', PunteoNeurodxSubdireccion.as_view()),
    path('punteo_antares_subdireccion/', PunteoAntaresSubdireccion.as_view()),
    path('admisiones_con_tipos_documento/', AdmisionesConTiposDeDocumento.as_view()),
    path('actualizar_regimen/<int:consecutivo>/', ActualizarRegimenArchivosView.as_view(), name='actualizar_regimen'),
    path('agregar_observacion_sin_archivo/', AgregarObservacionSinArchivoView.as_view(), name='agregar_observacion_sin_archivo'),
    path('observaciones/<int:user_id>/', ObservacionesPorUsuario.as_view(), name='observaciones-por-usuario'),
    path('revisar_observacion/<int:admision_id>/', RevisarObservacion.as_view(), name='revisar-observacion'), #
    path('actualizar_modificado_revisor/', actualizar_modificado_revisor, name='actualizar_modificado_revisor'),#envio de admsion al cm y tesoreria ya modificada
    path('admisiones_con_id_revisor/<int:id_revisor>/', admisiones_con_id_revisor, name='admisiones_con_id_revisor'),
    path('eliminar_archivo_facturacion/', ArchivoFacturacionDeleteView.as_view(), name='archivo_facturacion_delete'),
    path('actualizar_correciones_cm/', actualizar_correciones_cm, name='actualizar_correciones_cm'),
    path('admision_revisor_tesoreria/', idrevisor_tesoreria, name='enviar_tesoreria'),
    path('admisiones_enviadas_cm/<int:id_revisor>/', admisiones_revision_para_cm, name='admisiones_revision_para_cm'),
    path('admisiones_auditoria_subprocesos/',  AdmisionesPorUsuario.as_view(), name='admisiones_auditoria_subprocesos'),
    path('admision_revisadas_cm/',  ArchivosRevisadosPorCM.as_view(), name='admisiones_revisadas'),
    path('listado_admsiones_observaciones/',  AdmisionesConObservacionesView.as_view(), name='admisiones_revisadas'),
    path('users/facturador/', FacturadorListView.as_view(), name='facturador-list'),
    path('users/asistencial/', AsistencialListView.as_view(), name='facturador-list'),
    path('users/cargos_totales/', TotalCargosListView.as_view(), name='facturador-list'),
    path('users/cuentas_medicas/', CuentasMedicasListView.as_view(), name='facturador-list'),
    path('eliminar_idrevisor/<int:numero_admision>/', quitar_revisor_admision, name='facturador-list'),
    path('procesados/', ProcessedXMLView.as_view(), name='procesados'),
    path('generar-pdf/<str:orden_id>/', generar_pdf_orden_view, name='generar_pdf_orden'),


]




if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
