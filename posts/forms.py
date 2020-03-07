
from django import forms
from django.template.defaultfilters import slugify
from django.utils.translation import gettext, gettext_lazy as _
from accounts.tokens import account_activation_token
from accounts.decorators import parsleyfy

from ckeditor_uploader.widgets import CKEditorUploadingWidget

from .models import ( Post, Tags, Category, WrittenBy, STATUS_CHOICE, BibleStudies, Devotion,
    Tech, Quotes, Policy, PrayerRequest, REQUEST_CHOICE, Comment, CommentsBibleStudies, CommentsDevotion, CommentsTech, CommentsQuotes,
    CommentsPolicy,
)


@parsleyfy
class UserStoryArticleForm(forms.ModelForm):
    title = forms.CharField(
        label='Your story title', max_length=100, required=True,
        error_messages={'required': 'Story title field is required.'}
    )
    category = forms.ModelChoiceField(
        label='Topic / Category', queryset=None, required=True, empty_label='Select Topic / Category',
        error_messages={'required': 'Select any topic that describe your story..'}
    )
    tags = forms.CharField(
        label="Add or Change tags (up to 5) so readers know what your story is about", max_length=300, required=False,
    )

    class Meta:
        model = Post
        fields = ['title', 'featured_image', 'featured_video', 'content', 'category', 'tags', ]
        exclude = ('tags',)

        # widgets = {
        #     'featured_image': forms.ClearableFileInput(),
        # }

    def __init__(self, user, *args, **kwargs):
        # self.user = kwargs.pop('user', None)
        self.user_role = kwargs.pop('user_role', None)
        super(UserStoryArticleForm, self).__init__(*args, **kwargs)
        self.fields['title'].widget.attrs['placeholder'] = "Add title"
        self.fields['content'].widget.attrs['placeholder'] = "Tell your story..."
        self.fields['tags'].widget.attrs['placeholder'] = "Add a tag.."
        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                'class': 'form-control'
            })
        self.fields['category'].queryset = Category.objects.all().filter(user=user, is_active=True)

    # def clean_status(self):
    #     if self.user_role == "Author":
    #         raise forms.ValidationError("Admin and Publisher can change status only.")
    #     return self.cleaned_data.get("status")


@parsleyfy
class AddCategoryForm(forms.ModelForm):
    name = forms.CharField(
        label='Add Topic Or Category your story will based on!', max_length=100, required=True,
        error_messages={'required': 'Topic / Category field is required.'}
    )
    description = forms.CharField(
        max_length=7000, required=True,
        widget=forms.Textarea(
            attrs={'placeholder': 'Type short description'}
        ),
        error_messages={'required': 'Description field is required.'}
    )
    is_active = forms.BooleanField(
        label='On / Off', required=False,
        help_text=_('Designates whether this topic/category should be treated active or unactive'),
        error_messages={'required': 'Is active field is required.'}
    )

    class Meta:
        model = Category
        fields = ['name', 'description', 'is_active', ]
        exclude = ('slug',)

    def __init__(self, *args, **kwargs):
        super(AddCategoryForm, self).__init__(*args, **kwargs)
        self.fields['name'].widget.attrs['placeholder'] = "Add Topic / Category"


@parsleyfy
class BibleStudiesForm(forms.ModelForm):
    title = forms.CharField(
        label='Title', max_length=100, required=True,
        error_messages={'required': 'Title field is required.'}
    )
    written_by = forms.ModelChoiceField(
        label='Written by Who', queryset=None, required=True, empty_label='Select Author',
        error_messages={'required': 'Select author who write this story..'}
    )

    class Meta:
        model = BibleStudies
        fields = ['written_by', 'title', 'content', 'featured_image',]
        exclude = ('slug',)

    def __init__(self, *args, **kwargs):
        super(BibleStudiesForm, self).__init__(*args, **kwargs)
        self.fields['title'].widget.attrs['placeholder'] = "Bible Studies Title"
        self.fields['content'].widget.attrs['placeholder'] = "Tell your story..."
        self.fields['written_by'].queryset = WrittenBy.objects.all()


@parsleyfy
class DevotionForm(forms.ModelForm):
    title = forms.CharField(
        label='Title', max_length=100, required=True,
        error_messages={'required': 'Title field is required.'}
    )
    written_by = forms.ModelChoiceField(
        label='Written by Who', queryset=None, required=True, empty_label='Select Author',
        error_messages={'required': 'Select author who write this story..'}
    )

    class Meta:
        model = Devotion
        fields = ['written_by', 'title', 'content', 'featured_image',]
        exclude = ('slug',)

    def __init__(self, *args, **kwargs):
        super(DevotionForm, self).__init__(*args, **kwargs)
        self.fields['title'].widget.attrs['placeholder'] = "Devotion Title"
        self.fields['content'].widget.attrs['placeholder'] = "Tell your story..."
        self.fields['written_by'].queryset = WrittenBy.objects.all()


@parsleyfy
class TechForm(forms.ModelForm):
    title = forms.CharField(
        label='Title', max_length=100, required=True,
        error_messages={'required': 'Title field is required.'}
    )
    written_by = forms.ModelChoiceField(
        label='Written by Who', queryset=None, required=True, empty_label='Select Author',
        error_messages={'required': 'Select author who write this story..'}
    )

    class Meta:
        model = Tech
        fields = ['written_by', 'title', 'content', 'featured_image', ]
        exclude = ('slug',)

    def __init__(self, *args, **kwargs):
        super(TechForm, self).__init__(*args, **kwargs)
        self.fields['title'].widget.attrs['placeholder'] = "Tech Title"
        self.fields['content'].widget.attrs['placeholder'] = "Tell your story..."
        self.fields['written_by'].queryset = WrittenBy.objects.all()


@parsleyfy
class QuotesForm(forms.ModelForm):
    title = forms.CharField(
        label='Title', max_length=100, required=True,
        error_messages={'required': 'Title field is required.'}
    )
    written_by = forms.ModelChoiceField(
        label='Written by Who', queryset=None, required=True, empty_label='Select Author',
        error_messages={'required': 'Select author who write this story..'}
    )

    class Meta:
        model = Quotes
        fields = ['written_by', 'title', 'content', 'featured_image', ]
        exclude = ('slug',)

    def __init__(self, *args, **kwargs):
        super(QuotesForm, self).__init__(*args, **kwargs)
        self.fields['title'].widget.attrs['placeholder'] = "Quote Title"
        self.fields['content'].widget.attrs['placeholder'] = "Tell your story..."
        self.fields['written_by'].queryset = WrittenBy.objects.all()


@parsleyfy
class PolicyForm(forms.ModelForm):
    #---    Policy Form    ---#
    title = forms.CharField(
        label='Title', max_length=100, required=True,
        error_messages={'required': 'Title field is required.'}
    )
    written_by = forms.ModelChoiceField(
        label='Written by Who', queryset=None, required=True, empty_label='Select Author',
        error_messages={'required': 'Select author who write this story..'}
    )
    tags = forms.CharField(
        label="Add or Change tags (up to 5) so readers know what your story is about", max_length=300, required=False,
    )

    class Meta:
        model = Policy
        fields = ['written_by', 'title', 'content', 'tags', ]
        # exclude = ('tags',)


    def __init__(self, user, *args, **kwargs):
        # self.user = kwargs.pop('user', None)
        self.user_role = kwargs.pop('user_role', None)
        super(PolicyForm, self).__init__(*args, **kwargs)
        self.fields['title'].widget.attrs['placeholder'] = "Add title"
        self.fields['content'].widget.attrs['placeholder'] = "Tell your story..."
        self.fields['tags'].widget.attrs['placeholder'] = "Add a tag.."
        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                'class': 'form-control'
            })


@parsleyfy
class AddPrayerRequestForm(forms.ModelForm):
    area = forms.ChoiceField(
        label='Prayer Area', choices=REQUEST_CHOICE,
        required=True,
        error_messages={'required': 'Prayer Area is required.'},
    )
    message = forms.CharField(
        label='Request', max_length=7000, required=True,
        widget=forms.Textarea(
            attrs={'placeholder': 'Briefly tell us how we can pray for you'}
        ),
        error_messages={'required': 'Request field is required.'}
    )
    # is_done = forms.BooleanField(
    #     label='Prayer done', required=False,
    #     help_text=_('Designates whether this prayer request is done for praying.'),
    #     error_messages={'required': 'Is done field is required.'}
    # )

    class Meta:
        model = PrayerRequest
        fields = ['area', 'message', ]


@parsleyfy
class CommentForm(forms.ModelForm):
    content = forms.CharField(
        label="",
        widget=forms.Textarea(
            attrs={'class': 'form-control', 'placeholder': 'say something!!!', 'rows': '4', 'cols': '50'}
        )
    )

    class Meta:
        model = Comment
        fields = ('content',)


@parsleyfy
class BibleStudiesCommentForm(forms.ModelForm):
    content = forms.CharField(
        label="",
        widget=forms.Textarea(
            attrs={'class': 'form-control', 'placeholder': 'Write a response...', 'rows': '4', 'cols': '50'}
        )
    )

    class Meta:
        model = CommentsBibleStudies
        fields = ('content',)


@parsleyfy
class DevotionCommentForm(forms.ModelForm):
    content = forms.CharField(
        label="",
        widget=forms.Textarea(
            attrs={'class': 'form-control', 'placeholder': 'Write a response...', 'rows': '4', 'cols': '50'}
        )
    )

    class Meta:
        model = CommentsDevotion
        fields = ('content',)


@parsleyfy
class TechCommentForm(forms.ModelForm):
    content = forms.CharField(
        label="",
        widget=forms.Textarea(
            attrs={'class': 'form-control', 'placeholder': 'Write a response...', 'rows': '4', 'cols': '50'}
        )
    )

    class Meta:
        model = CommentsTech
        fields = ('content',)


@parsleyfy
class QuotesCommentForm(forms.ModelForm):
    content = forms.CharField(
        label="",
        widget=forms.Textarea(
            attrs={'class': 'form-control', 'placeholder': 'Write a response...', 'rows': '4', 'cols': '50'}
        )
    )

    class Meta:
        model = CommentsQuotes
        fields = ('content',)

@parsleyfy
class PolicyCommentForm(forms.ModelForm):
    content = forms.CharField(
        label="",
        widget=forms.Textarea(
            attrs={'class': 'form-control', 'placeholder': 'Write a response...', 'rows': '4', 'cols': '50'}
        )
    )

    class Meta:
        model = CommentsPolicy
        fields = ('content',)


class SearchForm(forms.Form):
    query = forms.CharField()

