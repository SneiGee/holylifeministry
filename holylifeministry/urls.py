from django.contrib import admin
from django.conf.urls import (
    handler400, handler403, handler404, handler500,
)
from django.urls import path, re_path, include
from django.conf import settings
from django.conf.urls.static import static

from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from ckeditor_uploader import views as ckeditor_view

from posts import views as post_view
from accounts import views
from helpcenter import views as help_view
from track.views import hit_count


handler403 = 'posts.views.handler403'
handler404 = 'posts.views.handler404'
handler500 = 'posts.views.handler500'

urlpatterns = [
    # -----    HOLY LIFE MINISTRY CREDENTIALS (Login, Craete account, Logout) .and more )    -------- #
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('create-account/', views.registration_form, name='create-account'),
    path('logged-out/', views.ChristianBaseUserLogoutView.as_view(), name='christian_logout'),

    # -----    HOLY LIFE MINISTRY STORIES URL.. .and more )
    path('', include('posts.urls')),

    # -----    HOLY LIFE MINISTRY ABOUT )
    path('about/', hit_count(help_view.AboutPageView.as_view()), name='about'),

    # -----    HOLY LIFE MINISTRY STORIES URL.. .and more )
    path('help/', include('helpcenter.urls')),

    # -----    HOLY LIFE MINISTRY Ckeditor default URL.. .and more )
    path('ckeditor/', login_required(ckeditor_view.upload), name='ckeditor_upload'),
    path('browse/', never_cache(login_required(ckeditor_view.browse)), name='ckeditor_browse'),
    # -----  END  CHRISTIANBASE ckedtor URL.. .and more )

    # -----    HOLY LIFE MINISTRY CREDENTIALS_ACTIVATION ( Activate account, Resend activation link .and more )    -------- #
    path('activate/<uidb64>/<token>', views.activate_christianBaseUser, name='activate_christianBaseUser'),
    path('activation-email-sent/', views.ActivateEmailSentView.as_view(), name='activate_email_sent'),
    path('activate/invalid-token/', views.ChristianBaseInvalidToken.as_view(), name='invalid_token'),
    path('resend-activation/', views.christianbase_resend_activation, name='christianbase_resend_activation'),
    # -----    HOLY LIFE MINISTRY ACCOUNT LOCKED ( Recover Account, Account Lock .and more )    -------- #
    path('recover-account/', views.christianbase_recover_account, name='christianbase_recover_account'),
    path('unlock/account/<uidb64>/<token>/', views.christianbase_unlocked_account, name='christianbase_unlocked_account'),
    # -----    HOLY LIFE MINISTRY CHANGE PASSWORD ( Password change .and more )    -------- #
    path('<str:username>/password-change/', views.ChristianBasePasswordChangeView.as_view(), name='password_change'),
    # -----    HOLY LIFE MINISTRY PASSWORD RESET ( Password Reset, Password Done .and more )    -------- #
    path('request/password-reset/', views.ChristianBasePasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', views.ChristianBaseResetPasswordDone.as_view(), name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', views.ChristianBasePasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset/success/', views.ChristianBasePasswordResetCompleteView.as_view(), name='password_reset_complete'),
    # -----    HOLY LIFE MINISTRY USER_ACCOUNT ( Profile, Update Profile, Upload Profile .and more )    -------- #
    path('<username>/', views.christianbase_userprofile, name='christianbase_userprofile'),
    path('user_follow', views.user_follow, name='user_follow'),
    path('<username>/edit/', views.christianbase_userprofile_edit, name='christianbase_userprofile_edit'),
    path('<username>/upload/', views.christianbase_uploadprofile, name='christianbase_userprofile_upload'),
    path('<username>/delete/', views.ChristianBaseDeleteProfilePhoto.as_view(), name='christianbase_delete_profilephoto'),
    # -----    HOLY LIFE MINISTRY Report User ( User Report Option .and more )    -------- #
    # path('report/', views.ChristianBaseUserReportView.as_view(), name='christianbase_user_report'),
    path('report/', views.christianbase_user_report, name='christianbase_user_report'),
    # -----    HOLY LIFE MINISTRY SETTINGST ( Setting, Delete Account .and more )    -------- #
    path('<str:username>/settings/', views.christianbase_user_setting, name='christianbase_user_settings'),
    path('<str:username>/settings/temporary-delete-account/', views.christianbase_temporary_delete, name='christianbase_temporary_delete'),
    path('<str:username>/settings/permanat-delete-account/', views.ChristianbasePermanantDeleteUser.as_view(), name='christianbase_permanant_delete'),
    path('<str:username>/settings/feedback/', views.ChristianbaseUserFeedbackView.as_view(), name='christianbase_user_feedback'),
    path('goodbye/sorry-to-see-you-go/', views.ChristianbaseSorryToSeeGoView.as_view(), name='christianbase_sorry_to_see_go'),

    # -- Super Admin
    path('base/super/secure/', admin.site.urls),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
