from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/incident/(?P<incident_id>\w+)/tracking/$', consumers.IncidentTrackingConsumer.as_asgi()),
]
