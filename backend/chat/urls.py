from django.urls import path
from . import views

urlpatterns = [
    path('send/', views.send_message, name='send-message'),
    path('conversations/', views.list_conversations, name='list-conversations'),
    path('conversations/<uuid:conversation_id>/', views.get_conversation, name='get-conversation'),
    path('conversations/<uuid:conversation_id>/delete/', views.delete_conversation, name='delete-conversation'),
]
