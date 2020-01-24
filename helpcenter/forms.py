
from django import forms
from django.template.defaultfilters import slugify
from django.utils.translation import gettext, gettext_lazy as _
from accounts.tokens import account_activation_token
from accounts.decorators import parsleyfy

from .models import HelpCenter, UsersRequest, USERREQUEST_CHOICE

@parsleyfy
class SubmitRequestForm(forms.ModelForm):
    status = forms.ChoiceField(
        label='How can we help you?', choices=USERREQUEST_CHOICE,
        required=True,
        error_messages={'required': 'Please select request issues.'},
    )
    description = forms.CharField(
        required=True,
        widget=forms.Textarea(
            attrs={'placeholder': ''},
        ),
        help_text='Please enter the details of your request. A member of our support staff will respond as soon as possible.',
        error_messages={'required': 'Description field is required.'}
    )

    class Meta:
        model = UsersRequest
        fields = ['status', 'description', ]
        exclude = ('slug',)



class SearchForm(forms.Form):
    query = forms.CharField()
