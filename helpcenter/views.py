import os
from itertools import chain
from django.conf import settings
from datetime import datetime
from operator import attrgetter
from urllib.parse import urlparse, urlunparse
from django.shortcuts import render, redirect, resolve_url, get_object_or_404
from django.http import HttpResponseRedirect, QueryDict, JsonResponse
from django.template import Context, RequestContext
from django.db.models import Q, Count
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic.base import TemplateView
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.views.generic.edit import FormView
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.urls import reverse_lazy, reverse
from django.utils.decorators import method_decorator
from django.utils.http import is_safe_url, urlsafe_base64_decode
from django.utils.translation import gettext_lazy as _

from django.db.models.functions import Greatest
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank, TrigramSimilarity

from .forms import SubmitRequestForm, SearchForm
from .models import Section, HelpCenter, UsersRequest


class TitleContextMixin:
    extra_context = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.title
        if self.extra_context is not None:
            context.update(self.extra_context)
        return context


class HelpHomePageView(ListView):
    """
    List both latest stories and both following author stories in main home page.
    """
    model = Section
    template_name = 'helpcenter/home.html'
    context_object_name = 'help_center'

    def get_context_data(self, *args, **kwargs):
        context = super(HelpHomePageView, self).get_context_data(*args, **kwargs)
        context['helpcenter'] = True
        return context


class ArticleDetailView(DetailView):
    """
    dsiplay the article info....
    """
    # model = HelpCenter
    template_name = 'helpcenter/articles_detail.html'
    context_object_name = 'articles'

    def get_object(self):
        return get_object_or_404(HelpCenter, help_hex=self.kwargs['help_hex'])

    def get_context_data(self, *args, **kwargs):
        context = super(ArticleDetailView, self).get_context_data(**kwargs)
        self.article_section = HelpCenter.objects.filter(section=self.object.section)
        context['article_section'] = self.article_section
        context['helpcenter'] = True
        return context


class SectionListView(ListView):
    """
    dsiplay the article info....
    """
    template_name = 'helpcenter/section.html'
    context_object_name = 'sections'

    def get_queryset(self):
        self.section = get_object_or_404(Section, slug=self.kwargs['slug'])
        return HelpCenter.objects.filter(section=self.section)

    def get_context_data(self, *args, **kwargs):
        context = super(SectionListView, self).get_context_data(**kwargs)
        self.article_section = HelpCenter.objects.filter(section=self.section)
        context['article_section'] = self.article_section
        context['section'] = self.section
        context['helpcenter'] = True
        return context


def search_helpcenter(request):
    form = SearchForm()
    query = None
    results = []
    if 'query' in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data['query']
            results = HelpCenter.objects.annotate(
                similarity=Greatest(TrigramSimilarity('title', query),
                    TrigramSimilarity('section__name', query)
                )
            ).filter(similarity__gt=0.1).order_by('-similarity')
    context = {
        'form': form,
        'query': query,
        'results': results,
        'helpcenter': True,
        'title': 'Search results',
    }
    return render(request, 'helpsearch/search.html', context)


@method_decorator(login_required, name='dispatch')
class SubmitRequestView(TitleContextMixin, CreateView):
    """
    Display the create new topic / category form and handle the topic action.
    """
    model = UsersRequest
    form_class = SubmitRequestForm
    template_name = "helpcenter/submit_request.html"
    success_url = reverse_lazy('submit_request')
    title = _('Submit a request')

    def form_valid(self, form):
        # self.user = User.objects.filter(user=self.request.user)
        self.submit_request = form.save(commit=False)
        self.submit_request.user = self.request.user
        self.submit_request.save()
        messages.success(self.request, 'Great!! Your request is sent us and we\' notify you soon...!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(SubmitRequestView, self).get_context_data(**kwargs)
        context['helpcenter'] = True
        return context


class AboutPageView(TemplateView):
    """
    Display the create new topic / category form and handle the topic action.
    """
    template_name = "about.html"

    def get_context_data(self, **kwargs):
        context = super(AboutPageView, self).get_context_data(**kwargs)
        context['helpcenter'] = True
        return context
