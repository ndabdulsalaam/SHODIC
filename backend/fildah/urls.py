from django.urls import path

from . import views


urlpatterns = [
    path('home/', views.home, name='fildah-home'),
    path('products/', views.products, name='fildah-products'),
    path('products/<slug:slug>/', views.product_detail, name='fildah-product-detail'),
    path('pages/<slug:slug>/', views.page_detail, name='fildah-page-detail'),
    path('docs/', views.docs, name='fildah-docs'),
    path('docs/<slug:slug>/', views.doc_detail, name='fildah-doc-detail'),
    path('blog/', views.blog, name='fildah-blog'),
    path('blog/<slug:slug>/', views.blog_detail, name='fildah-blog-detail'),
    path('contact/', views.contact, name='fildah-contact'),
    path('account/products/', views.account_products, name='fildah-account-products'),
    path('developers/api/', views.developer_api, name='fildah-developer-api'),
]
