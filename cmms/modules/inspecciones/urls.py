from django.urls import path
from . import views
app_name='inspections'
urlpatterns=[path('notificaciones/',views.notifications,name='notifications')]
