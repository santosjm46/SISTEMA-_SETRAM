from django.urls import path
from . import views
app_name='administration'
urlpatterns=[path('',views.organization,name='organization'),path('modulos/',views.visibility,name='visibility'),path('facturacion/',views.finance,name='finance')]
