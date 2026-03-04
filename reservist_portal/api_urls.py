from django.urls import path
from . import api

urlpatterns = [
    path('incidents/', api.incidents_geojson, name='api_incidents_geojson'),
]
