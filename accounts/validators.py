import re
import os
from django.core.exceptions import ValidationError
from django.core import validators
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _


@deconstructible
class ASCIIUsernameValidator(validators.RegexValidator):
    regex = r'^[\w.@+-]+$'
    message = _(
        'Enter a valid username. This value may contain only English letters, '
        'numbers, and @/./+/-/_ characters.'
    )
    flags = re.ASCII


@deconstructible
class UnicodeUsernameValidator(validators.RegexValidator):
    regex = r'^[\w.@+-]+$'
    message = _(
        'Enter a valid username. This value may contain only letters, '
        'numbers, and @/./+/-/_ characters.'
    )
    flags = 0


@deconstructible
class UnicodeEmailValidator(validators.RegexValidator):
    regex = r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$'
    message = _(
        'Enter a valid email address. This value may contain only letters, '
        'numbers, and @/./com characters.'
    )
    flags = 0


def validate_file_extension(value):
    ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
    valid_extensions = ['.mp4', ]
    if not ext.lower() in valid_extensions:
        raise ValidationError(u'Unsupported file extension.')


def validate_Image_extension(value):
    ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
    valid_extensions = ['.png', '.jpg', '.jpeg', '.gif', ]
    if not ext.lower() in valid_extensions:
        raise ValidationError(u'Unsupported file extension.')
