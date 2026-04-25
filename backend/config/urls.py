from django.contrib import admin
from django.urls import path, include
from config.views import health_check

import config.admin_config  # noqa: F401 — registers RxChat admin branding

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/chat/', include('chat.urls')),
    path('api/auth/', include('accounts.urls')),
    path('api/health/', health_check, name='health_check'),
]
