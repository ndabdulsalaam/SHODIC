from django.contrib import admin
from django.urls import path, include
from config.views import health_check, root_redirect

import config.admin_config  # noqa: F401 — registers Fildah admin branding

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', root_redirect),
    path('', include('fildah.urls')),
    path('rxchat/', include('rxchat.urls')),
    path('auth/', include('accounts.urls')),
    path('health/', health_check, name='health_check'),
]
