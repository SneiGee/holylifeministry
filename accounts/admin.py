from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.contrib.admin.options import IS_POPUP_VAR
from django.contrib.admin.utils import unquote
from django.contrib.auth import update_session_auth_hash
from django.utils.translation import gettext, gettext_lazy as _
from django.contrib.auth.forms import (
    AdminPasswordChangeForm, UserChangeForm, UserCreationForm,
)
from django.core.exceptions import PermissionDenied
from django.db import router, transaction
from django.http import Http404, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.decorators import method_decorator
from django.utils.html import escape
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters

csrf_protect_m = method_decorator(csrf_protect)
sensitive_post_parameters_m = method_decorator(sensitive_post_parameters())

from accounts.models import User, UserRole, Profile, Action, Report, ReportUser, ContactUs, ContactUsSettings

class CustomUserAdmin(UserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    # change_password_form = AdminPasswordChangeForm
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_superuser')
    list_filter = ('is_superuser', 'is_active', 'groups')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('username',)


@admin.register(Action)
class ActionAdmin(admin.ModelAdmin):
    list_display = ('user', 'verb', 'target', 'created')
    list_filter = ('created',)
    search_fields = ('verb',)

class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'bio', 'website', 'created')


class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')

class ContactUsAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'email', 'message')


class ContactUsSettingsAdmin(admin.ModelAdmin):
    list_display = ('from_email', 'reply_to_email', 'email_admin')


admin.site.register(User, CustomUserAdmin)

admin.site.register(UserRole, UserRoleAdmin)

admin.site.register(Profile, ProfileAdmin)

admin.site.register(Report)

admin.site.register(ReportUser)

admin.site.register(ContactUs, ContactUsAdmin)
admin.site.register(ContactUsSettings, ContactUsSettingsAdmin)
