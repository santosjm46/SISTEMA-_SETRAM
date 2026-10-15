from django.urls import path
from . import views
app_name='documents'
urlpatterns=[path('auditor/',views.auditor,name='auditor'),path('vision/',views.vision,name='vision')]
