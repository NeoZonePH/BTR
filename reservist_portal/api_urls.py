from django.urls import path
from . import api

urlpatterns = [
    path('incidents/', api.incidents_geojson, name='api_incidents_geojson'),
    path('responder/update-location/', api.update_responder_location, name='api_update_location'),
    path('responder/stop/', api.stop_responder, name='api_stop_responder'),
    path('responders/active/', api.active_responders_list, name='api_active_responders'),
]
