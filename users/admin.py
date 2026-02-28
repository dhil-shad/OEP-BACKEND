from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Role & Profile', {'fields': ('role', 'enrollment_number', 'department')}),
    )

admin.site.register(User, CustomUserAdmin)
