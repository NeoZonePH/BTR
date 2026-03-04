import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TARGET.settings')
django.setup()

from users.models import User

# Migrate RCDG
for u in User.objects.filter(role='RCDG').exclude(latitude__isnull=True):
    if u.assigned_rcdg:
        if not u.assigned_rcdg.latitude:
            u.assigned_rcdg.latitude = str(u.latitude)[:50]
        if not u.assigned_rcdg.longitude:
            u.assigned_rcdg.longitude = str(u.longitude)[:50]
        u.assigned_rcdg.save()
        print(f"Migrated loc for RCDG {u.full_name}")

# Migrate CDC
for u in User.objects.filter(role='CDC').exclude(latitude__isnull=True):
    if u.assigned_cdc:
        if not u.assigned_cdc.latitude:
            u.assigned_cdc.latitude = str(u.latitude)[:50]
        if not u.assigned_cdc.longitude:
            u.assigned_cdc.longitude = str(u.longitude)[:50]
        u.assigned_cdc.save()
        print(f"Migrated loc for CDC {u.full_name}")
