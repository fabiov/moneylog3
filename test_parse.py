import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from unfold.contrib.filters.admin.datetime_filters import parse_date_str
print("Parsing 18/07/2026:", parse_date_str('18/07/2026'))
print("Parsing 2026-07-18:", parse_date_str('2026-07-18'))
