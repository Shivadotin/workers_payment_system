from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User



@admin.register(User)
class CustomUserAdmin(UserAdmin):

    fieldsets = UserAdmin.fieldsets + (
        ('Role Information', {
            'fields': ('role', 'superwiser_code' , 'phone_number')
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Role Information', {
            'fields': ('role',  )
        }),
    )

    list_display = (
        'superwiser_code' ,
        'username',
        'email',
        'first_name',
        'last_name',
        'role',
        'is_staff',
    )
