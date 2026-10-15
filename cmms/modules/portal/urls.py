from django.urls import path
from . import views
app_name='portal'
urlpatterns=[path('comenzar/',views.start,name='start'),path('ejecutivo/',views.executive,name='executive'),path('flota/pulso/',views.pulse,name='pulse')]
