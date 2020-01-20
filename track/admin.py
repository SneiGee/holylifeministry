from django.db.models import Count
from django.contrib import admin
from track.models import UrlHit, HitCount


class UrlHitModelAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'url', 'hits')
    search_fields = ('url',)
    list_filter = ('url',)

    class Meta:
        model = UrlHit


class HitCountModelAdmin(admin.ModelAdmin):
    list_display = ('url_hit', 'ip', 'session', 'date')
    search_fields = ('url_hit',)
    list_filter = ('url_hit',)

    class Meta:
        model = HitCount


admin.site.register(UrlHit, UrlHitModelAdmin)
admin.site.register(HitCount, HitCountModelAdmin)
