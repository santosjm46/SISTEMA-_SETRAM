from django.urls import path
from . import views
app_name='security'
urlpatterns=[path('',views.index,name='index')]
