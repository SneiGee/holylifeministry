
from django.urls import path
from posts import views as post_view
from track.views import hit_count

urlpatterns = [
    path('', hit_count(post_view.HolyLifeMinistryHomePageView.as_view()), name='home'),
    # -----    CHRISTIANBASE BIBLE STUDIES ( Bible Studies, Craete and Update  .and more )    -------- #
    path('bible-studies/', hit_count(post_view.HolyLifeMinistryBibleStudiesView.as_view()), name='bible-studies'),
    path('bible-studies/add/', post_view.HolyLifeMinistryAddBibleStudiesView.as_view(), name='bible-studies-add'),
    path('bible-studies/<slug>/', hit_count(post_view.HolyLifeMinistryBibleStudiesDetailView.as_view()), name='bible-studies-view'),
    path('bible-studies/<slug>/edit/', post_view.HolyLifeMinistryBibleStudiesUpdateView.as_view(), name='bible-studies-edit'),
    path('bible-studies-like/', post_view.biblestudies_like_post, name='biblestudies_like_post'),
    path('bible-studies-comment/<int:id>/', post_view.bible_studies_comment, name='bible_studies_comment'),
    path('bible-studies/<slug:slug>/archive/', post_view.MakeBibleStudiesArchiveView.as_view(), name='make-bible-studies-archive'),
    path('bible-studies/<slug:slug>/remove-archive/', post_view.UnArchiveBibleStudiesView.as_view(), name='unarchive-bible-studies'),
    # -----    CHRISTIANBASE DEVOTION ( Devotion Create and Update  .and more )    -------- #
    path('devotion/', hit_count(post_view.HolyLifeMinistryDevotionView.as_view()), name='devotion'),
    path('devotion/add/', post_view.HolyLifeMinistryAddDevotionView.as_view(), name='devotion-add'),
    path('devotion/<slug>/', hit_count(post_view.HolyLifeMinistryDevotionDetailView.as_view()), name='devotion-view'),
    path('devotion/<slug>/edit/', post_view.HolyLifeMinistryDevotionUpdateView.as_view(), name='devotion-edit'),
    path('devotion-like/', post_view.devotion_like_post, name='devotion_like_post'),
    path('devotion-comment/<int:id>/', post_view.devotion_comment, name='devotion_comment'),
    path('devotion/<slug:slug>/archive/', post_view.MakeDevotionArchiveView.as_view(), name='make-devotion-archive'),
    path('devotion/<slug:slug>/remove-archive/', post_view.UnArchiveDevotionView.as_view(), name='unarchive-devotion'),
    # -----    CHRISTIANBASE TECH ( Tech Create and Update  .and more )    -------- #
    path('tech/', hit_count(post_view.HolyLifeMinistryTechView.as_view()), name='tech'),
    path('tech/add/', post_view.HolyLifeMinistryAddTechView.as_view(), name='tech-add'),
    path('tech/<slug>/', hit_count(post_view.HolyLifeMinistryTechDetailView.as_view()), name='tech-view'),
    path('tech/<slug>/edit/', post_view.HolyLifeMinistryTechUpdateView.as_view(), name='tech-edit'),
    path('tech-like/', post_view.tech_like_post, name='tech_like_post'),
    path('tech-like/<int:id>/', post_view.tech_comment, name='tech_comment'),
    path('tech/<slug:slug>/archive/', post_view.MakeTechArchiveView.as_view(), name='make-tech-archive'),
    path('tech/<slug:slug>/remove-archive/', post_view.UnArchiveTechView.as_view(), name='unarchive-tech'),
    # -----    CHRISTIANBASE QUOTES ( Quotes Create and Update  .and more )    -------- #
    path('quotes/', hit_count(post_view.HolyLifeMinistryQuotesView.as_view()), name='quotes'),
    path('quotes/add/', post_view.HolyLifeMinistryAddQuotesView.as_view(), name='quotes-add'),
    path('quotes/<slug>/', hit_count(post_view.HolyLifeMinistryQuotesDetailView.as_view()), name='quotes-view'),
    path('quotes/<slug>/edit/', post_view.HolyLifeMinistryQuotesUpdateView.as_view(), name='quotes-edit'),
    path('quotes-like/', post_view.quotes_like_post, name='quotes_like_post'),
    path('quotes-comment/<int:id>/', post_view.quotes_comment, name='quotes_comment'),
    path('quotes/<slug:slug>/archive/', post_view.MakeQuotesArchiveView.as_view(), name='make-quotes-archive'),
    path('quotes/<slug:slug>/remove-archive/', post_view.UnArchiveQuotesView.as_view(), name='unarchive-quotes'),

    # -----    CHRISTIANBASE QUOTES ( Quotes Create and Update  .and more )    -------- #
    path('policy/', hit_count(post_view.HolyLifeMinistryPolicyView.as_view()), name='policy'),
    path('policy/add/', post_view.HolyLifeMinistryAddPolicyView.as_view(), name='policy-add'),
    path('policy/<slug>-<policy_hex>/', hit_count(post_view.HolyLifeMinistryPolicyDetailView.as_view()), name='policy-view'),
    path('policy/<slug>-<policy_hex>/edit/', post_view.HolyLifeMinistryUpdatePolicyView.as_view(), name='policy-edit'),
    path('policy-like/', post_view.policy_like_post, name='policy_like_post'),
    path('policy/add-bookmarks/', post_view.bookmarks_policy, name='bookmarks_policy'),
    path('policy-comment/<int:id>/', post_view.policy_comment, name='policy_comment'),
    path('policy/<slug>/archive-policy/', post_view.MakePolicyArchiveView.as_view(), name='make-policy-archive'),
    path('policy/<slug>/remove-archive/', post_view.UnArchivePolicysView.as_view(), name='unarchive-policy'),

    # -----    REQUEST PRAYER ( Sent Prayer Request.and more )    -------- #
    path('request-prayer/', hit_count(post_view.PrayerRequestCreateView.as_view()), name='request-prayer'),

    # -----    CHRISTIANBASE STORY ( New Story. Update Story, View Story, Archive story .and more )    -------- #
    path('new-story/', post_view.ChristianbaseUserStoryArticleView.as_view(), name='christianbase_new_story'),
    path('<slug:slug>-<story_code>', hit_count(post_view.ChristianbaseUserPostDetailView.as_view()), name='christianbase_story_detail'),
    path('me/stories/', hit_count(post_view.ChristianbaseUserStoriesView.as_view()), name='christianbase_user_stories'),
    path('<slug:slug>-<story_code>/edit/', post_view.ChristianbaseUpdateUserStoryArticleView.as_view(), name='christianbase_story_edit'),

    # -----    CHRISTIANBASE CATEGORY ( New Category, Update, View Topic/Category Story and more )    -------- #
    path('like/', post_view.like_post, name='like_post'),
    # -----    CHRISTIANBASE Comment ( New Story. Update Story, View Story, Archive story .and more )    -------- #
    path('comment/<int:id>/', post_view.user_comment, name='user_comment'),

    # -----    CHRISTIANBASE ARCHIVE ( Archive,  Story and more )    -------- #
    path('archive-stories/', hit_count(post_view.ChristianbaseArchiveStoryView.as_view()), name='christianbase_archive_stories'),
    path('archive/<slug:slug>/', post_view.ChristianbaseMakeStoryArchiveView.as_view(), name='christianbase_make_archive'),
    path('archive-stories/<slug:slug>/', post_view.ChristianbaseUnArchiveStoryView.as_view(), name='christianbase_unarchive_stories'),

    # -----    CHRISTIANBASE TRASH ( Trash / Delete Story and more )    -------- #
    path('trash-stories/', hit_count(post_view.ChristianbaseTrashStoryView.as_view()), name='christianbase_trash_stories'),
    path('trash-stories/<slug:slug>/', post_view.ChristianbaseDeleteStoryView.as_view(), name='christianbase_delete_stories'),
    path('trash-stories/<slug:slug>/restored/', post_view.ChristianbaseRestoredStoryView.as_view(), name='christianbase_restored_stories'),
    path('trash-stories/<slug:slug>/delete/', post_view.ChristianbasePermenantDeleteStoryView.as_view(), name='christianbase_permenant_stories'),

    # -----    CHRISTIANBASE CATEGORY ( New Category, Update, View Topic/Category Story and more )    -------- #
    path('categories/', post_view.AddUserCategoryView.as_view(), name='christianbase_add_category'),
    path('categories/<slug:slug>/edit/', post_view.UpdateUserCategoryForm.as_view(), name='christianbase_update_category'),
    path('categories/<slug:slug>/', hit_count(post_view.ChristianbaseSelectedCategoryView.as_view()), name='christianbase_category_story'),

    # -----    CHRISTIANBASE BOOKMARKS ( User Bookmarks Stories )    -------- #
    path('bookmarks/', hit_count(post_view.ChristianbaseBookmarkStoriesView.as_view()), name='christianbase_user_bookmarks'),
    path('bookmark/add/', post_view.christianbase_add_user_bookmarks, name='christianbase_add_user_bookmarks'),

    # -----    CHRISTIANBASE SEARCH ( Search Stories )    -------- #
    path('search/', post_view.search_stories, name='search_stories'),


]
