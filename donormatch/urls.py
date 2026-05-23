from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/',        admin.site.urls),
    path('api/auth/',     include('core.urls')),
    path('api/hospital/', include('hospitals.urls')),
    path('api/requests/', include('blood_requests.urls')),
    path('api/payments/', include('payments.urls')),
    path('webhook/',      include('blood_requests.webhook_urls')),
    path('',              include('core.page_urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
