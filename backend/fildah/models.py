from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class PublishedQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_published=True).filter(
            models.Q(published_at__isnull=True) | models.Q(published_at__lte=timezone.now())
        )


class Product(models.Model):
    STATUS_PLANNED = "planned"
    STATUS_PRIVATE_BETA = "private_beta"
    STATUS_ACTIVE = "active"
    STATUS_DEPRECATED = "deprecated"
    STATUS_CHOICES = [
        (STATUS_PLANNED, "Planned"),
        (STATUS_PRIVATE_BETA, "Private beta"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_DEPRECATED, "Deprecated"),
    ]

    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    tagline = models.CharField(max_length=180, blank=True)
    short_description = models.CharField(max_length=280)
    long_description = models.TextField(blank=True)
    category = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PLANNED)
    marketing_path = models.CharField(max_length=160, blank=True)
    frontend_url = models.URLField(blank=True)
    api_namespace = models.CharField(max_length=80, blank=True)
    primary_color = models.CharField(max_length=20, default="#4f8f70")
    secondary_color = models.CharField(max_length=20, default="#d8a85b")
    logo_url = models.URLField(blank=True)
    icon_url = models.URLField(blank=True)
    is_featured = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class Page(models.Model):
    TYPE_ABOUT = "about"
    TYPE_LEGAL = "legal"
    TYPE_CUSTOM = "custom"
    PAGE_TYPE_CHOICES = [
        (TYPE_ABOUT, "About"),
        (TYPE_LEGAL, "Legal"),
        (TYPE_CUSTOM, "Custom"),
    ]

    title = models.CharField(max_length=180)
    slug = models.SlugField(unique=True)
    page_type = models.CharField(max_length=20, choices=PAGE_TYPE_CHOICES, default=TYPE_CUSTOM)
    summary = models.CharField(max_length=280, blank=True)
    body = models.TextField()
    seo_title = models.CharField(max_length=180, blank=True)
    seo_description = models.CharField(max_length=300, blank=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PublishedQuerySet.as_manager()

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class DocumentationSection(models.Model):
    title = models.CharField(max_length=180)
    slug = models.SlugField(unique=True)
    summary = models.CharField(max_length=280, blank=True)
    body = models.TextField()
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name="docs")
    sort_order = models.PositiveIntegerField(default=100)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PublishedQuerySet.as_manager()

    class Meta:
        ordering = ["sort_order", "title"]

    def __str__(self):
        return self.title


class BlogPost(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"
    STATUS_ARCHIVED = "archived"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_PUBLISHED, "Published"),
        (STATUS_ARCHIVED, "Archived"),
    ]

    title = models.CharField(max_length=180)
    slug = models.SlugField(unique=True)
    excerpt = models.CharField(max_length=320, blank=True)
    body = models.TextField()
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name="blog_posts")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PublishedQuerySet.as_manager()

    class Meta:
        ordering = ["-published_at", "-created_at"]

    def __str__(self):
        return self.title


class ContactMessage(models.Model):
    STATUS_NEW = "new"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = [
        (STATUS_NEW, "New"),
        (STATUS_IN_PROGRESS, "In progress"),
        (STATUS_CLOSED, "Closed"),
    ]

    name = models.CharField(max_length=160)
    email = models.EmailField()
    company = models.CharField(max_length=160, blank=True)
    topic = models.CharField(max_length=120)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name="contact_messages")
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_NEW)
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.topic} from {self.email}"


class ProductAccess(models.Model):
    ROLE_OWNER = "owner"
    ROLE_ADMIN = "admin"
    ROLE_MEMBER = "member"
    ROLE_VIEWER = "viewer"
    ROLE_CHOICES = [
        (ROLE_OWNER, "Owner"),
        (ROLE_ADMIN, "Admin"),
        (ROLE_MEMBER, "Member"),
        (ROLE_VIEWER, "Viewer"),
    ]

    STATUS_ACTIVE = "active"
    STATUS_INVITED = "invited"
    STATUS_SUSPENDED = "suspended"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_INVITED, "Invited"),
        (STATUS_SUSPENDED, "Suspended"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="fildah_product_access")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="user_access")
    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="product_access",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_VIEWER)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["product__name", "role"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "product", "organization"],
                name="unique_product_access_per_user_org",
            ),
        ]

    def __str__(self):
        org = f" @ {self.organization.name}" if self.organization else ""
        return f"{self.user.email} - {self.product.name}{org}"
