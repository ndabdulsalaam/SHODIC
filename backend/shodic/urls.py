from django.urls import path
from . import views

urlpatterns = [
    path('send/', views.send_message, name='send-message'),
    path('conversations/', views.list_conversations, name='list-conversations'),
    path('conversations/<uuid:conversation_id>/', views.get_conversation, name='get-conversation'),
    path('conversations/<uuid:conversation_id>/delete/', views.delete_conversation, name='delete-conversation'),
    path('conversations/<uuid:conversation_id>/rename/', views.rename_conversation, name='rename-conversation'),
    path('messages/<uuid:message_id>/', views.edit_message, name='edit-message'),
    path('messages/<uuid:message_id>/resend/', views.resend_message, name='resend-message'),
]

