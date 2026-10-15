from django.contrib import admin
from django.contrib.auth import views as auth
from django.urls import path,include
from cmms.modules.telemetria.views import ingest_endpoint
from cmms import views
from cmms.modules import extended_views as extended
from cmms.modules.personal import joining
from cmms.modules.documentos.vision_api import endpoint as vision_ingest

urlpatterns = [
    path('catalogos/iniciales/',extended.catalog_presets,name='catalog-presets'),
    path('api/v1/vision/ingest/',vision_ingest,name='vision-ingest'),
    path('equipo/qr/',joining.qr,name='team-qr'),
    path('equipo/solicitar/<str:token>/',joining.join,name='team-join'),
    path('cuenta/reactivacion/',joining.reactivation,name='reactivation-request'),
    path('buscar/',extended.search,name='global-search'),
    path('operacion/combustible/analitica/',extended.fuel_analytics,name='fuel-analytics'),
    path('panel/widgets/',extended.widgets,name='dashboard-widgets'),
    path('flota/<int:pk>/qr/',extended.bus_qr,name='bus-qr'),
    path('modulos/<str:key>/pdf/',extended.record_pdf,name='record-pdf'),
    path('modulos/<str:key>/importar/',extended.catalog_import,name='catalog-import'),
    path('informes/todos.zip',extended.report_zip,name='report-zip'),
    path('informes/generados/<int:pk>/archivo/',extended.report_run_file,name='report-run-file'),
    path('informes/<str:kind>/',extended.report,name='report-detail'),
    path('flota/fotos/<int:pk>/archivo/',extended.bus_photo_file,name='bus-photo-file'),
    path('compras/<int:pk>/recibir/',extended.purchase_partial,name='purchase-partial'),
    path('',include('cmms.modules.portal.urls')),
    path('telemetria/',include('cmms.modules.telemetria.urls')),
    path('predictivo/',include('cmms.modules.predictivo.urls')),
    path('cumplimiento/',include('cmms.modules.seguridad.urls')),
    path('operacion/',include('cmms.modules.operacion.urls')),
    path('inspecciones/',include('cmms.modules.inspecciones.urls')),
    path('documentos/',include('cmms.modules.documentos.urls')),
    path('organizacion/',include('cmms.modules.administracion.urls')),
    path('equipo/',include('cmms.modules.personal.urls')),
    path('api/v1/telemetria/ingest/',ingest_endpoint,name='telemetry-ingest'),
    path('login/',auth.LoginView.as_view(template_name='registration/login.html'),name='login'),
    path('logout/',auth.LogoutView.as_view(),name='logout'),
    path('perfil/clave/',auth.PasswordChangeView.as_view(template_name='registration/password_change.html',success_url='/perfil/clave/listo/'),name='password_change'),
    path('perfil/clave/listo/',auth.PasswordChangeDoneView.as_view(template_name='registration/password_done.html'),name='password_change_done'),
    path('',views.dashboard,name='dashboard'),
    path('calendario/',views.calendar_view,name='calendar'),
    path('informes/',views.reports,name='reports'),
    path('configuracion/',views.settings_view,name='settings'),
    path('salud/',views.health,name='health'),
    path('documentos/<int:pk>/descargar/',views.document_file,name='document-file'),
    path('modulos/<str:key>/',views.list_records,name='list'),
    path('modulos/<str:key>/nuevo/',views.edit_record,name='create'),
    path('modulos/<str:key>/exportar/',views.export_csv,name='export'),
    path('modulos/<str:key>/<int:pk>/',views.detail,name='detail'),
    path('modulos/<str:key>/<int:pk>/editar/',views.edit_record,name='edit'),
    path('modulos/<str:key>/<int:pk>/accion/',views.action,name='action'),
    path('api/v1/<str:key>/',views.api_records,name='api-list'),
    path('api/v1/<str:key>/<int:pk>/',views.api_records,name='api-detail'),
    path('api/v1/ordenes/<int:pk>/estado/',views.api_order_state,name='api-order-state'),
]
