from django.urls import path
from . import views
app_name='operation'
urlpatterns=[path('jornadas/',views.hos,name='hos')]
