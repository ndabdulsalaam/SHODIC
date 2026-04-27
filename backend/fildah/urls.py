from django.urls import path

from . import views


urlpatterns = [
    path('home/', views.home, name='fildah-home'),
    path('products/', views.products, name='fildah-products'),
    path('docs/', views.docs, name='fildah-docs'),
    path('developers/api/', views.developer_api, name='fildah-developer-api'),
]
