from django.urls import path
from . import webhook_views

urlpatterns = [
    # Any configured source can call these — not just N8N
    path('inbound/donors-found/',       webhook_views.donors_found,       name='wh-donors-found'),
    path('inbound/availability-result/', webhook_views.availability_result, name='wh-availability'),
]
