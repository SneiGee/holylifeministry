import os
import json
from decouple import config, Csv
from django import template
from django.db.models import Count

from accounts.models import User
from ..models import Category, Post, BibleStudies, Devotion

register = template.Library()

@register.filter
def human_format(num): # format long number like 1000 to 1k....
    num = float("{:.3g}".format(num))

    # num = '{:.3}'.format(float(num))
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return '{}{}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), ['', 'k', 'm', 'b', 't', 'p'][magnitude])

# register.filter('human_format', human_format)

# print(human_format(999999))

@register.simple_tag(takes_context=True)
def user_categories_list(context):
    # retrive user topic / categories
    request = context['request']
    return Category.objects.filter(user=request.user.id, is_active=True)


@register.simple_tag
def popular_post(count=4):
    # show most liked post. Popular post
    return Post.objects.annotate(like_count=Count('likes'), total_post_comments=Count('comment')).order_by('-like_count')[:count]


@register.simple_tag(takes_context=True)
def who_to_follow(context, count=1):
    # retrive random users for a login user to follow...
    request = context['request']
    return User.objects.filter(is_active=True).order_by('?').exclude(id=request.user.id).distinct()[:count]


@register.simple_tag
def google_analytics_id():
    return config("GOOGLE_ANALYTICS_ID")
