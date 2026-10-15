from django.urls import path
from . import views
app_name='predictive'
urlpatterns=[path('',views.index,name='index')]
