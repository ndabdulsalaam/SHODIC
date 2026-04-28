from django.db import migrations
from django.utils import timezone


def seed_initial_parent_platform(apps, schema_editor):
    Product = apps.get_model("fildah", "Product")
    Page = apps.get_model("fildah", "Page")
    DocumentationSection = apps.get_model("fildah", "DocumentationSection")
    BlogPost = apps.get_model("fildah", "BlogPost")

    now = timezone.now()

    rxchat, _created = Product.objects.update_or_create(
        slug="rxchat",
        defaults={
            "name": "RxChat",
            "tagline": "Medication answers and pharmacy guidance with practical safety boundaries.",
            "short_description": (
                "An AI pharmacy assistant for medication questions, drug information, "
                "and safer health decisions."
            ),
            "long_description": (
                "RxChat is the first product under Fildah. It helps people ask clearer "
                "questions about medicines, possible interactions, OTC choices, and "
                "healthcare next steps while keeping clinical safety guidance visible."
            ),
            "category": "Health AI",
            "status": "active",
            "marketing_path": "/products/rxchat",
            "frontend_url": "https://rxchat.fildah.com",
            "api_namespace": "/rxchat/",
            "primary_color": "#5CB832",
            "secondary_color": "#1A6BC4",
            "is_featured": True,
            "sort_order": 10,
        },
    )

    Page.objects.update_or_create(
        slug="about",
        defaults={
            "title": "About Fildah",
            "page_type": "about",
            "summary": (
                "Fildah is a parent brand for focused health and technology products "
                "that are useful, trustworthy, and built for real-world workflows."
            ),
            "body": (
                "Fildah builds practical technology products with a health-first sense "
                "of responsibility. The company platform exists to make each product "
                "easy to discover, understand, support, and grow without forcing every "
                "new idea into the same interface.\n\n"
                "RxChat is the first product in the Fildah family. Future products can "
                "join the same parent platform while keeping their own product identity, "
                "domain, routes, and user experience."
            ),
            "seo_title": "About Fildah",
            "seo_description": "Learn about Fildah, the parent brand behind RxChat.",
            "is_published": True,
            "published_at": now,
        },
    )

    DocumentationSection.objects.update_or_create(
        slug="overview",
        defaults={
            "title": "Fildah overview",
            "summary": "How the Fildah parent platform, product websites, and shared API fit together.",
            "body": (
                "Fildah is the central brand and product directory. Product experiences "
                "such as RxChat can run on their own subdomains while the shared backend "
                "keeps common services like authentication and product metadata available."
            ),
            "product": None,
            "sort_order": 10,
            "is_published": True,
            "published_at": now,
        },
    )
    DocumentationSection.objects.update_or_create(
        slug="rxchat",
        defaults={
            "title": "RxChat",
            "summary": "Product notes for the RxChat pharmacy assistant frontend and API namespace.",
            "body": (
                "RxChat lives at rxchat.fildah.com and uses the /rxchat/ API namespace. "
                "Its product UI, safety copy, and color palette remain separate from the "
                "parent Fildah website."
            ),
            "product": rxchat,
            "sort_order": 20,
            "is_published": True,
            "published_at": now,
        },
    )
    DocumentationSection.objects.update_or_create(
        slug="auth",
        defaults={
            "title": "Authentication",
            "summary": "Global sign-in routes shared by Fildah products.",
            "body": (
                "Authentication is served from the shared /auth/ namespace. Product apps "
                "can use the same session-aware endpoints while keeping their own frontend "
                "routing and onboarding flows."
            ),
            "product": None,
            "sort_order": 30,
            "is_published": True,
            "published_at": now,
        },
    )

    BlogPost.objects.update_or_create(
        slug="introducing-fildah",
        defaults={
            "title": "Introducing Fildah",
            "excerpt": "Fildah is the parent platform for RxChat and future focused products.",
            "body": (
                "Fildah now acts as the home for product discovery, support, documentation, "
                "and account access. RxChat remains the first live product under the brand."
            ),
            "product": rxchat,
            "status": "published",
            "is_published": True,
            "published_at": now,
        },
    )


def unseed_initial_parent_platform(apps, schema_editor):
    BlogPost = apps.get_model("fildah", "BlogPost")
    DocumentationSection = apps.get_model("fildah", "DocumentationSection")
    Page = apps.get_model("fildah", "Page")
    Product = apps.get_model("fildah", "Product")

    BlogPost.objects.filter(slug="introducing-fildah").delete()
    DocumentationSection.objects.filter(slug__in=["overview", "rxchat", "auth"]).delete()
    Page.objects.filter(slug="about").delete()
    Product.objects.filter(slug="rxchat").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("fildah", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_initial_parent_platform, unseed_initial_parent_platform),
    ]
