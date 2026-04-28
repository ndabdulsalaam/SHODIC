import json

from django.contrib.auth.models import User
from django.test import TestCase

from .models import ContactMessage, Product, ProductAccess


class FildahPublicApiTests(TestCase):
    def test_home_endpoint_returns_database_backed_brand_metadata(self):
        response = self.client.get("/home/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["brand"]["name"], "Fildah")
        self.assertEqual(payload["primary_product"]["slug"], "rxchat")
        self.assertEqual(payload["featured_products"][0]["frontend_url"], "https://rxchat.fildah.com")
        self.assertEqual(len(payload["trust_points"]), 3)

    def test_products_endpoint_describes_shared_auth_and_rxchat(self):
        response = self.client.get("/products/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["auth"]["namespace"], "/auth/")
        self.assertEqual(payload["products"][0]["api_namespace"], "/rxchat/")

    def test_product_detail_endpoint_returns_rxchat(self):
        response = self.client.get("/products/rxchat/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["product"]["name"], "RxChat")
        self.assertEqual(payload["product"]["marketing_path"], "/products/rxchat")

    def test_page_detail_endpoint_returns_about_page(self):
        response = self.client.get("/pages/about/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["page"]["title"], "About Fildah")

    def test_docs_endpoint_returns_seeded_sections(self):
        response = self.client.get("/docs/")

        self.assertEqual(response.status_code, 200)
        section_slugs = {section["slug"] for section in response.json()["sections"]}
        self.assertIn("overview", section_slugs)
        self.assertIn("rxchat", section_slugs)

    def test_doc_detail_endpoint_returns_section(self):
        response = self.client.get("/docs/rxchat/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["section"]["product"]["slug"], "rxchat")

    def test_blog_endpoint_returns_published_posts(self):
        response = self.client.get("/blog/")

        self.assertEqual(response.status_code, 200)
        post_slugs = {post["slug"] for post in response.json()["posts"]}
        self.assertIn("introducing-fildah", post_slugs)

    def test_contact_endpoint_creates_message(self):
        response = self.client.post(
            "/contact/",
            data=json.dumps({
                "name": "Amina Bello",
                "email": "amina@example.com",
                "company": "Care Clinic",
                "topic": "Partnership",
                "product": "rxchat",
                "message": "We would like to discuss RxChat for our team.",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        message = ContactMessage.objects.get(email="amina@example.com")
        self.assertEqual(message.product.slug, "rxchat")
        self.assertEqual(message.status, ContactMessage.STATUS_NEW)

    def test_developer_api_endpoint_lists_root_and_product_namespaces(self):
        response = self.client.get("/developers/api/")

        self.assertEqual(response.status_code, 200)
        paths = {namespace["path"] for namespace in response.json()["namespaces"]}
        self.assertEqual(
            paths,
            {"/", "/auth/", "/rxchat/"},
        )


class FildahAccountApiTests(TestCase):
    def test_account_products_requires_authentication(self):
        response = self.client.get("/account/products/")

        self.assertEqual(response.status_code, 401)

    def test_account_products_returns_access_and_available_products(self):
        user = User.objects.create_user(
            username="member@example.com",
            email="member@example.com",
            password="password-123",
        )
        rxchat = Product.objects.get(slug="rxchat")
        ProductAccess.objects.create(
            user=user,
            product=rxchat,
            role=ProductAccess.ROLE_MEMBER,
        )
        self.client.force_login(user)

        response = self.client.get("/account/products/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["user"]["email"], "member@example.com")
        self.assertEqual(payload["product_access"][0]["product"]["slug"], "rxchat")
        self.assertEqual(payload["available_products"][0]["slug"], "rxchat")
