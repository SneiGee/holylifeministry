import unicodedata
from datetime import datetime
from django import forms
from django.contrib.auth import (
    authenticate, get_user_model, password_validation,
)
from django.contrib.auth.hashers import (
    UNUSABLE_PASSWORD_PREFIX, identify_hasher,
)
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.text import capfirst
from django.utils.translation import gettext, gettext_lazy as _
from email.mime.image import MIMEImage
from django.contrib.staticfiles import finders

from .tokens import account_activation_token
from .decorators import parsleyfy
from .models import User, Profile, Feedback, ContactUs, ContactUsSettings

UserModel = get_user_model()


class ReadOnlyPasswordHashWidget(forms.Widget):
    template_name = 'credential/password_reset/auth/widgets/read_only_password_hash.html'
    read_only = True

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        summary = []
        if not value or value.startswith(UNUSABLE_PASSWORD_PREFIX):
            summary.append({'label': gettext("No password set.")})
        else:
            try:
                hasher = identify_hasher(value)
            except ValueError:
                summary.append({'label': gettext("Invalid password format or unknown hashing algorithm.")})
            else:
                for key, value_ in hasher.safe_summary(value).items():
                    summary.append({'label': gettext(key), 'value': value_})
        context['summary'] = summary
        return context


class ReadOnlyPasswordHashField(forms.Field):
    widget = ReadOnlyPasswordHashWidget

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("required", False)
        super().__init__(*args, **kwargs)

    def bound_data(self, data, initial):
        # Always return initial because the widget doesn't
        # render an input field.
        return initial

    def has_changed(self, initial, data):
        return False


class UsernameField(forms.CharField):
    def to_python(self, value):
        return unicodedata.normalize('NFKC', super().to_python(value))

    def widget_attrs(self, widget):
        return {
            **super().widget_attrs(widget),
            'autocapitalize': 'none',
            'autocomplete': 'username',
        }


@parsleyfy
class UserCreationForm(forms.ModelForm):
    """
    A form that creates a user, with no privileges, from the given username and
    password.
    """
    error_messages = {
        'password_mismatch': _("The two password fields didn't match."),
    }
    first_name = forms.CharField(
        max_length=255, required=True, error_messages={'required': 'First Name field is required.'}
    )
    last_name = forms.CharField(
        max_length=255, required=True, error_messages={'required': 'Last Name field is required.'}
    )
    email = forms.EmailField(
        max_length=255, required=True, error_messages={
            'required': 'Email field is required.', "invalid": "Invalid email",
            'unique': "A user with that email already exists.",
            # 'remote-message': "User with this email is already exists.",
        }
    )
    username = UsernameField(
        max_length=255, required=True, error_messages={
            'required': 'Username field is required.',
            'unique': _("A user with that username already exists."),
        },
    )
    password1 = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput,
        help_text=password_validation.password_validators_help_text_html(),
        error_messages={'required': 'Password field is required.'},
    )
    password2 = forms.CharField(
        label=_("Password confirmation"),
        widget=forms.PasswordInput,
        strip=False,
        # help_text=_("Enter the same password as before, for verification."),

        error_messages={
            'required': 'Password Confirmation field is required.',
            'equalto': 'Your passwords do not match',
        },
    )

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email",)
        field_classes = {'username': UsernameField}

        parsley_extras = {
            # 'username': {
            #     'remote': 'unique',
            #     'error-message': "A user with that username already exists."
            # },
            # 'email': {
            #     'remote': 'unique',
            #     'error-message': "A user with that email already exists."
            # },
            'password2': {
                'equalto': "password1",
                'error-message': "The two password fields didn't match.",
            },
        }

    def __init__(self, *args, **kwargs):
        super(UserCreationForm, self).__init__(*args, **kwargs)
        self.fields['first_name'].widget.attrs['placeholder'] = "First Name"
        self.fields['last_name'].widget.attrs['placeholder'] = "Last Name"
        self.fields['email'].widget.attrs['placeholder'] = "Email"
        self.fields['username'].widget.attrs['placeholder'] = "Username"
        self.fields['password1'].widget.attrs['placeholder'] = "Password"
        self.fields['password2'].widget.attrs['placeholder'] = "Password Confirmation"
        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                'class': 'form-control'
            })

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(
                self.error_messages['password_mismatch'],
                code='password_mismatch',
            )
        return password2

    def _post_clean(self):
        super()._post_clean()
        # Validate the password after self.instance is updated with form data
        # by super().
        password = self.cleaned_data.get('password2')
        if password:
            try:
                password_validation.validate_password(password, self.instance)
            except forms.ValidationError as error:
                self.add_error('password2', error)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


@parsleyfy
class ChristianBaseAuthenticationForm(forms.Form):
    """
    Base class for authenticating users. Extend this to get a form that accepts
    username/password logins.
    """
    username = UsernameField(
        max_length=254,
        widget=forms.TextInput(attrs={'autofocus': True}),
        error_messages={
            'required': 'Username field is required.',
        },
    )
    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput,
        error_messages={
            'required': 'Password field is required.',
        },
    )

    error_messages = {
        'invalid_login': _(
            "Please enter a correct %(username)s and password."
        ),
        'inactive': _("This account is inactive."),
    }

    def __init__(self, request=None, *args, **kwargs):
        """
        The 'request' parameter is set for custom auth use by subclasses.
        The form data comes in via the standard 'data' kwarg.
        """
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['placeholder'] = "Your Username"
        self.fields['password'].widget.attrs['placeholder'] = "Your password"

        # Set the label for the "username" field.
        self.username_field = UserModel._meta.get_field(UserModel.USERNAME_FIELD)
        if self.fields['username'].label is None:
            self.fields['username'].label = capfirst(self.username_field.verbose_name)

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username is not None and password:
            self.user_cache = authenticate(self.request, username=username, password=password)
            if self.user_cache is None:
                raise forms.ValidationError(
                    self.error_messages['invalid_login'],
                    code='invalid_login',
                    params={'username': self.username_field.verbose_name},
                )
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data

    def confirm_login_allowed(self, user):
        """
        Controls whether the given User may log in. This is a policy setting,
        independent of end-user authentication. This default behavior is to
        allow login by active users, and reject login by inactive users.

        If the given user cannot log in, this method should raise a
        ``forms.ValidationError``.

        If the given user may log in, this method should return None.
        """
        if not user.is_active:
            raise forms.ValidationError(
                self.error_messages['inactive'],
                code='inactive',
            )

    def get_user_id(self):
        if self.user_cache:
            return self.user_cache.id
        return None

    def get_user(self):
        return self.user_cache


@parsleyfy
class ChristianBaseForgotPasswordAndUserResendActivationForm(forms.Form):
    email = forms.EmailField(
        max_length=255, required=True, error_messages={
            'required': 'Email field is required.',
            "invalid": "Invalid email",
        }
    )

    def __init__(self, *args, **kwargs):
        super(ChristianBaseForgotPasswordAndUserResendActivationForm, self).__init__(*args, **kwargs)
        self.fields['email'].widget.attrs['placeholder'] = "Your email"

    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email, html_email_template_name=None):
        """
        Send a django.core.mail.EmailMultiAlternatives to `to_email`.
        """
        subject = render_to_string(subject_template_name, context)
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        body = render_to_string(email_template_name, context)

        email_message = EmailMultiAlternatives(subject, body, from_email, [to_email])
        email_message.attach_alternative(body, 'text/html')
        if html_email_template_name is not None:
            html_email = render_to_string(html_email_template_name, context)
            email_message.attach_alternative(html_email, 'text/html')

        email_message.send()

    def get_users(self, email):
        """Given an email, return matching user(s) who should receive a reset.

        This allows subclasses to more easily customize the default policies
        that prevent inactive users and users with unusable passwords from
        resetting their password.
        """
        active_users = UserModel._default_manager.filter(**{
            '%s__iexact' % UserModel.get_email_field_name(): email,
            'is_active': True,
        })
        return (u for u in active_users if u.has_usable_password())

    def save(self, domain_override=None,
             subject_template_name='email/password_reset_subject.txt',
             email_template_name='email/password_reset.html',
             use_https=False, token_generator=default_token_generator,
             from_email=None, request=None, html_email_template_name=None,
             extra_email_context=None):
        """
        Generate a one-use only link for resetting password and send it to the
        user.
        """
        myDate = datetime.now()  # get today datetime + year...

        email = self.cleaned_data["email"]
        for user in self.get_users(email):
            if not domain_override:
                current_site = get_current_site(request)
                site_name = current_site.name
                domain = current_site.domain
            else:
                site_name = domain = domain_override
            context = {
                'email': email,
                'domain': domain,
                'site_name': site_name,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'user': user,
                'token': token_generator.make_token(user),
                'protocol': 'https' if use_https else 'http',
                'myDate': myDate,
            }
            if extra_email_context is not None:
                context.update(extra_email_context)
            self.send_mail(
                subject_template_name, email_template_name, context, from_email,
                email, html_email_template_name=html_email_template_name,
            )


# def logo_data():
#     """  this fuction read/find logo image directory.  """
#     with open(finders.find('images/logo_text1.png'), 'rb') as f:
#         logo_data = f.read()
#     logo = MIMEImage(logo_data)
#     logo.add_header('Content-ID', '<logo>')
#     return logo


@parsleyfy
class ChristianBaseSetPasswordForm(forms.Form):
    """
    A form that lets a user change set their password without entering the old
    password
    """
    error_messages = {
        'password_mismatch': _("The two password fields didn't match."),
    }
    new_password1 = forms.CharField(
        label=_("New Password"),
        strip=False,
        widget=forms.PasswordInput,
        help_text=password_validation.password_validators_help_text_html(),
        error_messages={'required': 'New Password field is required.'},
    )
    new_password2 = forms.CharField(
        label=_("New Password confirmation"),
        widget=forms.PasswordInput,
        strip=False,
        # help_text=_("Enter the same password as before, for verification."),
        error_messages={'required': 'New Password Confirmation field is required.'},
    )

    class Meta:
        parsley_extras = {
            'new_password2': {
                'equalto': "new_password1",
                'error-message': "The two password fields didn't match.",
            },
        }

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].widget.attrs['placeholder'] = "Your New Password"
        self.fields['new_password2'].widget.attrs['placeholder'] = "Your New Password Confirmation"

    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError(
                    self.error_messages['password_mismatch'],
                    code='password_mismatch',
                )
        password_validation.validate_password(password2, self.user)
        return password2

    def save(self, commit=True):
        password = self.cleaned_data["new_password1"]
        self.user.set_password(password)
        if commit:
            self.user.save()
        return self.user


@parsleyfy
class ChristianBaseChangePasswordForm(ChristianBaseSetPasswordForm):
    """
    A form that lets a user change their password by entering their old
    password.
    """
    error_messages = {
        **ChristianBaseSetPasswordForm.error_messages,
        'password_incorrect': _("Your old password was entered incorrectly. Please enter it again."),
    }
    old_password = forms.CharField(
        label=_("Old password"),
        strip=False,
        widget=forms.PasswordInput,
        error_messages={'required': 'Old Password field is required.'},
    )
    new_password1 = forms.CharField(
        label=_("New Password"),
        strip=False,
        widget=forms.PasswordInput,
        help_text=password_validation.password_validators_help_text_html(),
        error_messages={'required': 'New Password field is required.'},
    )
    new_password2 = forms.CharField(
        label=_("New Password confirmation"),
        widget=forms.PasswordInput,
        strip=False,
        # help_text=_("Enter the same password as before, for verification."),
        error_messages={'required': 'New Password Confirmation field is required.'},
    )

    field_order = ['old_password', 'new_password1', 'new_password2']

    class Meta:
        parsley_extras = {
            'new_password2': {
                'equalto': "new_password1",
                'error-message': "The two password fields didn't match.",
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].widget.attrs['placeholder'] = "Your Old Password"
        self.fields['new_password1'].widget.attrs['placeholder'] = "Your New Password"
        self.fields['new_password2'].widget.attrs['placeholder'] = "Your New Password Confirmation"

    def clean_old_password(self):
        """
        Validate that the old_password field is correct.
        """
        old_password = self.cleaned_data["old_password"]
        if not self.user.check_password(old_password):
            raise forms.ValidationError(
                self.error_messages['password_incorrect'],
                code='password_incorrect',
            )
        return old_password


@parsleyfy
class AdminPasswordChangeForm(forms.Form):
    """
    A form used to change the password of a user in the admin interface.
    """
    error_messages = {
        'password_mismatch': _('The two password fields didn’t match.'),
    }
    required_css_class = 'required'
    password1 = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password', 'autofocus': True}),
        strip=False,
        help_text=password_validation.password_validators_help_text_html(),
    )
    password2 = forms.CharField(
        label=_("Password (again)"),
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        strip=False,
        help_text=_("Enter the same password as before, for verification."),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError(
                    self.error_messages['password_mismatch'],
                    code='password_mismatch',
                )
        password_validation.validate_password(password2, self.user)
        return password2

    def save(self, commit=True):
        """Save the new password."""
        password = self.cleaned_data["password1"]
        self.user.set_password(password)
        if commit:
            self.user.save()
        return self.user

    @property
    def changed_data(self):
        data = super().changed_data
        for name in self.fields:
            if name not in data:
                return []
        return ['password']


@parsleyfy
class ChristianBaseUserChangeForm(forms.ModelForm):
    """
        This form update request user detail ( - User  - )
    """
    password = ReadOnlyPasswordHashField(
        label=_("Password"),
        help_text=_(
            'Raw passwords are not stored, so there is no way to see this '
            'user’s password, but you can change the password using '
            '<a href="{}">this form</a>.'
        ),
    )

    first_name = forms.CharField(
        max_length=255, required=True, error_messages={'required': 'First Name field is required.'}
    )
    last_name = forms.CharField(
        max_length=255, required=True, error_messages={'required': 'Last Name field is required.'}
    )
    email = forms.EmailField(
        max_length=255, required=True, error_messages={
            'required': 'Email field is required.', "invalid": "Invalid email",
            'unique': _("A user with that email already exists."),
        }
    )
    username = forms.CharField(
        max_length=255, required=True, error_messages={'required': 'Username field is required.'}
    )

    class Meta:
        model = User
        fields = ['username','first_name','last_name','email',]
        field_classes = {'username': UsernameField}

    def __init__(self, *args, **kwargs):
        super(ChristianBaseUserChangeForm, self).__init__(*args, **kwargs)
        password = self.fields.get('password')
        if password:
            password.help_text = password.help_text.format('../password/')
        user_permissions = self.fields.get('user_permissions')
        if user_permissions:
            user_permissions.queryset = user_permissions.queryset.select_related('content_type')
        self.fields['first_name'].widget.attrs['placeholder'] = "Your First Name"
        self.fields['last_name'].widget.attrs['placeholder'] = "Your Last Name"
        self.fields['email'].widget.attrs['placeholder'] = "Your Email"
        self.fields['username'].widget.attrs['placeholder'] = "Your Username"
        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                'class': 'form-control'
            })

    def clean_password(self):
        # Regardless of what the user provides, return the initial value.
        # This is done here, rather than on the field, because the
        # field does not have access to the initial value
        return self.initial.get('password')


@parsleyfy
class ChristianBaseUserProfileForm(forms.ModelForm):
    """
        This form update request user detail ( - User Profile  - )
    """
    bio = forms.CharField(
        max_length=7000, required=True,
        widget=forms.Textarea(
            attrs={'placeholder': 'Short info about you!'}
        ),
        error_messages={'required': 'Bio field is required.'}
    )

    class Meta:
        model = Profile
        fields = ['bio', ]


class ChristianBaseUserProfilePhotoForm(forms.ModelForm):
    """
        This form update request user detail ( - User Profile  - )
    """
    class Meta:
        model = Profile
        fields = ['image']


@parsleyfy
class ChristianBaseUserSettingForm(forms.ModelForm):
    """
        This form allow to add their website and social accounts ( - User Setting  - )
    """
    website = forms.URLField(
        label="Your Website URL",
        max_length=255, required=False,
    )
    facebook_url = forms.URLField(
        label="Your Facebook URL",
        max_length=255, required=False,
    )
    youtube_url = forms.URLField(
        label="Your Youtube URL",
        max_length=255, required=False,
    )
    instagram_url = forms.URLField(
        label="Your Instagram URL",
        max_length=255, required=False,
    )
    linkedin_url = forms.URLField(
        label="Your Linkedin URL",
        max_length=255, required=False,
    )
    twitter_url = forms.URLField(
        label="Your Twitter URL",
        max_length=255, required=False,
    )

    class Meta:
        model = Profile
        fields = ['website', 'facebook_url', 'youtube_url', 'linkedin_url', 'twitter_url']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['website'].widget.attrs['placeholder'] = "https://www.yoursitename.com/"
        self.fields['facebook_url'].widget.attrs['placeholder'] = "https://www.facebook.com/yourfacebookid/"
        self.fields['youtube_url'].widget.attrs['placeholder'] = "https://www.youtube.com/youryoutubeid/"
        self.fields['instagram_url'].widget.attrs['placeholder'] = "https://www.youtube.com/yourinstagramid/"
        self.fields['linkedin_url'].widget.attrs['placeholder'] = "https://www.linkedin.com/yourlinkedinid/"
        self.fields['twitter_url'].widget.attrs['placeholder'] = "https://www.facebook.com/yourtwttierid/"


@parsleyfy
class ChristianBaseUserFeedbackForm(forms.ModelForm):
    """
        This form allow users give feedback ( - FeedBack  - )
    """
    message = forms.CharField(
        max_length=7000, required=True,
        widget=forms.Textarea(
            attrs={'placeholder': 'Please enter the details of your feedback. A member of our support staff will respond as soon as possible'}
        ),
        error_messages={'required': 'Message field is required.'}
    )

    class Meta:
        model = Feedback
        fields = ['message', ]


@parsleyfy
class ChristianBaseRecoverAccountForm(forms.Form):
    """
        This form allow users to recover or unlocked account ( - Recover Account  - )
    """
    username = UsernameField(
        max_length=255, required=True, error_messages={
            'required': 'Username field is required.',
        },
    )
    email = forms.EmailField(
        max_length=255, required=True, error_messages={
            'required': 'Email field is required.', "invalid": "Invalid email",
        }
    )

    class Meta:
        model = User
        fields = ['username', 'email', ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['placeholder'] = "Your Username"
        self.fields['email'].widget.attrs['placeholder'] = "Your Email Address"


@parsleyfy
class ContactUsForm(forms.ModelForm):
    """
        This form is contact form allow users give emergency issues ( - Contact Us Form  - )
    """
    name = forms.CharField(
        max_length=255, required=True, error_messages={
            'required': 'Name field is required.',
        },
    )
    subject = forms.CharField(
        max_length=255, required=True, error_messages={
            'required': 'Subject field is required.',
        },
    )
    email = forms.EmailField(
        max_length=255, required=True, error_messages={
            'required': 'Email field is required.', "invalid": "Invalid email",
        }
    )
    message = forms.CharField(
        max_length=9000, required=True,
        widget=forms.Textarea(
            attrs={'placeholder': 'Your message here?'}
        ),
        error_messages={'required': 'Message field is required.'}
    )

    class Meta:
        model = ContactUs
        fields = ['name', 'subject', 'email', 'message', ]

    def __init__(self, *args, **kwargs):
        super(ContactUsForm, self).__init__(*args, **kwargs)
        self.fields['name'].widget.attrs['placeholder'] = "Your Full Name"
        self.fields['subject'].widget.attrs['placeholder'] = "Subject / Title"
        self.fields['email'].widget.attrs['placeholder'] = "Your Email Address"


class ContactUsSettingsForm(forms.ModelForm):

    class Meta:
        model = ContactUsSettings
        exclude = ()

    def __init__(self, *args, **kwargs):
        super(ContactUsSettingsForm, self).__init__(*args, **kwargs)
        for field in iter(self.fields):
            if max(enumerate(iter(self.fields)))[0] != field:
                self.fields[field].widget.attrs.update({
                    'class': 'form-control',
                    "placeholder": "Please enter your " + field.replace('_', ' ').capitalize()
                })
