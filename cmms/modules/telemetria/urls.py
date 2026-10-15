from django.urls import path
from . import views
app_name='telemetry'
urlpatterns=[path('',views.index,name='index'),path('integraciones/',views.keys,name='keys'),
    path('importar/',views.import_file,name='import'),path('plantilla.csv',views.file_template,name='template')]
