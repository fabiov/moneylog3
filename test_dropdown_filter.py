import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from unfold.contrib.filters.admin import RelatedDropdownFilter
from moneylog.models import Movement
from moneylog.admin import MovementAdmin, UserRelatedDropdownFilter
from django.contrib.admin.sites import site
from django.contrib.auth.models import User
from django.test import RequestFactory

request = RequestFactory().get('/admin/')
request.user = User.objects.first()

field = Movement._meta.get_field('category')
filter_instance = UserRelatedDropdownFilter(field, request, {}, Movement, MovementAdmin(Movement, site), 'category')
print("Choices:", filter_instance.lookup_choices)

