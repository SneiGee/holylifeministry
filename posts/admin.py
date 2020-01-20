from django.contrib import admin
from django.utils.translation import gettext, gettext_lazy as _
from .models import Category, Tags, Post, BibleStudies, Devotion, Tech, Quotes, Policy, PrayerRequest


class CategoryAdmin(admin.ModelAdmin):
    fieldsets = (
        (_('Topic / Category'), {'fields': ('name', 'user', 'description', 'is_active')}),
    )
    list_display = ('name', 'slug', 'user', 'description', 'is_active')
    list_filter = ('name', 'description', 'is_active')
    search_fields = ('name', 'description')


class TagsAdmin(admin.ModelAdmin):
    fieldsets = (
        (_('Tags'), {'fields': ['name']}),
    )
    list_display = ('name', 'slug')
    list_filter = ('name', 'slug')
    search_fields = ('name', 'slug')


class PostAdmin(admin.ModelAdmin):
    fieldsets = (
        (_('New Story'), {'fields': ('title', 'user', 'featured_image', 'content', 'category', 'tags', 'status')}),
    )
    list_display = ('title', 'slug', 'user', 'category', 'status')
    list_filter = ('user', 'category')
    search_fields = ('title', 'user', 'category', 'status')


class BibleStudiesAdmin(admin.ModelAdmin):
    fieldsets = (
        (_('Create Bible Studies'), {'fields': ('title', 'featured_image', 'content', 'user')}),
    )
    list_display = ('title', 'slug', 'user', 'created_on')
    list_filter = ('user', 'created_on')
    search_fields = ('title', 'user', 'created_on')


class DevotionAdmin(admin.ModelAdmin):
    fieldsets = (
        (_('Create Devotion'), {'fields': ('title', 'featured_image', 'content', 'user')}),
    )
    list_display = ('title', 'slug', 'user', 'created_on')
    list_filter = ('user', 'created_on')
    search_fields = ('title', 'user', 'created_on')


class TechAdmin(admin.ModelAdmin):
    fieldsets = (
        (_('Add New Tech'), {'fields': ('title', 'featured_image', 'content', 'user')}),
    )
    list_display = ('title', 'slug', 'user', 'created_on')
    list_filter = ('user', 'created_on')
    search_fields = ('title', 'user', 'created_on')


class QuotesAdmin(admin.ModelAdmin):
    fieldsets = (
        (_('Add New Quote'), {'fields': ('title', 'content', 'featured_image', 'user')}),
    )
    list_display = ('title', 'slug', 'user', 'created_on')
    list_filter = ('user', 'created_on')
    search_fields = ('title', 'user', 'created_on')


class PrivacyAdmin(admin.ModelAdmin):
    fieldsets = (
        (_('Add New Privacy'), {'fields': ('title', 'featured_image', 'content', 'tags', 'user')}),
    )
    list_display = ('title', 'slug', 'user', 'created_on')
    list_filter = ('user', 'created_on')
    search_fields = ('title', 'user', 'created_on')


class PrayerRequestAdmin(admin.ModelAdmin):
    fieldsets = (
        (_('Prayer Request'), {'fields': ('user', 'area', 'message')}),
    )
    list_display = ('user', 'area', 'message', 'created_on')
    list_filter = ('user', 'created_on')
    search_fields = ('area', 'user', 'created_on')


admin.site.register(Category, CategoryAdmin)
admin.site.register(Tags, TagsAdmin)
admin.site.register(Post, PostAdmin)
admin.site.register(BibleStudies, BibleStudiesAdmin)
admin.site.register(Devotion, DevotionAdmin)
admin.site.register(Tech, TechAdmin)
admin.site.register(Quotes, QuotesAdmin)
admin.site.register(Policy, PrivacyAdmin)
admin.site.register(PrayerRequest, PrayerRequestAdmin)
