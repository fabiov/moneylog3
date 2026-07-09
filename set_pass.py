import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()
from django.contrib.auth.models import User
u = User.objects.get(username='fabio')
u.set_password('password123')
# Also make him superuser to login to django admin!
u.is_staff = True
u.is_superuser = True
u.save()
print("Passwords updated!")
