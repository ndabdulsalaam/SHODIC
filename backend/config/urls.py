from django.contrib import admin
from django.urls import include, path

from config.views import health_check


urlpatterns = [
    path('admin/', admin.site.urls),
    path('rxchat/', include('rxchat.urls')),
    path('health/', health_check, name='health_check'),
]
