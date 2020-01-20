from django.conf import settings
from django.contrib import auth
from django.contrib.auth.models import PermissionsMixin
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.db import models
from django.db.models.manager import EmptyManager
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.defaultfilters import slugify
from PIL import Image


from .validators import UnicodeUsernameValidator
from track.models import UrlHit


ROLE_CHOICE = (
    ('Admin', 'Admin'),
    ('Author', 'Author'),
    ('Publisher', 'Publisher'),
    ('BS P', 'Bible Studies Publisher'),
    ('Devotion P', 'Devotion Publisher'),
    ('Tech P', 'Tech Publisher'),
    ('Quotes P', 'Quotes Publisher'),
    ('Policy', 'Policy'),
)

ALLOW_ROLE_CHOICE = (
    ('Bible Studies', 'Bible Studies'),
    ('Devotion', 'Devotion'),
    ('Tech', 'Tech'),
    ('Quotes', 'Quotes'),
)

RELATIONSHIP_STATUSES = {
    ('Following', 'Following'),
    ('Blocked', 'Blocked'),
}

def update_last_login(sender, user, **kwargs):
    """
    A signal receiver which updates the last_login date for
    the user logging in.
    """
    user.last_login = timezone.now()
    user.save(update_fields=['last_login'])


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, username, email, password, **extra_fields):
        """
        Create and save a user with the given username, email, and password.
        """
        if not username:
            raise ValueError('The given username must be set')
        email = self.normalize_email(email)
        username = self.model.normalize_username(username)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(username, email, password, **extra_fields)

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(username, email, password, **extra_fields)

    # def with_perm(self, perm, is_active=True, include_superusers=True, backend=None, obj=None):
    #     if backend is None:
    #         backends = auth._get_backends(return_tuples=True)
    #         if len(backends) == 1:
    #             backend, _ = backends[0]
    #         else:
    #             raise ValueError(
    #                 'You have multiple authentication backends configured and '
    #                 'therefore must provide the `backend` argument.'
    #             )
    #     elif not isinstance(backend, str):
    #         raise TypeError(
    #             'backend must be a dotted import path string (got %r).'
    #             % backend
    #         )
    #     else:
    #         backend = auth.load_backend(backend)
    #     if hasattr(backend, 'with_perm'):
    #         return backend.with_perm(
    #             perm,
    #             is_active=is_active,
    #             include_superusers=include_superusers,
    #             obj=obj,
    #         )
    #     return self.none()


class AbstractUser(AbstractBaseUser, PermissionsMixin):
    """
    An abstract base class implementing a fully featured User model with
    admin-compliant permissions.

    Username and password are required. Other fields are optional.
    """
    username_validator = UnicodeUsernameValidator()

    username = models.CharField(
        _('username'),
        max_length=150,
        unique=True,
        help_text=_('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'),
        validators=[username_validator],
        error_messages={
            'unique': _("A user with that username already exists."),
        },
    )
    first_name = models.CharField(_('first name'), max_length=30, blank=True)
    last_name = models.CharField(_('last name'), max_length=150, blank=True)
    email = models.EmailField(_('email address'), unique=True, blank=True)
    following = models.ManyToManyField('self', through='Connection', related_name='followers', symmetrical=False)

    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this admin site.'),
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    objects = UserManager()

    EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        abstract = True

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name

    def email_user(self, subject, message, from_email=None, **kwargs):
        """Send an email to this user."""
        send_mail(subject, message, from_email, [self.email], **kwargs)


class User(AbstractUser):
    """
    Users within the Django authentication system are represented by this
    model.

    Username, password and email are required. Other fields are optional.
    """
    class Meta(AbstractUser.Meta):
        swappable = 'AUTH_USER_MODEL'


class UserRole(models.Model):
    """
    UserRole for all users -- Author, Admin, Publishers
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=50, choices=ROLE_CHOICE)
    is_locked = models.BooleanField(default=False)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return self.user.username


# class UserAllowBaseMenu(models.Model):
#     """
#     Allow users to have their own organization to be allow to post either in --
#     Bible Studies, Devotion, Tech, etc ...
#     """
#     user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
#     name = models.CharField(_('name'), max_length=150, blank=True)
#     slug = models.SlugField(default=slugify(name), unique=True, max_length=100)
#     email = models.EmailField(_('email address'), unique=True, blank=True)
#     phone = models.EmailField(_('phone number'), unique=True, blank=True)
#     description = models.CharField(max_length=500, blank=True)
#     role = models.CharField(max_length=10, choices=ALLOW_ROLE_CHOICE)
#     is_approved = models.BooleanField(
#         _('Approved status'),
#         default=False,
#         help_text=_('Designates whether the user should be approved to publish either in Tech, etc.'),
#     )
#     following = models.ManyToManyField('self', through='ConnectOrganization', related_name='followers', symmetrical=False)
#     created = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         ordering = ['-id']

#     def save(self, *args, **kwargs):
#         tempslug = slugify(self.name)
#         if self.id:
#             userorg = UserAllowBaseMenu.objects.get(pk=self.id)
#             if userorg.name != self.name:
#                 self.slug = create_userallowbasemenu_slug(tempslug)
#         else:
#             self.slug = create_userallowbasemenu_slug(tempslug)

#         super(UserAllowBaseMenu, self).save(*args, **kwargs)

#     def __str__(self):
#         return f'{self.name}. Status: {self.is_approved}'


# def create_userallowbasemenu_slug(tempslug):
#     slugcount = 0
#     while True:
#         try:
#             UserAllowBaseMenu.objects.get(slug=tempslug)
#             slugcount += 1
#             tempslug = tempslug + '-' + str(slugcount)
#         except ObjectDoesNotExist:
#             return tempslug

class Connection(models.Model):
    user_from = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='rel_from_set', on_delete=models.CASCADE)
    user_to = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='rel_to_set', on_delete=models.CASCADE)
    status = models.CharField(max_length=50, choices=RELATIONSHIP_STATUSES, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ('-created',)

    def __str__(self):
        return '{} follows {}'.format(self.user_from, self.user_to)


# class ConnectOrganization(models.Model):
#     user_from = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='org_from_set', on_delete=models.CASCADE)
#     to_org = models.ForeignKey(UserAllowBaseMenu, related_name='org_to_set', on_delete=models.CASCADE)
#     status = models.IntegerField(_('Status'), choices=RELATIONSHIP_STATUSES)
#     created = models.DateTimeField(auto_now_add=True, db_index=True)

#     class Meta:
#         ordering = ('-created',)

#     def __str__(self):
#         return '{} follows {}'.format(self.user_from, self.to_org)

def user_directory_path(profile, filename):
    return u'image_profile/%s/%s' % (str(profile.user.username), filename)


class Profile(models.Model):
    """
    Users Profile .   more detail for users models
    --- headline, bio , and etc..
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    bio = models.TextField()
    website = models.URLField(max_length=255, null=True, blank=True)
    facebook_url = models.URLField(max_length=255, null=True, blank=True)
    youtube_url = models.URLField(max_length=255, null=True, blank=True)
    instagram_url = models.URLField(max_length=255, null=True, blank=True)
    linkedin_url = models.URLField(max_length=255, null=True, blank=True)
    twitter_url = models.URLField(max_length=255, null=True, blank=True)
    image = models.ImageField(default='default.png', upload_to=user_directory_path, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '{} Profile'.format(str(self.user.username))

    def get_absolute_url(self):
        kwargs = {
            'username': self.user.username,
        }
        return reverse('christianbase_userprofile', kwargs=kwargs)

    @property
    def author_profile(self):
        return self.image.path

    @property
    def hit_count(self):
        url, created = UrlHit.objects.get_or_create(url=self.get_absolute_url())
        return url.hits


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    instance.profile.save()


class Action(models.Model):
    """
    Stream activity for users
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='actions', db_index=True, on_delete=models.CASCADE)
    verb = models.CharField(max_length=256)
    # target object
    target_ct = models.ForeignKey(ContentType, blank=True, null=True, related_name='target_obj', on_delete=models.CASCADE)
    target_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    target = GenericForeignKey('target_ct', 'target_id')
    created = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ('-created',)


class Report(models.Model):
    """
    feedback models for users give reason why leaving christianbase...
    """
    name = models.CharField(max_length=226, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '{}'.format(self.name)


class ReportUser(models.Model):
    """
    feedback models for users give reason why leaving christianbase...
    """
    report = models.ForeignKey(Report, on_delete=models.CASCADE)
    make = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='make', on_delete=models.CASCADE)
    to = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='to', on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(
        _('Approved Report'),
        default=False,
        help_text=_('Designates whether the user report is approved.'),
    )

    def __str__(self):
        return '{}'.format(self.report.name)

    def get_absolute_url(self):
        return reverse('christianbase_user_report')

    @property
    def hit_count(self):
        url, created = UrlHit.objects.get_or_create(url=self.get_absolute_url())
        return url.hits


class Feedback(models.Model):
    """
    feedback models for users give reason why leaving christianbase...
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '{}'.format(str(self.user.username))

    def get_absolute_url(self):
        kwargs = {
           'username': self.user.username
        }
        return reverse('christianbase_user_feedback', kwargs=kwargs)

    @property
    def hit_count(self):
        url, created = UrlHit.objects.get_or_create(url=self.get_absolute_url())
        return url.hits


class ContactUs(models.Model):
    """
    this model allow users contact us for emergency..
    """
    name = models.CharField(max_length=255, null=True, blank=True)
    subject = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(blank=True, null=True)
    message = models.TextField()
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '{}'.format(self.subject)


class ContactUsSettings(models.Model):
    from_email = models.EmailField()
    reply_to_email = models.EmailField(blank=True, null=True)
    email_admin = models.EmailField()
    subject = models.CharField(max_length=500)
    body_user = models.TextField()
    body_admin = models.TextField()

    def __str__(self):
        return '{}'.format(self.subject)

