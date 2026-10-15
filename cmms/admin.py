from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class SetramUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (('SETRAM',{'fields':('organization','role','phone')}),)
