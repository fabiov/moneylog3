import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from unfold.contrib.filters.forms import RangeDateForm, RangeNumericForm
f1 = RangeDateForm(name='date')
f2 = RangeNumericForm(name='amount')
print(f1.fields.keys())
print(f2.fields.keys())
