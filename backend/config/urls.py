from django.contrib import admin
from django.views.generic import RedirectView
from django.urls import include, path

from config.views import health_check


urlpatterns = [
    path('', RedirectView.as_view(pattern_name='admin:index', permanent=False)),
    path('admin/', admin.site.urls),
    path('shodic/', include('shodic.urls')),
    path('health/', health_check, name='health_check'),
]
