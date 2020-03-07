import uuid
import random
import os
from datetime import datetime
from django.db import models
from django.template.defaultfilters import slugify
from django.contrib.sites.shortcuts import get_current_site
from django.utils.functional import SimpleLazyObject
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives, send_mail
from email.mime.image import MIMEImage
from django.contrib.staticfiles import finders
from django.urls import reverse

# from hitcount.models import HitCountMixin, HitCount
# from django.contrib.contenttypes.fields import GenericRelation
# from django.utils.encoding import python_2_unicode_compatible

from taggit.managers import TaggableManager
from ckeditor_uploader.fields import RichTextUploadingField

from accounts.validators import validate_file_extension, validate_Image_extension
from accounts.models import User, UserRole
from track.models import UrlHit

STATUS_CHOICE = (
    ('Drafted', 'Drafted'),
    ('Published', 'Published'),
    ('Rejected', 'Rejected'),
    ('Trashed', 'Trashed'),
)

REQUEST_CHOICE = (
    {'', 'Select Prayer Area'},
    ('General', 'General'),
    ('Emotional', 'Emotional Healing'),
    ('Physical', 'Physical Healing'),
    ('Finances', 'Finances'),
    ('Relation', 'Relationship'),
    ('Spiritual', 'Spiritual Growth'),
)


class Category(models.Model):
    name = models.CharField(max_length=100, null=True, blank=True)
    slug = models.SlugField(default=slugify(name), max_length=100)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    description = models.CharField(max_length=500)
    is_active = models.BooleanField(default=False)

    class Meta:
        ordering = ['-id']

    def save(self, *args, **kwargs):
        tempslug = slugify(self.name)
        if self.id:
            category = Category.objects.get(pk=self.id)
            if category.name != self.name:
                self.slug = create_category_slug(tempslug)
        else:
            self.slug = create_category_slug(tempslug)

        super(Category, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

    def category_posts(self):
        return Post.objects.filter(status='Published', category=self).count()

    def get_absolute_url(self):
        kwargs = {
            'slug': self.slug,
        }
        return reverse('christianbase_category_story', kwargs=kwargs)

    @property
    def hit_count(self):
        url, created = UrlHit.objects.get_or_create(url=self.get_absolute_url())
        return url.hits


def create_category_slug(tempslug):
    slugcount = 0
    while True:
        try:
            Category.objects.get(slug=tempslug)
            slugcount += 1
            tempslug = tempslug + '-' + str(slugcount)
        except ObjectDoesNotExist:
            return tempslug


class Tags(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(default=slugify(name), max_length=100, unique=True)

    def save(self, *args, **kwargs):
        tempslug = slugify(self.name)
        if self.id:
            tag = Tags.objects.get(pk=self.id)
            if tag.name != self.name:
                self.slug = create_tag_slug(tempslug)
        else:
            self.slug = create_tag_slug(tempslug)
        super(Tags, self).save(*args, **kwargs)

    def __str__(self):
        return self.name


def create_tag_slug(tempslug):
    slugcount = 0
    while True:
        try:
            Tags.objects.get(slug=tempslug)
            slugcount += 1
            tempslug = tempslug + '-' + str(slugcount)
        except ObjectDoesNotExist:
            return tempslug

def GenerateOTP():
    import random,string
    allowed_chars = ''.join((string.ascii_letters, string.digits))
    return ''.join(random.choice(allowed_chars) for _ in range(20))


class Post(models.Model):
    story_code = models.CharField(max_length=20, unique=True, editable=False, default=GenerateOTP)
    title = models.CharField(max_length=500, unique=True)
    slug = models.SlugField(default=slugify(title), max_length=500, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = RichTextUploadingField(blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    tags = models.ManyToManyField(Tags, related_name='rel_posts')
    status = models.CharField(max_length=10, choices=STATUS_CHOICE, default='Drafted')
    featured_image = models.ImageField(
        upload_to='blog_photos/%Y/%m/%d/', blank=True, null=True, validators=[validate_Image_extension],
        help_text=_('Include a high-quality image in your story to make it more inviting to readers.'),
    )
    featured_video = models.FileField(
        upload_to='blog_videos/%Y/%m/%d/', blank=True, null=True, validators=[validate_file_extension],
        help_text=_('You can include high quality video about your story.'),
    )
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateField(auto_now=True)
    likes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='likes', blank=True)
    restrict_comment = models.BooleanField(default=False)
    favourite = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='favourite', blank=True)

    class Meta:
        ordering = ['-updated_on']

    def save(self, *args, **kwargs):
        tempslug = slugify(self.title)
        if self.id:
            blogpost = Post.objects.get(pk=self.id)
            if blogpost.title != self.title:
                self.slug = create_story_slug(tempslug)
        else:
            self.slug = create_story_slug(tempslug)
            # self.email_to_admins_on_post_create()

        super(Post, self).save(*args, **kwargs)

    def __str__(self):
        return self.title

    def total_likes(self):
        return self.likes.count()

    def is_deletable_by(self, user):
        if self.user == user or user.is_superuser:
            return True
        return False

    def create_activity(self, user, content):
        return PostHistory.objects.create(
            user=user, post=self, content=content
        )

    def create_activity_instance(self, user, content):
        return PostHistory(
            user=user, post=self, content=content
        )

    def remove_activity(self):
        self.history.all().delete()

    def get_absolute_url(self):
        kwargs = {
            'slug': self.slug,
            'story_code': self.story_code
        }
        return reverse('christianbase_story_detail', kwargs=kwargs)

    @property
    def hit_count(self):
        url, created = UrlHit.objects.get_or_create(url=self.get_absolute_url())
        return url.hits

    @property
    def image_file(self):
        return self.featured_image.path

    # def email_to_admins_on_post_create(self, request=None):
    #     email = settings.EMAIL_HOST_USER
    #     if not self.id and email:
    #         admin_roles = UserRole.objects.select_related().filter(role="Admin")
    #         admin_is_staff = User.objects.select_related().filter(is_staff=True)
    #         admin_m = admin_is_staff and admin_roles
    #         admin_emails = [admin_role.user.email for admin_role in admin_m]
    #         myDate = datetime.now()
    #         slug = self.slug
    #         story_code = self.story_code
    #         user = self.user
    #         author_name = user.first_name + ' ' + user.last_name if user.first_name else user.email
    #         author_story_title = self.title
    #         author_story_content = self.content
    #         mail_subject = f'New Story Published by, { author_name }!'
    #         html_content = render_to_string('email_messages/new_story/new_story_admin.html', {
    #             'author_name': author_name,
    #             'author_story_title': author_story_title,
    #             'author_story_content': author_story_content,
    #             'myDate': myDate,
    #             'username': user.username,
    #             'slug': slug,
    #             'story_code': story_code,
    #         })
    #         # to_email = form.cleaned_data.get('email')
    #         email = EmailMultiAlternatives(
    #             mail_subject, to=[admin_emails]
    #         )
    #         email.attach_alternative(html_content, "text/html")
    #         email.attach(logo_data())
    #         email.send(fail_silently=False)
            # text = "New blog post has been created by {0} with the name {1} in the category {2}.".format(author_name, self.title, self.category.name)
            # send_mail(
            #     subject="New Blog Post created",
            #     message=text,
            #     from_email=email,
            #     recipient_list=admin_emails,
            #     fail_silently=False,
            # )


def create_story_slug(tempslug):
    slugcount = 0
    while True:
        try:
            Post.objects.get(slug=tempslug)
            slugcount += 1
            tempslug = tempslug + '-' + str(slugcount)
        except ObjectDoesNotExist:
            return tempslug


def logo_data():
    """  this fuction read/find logo image directory.  """
    with open(finders.find('images/logo_icon-2.jpg'), 'rb') as f:
        logo_data = f.read()
    logo = MIMEImage(logo_data)
    logo.add_header('Content-ID', '<logo>')
    return logo


class PostHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, related_name='history', on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '{username} {content} {blog_title}'.format(
            username=str(self.user.get_username()),
            content=str(self.content),
            blog_title=str(self.post.title)
        )


class WrittenBy(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_approved = models.BooleanField(default=False)
    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username

class BibleStudies(models.Model):
    title = models.CharField(max_length=500, unique=True)
    slug = models.SlugField(default=slugify(title), max_length=500, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    written_by = models.ForeignKey(WrittenBy, on_delete=models.CASCADE, blank=True, null=True)
    content = RichTextUploadingField(blank=True, null=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateField(auto_now=True)
    bible_likes = models.ManyToManyField(User, related_name='bible_likes', blank=True)
    featured_image = models.ImageField(
        upload_to='biblestudies_photos/%Y/%m/%d/', blank=True, null=True, validators=[validate_Image_extension],
        help_text=_('Include a high-quality image in your story to make it more inviting to readers.'),
    )
    bookmarks_bible = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='bookmarks_bible', blank=True)
    restrict_comment = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)


    def save(self, *args, **kwargs):
        tempslug = slugify(self.title)
        if self.id:
            blogpost = BibleStudies.objects.get(pk=self.id)
            if blogpost.title != self.title:
                self.slug = create_biblestudies_slug(tempslug)
        else:
            self.slug = create_biblestudies_slug(tempslug)

        super(BibleStudies, self).save(*args, **kwargs)

    def __str__(self):
        return self.title

    def total_likes(self):
        return self.bible_likes.count()

    def get_absolute_url(self):
        kwargs = {
            'slug': self.slug,
        }
        return reverse('bible-studies-view', kwargs=kwargs)

    @property
    def hit_count(self):
        url, created = UrlHit.objects.get_or_create(url=self.get_absolute_url())
        return url.hits

    @property
    def image_file(self):
        return self.featured_image.path


def create_biblestudies_slug(tempslug):
    slugcount = 0
    while True:
        try:
            BibleStudies.objects.get(slug=tempslug)
            slugcount += 1
            tempslug = tempslug + '-' + str(slugcount)
        except ObjectDoesNotExist:
            return tempslug


class Devotion(models.Model):
    title = models.CharField(max_length=500, unique=True)
    slug = models.SlugField(default=slugify(title), max_length=500, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    written_by = models.ForeignKey(WrittenBy, on_delete=models.CASCADE, blank=True, null=True)
    content = RichTextUploadingField(blank=True, null=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateField(auto_now=True)
    devotion_likes = models.ManyToManyField(User, related_name='devotion_likes', blank=True)
    featured_image = models.ImageField(
        upload_to='devotion_photos/%Y/%m/%d/', blank=True, null=True, validators=[validate_Image_extension],
        help_text=_('Include a high-quality image in your story to make it more inviting to readers.'),
    )
    bookmarks_devotion = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='bookmarks_devotion', blank=True)
    restrict_comment = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)


    def save(self, *args, **kwargs):
        tempslug = slugify(self.title)
        if self.id:
            blogpost = Devotion.objects.get(pk=self.id)
            if blogpost.title != self.title:
                self.slug = create_devotion_slug(tempslug)
        else:
            self.slug = create_devotion_slug(tempslug)

        super(Devotion, self).save(*args, **kwargs)

    def __str__(self):
        return self.title

    def total_likes(self):
        return self.devotion_likes.count()

    def get_absolute_url(self):
        kwargs = {
            'slug': self.slug,
        }
        return reverse('devotion-view', kwargs=kwargs)

    @property
    def hit_count(self):
        url, created = UrlHit.objects.get_or_create(url=self.get_absolute_url())
        return url.hits

    @property
    def image_file(self):
        return self.featured_image.path


def create_devotion_slug(tempslug):
    slugcount = 0
    while True:
        try:
            Devotion.objects.get(slug=tempslug)
            slugcount += 1
            tempslug = tempslug + '-' + str(slugcount)
        except ObjectDoesNotExist:
            return tempslug


class Tech(models.Model):
    title = models.CharField(max_length=500, unique=True)
    slug = models.SlugField(default=slugify(title), max_length=500, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    written_by = models.ForeignKey(WrittenBy, on_delete=models.CASCADE, blank=True, null=True)
    content = RichTextUploadingField(blank=True, null=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateField(auto_now=True)
    tech_likes = models.ManyToManyField(User, related_name='tech_likes', blank=True)
    featured_image = models.ImageField(
        upload_to='tech_photos/%Y/%m/%d/', blank=True, null=True, validators=[validate_Image_extension],
        help_text=_('Include a high-quality image in your story to make it more inviting to readers.'),
    )
    bookmarks_tech = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='bookmarks_tech', blank=True)
    restrict_comment = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)


    def save(self, *args, **kwargs):
        tempslug = slugify(self.title)
        if self.id:
            blogpost = Tech.objects.get(pk=self.id)
            if blogpost.title != self.title:
                self.slug = create_tech_slug(tempslug)
        else:
            self.slug = create_tech_slug(tempslug)

        super(Tech, self).save(*args, **kwargs)

    def __str__(self):
        return self.title

    def total_likes(self):
        return self.tech_likes.count()

    def get_absolute_url(self):
        kwargs = {
            'slug': self.slug,
        }
        return reverse('tech-view', kwargs=kwargs)

    @property
    def hit_count(self):
        url, created = UrlHit.objects.get_or_create(url=self.get_absolute_url())
        return url.hits

    @property
    def image_file(self):
        return self.featured_image.path


def create_tech_slug(tempslug):
    slugcount = 0
    while True:
        try:
            Tech.objects.get(slug=tempslug)
            slugcount += 1
            tempslug = tempslug + '-' + str(slugcount)
        except ObjectDoesNotExist:
            return tempslug


class Quotes(models.Model):
    title = models.CharField(max_length=500, unique=True)
    slug = models.SlugField(default=slugify(title), max_length=500, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    written_by = models.ForeignKey(WrittenBy, on_delete=models.CASCADE, blank=True, null=True)
    content = RichTextUploadingField(blank=True, null=True)
    quotes_likes = models.ManyToManyField(User, related_name='quotes_likes', blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateField(auto_now=True)
    featured_image = models.ImageField(
        upload_to='quotes_photos/%Y/%m/%d/', blank=True, null=True, validators=[validate_Image_extension],
        help_text=_('Include a high-quality image in your story to make it more inviting to readers.'),
    )
    bookmark_quote = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='bookmark_quote', blank=True)
    restrict_comment = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)


    def save(self, *args, **kwargs):
        tempslug = slugify(self.title)
        if self.id:
            blogpost = Quotes.objects.get(pk=self.id)
            if blogpost.title != self.title:
                self.slug = create_quotes_slug(tempslug)
        else:
            self.slug = create_quotes_slug(tempslug)

        super(Quotes, self).save(*args, **kwargs)

    def __str__(self):
        return self.title

    def total_likes(self):
        return self.quotes_likes.count()

    def get_absolute_url(self):
        kwargs = {
            'slug': self.slug,
        }
        return reverse('quotes-view', kwargs=kwargs)

    @property
    def hit_count(self):
        url, created = UrlHit.objects.get_or_create(url=self.get_absolute_url())
        return url.hits

    @property
    def image_file(self):
        return self.featured_image.path


def create_quotes_slug(tempslug):
    slugcount = 0
    while True:
        try:
            Quotes.objects.get(slug=tempslug)
            slugcount += 1
            tempslug = tempslug + '-' + str(slugcount)
        except ObjectDoesNotExist:
            return tempslug


class Policy(models.Model):
    policy_hex = models.CharField(max_length=20, unique=True, editable=False, default=GenerateOTP)
    title = models.CharField(max_length=500, unique=True)
    slug = models.SlugField(default=slugify(title), max_length=500, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    written_by = models.ForeignKey(WrittenBy, on_delete=models.CASCADE, blank=True, null=True)
    content = RichTextUploadingField(blank=True, null=True)
    tags = models.ManyToManyField(Tags, related_name='tags')
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateField(auto_now=True)
    policy_likes = models.ManyToManyField(User, related_name='policy_likes', blank=True)
    bookmarks = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='bookmarks', blank=True)
    restrict_comment = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)


    def save(self, *args, **kwargs):
        tempslug = slugify(self.title)
        if self.id:
            blogpost = Policy.objects.get(pk=self.id)
            if blogpost.title != self.title:
                self.slug = create_policy_slug(tempslug)
        else:
            self.slug = create_policy_slug(tempslug)

        super(Policy, self).save(*args, **kwargs)

    def __str__(self):
        return self.title

    def total_likes(self):
        return self.policy_likes.count()

    def is_deletable_by(self, user):
        if self.user == user or user.is_superuser:
            return True
        return False

    def get_absolute_url(self):
        kwargs = {
            'slug': self.slug,
            'policy_hex': self.policy_hex
        }
        return reverse('policy-view', kwargs=kwargs)

    @property
    def hit_count(self):
        url, created = UrlHit.objects.get_or_create(url=self.get_absolute_url())
        return url.hits

    @property
    def image_file(self):
        return self.featured_image.path


def create_policy_slug(tempslug):
    slugcount = 0
    while True:
        try:
            Policy.objects.get(slug=tempslug)
            slugcount += 1
            tempslug = tempslug + '-' + str(slugcount)
        except ObjectDoesNotExist:
            return tempslug


class PrayerRequest(models.Model):
    prayerrequest_hex = models.CharField(max_length=22, unique=True, editable=False, default=GenerateOTP)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    area = models.CharField(_('Please Pray For Me In The Following Area'), max_length=50, choices=REQUEST_CHOICE)
    message = models.TextField()
    is_done = models.BooleanField(default=False)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateField(auto_now=True)

    def __str__(self):
        return '{} as for prayer request on {}'.format(str(self.user.username), self.area)

    def get_absolute_url(self):
        return reverse('request-prayer')

    @property
    def hit_count(self):
        url, created = UrlHit.objects.get_or_create(url=self.get_absolute_url())
        return url.hits


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reply = models.ForeignKey('Comment', null=True, related_name="replies", on_delete=models.CASCADE)
    content = models.TextField()
    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '{} comment on {}'.format(str(self.user.username), self.post.title)


class CommentsBibleStudies(models.Model):
    biblestudies = models.ForeignKey(BibleStudies, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reply = models.ForeignKey('CommentsBibleStudies', null=True, related_name="replies", on_delete=models.CASCADE)
    content = models.TextField()
    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '{} comment on {}'.format(str(self.user.username), self.biblestudies.title)


class CommentsDevotion(models.Model):
    devotion = models.ForeignKey(Devotion, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reply = models.ForeignKey('CommentsDevotion', null=True, related_name="replies", on_delete=models.CASCADE)
    content = models.TextField()
    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '{} comment on {}'.format(str(self.user.username), self.devotion.title)


class CommentsTech(models.Model):
    tech = models.ForeignKey(Tech, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reply = models.ForeignKey('CommentsTech', null=True, related_name="replies", on_delete=models.CASCADE)
    content = models.TextField()
    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '{} comment on {}'.format(str(self.user.username), self.tect.title)


class CommentsQuotes(models.Model):
    quote = models.ForeignKey(Quotes, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reply = models.ForeignKey('CommentsQuotes', null=True, related_name="replies", on_delete=models.CASCADE)
    content = models.TextField()
    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '{} comment on {}'.format(str(self.user.username), self.quote.title)


    def total_comment(self):
        return self.content.count()


class CommentsPolicy(models.Model):
    policy = models.ForeignKey(Policy, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reply = models.ForeignKey('CommentsPolicy', null=True, related_name="replies", on_delete=models.CASCADE)
    content = models.TextField()
    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '{} comment on {}'.format(str(self.user.username), self.policy.title)
