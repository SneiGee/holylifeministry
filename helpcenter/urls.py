from django.urls import path
from track.views import hit_count

from helpcenter import views as help_view


urlpatterns = [
    # -----    HOLY LIFE MINISTRY CREDENTIALS (Login, Craete account, Logout) .and more )    -------- #
    path('', hit_count(help_view.HelpHomePageView.as_view()), name='help_homepage'),
    path('section/<slug>/', hit_count(help_view.SectionListView.as_view()), name='section_view'),
    path('articles/<help_hex>/', hit_count(help_view.ArticleDetailView.as_view()), name='articles_detail'),

    path('search/', help_view.search_helpcenter, name='search_helpcenter'),

    path('request/new/', hit_count(help_view.SubmitRequestView.as_view()), name='submit_request'),


]
