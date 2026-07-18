import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()
from django.test import RequestFactory
from moneylog.models import Movement
from moneylog.admin import MovementAdmin
from django.contrib.admin.sites import site
from django.contrib.auth.models import User
request = RequestFactory().get('/admin/moneylog/movement/')
request.user = User.objects.first()
ma = MovementAdmin(Movement, site)
response = ma.changelist_view(request)
if hasattr(response, 'render'): response.render()
html = response.content.decode('utf-8')
import re
match = re.search(r'<form id="filter-form".*?</form>', html, re.DOTALL)
if match:
    filter_form_html = match.group(0)
    print("Submit elements in filter-form:")
    for m in re.finditer(r'<button[^>]*>.*?</button>|<input[^>]*type="submit"[^>]*>', filter_form_html, re.IGNORECASE | re.DOTALL):
        print(m.group(0))
else:
    print("filter-form not found")
