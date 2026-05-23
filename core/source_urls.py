from django.urls import path
from . import source_views

urlpatterns = [
    path('',       source_views.list_sources,  name='sources-list'),
    path('reload/', source_views.reload_sources, name='sources-reload'),
]
