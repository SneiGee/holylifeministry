import os
import random
from itertools import chain
from django.conf import settings
from datetime import datetime
from operator import attrgetter
from urllib.parse import urlparse, urlunparse
from django.shortcuts import render, redirect, resolve_url, get_object_or_404
from django.http import HttpResponseRedirect, QueryDict, JsonResponse
from django.template import Context, RequestContext
from django.contrib.auth import (
    get_user_model
)
from django.db.models import Q, Count
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic.base import TemplateView
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.views.generic.edit import FormView
from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from accounts.tokens import account_activation_token
from django.core.mail import EmailMultiAlternatives
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.urls import reverse_lazy, reverse
from django.utils.decorators import method_decorator
from django.utils.http import is_safe_url, urlsafe_base64_decode
from django.utils.translation import gettext_lazy as _
from django.utils.html import strip_tags
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from email.mime.image import MIMEImage
from django.contrib.staticfiles import finders

from microurl import google_mini

from django.views.decorators.http import require_POST
from .decorators import ajax_required

from django import forms
from django.forms import inlineformset_factory
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank, TrigramSimilarity

from accounts.models import User, UserRole, Profile, Connection, ROLE_CHOICE
from accounts.utils import create_action

from track.views import hit_count

from .models import (
    Post, Tags, Category, PostHistory, UserRole, STATUS_CHOICE, BibleStudies,
    Devotion, Tech, Quotes, Policy, PrayerRequest, Comment, CommentsBibleStudies, CommentsDevotion, CommentsTech, CommentsQuotes,
    CommentsPolicy,
)
from .forms import (
    UserStoryArticleForm, AddCategoryForm, BibleStudiesForm, DevotionForm, TechForm, QuotesForm, PolicyForm,
    AddPrayerRequestForm, CommentForm, BibleStudiesCommentForm, DevotionCommentForm, TechCommentForm, QuotesCommentForm,
    PolicyCommentForm, SearchForm,
)

UserModel = get_user_model()


def mail_logo_data():
    """  this fuction read/find logo image directory.  """
    with open(finders.find('images/logo_text1.png'), 'rb') as f:
        logo_data = f.read()
    logo = MIMEImage(logo_data)
    logo.add_header('Content-ID', '<logo>')
    return logo


def mail_logo_data2():
    """  this fuction read/find logo image directory.  """
    with open(finders.find('images/logo_icon1.png'), 'rb') as f:
        logo_data = f.read()
    logo_icon = MIMEImage(logo_data)
    logo_icon.add_header('Content-ID', '<logo_icon>')
    return logo_icon

def categories_tags_lists():
    categories_list = Category.objects.filter(is_active=True, post__status='Published').distinct()
    tags_list = Tags.objects.annotate(
        Num=Count('rel_posts')).filter(Num__gt=0, rel_posts__status='Published', rel_posts__category__is_active=True)[:20]
    posts = Post.objects.filter(status='Published').order_by('-updated_on')[0:3]
    return {'categories_list': categories_list, 'tags_list': tags_list, 'recent_posts': posts}


def get_user_role(user): # get user role..
    user_role = UserRole.objects.filter(user=user)
    if user_role:
        return user_role[0].role
    return 'No User Role'

def who_to_follow(self):
    know_follower = User.objects.filter(is_active=True).order_by('?').exclude(id=self.request.user.id).distinct()[:1]
    return {'know_follower': know_follower}


class TitleContextMixin:
    extra_context = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.title
        if self.extra_context is not None:
            context.update(self.extra_context)
        return context


class HolyLifeMinistryHomePageView(TitleContextMixin, ListView):
    """
    List both latest stories and both following author stories in main home page.
    """
    model = Post
    paginate_by = 4
    template_name = 'home.html'
    title = _('')
    context_object_name = 'my_authors_story'

    def get_queryset(self):
        if self.request.user.is_authenticated: # check if user is authenticated then
            # list authenticate use following authors ...
            self.following_ids = self.request.user.following.values_list('id', flat=True).distinct()
            self.user = self.request.user.id

            if self.following_ids:
                # retreive follwoing stories
                self.authors_stories = Post.objects.filter(
                    Q(user=self.user) | Q(user_id__in=self.following_ids), status='Published', category__is_active=True
                ).annotate(total_post_comments=Count('comment')).order_by('-created_on')
            else:
                # if author have no followers....
                self.union_biblestudies_story = BibleStudies.objects.filter(is_active=True).annotate(
                    total_post_comments=Count('commentsbiblestudies')
                ).order_by('?')
                self.union_devotion_story = Devotion.objects.filter(is_active=True).annotate(total_post_comments=Count('commentsdevotion')).order_by('?')
                self.union_tech_story = Tech.objects.filter(is_active=True).annotate(total_post_comments=Count('commentstech')).order_by('?')
                self.union_authors_stories = Post.objects.all().filter(status='Published', category__is_active=True)\
                .annotate(total_post_comments=Count('comment')).order_by('?')
                self.authors_stories = list(sorted(
                    chain(self.union_authors_stories, self.union_devotion_story, self.union_tech_story, self.union_biblestudies_story), key=lambda objects: objects.updated_on, reverse=True)
                )
        else:
            # if user/author is not authenticated....
            self.union_biblestudies_story = BibleStudies.objects.filter(is_active=True).annotate(
                total_post_comments=Count('commentsbiblestudies')
            ).order_by('?')
            self.union_devotion_story = Devotion.objects.filter(is_active=True).annotate(total_post_comments=Count('commentsdevotion')).order_by('?')
            self.union_tech_story = Tech.objects.filter(is_active=True).annotate(total_post_comments=Count('commentstech')).order_by('?')
            self.union_authors_story = Post.objects.all().filter(status='Published', category__is_active=True)\
            .annotate(total_post_comments=Count('comment')).order_by('?')
            self.authors_stories = list(sorted(
                chain(self.union_authors_story, self.union_biblestudies_story, self.union_devotion_story, self.union_tech_story), key=lambda objects: objects.updated_on, reverse=True)
            )
        return self.authors_stories

    def get_context_data(self, *args, **kwargs):
        context = super(HolyLifeMinistryHomePageView, self).get_context_data(*args, **kwargs)
        # Home Center:: sort and chain stories on Post, devotion, Tech, biblestudies on slide middle or center page..
        self.union_devotion = Devotion.objects.filter(is_active=True).annotate(total_post_comments=Count('commentsdevotion')).order_by('?').distinct()[:1]
        self.union_biblestudies = BibleStudies.objects.filter(is_active=True).annotate(total_post_comments=Count('commentsbiblestudies')).order_by('?').distinct()[:1]
        self.union_tech = Tech.objects.filter(is_active=True).annotate(total_post_comments=Count('commentstech')).order_by('?').distinct()[:1]
        self.union_quote = Quotes.objects.filter(is_active=True).annotate(total_post_comments=Count('commentsquotes')).order_by('?').distinct()[:1]
        self.slide = Post.objects.all().filter(
            status='Published', category__is_active=True
        ).annotate(total_post_comments=Count('comment')).order_by('-created_on').distinct()[:4]
        self.slide_story = list(sorted(
            chain(self.union_devotion, self.slide, self.union_biblestudies, self.union_tech,self.union_quote),key=lambda objects: objects.created_on, reverse=True)
        )
        # Home Right:: Show only latest stories on tech and quotes
        self.union_latest_tech_story = Tech.objects.filter(is_active=True).annotate(total_post_comments=Count('commentstech')).distinct()[:1]
        self.union_latest_quote_story = Quotes.objects.filter(is_active=True).annotate(total_post_comments=Count('commentsquotes')).distinct()[:1]
        self.home_right_stories = list(sorted( # merge queryset
            chain(self.union_latest_tech_story, self.union_latest_quote_story),
            key=lambda objects: objects.created_on, reverse=True)
        )
        # self.home_right_stories = self._home_right_stories.distinct().order_by('-created_on')[:1]
        # Home Left:: Show only latest stories on bible studies and devotion ....
        self.union_latest_biblestudies_story = BibleStudies.objects.filter(is_active=True).annotate(total_post_comments=Count('commentsbiblestudies')).order_by('-created_on').distinct()[:1]
        self.union_latest_devotion_story = Devotion.objects.filter(is_active=True).annotate(total_post_comments=Count('commentsdevotion')).order_by('-created_on').distinct()[:1]
        self.home_left_stories = list(sorted(
            chain(self.union_latest_biblestudies_story, self.union_latest_devotion_story),
            key=lambda objects: objects.created_on, reverse=True)
        )
        context['slide_story'] = self.slide_story
        context['home_right_stories'] = self.home_right_stories
        context['home_left_stories'] = self.home_left_stories
        return context


class ChristianbaseUserPostDetailView(TitleContextMixin, DetailView):
    """
    Display the user story detail -- Story Detail.
    """
    model = Post
    template_name = 'story/new_story_view.html'
    form_class = CommentForm
    title = _('Story detail')
    slug_url_kwarg = "slug"
    context_object_name = 'user_post'
    # set to True to count the hit

    def get_queryset(self):
        return Post.objects.annotate(total_post_comments=Count('comment'))

    def get_mini_url(self, request):
        url = request.build_absolute_uri()
        try:
            api_key = os.getenv('API_KEY')
            url = google_mini(url, api_key)
        except Exception:
            pass
        return url

    def get_context_data(self, *args, **kwargs):
        context = super(ChristianbaseUserPostDetailView, self).get_context_data(*args, **kwargs)
        user = self.object.user
        author = user.first_name if user.first_name else user.username
        related_storys = Post.objects.filter(
            status='Published',
            category=self.object.category,
            tags__in=self.object.tags.all(),
        ).annotate(total_post_comments=Count('comment')).exclude(id=self.object.id).distinct()[:3]
        context.update(
            who_to_follow(self)
        ),
        user_like = Post.objects.filter(id=self.object.id, likes=self.request.user.id)
        user_favourite = Post.objects.filter(id=self.object.id, favourite=self.request.user.id)
        comments = Comment.objects.filter(post=self.object.pk).order_by('-created_on')
        # increment total image views by 1
        # total_views =

        is_liked = False
        is_favorite = False

        comment_form = CommentForm

        if self.request.user.is_authenticated and user_like.exists():
            is_liked = True

        if self.request.user.is_authenticated and user_favourite.exists():
            is_favorite = True

        context.update({
            "related_storys": related_storys,
            "author": author,
            "short_url": self.get_mini_url(self.request),
            'user_like': user_like,
            'is_liked': is_liked,
            'is_favorite': is_favorite,
            'comments': comments,
            'comment_form': comment_form,
        })
        context.update(categories_tags_lists())
        return context


@login_required
def user_comment(request, id):
    # post_id = request.POST.get('id')
    post = get_object_or_404(Post, id=id)
    user = User.objects.get(username=post.user.username)
    comments = Comment.objects.filter(post=post, reply=None).order_by('-id')
    if request.method == 'POST':
        comment_form = CommentForm(request.POST or None)
        if comment_form.is_valid():
            content = request.POST.get('content')
            comment = Comment.objects.create(post=post, user=request.user, content=content)
            comment.save()
            return HttpResponseRedirect(post.get_absolute_url())
    else:
        comment_form = CommentForm()

    context = {
        'post': post,
        'comments': comments,
        'comment_form': comment_form,
    }
    if request.is_ajax():
        html = render_to_string('comments/comments.html', context, request=request)
        return JsonResponse({'form': html})


@login_required
def like_post(request):
    """
    THis fucntion take the action of users liked / unliked story ..
    """
    post_id = request.POST.get('id')
    user_post = Post.objects.get(id=post_id)
    is_liked = False
    if user_post.likes.filter(id=request.user.id).exists():
        user_post.likes.remove(request.user)
        is_liked = False
    else:
        user_post.likes.add(request.user)
        is_liked = True
        create_action(request.user, 'liked', user_post)
    # return HttpResponseRedirect(pos.get_absolute_url())
    context = {
        'user_post': user_post,
        'is_liked': is_liked,
        'total_likes': user_post.total_likes(),
    }
    if request.is_ajax():
        html = render_to_string('liked/like_section.html', context, request=request)
        return JsonResponse({'form': html})


@method_decorator(login_required, name='dispatch')
class ChristianbaseMakeStoryArchiveView(View):
    """
    Archive / Drafted user story
    """

    def get(self, request, *args, **kwargs):
        # user = User.objects.get(username=request.user)
        self.make_archive = Post.objects.get(
            slug=self.kwargs.get('slug')
        )
        self.previous_status = self.make_archive.status
        if self.request.user.is_active:
            self.make_archive.status = "Drafted"
            self.make_archive.save()
            self.make_archive.create_activity(
                user=request.user,
                content="moved to draft from " + str(self.previous_status)
            )
            messages.success(
                request,
                'Story "' + str(self.make_archive.title) + '" has been moved to draft.'
            )
            return HttpResponseRedirect(reverse_lazy('christianbase_archive_stories'))


@method_decorator(login_required, name="dispatch")
class ChristianbaseUserStoryArticleView(TitleContextMixin, CreateView):
    """
    Display the create new story form and handle the story create action.
    """
    model = Post
    form_class = UserStoryArticleForm
    template_name = "story/new_story.html"
    context_object_name = 'story'
    title = _('New story')

    # def get_success_url(self):
    #     return reverse_lazy('christianbase_story_detail', kwargs=dict(slug=self.object.slug))

    def get_form_kwargs(self):
        kwargs = super(ChristianbaseUserStoryArticleView, self).get_form_kwargs()
        kwargs.update({'user': self.request.user})
        role = get_user_role(self.request.user)
        role = role if role in dict(ROLE_CHOICE).keys() else None
        kwargs["user_role"] = role
        return kwargs

    def form_valid(self, form):
        self.blog_story = form.save(commit=False)
        self.blog_story.user = self.request.user
        # if self.request.user.is_superuser or get_user_role(self.request.user) == 'Admin' or get_user_role(self.request.user) == 'Author':
        self.blog_story.status = "Published"
        self.blog_story.save()
        if self.request.POST.get('tags', ''):
            splitted = self.request.POST.get('tags').split(',')
            for s in splitted:
                story_tags = Tags.objects.filter(name__iexact=s.strip())
                if story_tags:
                    story_tag = story_tags.first()
                else:
                    story_tag = Tags.objects.create(name=s.strip())
                self.blog_story.tags.add(story_tag)

        self.blog_story.create_activity(user=self.request.user, content="added")
        # send story / articel to author via mail..
        if self.request.user:
            self.myDate = datetime.now()
            self.current_site = get_current_site(self.request)
            self.user = self.request.user
            self.slug = self.blog_story.slug
            self.story_code = self.blog_story.story_code
            self.author_name = self.user.first_name + ' ' + self.user.last_name if self.user.first_name else self.user.email
            self.story_title = form.cleaned_data.get('title')
            self.story_content = form.cleaned_data.get('content')
            self.mail_subject = 'You Just Published "' + str(self.story_title) + '" on Holy Life Ministry'
            self.to_email = self.request.user.email  # get user email
            html_content = render_to_string('email_messages/new_story/new_story_to_author.html', {
                'user': self.user.username,
                'domain': self.current_site.domain,
                'myDate': self.myDate,
                'blog_story': self.blog_story,
                'author_name': self.author_name,
                'story_title': self.story_title,
                'story_content': self.story_content,
                'slug': self.slug,
                'story_code': self.story_code,
            })
            resend_email = EmailMultiAlternatives(
                self.mail_subject, to=[self.to_email]
            )
            image = MIMEImage(self.blog_story.featured_image.read())
            image.add_header('Content-ID','<{}>'.format(self.blog_story.image_file))
            resend_email.attach_alternative(html_content, "text/html")
            resend_email.attach(image)
            resend_email.send(fail_silently=False)
        # if author has followers. ...
        self.followers_id = [self.user for self.user in self.request.user.followers.all()]
        if self.followers_id:
            self.myDate = datetime.now()
            self.current_site = get_current_site(self.request)
            self.user = self.request.user
            self.slug = self.blog_story.slug
            self.story_code = self.blog_story.story_code
            self.author_name = self.user.first_name + ' ' + self.user.last_name if self.user.first_name else self.user.email
            self.author_story_title = form.cleaned_data.get('title')
            self.author_story_content = form.cleaned_data.get('content')
            self.mail_subject = str(self.author_name) + ' published a new article'
            # author_image = MIMEImage(self.user.profile.image.read()) #find author profile photo..
            # author_image.add_header('Content-ID','<{}>'.format(self.user.profile.author_profile))
            # loop throught all the followers
            for self.followers_detail in self.followers_id:
                self.followers_name = self.followers_detail.first_name + ' ' + self.followers_detail.last_name if self.followers_detail.first_name else self.followers_detail.email
                self.followers_email = self.followers_detail.email  # get followers user email
                # followers_image = MIMEImage(self.followers_detail.profile.image.read())
                # followers_image.add_header('Content-ID','<{}>'.format(self.followers_detail.profile.author_profile))
                html_content = render_to_string('email_messages/new_story/new_story_to_followers.html', {
                    'user': self.user,
                    'domain': self.current_site.domain,
                    'myDate': self.myDate,
                    'author_username': self.user.username,
                    'author_name': self.author_name,
                    'author_story_title': self.author_story_title,
                    'author_story_content': self.author_story_content,
                    'slug': self.slug,
                    'story_code': self.story_code,
                    'followers_username': self.followers_detail.username,
                    'followers_name': self.followers_name,
                    'followers_detail': self.followers_detail,
                })
                resend_email = EmailMultiAlternatives(
                    self.mail_subject, to=[self.followers_email]
                )
                resend_email.attach_alternative(html_content, "text/html")
                # resend_email.attach(author_image)
                # resend_email.attach(followers_image)
                resend_email.send(fail_silently=False)
        messages.success(self.request, 'Great! Your story is published.')
        # data = {'error': False, 'response': 'Great! Your story is published.',
        #         'title': self.request.POST['title']}
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(ChristianbaseUserStoryArticleView, self).get_context_data(**kwargs)
        tags_list = Tags.objects.all()
        # user = self.request.user
        context['status_choices'] = STATUS_CHOICE
        context['tags_list'] = tags_list
        context['add_blog'] = True
        return context


@method_decorator(login_required, name="dispatch")
class ChristianbaseUpdateUserStoryArticleView(TitleContextMixin, UserPassesTestMixin, UpdateView):
    """
    Display the update new story form and handle the story update action.
    """
    model = Post
    form_class = UserStoryArticleForm
    template_name = "story/new_story.html"
    context_object_name = 'story'
    title = _('Update story')

    def get_form_kwargs(self):
        kwargs = super(ChristianbaseUpdateUserStoryArticleView, self).get_form_kwargs()
        kwargs.update({'user': self.request.user})
        role = get_user_role(self.request.user)
        role = role if role in dict(ROLE_CHOICE).keys() else None
        kwargs["user_role"] = role
        return kwargs

    def form_valid(self, form):
        previous_content = self.get_object().content
        self.update_story = form.save(commit=False)
        self.update_story.user = self.request.user
        self.update_story.updated_on = timezone.now()
        self.update_story.save()
        if self.request.POST.get('tags', ''):
            self.update_story.tags.clear()
            splitted = self.request.POST.get('tags').split(',')
            for s in splitted:
                story_tags = Tags.objects.filter(name__iexact=s.strip())
                if story_tags:
                    story_tag = story_tags.first()
                else:
                    story_tag = Tags.objects.create(name=s.strip())
                self.update_story.tags.add(story_tag)
        if previous_content != self.update_story.content:
            self.update_story.create_activity(
                user=self.request.user, content=previous_content)
        messages.success(self.request, 'Great! Your story is updated.!!!')
        # data = {'error': False, 'response': 'Great! Your story is updated.',
        #         'title': self.request.POST['title']}
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(ChristianbaseUpdateUserStoryArticleView, self).get_context_data(**kwargs)
        context['status_choices'] = STATUS_CHOICE
        return context

    def test_func(self):
        self.story = self.get_object()
        if self.request.user == self.story.user:
            return True
        else:
            False


@method_decorator(login_required, name='dispatch')
class ChristianbaseUserStoriesView(TitleContextMixin, ListView):
    """
    Display the user stories
    """
    model = Post
    paginate_by = 4
    template_name = "story/all_user_story.html"
    context_object_name = 'user_stories'
    title = _('My stories')

    def get_queryset(self):
        self.user = self.request.user
        if get_user_role(self.user) == "Author" or get_user_role(self.user) == "Admin":
            user_story = Post.objects.filter(status='Published', category__is_active=True, user=self.user).annotate(total_post_comments=Count('comment')).order_by('-created_on')
        elif get_user_role(self.user) == "BS P":
            user_story = BibleStudies.objects.filter(user=self.user, is_active=True).annotate(total_post_comments=Count('commentsbiblestudies')).order_by('-created_on')
        elif get_user_role(self.user) == "Devotion P":
            user_story = Devotion.objects.filter(user=self.user, is_active=True).annotate(total_post_comments=Count('commentsdevotion')).order_by('-created_on')
        elif get_user_role(self.user) == "Tech P":
            user_story = Tech.objects.filter(user=self.user, is_active=True).annotate(total_post_comments=Count('commentstech')).order_by('-created_on')
        elif get_user_role(self.user) == 'Quotes P':
            user_story = Quotes.objects.filter(user=self.user, is_active=True).annotate(total_post_comments=Count('commentsquotes')).order_by('-created_on')
        else:
            user_story = Policy.objects.filter(user=self.user, is_active=True).annotate(total_post_comments=Count('commentspolicy')).order_by('-created_on')
        return user_story

    def get_context_data(self, *args, **kwargs):
        context = super(ChristianbaseUserStoriesView, self).get_context_data(*args, **kwargs)
        user_total_post = Post.objects.filter(user=self.request.user).count()
        context['user_total_post'] = user_total_post
        return context


@method_decorator(login_required, name='dispatch')
class ChristianbaseArchiveStoryView(TitleContextMixin, ListView):
    """
    Display the all user archive story
    """
    model = Post
    paginate_by = 4
    template_name = "story/user_archive_story.html"
    context_object_name = 'story_archive'
    title = _('Archive stories')

    def get_queryset(self):
        self.user = self.request.user
        if get_user_role(self.user) == "Author" or get_user_role(self.user) == "Admin":
            archive = Post.objects.filter(status='Drafted', category__is_active=True, user=self.user).annotate(total_post_comments=Count('comment')).order_by('-updated_on')
        elif get_user_role(self.user) == "BS P":
            archive = BibleStudies.objects.filter(user=self.user, is_active=False).annotate(total_post_comments=Count('commentsbiblestudies')).order_by('-updated_on')
        elif get_user_role(self.user) == "Devotion P":
            archive = Devotion.objects.filter(user=self.user, is_active=False).annotate(total_post_comments=Count('commentsdevotion')).order_by('-updated_on')
        elif get_user_role(self.user) == "Tech P":
            archive = Tech.objects.filter(user=self.user, is_active=False).annotate(total_post_comments=Count('commentstech')).order_by('-updated_on')
        elif get_user_role(self.user) == "Quotes P":
            archive = Quotes.objects.filter(user=self.user, is_active=False).annotate(total_post_comments=Count('commentsquotes')).order_by('-updated_on')
        else:
            archive = Policy.objects.filter(user=self.user, is_active=False).annotate(total_post_comments=Count('commentspolicy')).order_by('-updated_on')
        return archive

    def get_context_data(self, *args, **kwargs):
        context = super(ChristianbaseArchiveStoryView, self).get_context_data(*args, **kwargs)
        context.update(categories_tags_lists())
        user_total_post = Post.objects.filter(user=self.request.user).count()
        context['user_total_post'] = user_total_post
        return context


@method_decorator(login_required, name='dispatch')
class ChristianbaseUnArchiveStoryView(View):
    """
    Remove or Un-Archive and make user story public
    """

    def get(self, request, *args, **kwargs):
        self.story_archive = get_object_or_404(
            Post, slug=self.kwargs.get('slug')
        )
        self.previous_status = self.story_archive.status
        if self.request.user.is_active:
            self.story_archive.status = "Published"
            self.story_archive.save()
            self.story_archive.create_activity(
                user=request.user,
                content="restored from draft to " + str(self.previous_status)
            )
            messages.success(
                request,
                'Your Story: "' + str(self.story_archive.title) + '" has been restored from draft..'
            )
            return HttpResponseRedirect(reverse_lazy('christianbase_archive_stories'))


@method_decorator(login_required, name='dispatch')
class ChristianbaseDeleteStoryView(View):
    """
    This function delete user story ...
    """

    def get(self, request, *args, **kwargs):
        self.story_trash = get_object_or_404(
            Post, slug=self.kwargs.get('slug')
        )
        self.previous_status = self.story_trash.status
        if self.request.user.is_active:
            self.story_trash.status = "Trashed"
            self.story_trash.save()
            self.story_trash.create_activity(
                user=request.user,
                content="moved to trash from " + str(self.previous_status)
            )
            messages.success(
                request,
                'Your Story: "' + str(self.story_trash.title) + '" has been moved to trash..'
            )
            return HttpResponseRedirect(reverse_lazy('christianbase_trash_stories'))


@method_decorator(login_required, name='dispatch')
class ChristianbaseTrashStoryView(TitleContextMixin, ListView):
    """
    Display the user trash story
    """
    model = Post
    paginate_by = 4
    template_name = "story/user_trash_story.html"
    context_object_name = 'trash_story'
    title = _('Trash stories')

    def get_queryset(self):
        user = self.request.user
        return Post.objects.filter(status='Trashed', category__is_active=True, user=user).annotate(total_post_comments=Count('comment')).order_by('-created_on')

    def get_context_data(self, *args, **kwargs):
        context = super(ChristianbaseTrashStoryView, self).get_context_data(*args, **kwargs)
        context.update(categories_tags_lists())
        user_total_post = Post.objects.filter(user=self.request.user).count()
        context['user_total_post'] = user_total_post
        return context


@method_decorator(login_required, name='dispatch')
class ChristianbaseRestoredStoryView(View):
    """
    This function restored user story ...
    """

    def get(self, request, *args, **kwargs):
        self.story_restore = get_object_or_404(
            Post, slug=self.kwargs.get('slug')
        )
        self.previous_status = self.story_restore.status
        if self.request.user.is_active:
            self.story_restore.status = "Drafted"
            self.story_restore.save()
            self.story_restore.create_activity(
                user=request.user,
                content="restored from trash to " + str(self.previous_status)
            )
            messages.success(
                request,
                'Your Story: "' + str(self.story_restore.title) + '" has been restored from trash..'
            )
            return HttpResponseRedirect(reverse_lazy('christianbase_archive_stories'))


@method_decorator(login_required, name='dispatch')
class ChristianbasePermenantDeleteStoryView(View):
    """
    This function permenantly delete user story ...
    """

    def get(self, request, *args, **kwargs):
        self.story_delete = get_object_or_404(
            Post, slug=self.kwargs.get('slug')
        )
        if self.request.user.is_active:
            self.story_delete.delete()
            messages.success(
                request,
                'Your Story is permenantly delete!.'
            )
            return HttpResponseRedirect(reverse_lazy('christianbase_trash_stories'))


@method_decorator(login_required, name="dispatch")
class AddUserCategoryView(TitleContextMixin, CreateView):
    """
    Display the create new topic / category form and handle the topic action.
    """
    model = Category
    form_class = AddCategoryForm
    template_name = "category/add_category.html"
    success_url = reverse_lazy('christianbase_add_category')
    title = _('Add Topic or Category')

    def form_valid(self, form):
        # self.user = User.objects.filter(user=self.request.user)
        self.add_category = form.save(commit=False)
        self.add_category.user = self.request.user
        self.add_category.save()
        messages.success(self.request, 'Topic / Category added successfully..!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(AddUserCategoryView, self).get_context_data(**kwargs)
        context['add_category'] = True
        return context


@method_decorator(login_required, name="dispatch")
class UpdateUserCategoryForm(TitleContextMixin, UserPassesTestMixin, UpdateView):
    """
    Display the update topic / categoris and handle the form action
    """
    model = Category
    form_class = AddCategoryForm
    template_name = "category/add_category.html"
    success_url = reverse_lazy('christianbase_add_category')
    title = _('Update Topic or Category')

    def form_valid(self, form):
        self.update_category = form.save(commit=False)
        self.update_category.user = self.request.user
        self.update_category.save()
        messages.success(self.request, 'Topic / Category Update successfully..!')
        return super().form_valid(form)

    def test_func(self):
        story = self.get_object()
        if self.request.user == story.user:
            return True
        else:
            return False


class ChristianbaseSelectedCategoryView(ListView):
    template_name = "story/category/topic_stories.html"
    paginate_by = 4
    context_object_name = "category_story"
    title = _('Category story')

    def get_queryset(self):
        self.category = get_object_or_404(Category, slug=self.kwargs.get("slug"))
        return Post.objects.annotate(total_post_comments=Count('comment')).filter(category=self.category, category__is_active=True, status='Published')

    def get_context_data(self, *args, **kwargs):
        context = super(ChristianbaseSelectedCategoryView, self).get_context_data(*args, **kwargs)
        user = self.category.user
        author = user.first_name if user.first_name else user.username
        context.update({
            "author": author,
            "category": self.category,
        })
        context.update(categories_tags_lists())
        return context


@method_decorator(login_required, name="dispatch")
class ChristianbaseBookmarkStoriesView(TitleContextMixin, ListView):
    """
    List user bookmarks stories
    """
    template_name = "story/bookmarks/bookmark_story.html"
    paginate_by = 4
    context_object_name = 'bookmark_story'
    title = _('Bookmarks stories')

    def get_queryset(self):
        user = self.request.user
        favourite = Post.objects.filter(favourite=user).annotate(total_post_comments=Count('comment'))
        bookmarks = Policy.objects.filter(bookmarks=user).annotate(total_post_comments=Count('commentspolicy'))
        story = sorted(chain(favourite, bookmarks), key=lambda objects: objects.created_on, reverse=True)
        all_story = story
        return all_story


@login_required
def christianbase_add_user_bookmarks(request):
    """
    Allow User to add stories to bookmarks...
    """
    story_id = request.POST.get('id')
    story = Post.objects.get(id=story_id)
    is_favorite = False
    if story.favourite.filter(id=request.user.id).exists():
        story.favourite.remove(request.user)
        is_favorite = False
    else:
        story.favourite.add(request.user)
        is_favorite = True

    context = {
        'is_favorite': is_favorite,
        'story': story,
    }

    if request.is_ajax():
        html = render_to_string('story/bookmarks/bookmark_section.html', context, request=request)
        return JsonResponse({'form': html})


class HolyLifeMinistryBibleStudiesView(TitleContextMixin, ListView):
    """
    List all bible studies psots
    """
    model = BibleStudies
    paginate_by = 4
    template_name = "bible_studies.html"
    context_object_name = 'bible_studies'
    title = _('Bible Studies')

    def get_queryset(self):
        return BibleStudies.objects.filter(is_active=True).annotate(total_comments=Count('commentsbiblestudies')).order_by('-created_on')

    def get_context_data(self, *args, **kwargs):
        context = super(HolyLifeMinistryBibleStudiesView, self).get_context_data(*args, **kwargs)
        context.update(categories_tags_lists())
        return context


class HolyLifeMinistryBibleStudiesDetailView(TitleContextMixin, DetailView):
    """
    Display the detail view of bible studies
    """
    model = BibleStudies
    template_name = "bible-studies/bible_studies_detail.html"
    context_object_name = 'bible_studies'
    title = _('Bible studies')

    def get_context_data(self, *args, **kwargs):
        context = super(HolyLifeMinistryBibleStudiesDetailView, self).get_context_data(*args, **kwargs)
        bible_like = BibleStudies.objects.filter(id=self.object.id, bible_likes=self.request.user.id)
        comments = CommentsBibleStudies.objects.filter(biblestudies=self.object.id).order_by('-created_on')

        is_liked = False

        if self.request.user.is_authenticated and bible_like.exists():
            is_liked = True

        comment_form = BibleStudiesCommentForm()

        context.update({
            "bible_like": bible_like,
            "is_liked": is_liked,
            "comment_form": comment_form,
            "comments": comments,
        })
        context.update(categories_tags_lists())
        return context


@login_required
def bible_studies_comment(request, id):
    #  This function allow users comments on biblestudies articles..
    post = get_object_or_404(BibleStudies, id=id)
    user = User.objects.get(username=post.user.username)
    comments = CommentsBibleStudies.objects.filter(biblestudies=post, reply=None).order_by('-id')
    if request.method == 'POST':
        comment_form = BibleStudiesCommentForm(request.POST or None)
        if comment_form.is_valid():
            content = request.POST.get('content')
            comment = CommentsBibleStudies.objects.create(biblestudies=post, user=request.user, content=content)
            comment.save()
            return HttpResponseRedirect(post.get_absolute_url())
    else:
        comment_form = BibleStudiesCommentForm()

    context = {
        'post': post,
        'comments': comments,
        'comment_form': comment_form,
    }
    if request.is_ajax():
        html = render_to_string('comments/bible_studies_comments.html', context, request=request)
        return JsonResponse({'form': html})


@method_decorator(login_required, name='dispatch')
class MakeBibleStudiesArchiveView(View):
    """
    Archive / Drafted Bible Studies story
    """

    def get(self, request, *args, **kwargs):
        # user = User.objects.get(username=request.user)
        self.make_archive = BibleStudies.objects.get(
            slug=self.kwargs.get('slug')
        )
        if get_user_role(self.request.user) == 'BS P':
            self.make_archive.is_active = False
            self.make_archive.save()
            messages.success(
                request,
                'Story: "' + str(self.make_archive.title) + '" has been moved to draft.'
            )
            return HttpResponseRedirect(reverse_lazy('christianbase_archive_stories'))


@method_decorator(login_required, name='dispatch')
class UnArchiveBibleStudiesView(View):
    """
    Un-Archive or remover Bible Studies story from archive ( private mood-- )
    """

    def get(self, request, *args, **kwargs):
        # user = User.objects.get(username=request.user)
        self.make_archive = BibleStudies.objects.get(
            slug=self.kwargs.get('slug')
        )
        if get_user_role(self.request.user) == 'BS P':
            self.make_archive.is_active = True
            self.make_archive.save()
            messages.success(
                request,
                'Your Story: "' + str(self.make_archive.title) + '" has been restored from draft...'
            )
            return HttpResponseRedirect(reverse_lazy('christianbase_archive_stories'))


@method_decorator(login_required, name="dispatch")
class HolyLifeMinistryAddBibleStudiesView(TitleContextMixin, CreateView):
    """
    Display the create new bible studies form
    """
    model = BibleStudies
    form_class = BibleStudiesForm
    template_name = "bible-studies/bible_studies_edit.html"
    context_object_name = 'bible_studies'
    title = _('Add New Bible Studies')

    def form_valid(self, form):
        # self.user = User.objects.filter(user=self.request.user)
        self.add_biblestudies = form.save(commit=False)
        if get_user_role(self.request.user) == 'BS P':
            self.add_biblestudies.user = self.request.user
            self.add_biblestudies.is_active = True
            self.add_biblestudies.save()
            # if publisher has followers. ...
            self.followers_id = [self.user for self.user in self.request.user.followers.all()]
            if self.followers_id:
                self.myDate = datetime.now()
                self.current_site = get_current_site(self.request)
                self.user = self.request.user
                self.slug = self.add_biblestudies.slug
                self.author_name = self.user.first_name + ' ' + self.user.last_name if self.user.first_name else self.user.email
                self.author_story_title = form.cleaned_data.get('title')
                self.author_story_content = form.cleaned_data.get('content')
                self.base_name = 'BIBLE STUDIES!'
                self.mail_subject = str(self.base_name) + ' - "' + str(self.author_story_title) + '"!'
                image = MIMEImage(self.add_biblestudies.featured_image.read())
                image.add_header('Content-ID','<{}>'.format(self.add_biblestudies.image_file))
                # loop throught all the followers
                for self.followers_detail in self.followers_id:
                    self.followers_email = self.followers_detail.email  # get followers user email
                    html_content = render_to_string('email_messages/new_story/new_bible_studies_to_followers.html', {
                        'user': self.user,
                        'domain': self.current_site.domain,
                        'myDate': self.myDate,
                        'add_biblestudies': self.add_biblestudies,
                        'author_username': self.user.username,
                        'author_name': self.author_name,
                        'author_story_title': self.author_story_title,
                        'author_story_content': self.author_story_content,
                        'base_name': self.base_name,
                        'slug': self.slug,
                        'followers_username': self.followers_detail.username,
                        'followers_detail': self.followers_detail,
                    })
                    resend_email = EmailMultiAlternatives(
                        self.mail_subject, to=[self.followers_email]
                    )
                    resend_email.attach_alternative(html_content, "text/html")
                    resend_email.attach(image)
                    resend_email.send(fail_silently=False)
            messages.success(self.request, 'Great! Your story is published.')
            return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(HolyLifeMinistryAddBibleStudiesView, self).get_context_data(**kwargs)
        context['add_biblestudies'] = True
        return context


@method_decorator(login_required, name="dispatch")
class HolyLifeMinistryBibleStudiesUpdateView(TitleContextMixin, UserPassesTestMixin, UpdateView):
    """
    This function allow self.author user to update bible studies.. Admin....
    """
    model = BibleStudies
    template_name = "bible-studies/bible_studies_edit.html"
    form_class = BibleStudiesForm
    context_object_name = 'bible_studies'
    title = _('Edit')

    def form_valid(self, form):
        self.update_story = form.save(commit=False)
        self.update_story.user = self.request.user
        self.update_story.updated_on = timezone.now()
        self.update_story.save()
        messages.success(self.request, 'Great! Your story is updated.!!!')
        # data = {'error': False, 'response': 'Great! Your story is updated.',
        #         'title': self.request.POST['title']}
        return super().form_valid(form)

    def test_func(self):
        biblestudies = self.get_object()
        if self.request.user == biblestudies.user:
            return True
        return False


@login_required
def biblestudies_like_post(request):
    """
    THis fucntion take the action of users liked / unliked bible studies story ..
    """
    post_id = request.POST.get('id')
    bible_studies = BibleStudies.objects.get(id=post_id)
    is_liked = False
    if bible_studies.bible_likes.filter(id=request.user.id).exists():
        bible_studies.bible_likes.remove(request.user)
        is_liked = False
    else:
        bible_studies.bible_likes.add(request.user)
        is_liked = True
        create_action(request.user, 'liked', bible_studies)
    # return HttpResponseRedirect(pos.get_absolute_url())
    context = {
        'bible_studies': bible_studies,
        'is_liked': is_liked,
        'total_likes': bible_studies.total_likes(),
    }
    if request.is_ajax():
        html = render_to_string('liked/bible_like_section.html', context, request=request)
        return JsonResponse({'form': html})


class HolyLifeMinistryDevotionView(TitleContextMixin, ListView):
    """
    List all devotion psots
    """
    model = Devotion
    paginate_by = 4
    template_name = "devotion.html"
    context_object_name = 'devotions'
    title = _('Devotion')

    def get_queryset(self):
        return Devotion.objects.filter(is_active=True).annotate(total_comments=Count('commentsdevotion')).order_by('-created_on')

    def get_context_data(self, *args, **kwargs):
        context = super(HolyLifeMinistryDevotionView, self).get_context_data(*args, **kwargs)
        context.update(categories_tags_lists())
        return context


class HolyLifeMinistryDevotionDetailView(TitleContextMixin, DetailView):
    """
    Display the detail view of devotion
    """
    model = Devotion
    template_name = "devotion/devotion_detail.html"
    context_object_name = 'devotions'
    title = _('Devotion')

    def get_context_data(self, *args, **kwargs):
        context = super(HolyLifeMinistryDevotionDetailView, self).get_context_data(*args, **kwargs)
        devotion_like = Devotion.objects.filter(id=self.object.id, devotion_likes=self.request.user.id)
        comments = CommentsDevotion.objects.filter(devotion=self.object.id).order_by('-created_on')

        is_liked = False

        if self.request.user.is_authenticated and devotion_like.exists():
            is_liked = True

        comment_form = DevotionCommentForm()

        context.update({
            "devotion_like": devotion_like,
            "is_liked": is_liked,
            "comments": comments,
            "comment_form": comment_form,
        })
        context.update(categories_tags_lists())
        return context


@login_required
def devotion_comment(request, id):
    #  This function allow users comments on devotion articles..
    post = get_object_or_404(Devotion, id=id)
    user = User.objects.get(username=post.user.username)
    comments = CommentsDevotion.objects.filter(devotion=post, reply=None).order_by('-id')
    if request.method == 'POST':
        comment_form = DevotionCommentForm(request.POST or None)
        if comment_form.is_valid():
            content = request.POST.get('content')
            comment = CommentsDevotion.objects.create(devotion=post, user=request.user, content=content)
            comment.save()
            return HttpResponseRedirect(post.get_absolute_url())
    else:
        comment_form = DevotionCommentForm()

    context = {
        'post': post,
        'comments': comments,
        'comment_form': comment_form,
    }
    if request.is_ajax():
        html = render_to_string('comments/devotion_comments.html', context, request=request)
        return JsonResponse({'form': html})


@method_decorator(login_required, name='dispatch')
class MakeDevotionArchiveView(View):
    """
    Archive / Drafted Devotion story
    """

    def get(self, request, *args, **kwargs):
        # user = User.objects.get(username=request.user)
        self.make_archive = Devotion.objects.get(
            slug=self.kwargs.get('slug')
        )
        if get_user_role(self.request.user) == 'Devotion P':
            self.make_archive.is_active = False
            self.make_archive.save()
            messages.success(
                request,
                'Story: "' + str(self.make_archive.title) + '" has been moved to draft.'
            )
            return HttpResponseRedirect(reverse_lazy('christianbase_archive_stories'))


@method_decorator(login_required, name='dispatch')
class UnArchiveDevotionView(View):
    """
    Un-Archive or remover Devotion story from archive ( private mood-- )
    """

    def get(self, request, *args, **kwargs):
        # user = User.objects.get(username=request.user)
        self.make_archive = Devotion.objects.get(
            slug=self.kwargs.get('slug')
        )
        if get_user_role(self.request.user) == 'Devotion P':
            self.make_archive.is_active = True
            self.make_archive.save()
            messages.success(
                    request,
                'Your Story: "' + str(self.make_archive.title) + '" has been restored from draft...'
            )
            return HttpResponseRedirect(reverse_lazy('christianbase_archive_stories'))


@method_decorator(login_required, name="dispatch")
class HolyLifeMinistryAddDevotionView(TitleContextMixin, CreateView):
    """
    Display the create new devotion form
    """
    model = Devotion
    form_class = DevotionForm
    template_name = "devotion/devotion_edit.html"
    context_object_name = 'devotions'
    title = _('Add New Devotion')

    def form_valid(self, form):
        # self.user = User.objects.filter(user=self.request.user)
        self.add_devotion = form.save(commit=False)
        if get_user_role(self.request.user) == 'Devotion P':
            self.add_devotion.user = self.request.user
            self.add_devotion.is_active = True
            self.add_devotion.save()
            # if publisher has followers. ...
            self.followers_id = [self.user for self.user in self.request.user.followers.all()]
            if self.followers_id:
                self.myDate = datetime.now()
                self.current_site = get_current_site(self.request)
                self.user = self.request.user
                self.slug = self.add_devotion.slug
                self.author_name = self.user.first_name + ' ' + self.user.last_name if self.user.first_name else self.user.email
                self.author_story_title = form.cleaned_data.get('title')
                self.author_story_content = form.cleaned_data.get('content')
                self.base_name = 'DEVOTION!'
                self.mail_subject = str(self.base_name) + ' - "' + str(self.author_story_title) + '"!'
                image = MIMEImage(self.add_devotion.featured_image.read())
                image.add_header('Content-ID','<{}>'.format(self.add_devotion.image_file))
                # loop throught all the followers
                for self.followers_detail in self.followers_id:
                    self.followers_email = self.followers_detail.email  # get followers user email
                    html_content = render_to_string('email_messages/new_story/new_devotion_to_followers.html', {
                        'user': self.user,
                        'domain': self.current_site.domain,
                        'myDate': self.myDate,
                        'add_devotion': self.add_devotion,
                        'author_username': self.user.username,
                        'author_name': self.author_name,
                        'author_story_title': self.author_story_title,
                        'author_story_content': self.author_story_content,
                        'base_name': self.base_name,
                        'slug': self.slug,
                        'followers_username': self.followers_detail.username,
                        'followers_detail': self.followers_detail,
                    })
                    resend_email = EmailMultiAlternatives(
                        self.mail_subject, to=[self.followers_email]
                    )
                    resend_email.attach_alternative(html_content, "text/html")
                    resend_email.attach(image)
                    resend_email.send(fail_silently=False)
            messages.success(self.request, 'Great! Your story is published.')
            return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(HolyLifeMinistryAddDevotionView, self).get_context_data(**kwargs)
        context['add_devotion'] = True
        return context


@method_decorator(login_required, name="dispatch")
class HolyLifeMinistryDevotionUpdateView(TitleContextMixin, UserPassesTestMixin, UpdateView):
    """
    This function allow self.author user to update devotion.. Admin....
    """
    model = Devotion
    template_name = "devotion/devotion_edit.html"
    form_class = DevotionForm
    context_object_name = 'devotions'
    title = _('Edit')

    def form_valid(self, form):
        self.update_story = form.save(commit=False)
        self.update_story.user = self.request.user
        self.update_story.updated_on = timezone.now()
        self.update_story.save()
        messages.success(self.request, 'Great! Your story is updated.!!!')
        # data = {'error': False, 'response': 'Great! Your story is updated.',
        #         'title': self.request.POST['title']}
        return super().form_valid(form)

    def test_func(self):
        devotion = self.get_object()
        if self.request.user == devotion.user:
            return True
        return False


@login_required
def devotion_like_post(request):
    """
    THis fucntion take the action of users liked / unliked deotion story ..
    """
    post_id = request.POST.get('id')
    devotions = Devotion.objects.get(id=post_id)
    is_liked = False
    if devotions.devotion_likes.filter(id=request.user.id).exists():
        devotions.devotion_likes.remove(request.user)
        is_liked = False
    else:
        devotions.devotion_likes.add(request.user)
        is_liked = True
        create_action(request.user, 'liked', devotions)
    # return HttpResponseRedirect(pos.get_absolute_url())
    context = {
        'devotions': devotions,
        'is_liked': is_liked,
        'total_likes': devotions.total_likes(),
    }
    if request.is_ajax():
        html = render_to_string('liked/devotion_like_section.html', context, request=request)
        return JsonResponse({'form': html})


class HolyLifeMinistryTechView(TitleContextMixin, ListView):
    """
    List all techs posts
    """
    model = Tech
    paginate_by = 4
    template_name = "tech.html"
    context_object_name = 'techs'
    title = _('Tech')

    def get_queryset(self):
        return Tech.objects.filter(is_active=True).annotate(total_comments=Count('commentstech')).order_by('-created_on')

    def get_context_data(self, *args, **kwargs):
        context = super(HolyLifeMinistryTechView, self).get_context_data(*args, **kwargs)
        context.update(categories_tags_lists())
        return context


class HolyLifeMinistryTechDetailView(TitleContextMixin, DetailView):
    """
    Display the detail view of tech
    """
    model = Tech
    template_name = "tech/tech_detail.html"
    context_object_name = 'techs'
    title = _('Tech')

    def get_context_data(self, *args, **kwargs):
        context = super(HolyLifeMinistryTechDetailView, self).get_context_data(*args, **kwargs)
        tech_like = Tech.objects.filter(id=self.object.id, tech_likes=self.request.user.id)
        comments = CommentsTech.objects.filter(tech=self.object.id).order_by('-created_on')
        is_liked = False
        if self.request.user.is_authenticated and tech_like.exists(): # if request.user has already liked
            is_liked = True
        comment_form = TechCommentForm()
        context.update({
            "tech_like": tech_like,
            "is_liked": is_liked,
            "comments": comments,
            "comment_form": comment_form,
        })
        context.update(categories_tags_lists())
        return context


@login_required
def tech_comment(request, id):
    #  This function allow users comments on tech articles..
    post = get_object_or_404(Tech, id=id)
    user = User.objects.get(username=post.user.username)
    comments = CommentsDevotion.objects.filter(tech=post, reply=None).order_by('-id')
    if request.method == 'POST':
        comment_form = TechCommentForm(request.POST or None)
        if comment_form.is_valid():
            content = request.POST.get('content')
            comment = CommentsTech.objects.create(tech=post, user=request.user, content=content)
            comment.save()
            return HttpResponseRedirect(post.get_absolute_url())
    else:
        comment_form = TechCommentForm()

    context = {
        'post': post,
        'comments': comments,
        'comment_form': comment_form,
    }
    if request.is_ajax():
        html = render_to_string('comments/tech_comments.html', context, request=request)
        return JsonResponse({'form': html})

@method_decorator(login_required, name='dispatch')
class MakeTechArchiveView(View):
    """
    Archive / Drafted Tech story
    """

    def get(self, request, *args, **kwargs):
        # user = User.objects.get(username=request.user)
        self.make_archive = Tech.objects.get(
            slug=self.kwargs.get('slug')
        )
        if get_user_role(self.request.user) == 'Tech P':
            self.make_archive.is_active = False
            self.make_archive.save()
            messages.success(
                request,
                'Story: "' + str(self.make_archive.title) + '" has been moved to draft.'
            )
            return HttpResponseRedirect(reverse_lazy('christianbase_archive_stories'))


@method_decorator(login_required, name='dispatch')
class UnArchiveTechView(View):
    """
    Un-Archive or remover Tech story from archive ( private mood-- )
    """

    def get(self, request, *args, **kwargs):
        # user = User.objects.get(username=request.user)
        self.make_archive = Tech.objects.get(
            slug=self.kwargs.get('slug')
        )
        if get_user_role(self.request.user) == 'Tech P':
            self.make_archive.is_active = True
            self.make_archive.save()
            messages.success(
                request,
                'Your Story: "' + str(self.make_archive.title) + '" has been restored from draft...'
            )
            return HttpResponseRedirect(reverse_lazy('christianbase_archive_stories'))


@method_decorator(login_required, name="dispatch")
class HolyLifeMinistryAddTechView(TitleContextMixin, CreateView):
    """
    Display the create new techs form
    """
    model = Tech
    form_class = TechForm
    template_name = "tech/tech_edit.html"
    context_object_name = 'techs'
    title = _('Add New Tech')

    def form_valid(self, form):
        # self.user = User.objects.filter(user=self.request.user)
        self.add_tech = form.save(commit=False)
        if get_user_role(self.request.user) == 'Tech P':
            self.add_tech.user = self.request.user
            self.add_tech.is_active = True
            self.add_tech.save()
            # if publisher has followers. ...
            self.followers_id = [self.user for self.user in self.request.user.followers.all()]
            if self.followers_id:
                self.myDate = datetime.now()
                self.current_site = get_current_site(self.request)
                self.user = self.request.user
                self.slug = self.add_tech.slug
                self.author_name = self.user.first_name + ' ' + self.user.last_name if self.user.first_name else self.user.email
                self.author_story_title = form.cleaned_data.get('title')
                self.author_story_content = form.cleaned_data.get('content')
                self.base_name = 'TECH!'
                self.mail_subject = str(self.base_name) + ' - "' + str(self.author_story_title) + '"!'
                image = MIMEImage(self.add_tech.featured_image.read())
                image.add_header('Content-ID','<{}>'.format(self.add_tech.image_file))
                # loop throught all the followers
                for self.followers_detail in self.followers_id:
                    self.followers_email = self.followers_detail.email  # get followers user email
                    html_content = render_to_string('email_messages/new_story/new_tech_to_followers.html', {
                        'user': self.user,
                        'domain': self.current_site.domain,
                        'myDate': self.myDate,
                        'add_tech': self.add_tech,
                        'author_username': self.user.username,
                        'author_name': self.author_name,
                        'author_story_title': self.author_story_title,
                        'author_story_content': self.author_story_content,
                        'base_name': self.base_name,
                        'slug': self.slug,
                        'followers_username': self.followers_detail.username,
                        'followers_detail': self.followers_detail,
                    })
                    resend_email = EmailMultiAlternatives(
                        self.mail_subject, to=[self.followers_email]
                    )
                    resend_email.attach_alternative(html_content, "text/html")
                    resend_email.attach(image)
                    resend_email.send(fail_silently=False)
            messages.success(self.request, 'Great! Your story is published.')
            return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(HolyLifeMinistryAddTechView, self).get_context_data(**kwargs)
        context['add_tech'] = True
        return context


@method_decorator(login_required, name="dispatch")
class HolyLifeMinistryTechUpdateView(TitleContextMixin, UserPassesTestMixin, UpdateView):
    """
    This function allow self.author user to update tech.. Admin....
    """
    model = Tech
    template_name = "tech/tech_edit.html"
    form_class = TechForm
    context_object_name = 'techs'
    title = _('Edit')

    def form_valid(self, form):
        self.update_story = form.save(commit=False)
        self.update_story.user = self.request.user
        self.update_story.updated_on = timezone.now()
        self.update_story.save()
        messages.success(self.request, 'Great! Your story is updated.!!!')
        # data = {'error': False, 'response': 'Great! Your story is updated.',
        #         'title': self.request.POST['title']}
        return super().form_valid(form)

    def test_func(self):
        tech = self.get_object()
        if self.request.user == tech.user:
            return True
        return False


@login_required
def tech_like_post(request):
    """
    THis fucntion take the action of users liked / unliked tech story ..
    """
    post_id = request.POST.get('id')
    techs = Tech.objects.get(id=post_id)
    is_liked = False
    if techs.tech_likes.filter(id=request.user.id).exists():
        techs.tech_likes.remove(request.user)
        is_liked = False
    else:
        techs.tech_likes.add(request.user)
        is_liked = True
        create_action(request.user, 'liked', techs)
    # return HttpResponseRedirect(pos.get_absolute_url())
    context = {
        'techs': techs,
        'is_liked': is_liked,
        'total_likes': techs.total_likes(),
    }
    if request.is_ajax():
        html = render_to_string('liked/tech_like_section.html', context, request=request)
        return JsonResponse({'form': html})


class HolyLifeMinistryQuotesView(TitleContextMixin, ListView):
    """
    List all devotion psots
    """
    model = Quotes
    paginate_by = 4
    template_name = "quote.html"
    context_object_name = 'quotes'
    title = _('Quotes')

    def get_queryset(self):
        return Quotes.objects.filter(is_active=True).annotate(total_comments=Count('commentsquotes')).order_by('-created_on')

    def get_context_data(self, *args, **kwargs):
        context = super(HolyLifeMinistryQuotesView, self).get_context_data(*args, **kwargs)
        context.update(categories_tags_lists())
        return context


class HolyLifeMinistryQuotesDetailView(TitleContextMixin, DetailView):
    """
    Display the detail view of quotes
    """
    model = Quotes
    template_name = "quotes/quote_detail.html"
    context_object_name = 'quotes'
    title = _('Quotes')

    def get_context_data(self, *args, **kwargs):
        context = super(HolyLifeMinistryQuotesDetailView, self).get_context_data(*args, **kwargs)
        quote_like = Quotes.objects.filter(id=self.object.id, quotes_likes=self.request.user.id)
        comments = CommentsQuotes.objects.filter(quote=self.object.id).order_by('-created_on')
        is_liked = False
        if self.request.user.is_authenticated and quote_like.exists():
            is_liked = True
        comment_form = QuotesCommentForm()
        context.update({
            "quote_like": quote_like,
            "is_liked": is_liked,
            "comments": comments,
            "comment_form": comment_form,
        })
        context.update(categories_tags_lists())
        return context


@login_required
def quotes_comment(request, id):
    #  This function allow users comments on tech articles..
    post = get_object_or_404(Quotes, id=id)
    user = User.objects.get(username=post.user.username)
    comments = CommentsQuotes.objects.filter(quote=post, reply=None).order_by('-id')
    if request.method == 'POST':
        comment_form = QuotesCommentForm(request.POST or None)
        if comment_form.is_valid():
            content = request.POST.get('content')
            comment = CommentsQuotes.objects.create(quote=post, user=request.user, content=content)
            comment.save()
            return HttpResponseRedirect(post.get_absolute_url())
    else:
        comment_form = QuotesCommentForm()

    context = {
        'post': post,
        'comments': comments,
        'comment_form': comment_form,
    }
    if request.is_ajax():
        html = render_to_string('comments/quotes_comments.html', context, request=request)
        return JsonResponse({'form': html})

@method_decorator(login_required, name='dispatch')
class MakeQuotesArchiveView(View):
    """
    Archive / Drafted Quotes story
    """

    def get(self, request, *args, **kwargs):
        # user = User.objects.get(username=request.user)
        self.make_archive = Quotes.objects.get(
            slug=self.kwargs.get('slug')
        )
        if get_user_role(self.request.user) == 'Quotes P':
            self.make_archive.is_active = False
            self.make_archive.save()
            messages.success(
                request,
                'Story: "' + str(self.make_archive.title) + '" has been moved to draft.'
            )
            return HttpResponseRedirect(reverse_lazy('christianbase_archive_stories'))


@method_decorator(login_required, name='dispatch')
class UnArchiveQuotesView(View):
    """
    Un-Archive or remover Quotes story from archive ( private mood-- )
    """

    def get(self, request, *args, **kwargs):
        # user = User.objects.get(username=request.user)
        self.make_archive = Quotes.objects.get(
            slug=self.kwargs.get('slug')
        )
        if get_user_role(self.request.user) == 'Quotes P':
            self.make_archive.is_active = True
            self.make_archive.save()
            messages.success(
                request,
                'Your Story: "' + str(self.make_archive.title) + '" has been restored from draft...'
            )
            return HttpResponseRedirect(reverse_lazy('christianbase_archive_stories'))


@method_decorator(login_required, name="dispatch")
class HolyLifeMinistryAddQuotesView(TitleContextMixin, CreateView):
    """
    Display the create new quotes form
    """
    model = Quotes
    form_class = QuotesForm
    template_name = "quotes/quote_edit.html"
    context_object_name = 'quotes'
    title = _('Add New Quotes')

    def form_valid(self, form):
        # self.user = User.objects.filter(user=self.request.user)
        self.add_quote = form.save(commit=False)
        if get_user_role(self.request.user) == 'Quotes P':
            self.add_quote.user = self.request.user
            self.add_quote.is_active = True
            self.add_quote.save()
            # if publisher has followers. ...
            self.followers_id = [self.user for self.user in self.request.user.followers.all()]
            if self.followers_id:
                self.myDate = datetime.now()
                self.current_site = get_current_site(self.request)
                self.user = self.request.user
                self.slug = self.add_quote.slug
                self.author_name = self.user.first_name + ' ' + self.user.last_name if self.user.first_name else self.user.email
                self.author_story_title = form.cleaned_data.get('title')
                self.author_story_content = form.cleaned_data.get('content')
                self.base_name = 'DAILY QUOTE!'
                self.mail_subject = str(self.base_name) + ' - "' + str(self.author_story_title) + '"!'
                image = MIMEImage(self.add_quote.featured_image.read())
                image.add_header('Content-ID','<{}>'.format(self.add_quote.image_file))
                # loop throught all the followers
                for self.followers_detail in self.followers_id:
                    self.followers_email = self.followers_detail.email  # get followers user email
                    html_content = render_to_string('email_messages/new_story/new_quotes_to_followers.html', {
                        'user': self.user,
                        'domain': self.current_site.domain,
                        'myDate': self.myDate,
                        'add_quote': self.add_quote,
                        'author_username': self.user.username,
                        'author_name': self.author_name,
                        'author_story_title': self.author_story_title,
                        'author_story_content': self.author_story_content,
                        'base_name': self.base_name,
                        'slug': self.slug,
                        'followers_username': self.followers_detail.username,
                        'followers_detail': self.followers_detail,
                    })
                    resend_email = EmailMultiAlternatives(
                        self.mail_subject, to=[self.followers_email]
                    )
                    resend_email.attach_alternative(html_content, "text/html")
                    resend_email.attach(image)
                    resend_email.send(fail_silently=False)
            messages.success(self.request, 'Great! Your story is published.')
            return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(HolyLifeMinistryAddQuotesView, self).get_context_data(**kwargs)
        context['add_quotes'] = True
        return context


@method_decorator(login_required, name="dispatch")
class HolyLifeMinistryQuotesUpdateView(TitleContextMixin, UserPassesTestMixin, UpdateView):
    """
    This function allow self.author user to update quotes.. Admin....
    """
    model = Quotes
    template_name = "quotes/quote_edit.html"
    form_class = QuotesForm
    context_object_name = 'quotes'
    title = _('Edit')

    def form_valid(self, form):
        self.update_story = form.save(commit=False)
        self.update_story.user = self.request.user
        self.update_story.updated_on = timezone.now()
        self.update_story.save()
        messages.success(self.request, 'Great! Your story is updated.!!!')
        # data = {'error': False, 'response': 'Great! Your story is updated.',
        #         'title': self.request.POST['title']}
        return super().form_valid(form)

    def test_func(self):
        quotes = self.get_object()
        if self.request.user == quotes.user:
            return True
        return False


@login_required
def quotes_like_post(request):
    """
    THis fucntion take the action of users liked / unliked quotes story ..
    """
    post_id = request.POST.get('id')
    quotes = Quotes.objects.get(id=post_id)
    is_liked = False
    if quotes.quotes_likes.filter(id=request.user.id).exists():
        quotes.quotes_likes.remove(request.user)
        is_liked = False
    else:
        quotes.quotes_likes.add(request.user)
        is_liked = True
        create_action(request.user, 'liked', quotes)
    # return HttpResponseRedirect(pos.get_absolute_url())
    context = {
        'quotes': quotes,
        'is_liked': is_liked,
        'total_likes': quotes.total_likes(),
    }
    if request.is_ajax():
        html = render_to_string('liked/quotes_like_section.html', context, request=request)
        return JsonResponse({'form': html})


class HolyLifeMinistryPolicyView(TitleContextMixin, ListView):
    """
    List all HolyLifeMinistry policy psots like Privacy Policy, Terms of Service...
    """
    model = Policy
    paginate_by = 4
    template_name = "policy/policy.html"
    context_object_name = 'policy'
    title = _('Holy Life Ministry Policy')

    def get_queryset(self):
        return Policy.objects.filter(is_active=True).annotate(total_comments=Count('commentspolicy')).order_by('-created_on')

    def get_context_data(self, *args, **kwargs):
        context = super(HolyLifeMinistryPolicyView, self).get_context_data(*args, **kwargs)
        context.update(categories_tags_lists())
        return context


class HolyLifeMinistryPolicyDetailView(TitleContextMixin, DetailView):
    """
    Display the detail view of policy
    """
    model = Policy
    template_name = "policy/policy_detail.html"
    title = _('Holy Life Ministry Policy')
    context_object_name = 'policy'

    def get_context_data(self, *args, **kwargs):
        context = super(HolyLifeMinistryPolicyDetailView, self).get_context_data(*args, **kwargs)
        user = self.object.user
        author = user.first_name if user.first_name else user.username
        more_storys = Post.objects.filter(
            status='Published',
            tags__in=self.object.tags.all(),
        ).annotate(total_post_comments=Count('comment')).exclude(id=self.object.id).distinct()[:3]
        policy_like = Policy.objects.filter(id=self.object.id, policy_likes=self.request.user.id)
        comments = CommentsPolicy.objects.filter(policy=self.object.id).order_by('-created_on')
        is_liked = False
        if self.request.user.is_authenticated and policy_like.exists():
            is_liked = True
        comment_form = PolicyCommentForm()
        context.update({
            "more_storys": more_storys,
            "author": author,
            "policy_like": policy_like,
            "is_liked": is_liked,
            "comments": comments,
            "comment_form": comment_form,
        })
        context.update(categories_tags_lists())
        return context


@login_required
def policy_like_post(request):
    """
    THis fucntion take the action of users liked / unliked policy story ..
    """
    post_id = request.POST.get('id')
    policy = Policy.objects.get(id=post_id)
    is_liked = False
    if policy.policy_likes.filter(id=request.user.id).exists():
        policy.policy_likes.remove(request.user)
        is_liked = False
    else:
        policy.policy_likes.add(request.user)
        is_liked = True
        create_action(request.user, 'liked', policy)
    # return HttpResponseRedirect(pos.get_absolute_url())
    context = {
        'policy': policy,
        'is_liked': is_liked,
        'total_likes': policy.total_likes(),
    }
    if request.is_ajax():
        html = render_to_string('liked/policy_like_section.html', context, request=request)
        return JsonResponse({'form': html})


@login_required
def policy_comment(request, id):
    #  This function allow users comments on policy articles..
    post = get_object_or_404(Policy, id=id)
    user = User.objects.get(username=post.user.username)
    comments = CommentsPolicy.objects.filter(policy=post, reply=None).order_by('-id')
    if request.method == 'POST':
        comment_form = PolicyCommentForm(request.POST or None)
        if comment_form.is_valid():
            content = request.POST.get('content')
            comment = CommentsPolicy.objects.create(policy=post, user=request.user, content=content)
            comment.save()
            return HttpResponseRedirect(post.get_absolute_url())
    else:
        comment_form = PolicyCommentForm()

    context = {
        'post': post,
        'comments': comments,
        'comment_form': comment_form,
    }
    if request.is_ajax():
        html = render_to_string('comments/policy_comments.html', context, request=request)
        return JsonResponse({'form': html})


@login_required
def bookmarks_policy(request):
    """
    Allow User to bookmarks policy stories / stories...
    """
    story_id = request.POST.get('id')
    story = Policy.objects.get(id=story_id)
    is_favorite = False
    if story.bookmarks.filter(id=request.user.id).exists():
        story.bookmarks.remove(request.user)
        is_favorite = False
    else:
        story.bookmarks.add(request.user)
        is_favorite = True

    context = {
        'is_favorite': is_favorite,
        'story': story,
    }

    if request.is_ajax():
        html = render_to_string('story/bookmarks/bookmark_policy.html', context, request=request)
        return JsonResponse({'form': html})


@method_decorator(login_required, name='dispatch')
class MakePolicyArchiveView(View):
    """
    Archive / Drafted Policy story
    """

    def get(self, request, *args, **kwargs):
        self.make_archive = Policy.objects.get(
            slug=self.kwargs.get('slug')
        )
        if get_user_role(self.request.user) == 'Policy':
            self.make_archive.is_active = False
            self.make_archive.save()
            messages.success(
                request,
                'Story: "' + str(self.make_archive.title) + '" has been moved to draft.'
            )
            return HttpResponseRedirect(reverse_lazy('christianbase_archive_stories'))


@method_decorator(login_required, name='dispatch')
class UnArchivePolicysView(View):
    """
    Un-Archive or remover Quotes story from archive ( private mood-- )
    """

    def get(self, request, *args, **kwargs):
        # user = User.objects.get(username=request.user)
        self.make_archive = Policy.objects.get(
            slug=self.kwargs.get('slug')
        )
        if get_user_role(self.request.user) == 'Policy':
            self.make_archive.is_active = True
            self.make_archive.save()
            messages.success(
                request,
                'Your Story: "' + str(self.make_archive.title) + '" has been restored from draft...'
            )
            return HttpResponseRedirect(reverse_lazy('christianbase_archive_stories'))


@method_decorator(login_required, name="dispatch")
class HolyLifeMinistryAddPolicyView(TitleContextMixin, CreateView):
    """
    Display the create new policy form
    """
    model = Policy
    form_class = PolicyForm
    template_name = "policy/policy_edit.html"
    context_object_name = 'policy'
    title = _('Add New Policy')

    def get_form_kwargs(self):
        kwargs = super(HolyLifeMinistryAddPolicyView, self).get_form_kwargs()
        kwargs.update({'user': self.request.user})
        role = get_user_role(self.request.user)
        role = role if role in dict(ROLE_CHOICE).keys() else None
        kwargs["user_role"] = role
        return kwargs

    def form_valid(self, form):
        # self.user = User.objects.filter(user=self.request.user)
        self.add_policy = form.save(commit=False)
        if get_user_role(self.request.user) == 'Policy':
            self.add_policy.user = self.request.user
            self.add_policy.is_active = True
            self.add_policy.save()
            if self.request.POST.get('tags', ''):
                splitted = self.request.POST.get('tags').split(',')
                for s in splitted:
                    story_tags = Tags.objects.filter(name__iexact=s.strip())
                    if story_tags:
                        story_tag = story_tags.first()
                    else:
                        story_tag = Tags.objects.create(name=s.strip())
                    self.add_policy.tags.add(story_tag)

            self.add_policy.create_activity(user=self.request.user, content="added")
            # if publisher has followers. ...
            self.followers_id = [self.user for self.user in self.request.user.followers.all()]
            if self.followers_id:
                self.myDate = datetime.now()
                self.current_site = get_current_site(self.request)
                self.user = self.request.user
                self.slug = self.add_policy.slug
                self.policy_hex = self.add_policy.policy_hex
                self.author_name = self.user.first_name + ' ' + self.user.last_name if self.user.first_name else self.user.email
                self.author_story_title = form.cleaned_data.get('title')
                self.author_story_content = form.cleaned_data.get('content')
                self.mail_subject = str(self.author_name) + ' published a new article'
                image = MIMEImage(self.add_policy.featured_image.read())
                image.add_header('Content-ID','<{}>'.format(self.add_policy.image_file))
                # loop throught all the followers
                for self.followers_detail in self.followers_id:
                    self.followers_email = self.followers_detail.email  # get followers user email
                    html_content = render_to_string('email_messages/policy_story/new_policy_to_followers.html', {
                        'user': self.user,
                        'domain': self.current_site.domain,
                        'myDate': self.myDate,
                        'add_quote': self.add_quote,
                        'author_username': self.user.username,
                        'author_name': self.author_name,
                        'author_story_title': self.author_story_title,
                        'author_story_content': self.author_story_content,
                        'slug': self.slug,
                        'policy_hex': self.policy_hex,
                        'followers_username': self.followers_detail.username,
                        'followers_detail': self.followers_detail,
                    })
                    resend_email = EmailMultiAlternatives(
                        self.mail_subject, to=[self.followers_email]
                    )
                    resend_email.attach_alternative(html_content, "text/html")
                    resend_email.attach(image)
                    resend_email.send(fail_silently=False)
            messages.success(self.request, 'Great! Your story is published.')
            return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(HolyLifeMinistryAddPolicyView, self).get_context_data(**kwargs)
        context['add_policy'] = True
        return context


@method_decorator(login_required, name="dispatch")
class HolyLifeMinistryUpdatePolicyView(TitleContextMixin, UserPassesTestMixin, UpdateView):
    """
    Display the update new story form and handle the story update action.
    """
    model = Policy
    form_class = PolicyForm
    template_name = "policy/policy_edit.html"
    context_object_name = 'policy'
    title = _('Update Policy story')

    def get_form_kwargs(self):
        kwargs = super(HolyLifeMinistryUpdatePolicyView, self).get_form_kwargs()
        kwargs.update({'user': self.request.user})
        role = get_user_role(self.request.user)
        role = role if role in dict(ROLE_CHOICE).keys() else None
        kwargs["user_role"] = role
        return kwargs

    def form_valid(self, form):
        self.update_story = form.save(commit=False)
        self.update_story.user = self.request.user
        self.update_story.updated_on = timezone.now()
        self.update_story.save()
        if self.request.POST.get('tags', ''):
            self.update_story.tags.clear()
            splitted = self.request.POST.get('tags').split(',')
            for s in splitted:
                story_tags = Tags.objects.filter(name__iexact=s.strip())
                if story_tags:
                    story_tag = story_tags.first()
                else:
                    story_tag = Tags.objects.create(name=s.strip())
                self.update_story.tags.add(story_tag)
        messages.success(self.request, 'Great! Your story is updated.!!!')
        # data = {'error': False, 'response': 'Great! Your story is updated.',
        #         'title': self.request.POST['title']}
        return super().form_valid(form)


    def test_func(self):
        self.story = self.get_object()
        if self.request.user == self.story.user:
            return True
        else:
            False


class PrayerRequestCreateView(TitleContextMixin, CreateView):
    """
    Display the prayer request form and add
    """
    model = PrayerRequest
    form_class = AddPrayerRequestForm
    template_name = "prayer_request/prayer_request_add.html"
    context_object_name = 'prayer_request'
    title = _('Prayer Request')

    def form_valid(self, form):
        # self.user = User.objects.filter(user=self.request.user)
        self.add_prayer_request = form.save(commit=False)
        self.add_prayer_request.user = self.request.user
        self.add_prayer_request.save()
        # sent mail to request user. ...
        if self.request.user:
            self.myDate = datetime.now()
            self.current_site = get_current_site(self.request)
            self.user = self.request.user
            self.author_name = self.user.first_name + ' ' + self.user.last_name if self.user.first_name else self.user.email
            self.area = form.cleaned_data.get('area')
            self.message = form.cleaned_data.get('message')
            self.mail_subject = 'PRAYER REQUEST!! You Sent A Prayer Request To Holy Life Ministry!'
            self.to_email = self.request.user.email  # get user email
            html_content = render_to_string('email_messages/prayer_request/user_request_sent.html', {
                'user': self.user.username,
                'domain': self.current_site.domain,
                'myDate': self.myDate,
                'add_prayer_request': self.add_prayer_request,
                'author_name': self.author_name,
                'area': self.area,
                'message': self.message,
            })
            resend_email = EmailMultiAlternatives(
                self.mail_subject, to=[self.to_email]
            )
            resend_email.attach_alternative(html_content, "text/html")
            resend_email.send(fail_silently=False)
        messages.success(self.request, 'Great! Your story is published.')
        return HttpResponseRedirect(reverse_lazy('request-prayer'))

    def get_context_data(self, **kwargs):
        context = super(PrayerRequestCreateView, self).get_context_data(**kwargs)
        context['add_policy'] = True
        return context


@hit_count
def search_stories(request):
    form = SearchForm()
    query = None
    results = []
    if 'query' in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data['query']
            post_results = Post.objects.annotate(total_post_comments=Count('comment'),
                similarity=TrigramSimilarity('title', query),
            ).filter(similarity__gt=0.1).order_by('-similarity')
            bible_results = BibleStudies.objects.annotate(total_post_comments=Count('commentsbiblestudies'),
                similarity=TrigramSimilarity('title', query),
            ).filter(similarity__gt=0.1).order_by('-similarity')
            devotion_results = Devotion.objects.annotate(total_post_comments=Count('commentsdevotion'),
                similarity=TrigramSimilarity('title', query),
            ).filter(similarity__gt=0.1).order_by('-similarity')
            tech_results = Tech.objects.annotate(total_post_comments=Count('commentstech'),
                similarity=TrigramSimilarity('title', query),
            ).filter(similarity__gt=0.1).order_by('-similarity')
            policy_results = Policy.objects.annotate(total_post_comments=Count('commentspolicy'),
                similarity=TrigramSimilarity('title', query),
            ).filter(similarity__gt=0.1).order_by('-similarity')
            results = list(chain(post_results, bible_results, devotion_results, tech_results, policy_results))
    context = {
        'form': form,
        'query': query,
        'results': results,
        'title': 'Search and find',
    }
    return render(request, 'search/search.html', context)


def handler403(request, exception):
    # handler 403 error page...
    return render(request, "error_page/403.html", status=403)


def handler404(request, exception):
    # handler 404 error page...
    return render(request, "error_page/404.html", status=404)


def handler500(request):
    # handler 404 error page...
    return render(request, "error_page/500.html", status=500)


