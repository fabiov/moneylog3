import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.test import RequestFactory
from moneylog.models import Movement
from moneylog.admin import MovementAdmin
from django.contrib.admin.sites import site
from django.contrib.auth.models import User

user = User.objects.first()
factory = RequestFactory()
request = factory.get('/admin/moneylog/movement/?date_from=2024-01-01&amount_from=10')
request.user = user

ma = MovementAdmin(Movement, site)
cl = ma.get_changelist_instance(request)
qs = cl.get_queryset(request)
print("Query parameters:", request.GET)
print("Filters applied:", cl.get_filters(request))
print("Queryset:", qs.query)
