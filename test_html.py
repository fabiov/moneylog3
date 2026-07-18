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
request = factory.get('/admin/moneylog/movement/')
request.user = user

ma = MovementAdmin(Movement, site)
response = ma.changelist_view(request)
if hasattr(response, 'render'):
    response.render()
html = response.content.decode('utf-8')

import re
print("Form tags:")
for m in re.finditer(r'<form[^>]*>', html):
    print(m.group(0))

print("\nFilter inputs:")
for m in re.finditer(r'<input[^>]*name="(date_from|date_to|amount_from|amount_to)"[^>]*>', html):
    print(m.group(0))

print("\nSubmit button in filters:")
for m in re.finditer(r'<button[^>]*>.*Applica.*</button>|<button[^>]*type="submit"[^>]*>.*</button>', html, re.IGNORECASE):
    print(m.group(0))
