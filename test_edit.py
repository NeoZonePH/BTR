import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lphm.settings')
django.setup()

from reservist_portal.models import Incident
from users.models import User
from django.test import Client

user = User.objects.filter(role='RESERVIST').first()
if not user:
    print("No reservist found.")
    exit(1)

incident = Incident.objects.filter(reservist=user, is_deleted=False).first()
if not incident:
    print("Creating test incident...")
    incident = Incident.objects.create(
        reservist=user,
        title="Test Incident for Edit",
        description="Original description",
        incident_type="FIRE",
        latitude=14.5995,
        longitude=120.9842,
        region="NATIONAL CAPITAL REGION (NCR)",
        province="NCR, CITY OF MANILA, FIRST DISTRICT",
        municipality="CITY OF MANILA",
        barangay="Barangay 1"
    )

print(f"Testing edit for Incident ID {incident.pk}")
client = Client()
client.force_login(user)

# GET form
response = client.get(f'/reservist/incidents/{incident.pk}/edit/')
print(f"GET /edit/: {response.status_code}")
if '<form' in response.content.decode():
    print("Form loaded successfully.")
else:
    print("Form failed to load.")

# POST update
response = client.post(f'/reservist/incidents/{incident.pk}/edit/', {
    'title': 'Updated Incident Title',
    'description': 'Updated description',
    'incident_type': 'FLOOD',
    'latitude': 14.6,
    'longitude': 120.9,
    'region': incident.region,
    'province': incident.province,
    'municipality': incident.municipality,
    'barangay': incident.barangay
})
print(f"POST /edit/: {response.status_code}")

incident.refresh_from_db()
if incident.title == 'Updated Incident Title' and incident.incident_type == 'FLOOD':
    print("SUCCESS: Incident was updated.")
else:
    print("FAILED to update incident.")
