from django.urls import path
from config.debug_static import debug_static_view

urlpatterns = [
    path('', debug_static_view, name='debug-static'),
]
