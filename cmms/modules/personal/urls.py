from django.urls import path
from . import views
app_name='team'
urlpatterns=[path('invitaciones/',views.invitations,name='invitations'),path('unirse/<uuid:public_id>/',views.accept,name='accept')]
