
import uuid
from datetime import datetime
from django.db import models
from django.template.defaultfilters import slugify
from django.contrib.sites.shortcuts import get_current_site
from django.utils.functional import SimpleLazyObject
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _
from django.urls import reverse

from ckeditor_uploader.fields import RichTextUploadingField

from accounts.validators import validate_file_extension, validate_Image_extension
from accounts.models import User, UserRole
from track.models import UrlHit


HELPCENTER_CHOICE = (
    {'', 'Select Help Category'},
    ('Getting Started', 'Getting Started'),
    ('Login', 'Login'),
    ('Account Settings', 'Account Settings'),
    ('Reading Stories', 'Reading Stories'),
    ('User Memebership', 'User Memebership'),
    ('Navigating', 'Navigating'),
    ('Managing posts', 'Managing posts'),
    ('Writing && editing', 'Writing & editing'),
    ('Distribution', 'Distribution'),
    ('Holy L.M Publication', 'Holy L.M Publication'),
    ('Comments', 'Comments'),
)

USERREQUEST_CHOICE = (
    {'', 'Select Help Category'},
    ('Account issues', 'Account issues'),
    ('Publishing issues', 'Publishing issues'),
    ('Other', 'Other'),
)

class Section(models.Model):
    name = models.CharField(max_length=100, null=True, blank=True)
    slug = models.SlugField(default=slugify(name), max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['id']

    def save(self, *args, **kwargs):
        tempslug = slugify(self.name)
        if self.id:
            section = Section.objects.get(pk=self.id)
            if section.name != self.name:
                self.slug = create_section_slug(tempslug)
        else:
            self.slug = create_section_slug(tempslug)

        super(Section, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

    def section_posts(self):
        return HelpCenter.objects.filter(section=self).count()

    def get_absolute_url(self):
        kwargs = {
            'slug': self.slug,
        }
        return reverse('section_view', kwargs=kwargs)

    @property
    def hit_count(self):
        url, created = UrlHit.objects.get_or_create(url=self.get_absolute_url())
        return url.hits


def create_section_slug(tempslug):
    slugcount = 0
    while True:
        try:
            Section.objects.get(slug=tempslug)
            slugcount += 1
            tempslug = tempslug + '-' + str(slugcount)
        except ObjectDoesNotExist:
            return tempslug


def MakeOTP():
    import random,string
    allowed_chars = ''.join((string.ascii_letters, string.digits))
    return ''.join(random.choice(allowed_chars) for _ in range(10))


class HelpCenter(models.Model):
    help_hex = models.CharField(max_length=10, unique=True, editable=False, default=MakeOTP)
    title = models.CharField(max_length=500, unique=True)
    slug = models.SlugField(default=slugify(title), max_length=500, unique=True)
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    content = RichTextUploadingField(blank=True, null=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['id']


    def save(self, *args, **kwargs):
        tempslug = slugify(self.title)
        if self.id:
            blogpost = HelpCenter.objects.get(pk=self.id)
            if blogpost.title != self.title:
                self.slug = create_helpcenter_slug(tempslug)

        else:
            self.slug = create_helpcenter_slug(tempslug)

        super(HelpCenter, self).save(*args, **kwargs)

    def __str__(self):
        return '{title}: {help_hex}'.format(title=str(self.title), help_hex=str(self.help_hex))

    def is_deletable_by(self, user):
        if self.user == user or user.is_superuser:
            return True
        return False

    def get_absolute_url(self):
        kwargs = {
            'help_hex': self.help_hex
        }
        return reverse('articles_detail', kwargs=kwargs)

    @property
    def hit_count(self):
        url, created = UrlHit.objects.get_or_create(url=self.get_absolute_url())
        return url.hits

    @property
    def image_file(self):
        return self.featured_image.path


def create_helpcenter_slug(tempslug):
    slugcount = 0
    while True:
        try:
            HelpCenter.objects.get(slug=tempslug)
            slugcount += 1
            tempslug = tempslug + '-' + str(slugcount)
        except ObjectDoesNotExist:
            return tempslug


class UsersRequest(models.Model):
    help_hex = models.CharField(max_length=20, unique=True, editable=False, default=uuid.uuid4().hex[:10])
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    description = models.TextField()
    status = models.CharField(max_length=50, choices=USERREQUEST_CHOICE)
    created_on = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        tempslug = slugify(self.status)
        if self.id:
            blogpost = UsersRequest.objects.get(pk=self.id)
            if blogpost.status != self.status:
                self.slug = create_request_slug(tempslug)
        else:
            self.slug = create_request_slug(tempslug)

        super(UsersRequest, self).save(*args, **kwargs)

    def __str__(self):
        return self.status


def create_request_slug(tempslug):
    slugcount = 0
    while True:
        try:
            UsersRequest.objects.get(slug=tempslug)
            slugcount += 1
            tempslug = tempslug + '-' + str(slugcount)
        except ObjectDoesNotExist:
            return tempslug
