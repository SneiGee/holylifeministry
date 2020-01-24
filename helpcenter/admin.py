from django.contrib import admin

from django.utils.translation import gettext, gettext_lazy as _
from .models import Section, HelpCenter, UsersRequest


class SectionAdmin(admin.ModelAdmin):
    fieldsets = (
        (_('Add Section'), {'fields': ('name', 'is_active')}),
    )
    list_display = ('name', 'is_active')
    list_filter = ('name', 'is_active')
    search_fields = ('name', 'is_active')


class HelpCenterAdmin(admin.ModelAdmin):
    fieldsets = (
        (_('Help Center'), {'fields': ('section', 'title', 'content', 'is_active')}),
    )
    list_display = ('section', 'title', 'is_active')
    list_filter = ('title', 'is_active')
    search_fields = ('section', 'title', 'is_active')


class UsersRequestAdmin(admin.ModelAdmin):
    fieldsets = (
        (_('SUBMIT A REQUEST'), {'fields': ['description', 'status']}),
    )
    list_display = ('status', 'user')
    list_filter = ('status', 'user')
    search_fields = ('status', 'user', 'description')


admin.site.register(Section, SectionAdmin)
admin.site.register(HelpCenter, HelpCenterAdmin)
admin.site.register(UsersRequest, UsersRequestAdmin)
