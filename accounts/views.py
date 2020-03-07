from datetime import datetime
from django.conf import settings
from urllib.parse import urlparse, urlunparse
from django.db import transaction
from django.db.models import Count
from django.shortcuts import render, redirect, resolve_url, get_object_or_404
from django.http import HttpResponseRedirect, QueryDict, JsonResponse
from django.template import Context
from django.contrib.auth import (
    REDIRECT_FIELD_NAME, get_user_model, login as auth_login,
    logout as auth_logout, update_session_auth_hash,
)
from django.views.generic.base import TemplateView
from django.views.generic import UpdateView, View, DeleteView, DetailView, CreateView
from django.views.generic.edit import FormView
from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.decorators import login_required
from django.utils.encoding import force_bytes, force_text
from django.utils.http import is_safe_url, urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.utils.html import strip_tags
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from email.mime.image import MIMEImage
from django.contrib.staticfiles.finders import find
from django.core.files import File


from django.views.decorators.http import require_POST
from .decorators import ajax_required

from .utils import create_action
from .tokens import account_activation_token
from .models import User, UserRole, Profile, Connection, Feedback, Report, ReportUser, ContactUs, ContactUsSettings
from posts.models import Post, Category, BibleStudies, Devotion, Tech, Quotes, Policy
from .forms import (
    UserCreationForm, ChristianBaseAuthenticationForm, ChristianBaseForgotPasswordAndUserResendActivationForm,
    ChristianBaseUserChangeForm, ChristianBaseUserProfileForm, ChristianBaseSetPasswordForm, ChristianBaseChangePasswordForm,
    ChristianBaseUserProfilePhotoForm, ChristianBaseUserSettingForm, ChristianBaseUserFeedbackForm,
    ChristianBaseRecoverAccountForm, ContactUsForm,
)

from track.views import hit_count


UserModel = get_user_model()


# def logo_data():
#     """  this fuction read/find logo image directory.  """
#     with open(find('images/logo_text1.png'), 'rb') as f:
#         logo_data = f.read()
#     logo = MIMEImage(logo_data)
#     logo.add_header('Content-ID', '<logo>')
#     return logo


# def mail_logo_data():
#     """  this fuction read/find logo image directory.  """
#     with open(find('images/logo_text1.png'), 'rb') as f:
#         logo_data = f.read()
#     logo = MIMEImage(logo_data)
#     logo.add_header('Content-ID', '<logo>')
#     return logo


# def teams_data():
#     """  this fuction read/find logo image directory.  """
#     with open(find('images/email/teams_logo.jpg'), 'rb') as f:
#         team_data = f.read()
#     team_logo = MIMEImage(team_data)
#     team_logo.add_header('Content-ID', '<team_logo>')
#     return team_logo


def get_user_role(user): # get user role..
    user_role = UserRole.objects.filter(user=user)
    if user_role:
        return user_role[0].role
    return "No user role"


class ParselyValidResponse(JsonResponse):
    """
    JSON response to represent valid data to client-side
    """
    status_code = 200

    def __init__(self, data=None):
        if data is None:
            data = {'status': 'valid'}
        return super(ParselyValidResponse, self).__init__(data)


class ParselyInvalidResponse(JsonResponse):
    """
    JSON response to represent invalid data to client-side
    """
    status_code = 404

    def __init__(self, data=None):
        if data is None:
            data = {'status': 'invalid'}
        return super(ParselyInvalidResponse, self).__init__(data)


def registration_form(request):
    """  this fuction allow user to create new account and turn user active to false  """

    auth_logout(request)  # log user out if user is_authenticated

    if request.method == 'POST':
        form = UserCreationForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            myDate = datetime.now()
            current_site = get_current_site(request)
            mail_subject = 'Activate Your Accounts on Holy Life Ministry, ' + str(user.username) + '!'
            html_content = render_to_string('email/email_activation.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': account_activation_token.make_token(user),
                'myDate': myDate,
            })
            to_email = form.cleaned_data.get('email')
            send_mail = EmailMultiAlternatives(
                mail_subject, to=[to_email]
            )
            send_mail.attach_alternative(html_content, "text/html")
            send_mail.send(fail_silently=False)
            # messages.success(request, "Booom...! We've sent you a magic link. Click on the link to activate your account!")
            create_action(user, 'has created account')
            return redirect('activate_email_sent')
    else:
        form = UserCreationForm()
    context = {
        'form': form,
    }
    return render(request, 'credential/register.html', context)


class ActivateEmailSentView(TemplateView):
    """  this class dispaly a email activation sent to user  """
    template_name = 'credential/activation_email_sent.html'


def activate_christianBaseUser(request, uidb64, token):
    """  this function activate user email with token   """
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        # to_email = User.objects.filter(email=email)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None:
        user.is_active = True
        user.save()
        # once account is activated craete user role to Author
        UserRole.objects.create(user=user, role='Author')
        myDate = datetime.now()
        current_site = get_current_site(request)
        mail_subject = 'Welcome To holy Life Ministry, ' + str(user.username) + '!'
        to_email = user.email  # get user email and send welcome...
        html_content = render_to_string('email/welcome_email_message.html', {
            'user': user,
            'domain': current_site.domain,
            'myDate': myDate,
        })
        # to_email = form.cleaned_data.get('email')
        email = EmailMultiAlternatives(
            mail_subject, to=[to_email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        messages.success(request, "Thank you for your email confirmation. Now you can login your account.")
        return redirect('login')
    else:
        # messages.error(request, 'Activation link is broken or invalid.!')
        messages.add_message(request, messages.ERROR, 'Activation link is broken or invalid.!')
        return redirect('invalid_token')


class ChristianBaseInvalidToken(TemplateView):
    """  this class display a a success or warning on email activation link  """
    template_name = 'credential/invalid_activate.html'


def christianbase_resend_activation(request):
    """  this fuction allow user to resend user comfirmation link.  """
    if request.method == 'POST':
        form = ChristianBaseForgotPasswordAndUserResendActivationForm(request.POST)
        myDate = datetime.now()

        if form.is_valid():
            email = form.cleaned_data["email"]
            user = User.objects.filter(email=email, is_active=0)

            if not user.count():
                form._errors["email"] = ["Account for this email address can not be found. Mean it already activated or does not exist!!"]

            if user:
                myDate = datetime.now()
                current_site = get_current_site(request)
                mail_subject = 'Activate Your Accounts on Holy Life Ministry ' + str(user[0].username) + '!'
                html_content = render_to_string('email/email_activation.html', {
                    'user': user[0],
                    'domain': current_site.domain,
                    'uid': urlsafe_base64_encode(force_bytes(user[0].pk)),
                    'token': account_activation_token.make_token(user[0]),
                    'myDate': myDate,
                })
                resend_email = EmailMultiAlternatives(
                    mail_subject, to=[email]
                )
                resend_email.attach_alternative(html_content, "text/html")
                resend_email.send(fail_silently=False)
                # messages.success(request, "Booom...! We sent your activation link and now you can check your mail to activate your account!!")
                return redirect('activate_email_sent')

    else:
        form = ChristianBaseForgotPasswordAndUserResendActivationForm()
    context = {'form': form}
    return render(request, 'credential/resent_email_activation.html', context)


class SuccessURLAllowedHostsMixin:
    success_url_allowed_hosts = set()

    def get_success_url_allowed_hosts(self):
        allowed_hosts = {self.request.get_host()}
        allowed_hosts.update(self.success_url_allowed_hosts)
        return allowed_hosts


class UserLoginView(SuccessURLAllowedHostsMixin, FormView):
    """
    Display the login form and handle the login action.
    """
    form_class = ChristianBaseAuthenticationForm
    authentication_form = None
    redirect_field_name = REDIRECT_FIELD_NAME
    template_name = 'credential/login.html'
    redirect_authenticated_user = False
    extra_context = None

    @method_decorator(sensitive_post_parameters())
    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        auth_logout(request)
        if self.redirect_authenticated_user and self.request.user.is_authenticated:
            redirect_to = self.get_success_url()
            if redirect_to == self.request.path:
                raise ValueError(
                    "Redirection loop for authenticated user detected. Check that "
                    "your LOGIN_REDIRECT_URL doesn't point to a login page."
                )
            return HttpResponseRedirect(redirect_to)
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        url = self.get_redirect_url()
        return url or resolve_url(settings.LOGIN_REDIRECT_URL)

    def get_redirect_url(self):
        """Return the user-originating redirect URL if it's safe."""
        redirect_to = self.request.POST.get(
            self.redirect_field_name,
            self.request.GET.get(self.redirect_field_name, '')
        )
        url_is_safe = is_safe_url(
            url=redirect_to,
            allowed_hosts=self.get_success_url_allowed_hosts(),
            require_https=self.request.is_secure(),
        )
        return redirect_to if url_is_safe else ''

    def get_form_class(self):
        return self.authentication_form or self.form_class

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        """Security check complete. Log the user in."""
        auth_login(self.request, form.get_user())
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_site = get_current_site(self.request)
        context.update({
            self.redirect_field_name: self.get_redirect_url(),
            'site': current_site,
            'site_name': current_site.name,
        })
        if self.extra_context is not None:
            context.update(self.extra_context)
        return context


class ChristianBaseUserLogoutView(SuccessURLAllowedHostsMixin, TemplateView):
    """
    Log out the user and display the 'You are logged out' message.
    """
    next_page = None
    redirect_field_name = REDIRECT_FIELD_NAME
    template_name = 'credential/logged_out.html'
    extra_context = None

    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        auth_logout(request)
        next_page = self.get_next_page()
        if next_page:
            # Redirect to this page until the session has been cleared.
            return HttpResponseRedirect(next_page)
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """Logout may be done via POST."""
        return self.get(request, *args, **kwargs)

    def get_next_page(self):
        if self.next_page is not None:
            next_page = resolve_url(self.next_page)
        elif settings.LOGOUT_REDIRECT_URL:
            next_page = resolve_url(settings.LOGOUT_REDIRECT_URL)
        else:
            next_page = self.next_page

        if (self.redirect_field_name in self.request.POST or
                self.redirect_field_name in self.request.GET):
            next_page = self.request.POST.get(
                self.redirect_field_name,
                self.request.GET.get(self.redirect_field_name)
            )
            url_is_safe = is_safe_url(
                url=next_page,
                allowed_hosts=self.get_success_url_allowed_hosts(),
                require_https=self.request.is_secure(),
            )
            # Security check -- Ensure the user-originating redirection URL is
            # safe.
            if not url_is_safe:
                next_page = self.request.path
        return next_page

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_site = get_current_site(self.request)
        context.update({
            'site': current_site,
            'site_name': current_site.name,
            'title': _('Logged out'),
        })
        if self.extra_context is not None:
            context.update(self.extra_context)
        return context


def logout_then_login(request, login_url=None):
    """
    Log out the user if they are logged in. Then redirect to the login page.
    """
    if not login_url:
        login_url = settings.LOGIN_URL
    login_url = resolve_url(login_url)
    return ChristianBaseUserLogoutView.as_view(next_page=login_url)(request)


def redirect_to_login(next, login_url=None, redirect_field_name=REDIRECT_FIELD_NAME):
    """
    Redirect the user to the login page, passing the given 'next' page.
    """
    resolved_url = resolve_url(login_url or settings.LOGIN_URL)

    login_url_parts = list(urlparse(resolved_url))
    if redirect_field_name:
        querystring = QueryDict(login_url_parts[4], mutable=True)
        querystring[redirect_field_name] = next
        login_url_parts[4] = querystring.urlencode(safe='/')

    return HttpResponseRedirect(urlunparse(login_url_parts))


class PasswordContextMixin:
    extra_context = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.title
        if self.extra_context is not None:
            context.update(self.extra_context)
        return context


class ChristianBasePasswordResetView(PasswordContextMixin, FormView):
    email_template_name = 'email/password_reset.html'
    extra_email_context = None
    form_class = ChristianBaseForgotPasswordAndUserResendActivationForm
    from_email = None
    html_email_template_name = None
    subject_template_name = 'email/password_reset_subject.txt'
    success_url = reverse_lazy('password_reset_done')
    template_name = 'credential/password_reset/password_reset.html'
    title = _('Password reset')
    token_generator = account_activation_token

    @method_decorator(csrf_protect)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def form_valid(self, form):
        opts = {
            'use_https': self.request.is_secure(),
            'token_generator': self.token_generator,
            'from_email': self.from_email,
            'email_template_name': self.email_template_name,
            'subject_template_name': self.subject_template_name,
            'request': self.request,
            'html_email_template_name': self.html_email_template_name,
            'extra_email_context': self.extra_email_context,
        }
        form.save(**opts)
        return super().form_valid(form)


INTERNAL_RESET_URL_TOKEN = 'set-password'
INTERNAL_RESET_SESSION_TOKEN = '_password_reset_token'


class ChristianBaseResetPasswordDone(TemplateView):
    """  this class display a a success or warning on email activation link  """
    template_name = 'credential/password_reset/reset_password_done.html'


class ChristianBasePasswordResetConfirmView(PasswordContextMixin, FormView):
    form_class = ChristianBaseSetPasswordForm
    post_reset_login = False
    post_reset_login_backend = None
    success_url = reverse_lazy('password_reset_complete')
    template_name = 'credential/password_reset/password_reset_confirm.html'
    title = _('Enter new password')
    token_generator = account_activation_token

    @method_decorator(sensitive_post_parameters())
    @method_decorator(never_cache)
    def dispatch(self, *args, **kwargs):
        assert 'uidb64' in kwargs and 'token' in kwargs

        self.validlink = False
        self.user = self.get_user(kwargs['uidb64'])

        if self.user is not None:
            token = kwargs['token']
            if token == INTERNAL_RESET_URL_TOKEN:
                session_token = self.request.session.get(INTERNAL_RESET_SESSION_TOKEN)
                if self.token_generator.check_token(self.user, session_token):
                    # If the token is valid, display the password reset form.
                    self.validlink = True
                    return super().dispatch(*args, **kwargs)
            else:
                if self.token_generator.check_token(self.user, token):
                    # Store the token in the session and redirect to the
                    # password reset form at a URL without the token. That
                    # avoids the possibility of leaking the token in the
                    # HTTP Referer header.
                    self.request.session[INTERNAL_RESET_SESSION_TOKEN] = token
                    redirect_url = self.request.path.replace(token, INTERNAL_RESET_URL_TOKEN)
                    return HttpResponseRedirect(redirect_url)

        # Display the "Password reset unsuccessful" page.
        return sel(self.get_context_data())

    def get_user(self, uidb64):
        try:
            # urlsafe_base64_decode() decodes to bytestring
            uid = urlsafe_base64_decode(uidb64).decode()
            user = UserModel._default_manager.get(pk=uid)
        except (TypeError, ValueError, OverflowError, UserModel.DoesNotExist):
            user = None
        return user

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.user
        return kwargs

    def form_valid(self, form):
        user = form.save()
        del self.request.session[INTERNAL_RESET_SESSION_TOKEN]
        if self.post_reset_login:
            auth_login(self.request, user, self.post_reset_login_backend)
        # send security alert mail to user if successfully changed password..
        if user:
            myDate = datetime.now()
            current_site = get_current_site(self.request)
            mail_subject = f'Security alert!'
            to_email = user.email  # get user email
            html_content = render_to_string('email/password_securit_alert.html', {
                'user': user,
                'domain': current_site.domain,
                'myDate': myDate,
            })
            resend_email = EmailMultiAlternatives(
                mail_subject, to=[to_email]
            )
            resend_email.attach_alternative(html_content, "text/html")
            resend_email.send(fail_silently=False)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.validlink:
            context['validlink'] = True
        else:
            context.update({
                'form': None,
                'title': _('Password reset unsuccessful'),
                'validlink': False,
            })
        return context



class ChristianBasePasswordResetCompleteView(PasswordContextMixin, TemplateView):
    template_name = 'credential/password_reset/password_reset_complete.html'
    title = _('Password reset complete')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['login_url'] = resolve_url(settings.LOGIN_URL)
        return context


class ChristianBasePasswordChangeView(PasswordContextMixin, FormView):
    form_class = ChristianBaseChangePasswordForm
    # success_url = reverse_lazy('')
    template_name = 'credential/password_reset/change_password_form.html'
    title = _('Password Change')
    pk = 'pk'

    def get_success_url(self):
        return reverse_lazy('password_change', args=(self.kwargs['username'],))

    @method_decorator(sensitive_post_parameters())
    @method_decorator(csrf_protect)
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        user = form.save()
        # Updating the password logs out all other sessions for the user
        # except the current one.
        update_session_auth_hash(self.request, user)
        # send security alert mail to user if successfully changed password..
        if user:
            myDate = datetime.now()
            current_site = get_current_site(self.request)
            mail_subject = 'Security alert!'
            to_email = user.email  # get user email
            html_content = render_to_string('email/password_securit_alert.html', {
                'user': user,
                'domain': current_site.domain,
                'myDate': myDate,
            })
            resend_email = EmailMultiAlternatives(
                mail_subject, to=[to_email]
            )
            resend_email.attach_alternative(html_content, "text/html")
            resend_email.send(fail_silently=False)
        messages.success(self.request, 'Your Password has been changed!. You can logout and login with your new password.')
        return super().form_valid(form)


class TitleContextMixin:
    extra_context = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.title
        if self.extra_context is not None:
            context.update(self.extra_context)
        return context


@login_required
@hit_count
def christianbase_userprofile(request, username):
    """
    Display self request User Profile or view user profile account...
    """
    users = get_object_or_404(User, username=username, is_active=True)
    # count total author stories ...
    count_user_stories = Post.objects.filter(user=users, status='Published')
    count_biblestudies_stories = BibleStudies.objects.filter(user=users, is_active=True)
    count_devotion_stories = Devotion.objects.filter(user=users, is_active=True)
    count_tech_stories = Tech.objects.filter(user=users, is_active=True)
    count_quotes_stories = Quotes.objects.filter(user=users, is_active=True)
    count_policy_stories = Policy.objects.filter(user=users, is_active=True)

    reports = Report.objects.all()
    # get user role .....
    if get_user_role(users) == 'Author' or get_user_role(users) == 'Admin':
        user_stories = Post.objects.filter(user=users, status='Published').annotate(total_post_comment=Count('comment')).order_by('-created_on')
    elif get_user_role(users) == 'BS P':
        user_stories = BibleStudies.objects.filter(user=users, is_active=True).annotate(total_post_comment=Count('commentsbiblestudies')).order_by('-created_on')
    elif get_user_role(users) == 'Devotion P':
        user_stories = Devotion.objects.filter(user=users, is_active=True).annotate(total_post_comment=Count('commentsdevotion')).order_by('-created_on')
    elif get_user_role(users) == 'Tech P':
        user_stories = Tech.objects.filter(user=users, is_active=True).annotate(total_post_comment=Count('commentstech')).order_by('-created_on')
    elif get_user_role(users) == 'Tech P':
        user_stories = Quotes.objects.filter(user=users, is_active=True).annotate(total_post_comment=Count('commentsquotes')).order_by('-created_on')
    else:
        user_stories = Policy.objects.filter(user=users, is_active=True).annotate(total_post_comment=Count('commentspolicy')).order_by('-created_on')

    # bible studies stories on user profile...
    page = request.GET.get('page', 1)
    paginator = Paginator(user_stories, 4)
    try:
        user_stories = paginator.page(page)
    except PageNotAnInteger:
        user_stories = paginator.page(1)
    except EmptyPage:
        if request.is_ajax():
            return HttpResponseRedirect('')
        user_stories = paginator.page(paginator.num_pages)
    if request.is_ajax():
        return render(request, 'user_accounts/load_data/load_user_stories.html',
            {
                'user_stories': user_stories,
            }
        )

    context = {
        'users': users,
        'count_user_stories': count_user_stories,
        'count_biblestudies_stories': count_biblestudies_stories,
        'count_devotion_stories': count_devotion_stories,
        'count_tech_stories': count_tech_stories,
        'count_quotes_stories': count_quotes_stories,
        'count_policy_stories': count_policy_stories,
        'user_stories': user_stories,
        'reports': reports,
    }
    return render(request, 'user_accounts/user_profile.html', context)


@login_required
def christianbase_userprofile_edit(request, username):
    """
    This function update user profile
    """
    user = User.objects.get(username=username)

    if request.method == 'POST':
        uform = ChristianBaseUserChangeForm(request.POST, instance=request.user)
        pform = ChristianBaseUserProfileForm(request.POST, instance=request.user.profile)
        if uform.is_valid() and pform.is_valid():
            if request.user.is_active:
                with transaction.atomic():
                    uform.save()
                    pform.save()
                # messages.success(request, f'Successfully updated your profile')
                data = {
                    'error': False, 'response': 'Successfully updated your profile',
                }
                return JsonResponse(data)
    else:
        uform = ChristianBaseUserChangeForm(instance=request.user)
        pform = ChristianBaseUserProfileForm(instance=request.user.profile)

    context = {
        'uform': uform,
        'pform': pform,
        'user': user,
    }
    return render(request, 'user_accounts/edit_user_profile.html', context)


@login_required
def christianbase_uploadprofile(request, username):
    """
    This method allow user to upload profile photo
    """
    user = User.objects.get(username=username)

    if request.method == 'POST':
        form = ChristianBaseUserProfilePhotoForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            if request.user.is_active:
                photo = form.save(commit=False)
                photo.user = request.user
                photo.save()
            messages.success(request, 'Successfully updated your profile photo')
            return redirect('christianbase_userprofile_edit', user.username)
    else:
        form = ChristianBaseUserProfilePhotoForm(instance=request.user.profile)

    context = {
        'form': form,
        'user': user,
    }
    return render(request, 'user_accounts/upload_user_photo.html', context)


@method_decorator(login_required, name='dispatch')
class ChristianBaseDeleteProfilePhoto(View):
    """
    This method allow user to remove current profile photo
    """

    def get(self, request, *args, **kwargs):
        users = get_object_or_404(User, username=kwargs.get('username'))
        profile = Profile.objects.get(user=users)
        profile.image.delete()
        messages.success(request, 'Successfully remove profile photo!')
        return redirect('christianbase_userprofile_edit', users.username)


@login_required
def christianbase_user_report(request):
    """
    This method allow user to report users
    """
    user = User.objects.get(id=request.POST.get('id'))
    report_id = Report.objects .filter(id=request.GET.get('id'))
    ReportUser.objects.get_or_create(
        report=report_id,
        make=request.user,
        to=user
    )
    messages.success(request, 'Your report is successfully submitted!')
    return redirect('christianbase_userprofile', user.username)


@login_required
def christianbase_user_setting(request, username):
    """
    This method allow user to remove current profile photo
    """
    user = get_object_or_404(User, username=username)

    if request.method == "POST":
        form = ChristianBaseUserSettingForm(request.POST, instance=request.user.profile)
        if form.is_valid():
            if request.user.is_active and user.is_authenticated:
                setting = form.save(commit=False)
                setting.user = request.user
                setting.save()
            messages.success(request, 'Successfully updated your social account!')
            return redirect('christianbase_user_settings', user.username)
        else:
            messages.warning(request, 'Please enter a correct valid url!')
    else:
        form = ChristianBaseUserSettingForm(instance=request.user.profile)
    context = {
        'form': form,
        'user': user,
        'title': 'Setting',
    }
    return render(request, 'setting/settings.html', context)


@login_required
def christianbase_temporary_delete(request, username):
    """
    This function allow user to temproary put account to in-active
    """
    user = get_object_or_404(User, username=username)
    user_role = UserRole.objects.filter(user=request.user).last()
    if user_role:
        user_role = True if user_role.role == "Admin" or user_role.role == "Author" else False
    else:
        user_role = False
    if request.user.is_superuser or user_role:
        if request.user.is_active:
            user.is_active = False
        user.save()
        # logout user
        auth_logout(request)
        # send security alert mail to user if successfully changed password..
        if request.user:
            myDate = datetime.now()
            current_site = get_current_site(request)
            mail_subject = 'You\'ve temporary locked your account!'
            to_email = user.email  # get user email
            html_content = render_to_string('email/delete_account/temporary_delete_account.html', {
                'user': request.user,
                'domain': current_site.domain,
                'myDate': myDate,
            })
            resend_email = EmailMultiAlternatives(
                mail_subject, to=[to_email]
            )
            resend_email.attach_alternative(html_content, "text/html")
            resend_email.send(fail_silently=False)
        messages.warning(request, 'Your account is temporary locked!')
    else:
        messages.warning(request, 'You don\'t have permission !')
    return HttpResponseRedirect(reverse_lazy('login'))


@method_decorator(login_required, name='dispatch')
class ChristianbasePermanantDeleteUser(View):
    """
    This function allow user to permanant delete
    """

    def get(self, request, *args, **kwargs):
        user = get_object_or_404(User, username=kwargs.get("username"))
        user.delete()
        auth_logout(request)
        # send security alert mail to user if successfully changed password..
        if self.request.user:
            myDate = datetime.now()
            current_site = get_current_site(self.request)
            mail_subject = 'Sorry to see you go, We\'ll always welcome you back!'
            to_email = user.email  # get user email
            html_content = render_to_string('email/delete_account/permanant_delete_account.html', {
                'user': user,
                'domain': current_site.domain,
                'myDate': myDate,
            })
            resend_email = EmailMultiAlternatives(
                mail_subject, to=[to_email]
            )
            resend_email.attach_alternative(html_content, "text/html")
            resend_email.send(fail_silently=False)
        messages.warning(request, 'Your account is permanant delete!')
        return HttpResponseRedirect(reverse_lazy('christianbase_sorry_to_see_go'))


class ChristianbaseUserFeedbackView(TitleContextMixin, FormView):
    """
    This function allow user give report or feedback...
    """
    template_name = 'setting/user_feedback.html'
    form_class = ChristianBaseUserFeedbackForm
    title = _('Feedback')
    pk = 'pk'

    def get_success_url(self):
        return reverse_lazy('christianbase_user_feedback', args=(self.kwargs['username'],))

    @method_decorator(sensitive_post_parameters())
    @method_decorator(csrf_protect)
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def form_valid(self, form):
        self.feedback = form.save(commit=False)
        if self.request.user.is_active:
            self.feedback.user = self.request.user
            self.feedback.save()
            # send security alert mail to user if fedback successfully sent..
            if self.request.user:
                myDate = datetime.now()
                current_site = get_current_site(self.request)
                from_email = settings.DEFAULT_FROM_EMAIL
                mail_subject = 'Thanks for your feedback!'
                to_email = self.request.user.email  # get user email
                html_content = render_to_string('email/feedback/feedback_email.html', {
                    'user': self.request.user,
                    'domain': current_site.domain,
                    'myDate': myDate,
                })
                resend_email = EmailMultiAlternatives(
                    from_email, mail_subject, to=[to_email]
                )
                resend_email.attach_alternative(html_content, "text/html")
                resend_email.send(fail_silently=False)
        messages.success(self.request, "Thanks!! for your feedback. we'll check it out and deal with it!")
        return super().form_valid(form)


class ChristianbaseSorryToSeeGoView(TitleContextMixin, TemplateView):
    template_name = 'setting/sorry_to_see_go.html'
    title = _('Sorry to see you go')


def christianbase_recover_account(request):
    """
    This function allow user to recover account to in-active
    """
    if request.method == 'POST':
        form = ChristianBaseRecoverAccountForm(request.POST)
        myDate = datetime.now()

        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data["email"]
            user = User.objects.filter(username=username, email=email, is_active=False)

            if not user.exists():
                messages.warning(request, "Sorry! An error occure. please check your username and email")

            # if user.is_active:
            #     messages.warning(request, "Oops! it seems your account is active, you've trouble login your account!")

            if user:
                myDate = datetime.now()
                current_site = get_current_site(request)
                mail_subject = 'Recover your account on Holy Life Ministry, ' + str(user[0].username) + '!'
                html_content = render_to_string('email/recover_account/recover_account_email.html', {
                    'user': user[0],
                    'domain': current_site.domain,
                    'uid': urlsafe_base64_encode(force_bytes(user[0].pk)),
                    'token': account_activation_token.make_token(user[0]),
                    'myDate': myDate,
                })
                resend_email = EmailMultiAlternatives(
                    mail_subject, to=[email]
                )
                resend_email.attach_alternative(html_content, "text/html")
                resend_email.send(fail_silently=False)
                messages.success(request, "Booom...! We sent you magic link to unlock your account. You can check your inbox!")
                return redirect('christianbase_recover_account')

    else:
        form = ChristianBaseRecoverAccountForm()
    context = {
        'form': form,
        'title': 'Recover your account',
    }
    return render(request, 'credential/recover_account/recover_account.html', context)


def christianbase_unlocked_account(request, uidb64, token):
    """  this function unlocked/activate user email with token   """
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        # to_email = User.objects.filter(email=email)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None:
        user.is_active = True
        user.save()
        myDate = datetime.now()
        current_site = get_current_site(request)
        mail_subject = 'Your account is now unlocked,' + str(user.username) + '!'
        to_email = user.email  # get user email and send welcome...
        html_content = render_to_string('email/recover_account/recover_success_email.html', {
            'user': user,
            'domain': current_site.domain,
            'myDate': myDate,
        })
        # to_email = form.cleaned_data.get('email')
        email = EmailMultiAlternatives(
            mail_subject, to=[to_email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        messages.success(request, "Great! Your account is unlocked. Now you can login back to your account.")
        return redirect('login')
    else:
        # messages.error(request, 'Activation link is broken or invalid.!')
        messages.add_message(request, messages.ERROR, 'OOOPS! Activation link is broken or invalid.!')
        return redirect('invalid_token')


class ContactUsCreateView(TitleContextMixin, CreateView):
    """
    Display the prayer request form and add
    """
    model = ContactUs
    form_class = ContactUsForm
    template_name = "contact_us/contact_us.html"
    context_object_name = 'contact_us'
    title = _('Contact Us')

    def form_valid(self, form):
        # self.user = User.objects.filter(user=self.request.user)
        self.add_contact_us = form.save(commit=False)
        self.add_contact_us.created = timezone.now()
        self.add_contact_us.save()
        # sent mail to request user. ...
        contact_us = ContactUsSettings.objects.last()
        self.myDate = datetime.now()
        self.current_site = get_current_site(self.request)
        self.sender = form.cleaned_data.get('name')
        self.subject = form.cleaned_data.get('subject')
        self.message = form.cleaned_data.get('message')
        # email to admin
        self.mail_subject = 'HLM Platform Suggestions! -> "'  + str(self.subject) + '"!'
        from_email = form.cleaned_data.get("email")
        self.to_email = contact_us.email_admin  # get sender email
        html_content = render_to_string('email/contact_us/email_to_admin.html', {
            'domain': self.current_site.domain,
            'myDate': self.myDate,
            'add_contact_us': self.add_contact_us,
            'sender': self.sender,
            'subject': self.subject,
            'from_email': from_email,
            'message': self.message,
        })
        resend_email = EmailMultiAlternatives(
            self.mail_subject, from_email, to=[self.to_email]
        )
        resend_email.attach_alternative(html_content, "text/html")
        resend_email.send(fail_silently=False)
        # email to sender or user
        self.mail_subject = 'Thank you for contacting us - Holy Life Ministry!'
        from_email = contact_us.from_email
        self.to_email = form.cleaned_data.get('email')  # get sender email
        html_content = render_to_string('email/contact_us/email_to_user.html', {
            'domain': self.current_site.domain,
            'myDate': self.myDate,
            'sender': self.sender,
            'subject': self.subject,
        })
        resend_email = EmailMultiAlternatives(
            self.mail_subject, from_email, to=[self.to_email]
        )
        resend_email.attach_alternative(html_content, "text/html")
        resend_email.send(fail_silently=False)
        messages.success(self.request, 'Successfully sent!!!')
        return HttpResponseRedirect(reverse_lazy('contact-us'))

    def get_context_data(self, **kwargs):
        context = super(ContactUsCreateView, self).get_context_data(**kwargs)
        context['helpcenter'] = True
        return context


@ajax_required
@require_POST
@login_required
def user_follow(request):
    """
    Follow or Unfollow author...
    """
    user_id = request.POST.get('id')
    action = request.POST.get('action')
    if request.user.is_authenticated:
        if user_id and action:
            try:
                user = User.objects.get(id=user_id)
                if action == 'follow':
                    Connection.objects.get_or_create(user_from=request.user,
                                                     user_to=user, status='Following')
                    create_action(request.user, 'is following', user)
                else:
                    Connection.objects.filter(user_from=request.user,
                                              user_to=user).delete()
                return JsonResponse({'status': 'ok'})
            except User.DoesNotExist:
                return JsonResponse({'status': 'ko'})
        return JsonResponse({'status': 'ko'})
