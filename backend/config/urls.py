from django.contrib import admin
from django.views.generic import RedirectView
from django.urls import include, path

from config.views import health_check
from shodic.admin import ingestion_admin_view


urlpatterns = [
    path('', RedirectView.as_view(pattern_name='admin:index', permanent=False)),
    path('admin/shodic/ingestion/', admin.site.admin_view(ingestion_admin_view), name='shodic_ingestion'),
    path('admin/', admin.site.urls),
    path('shodic/', include('shodic.urls')),
    path('health/', health_check, name='health_check'),
]
