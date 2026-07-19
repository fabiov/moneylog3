import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

import inspect
from unfold.decorators import display
print(inspect.signature(display))
