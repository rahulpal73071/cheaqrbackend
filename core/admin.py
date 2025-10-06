from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User, AllowedEmail, UserItemStatus, QRToken, Menu

@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ('username', 'email', 'is_staff', 'public_id')
    search_fields = ('username', 'email')

@admin.register(AllowedEmail)
class AllowedEmailAdmin(admin.ModelAdmin):
    list_display = ('email', 'note')
    search_fields = ('email',)

@admin.register(UserItemStatus)
class UserItemStatusAdmin(admin.ModelAdmin):
    list_display = ('user', 'item', 'status', 'updated_at')
    list_filter = ('item', 'status')
    search_fields = ('user__username', 'user__email')

@admin.register(QRToken)
class QRTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'created_at', 'expires_at')
    search_fields = ('user__username', 'token')

# ✅ New
@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ('name', 'available', 'created_at', 'updated_at')
    search_fields = ('name',)
    list_filter = ('available',)
