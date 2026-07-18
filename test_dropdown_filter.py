import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from unfold.contrib.filters.admin import RelatedDropdownFilter
from moneylog.models import Movement
from moneylog.admin import MovementAdmin
from django.contrib.admin.sites import site
from django.contrib.auth.models import User
from django.test import RequestFactory

class UserRelatedDropdownFilter(RelatedDropdownFilter):
    def field_choices(self, field, request, model_admin):
        return field.get_choices(include_blank=False, limit_choices_to={'user': request.user})

request = RequestFactory().get('/admin/')
request.user = User.objects.first()

field = Movement._meta.get_field('category')
filter_instance = UserRelatedDropdownFilter(field, request, {}, Movement, MovementAdmin(Movement, site), 'category')
print("Choices:", filter_instance.lookup_choices)

