from django.urls import path
from . import webhook_views

urlpatterns = [
    path('inbound/donors-found/',        webhook_views.donors_found,       name='wh-donors-found'),
    path('inbound/availability-result/', webhook_views.availability_result, name='wh-availability'),
    # legacy path — keep so old n8n configs still work
    path('n8n/donors-found/',            webhook_views.donors_found,       name='wh-donors-found-legacy'),
    path('n8n/availability-result/',     webhook_views.availability_result, name='wh-availability-legacy'),
]