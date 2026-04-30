from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import BlogPost, ContactMessage, DocumentationSection, Page, Product, ProductAccess
from .serializers import (
    account_summary_dict,
    blog_post_dict,
    doc_dict,
    page_dict,
    product_access_dict,
    product_dict,
)


BRAND = {
    "name": "Fildah",
    "tagline": "Health technology products built with care, trust, and practical support.",
    "description": (
        "Fildah is the parent brand for focused health and technology products, "
        "starting with RxChat."
    ),
}

NAVIGATION = [
    {"label": "Products", "path": "/products"},
    {"label": "Docs", "path": "/docs"},
    {"label": "Blog", "path": "/blog"},
    {"label": "About", "path": "/about"},
    {"label": "Support", "path": "/support"},
]


def _active_products():
    return Product.objects.filter(status__in=[Product.STATUS_ACTIVE, Product.STATUS_PRIVATE_BETA])


def _published_posts():
    return BlogPost.objects.published()


@api_view(["GET"])
@permission_classes([AllowAny])
def home(request):
    featured_products = list(_active_products().filter(is_featured=True))
    primary_product = featured_products[0] if featured_products else _active_products().first()
    recent_posts = _published_posts()[:3]

    return Response({
        "brand": BRAND,
        "navigation": NAVIGATION,
        "primary_product": product_dict(primary_product) if primary_product else None,
        "featured_products": [product_dict(product) for product in featured_products],
        "recent_posts": [blog_post_dict(post) for post in recent_posts],
        "trust_points": [
            {
                "title": "Privacy-aware by default",
                "summary": "Account, support, and product access flows are designed around clear user control.",
            },
            {
                "title": "Healthcare safety posture",
                "summary": "Health products carry careful boundaries, escalation guidance, and source-aware design.",
            },
            {
                "title": "Built for local realities",
                "summary": "Fildah products can reflect Nigeria-first workflows while remaining globally usable.",
            },
        ],
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def products(request):
    product_rows = _active_products()
    return Response({
        "products": [product_dict(product) for product in product_rows],
        "auth": {
            "shared_account": True,
            "namespace": "/auth/",
            "session_endpoint": "/auth/me/",
        },
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def product_detail(request, slug):
    product = get_object_or_404(_active_products(), slug=slug)
    return Response({"product": product_dict(product)})


@api_view(["GET"])
@permission_classes([AllowAny])
def page_detail(request, slug):
    page = get_object_or_404(Page.objects.published(), slug=slug)
    return Response({"page": page_dict(page)})


@api_view(["GET"])
@permission_classes([AllowAny])
def docs(request):
    sections = DocumentationSection.objects.published().select_related("product")
    return Response({"sections": [doc_dict(section) for section in sections]})


@api_view(["GET"])
@permission_classes([AllowAny])
def doc_detail(request, slug):
    section = get_object_or_404(
        DocumentationSection.objects.published().select_related("product"),
        slug=slug,
    )
    return Response({"section": doc_dict(section)})


@api_view(["GET"])
@permission_classes([AllowAny])
def blog(request):
    posts = _published_posts().select_related("product")
    return Response({"posts": [blog_post_dict(post) for post in posts]})


@api_view(["GET"])
@permission_classes([AllowAny])
def blog_detail(request, slug):
    post = get_object_or_404(_published_posts().select_related("product"), slug=slug)
    return Response({"post": blog_post_dict(post)})


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def contact(request):
    required_fields = ["name", "email", "topic", "message"]
    missing = [field for field in required_fields if not str(request.data.get(field, "")).strip()]
    if missing:
        return Response(
            {"error": "Please complete all required fields.", "fields": missing},
            status=status.HTTP_400_BAD_REQUEST,
        )

    product = None
    product_slug = str(request.data.get("product", "")).strip()
    if product_slug:
        product = Product.objects.filter(slug=product_slug).first()
        if product is None:
            return Response(
                {"error": "Choose a valid product."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    message = ContactMessage.objects.create(
        name=str(request.data["name"]).strip(),
        email=str(request.data["email"]).strip().lower(),
        company=str(request.data.get("company", "")).strip(),
        topic=str(request.data["topic"]).strip(),
        product=product,
        message=str(request.data["message"]).strip(),
    )

    return Response(
        {
            "message": "Thanks for reaching out. The Fildah team will review your message.",
            "id": message.id,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
def account_products(request):
    if not request.user.is_authenticated:
        return Response(
            {"error": "Authentication is required."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    access_rows = (
        ProductAccess.objects.select_related("product", "organization")
        .filter(user=request.user)
        .order_by("product__name")
    )
    return Response({
        **account_summary_dict(request.user),
        "product_access": [product_access_dict(access) for access in access_rows],
        "available_products": [product_dict(product) for product in _active_products()],
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def developer_api(request):
    product_namespaces = [
        {
            "name": product.name,
            "path": product.api_namespace,
            "frontend_url": product.frontend_url,
        }
        for product in Product.objects.exclude(api_namespace="")
    ]

    return Response({
        "base_url": "https://api.fildah.com",
        "local_base_url": "http://localhost:8000",
        "namespaces": [
            {
                "name": "Global auth",
                "path": "/auth/",
                "examples": ["/auth/me/", "/auth/login/", "/auth/logout/"],
            },
            *product_namespaces,
            {
                "name": "Fildah public metadata",
                "path": "/",
                "examples": [
                    "/home/",
                    "/products/",
                    "/docs/",
                    "/blog/",
                    "/contact/",
                    "/account/products/",
                ],
            },
        ],
    })
