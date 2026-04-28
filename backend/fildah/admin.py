from django.contrib import admin

from .models import (
    BlogPost,
    ContactMessage,
    DocumentationSection,
    Page,
    Product,
    ProductAccess,
)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "status", "category", "is_featured", "sort_order", "updated_at"]
    list_filter = ["status", "category", "is_featured"]
    search_fields = ["name", "slug", "tagline", "short_description"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["sort_order", "name"]


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ["title", "slug", "page_type", "is_published", "published_at", "updated_at"]
    list_filter = ["page_type", "is_published", "published_at"]
    search_fields = ["title", "slug", "summary", "body"]
    prepopulated_fields = {"slug": ("title",)}


@admin.register(DocumentationSection)
class DocumentationSectionAdmin(admin.ModelAdmin):
    list_display = ["title", "slug", "product", "is_published", "sort_order", "updated_at"]
    list_filter = ["product", "is_published", "published_at"]
    search_fields = ["title", "slug", "summary", "body"]
    prepopulated_fields = {"slug": ("title",)}
    ordering = ["sort_order", "title"]


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ["title", "slug", "status", "product", "is_published", "published_at"]
    list_filter = ["status", "product", "is_published", "published_at"]
    search_fields = ["title", "slug", "excerpt", "body"]
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "published_at"


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ["topic", "name", "email", "product", "status", "created_at"]
    list_filter = ["status", "topic", "product", "created_at"]
    search_fields = ["name", "email", "company", "topic", "message"]
    readonly_fields = ["name", "email", "company", "topic", "product", "message", "created_at", "updated_at"]


@admin.register(ProductAccess)
class ProductAccessAdmin(admin.ModelAdmin):
    list_display = ["user", "product", "organization", "role", "status", "updated_at"]
    list_filter = ["product", "role", "status"]
    search_fields = ["user__email", "product__name", "organization__name"]
    autocomplete_fields = ["user", "product", "organization"]
