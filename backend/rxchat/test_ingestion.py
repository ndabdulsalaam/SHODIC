import importlib.util
import json
import tempfile
from pathlib import Path
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from rxchat.ingestion.storage import save_clean_record
from rxchat.ingestion.nafdac_parser import parse_nafdac, products_to_chunks
from rxchat.ingestion.nafdac_scraper import parse_detail_html, parse_listing_html
from rxchat.ingestion.source_status import source_status_rows
from rxchat.models import CleanData, DrugChunk, RawData, SOURCE_CHOICES


HAS_BS4 = importlib.util.find_spec("bs4") is not None


class NAFDACHtmlParserTests(TestCase):
    @skipUnless(HAS_BS4, "beautifulsoup4 is not installed")
    def test_listing_parser_extracts_detail_links(self):
        parsed = parse_listing_html(
            """
            <a href="/products/details/12">Amoxil Capsule NRN: A4-100153</a>
            <a href="/products/details/12">Duplicate</a>
            """,
            category_id=1,
            url="https://greenbook.nafdac.gov.ng/productCategory/products/1",
        )

        self.assertEqual(len(parsed.records), 1)
        self.assertEqual(parsed.records[0]["product_id"], 12)
        self.assertEqual(parsed.records[0]["nrn"], "A4-100153")

    @skipUnless(HAS_BS4, "beautifulsoup4 is not installed")
    def test_detail_parser_keeps_expired_status(self):
        detail = parse_detail_html(
            """
            <h3>Product Details</h3>
            <div>OLDTABS</div>
            <div>Paracetamol</div>
            <div>500 mg</div>
            <div>Tablet</div>
            <div>ROA</div><div>Oral</div>
            <div>Applicant Name</div><div>Ada Pharma</div>
            <div>NRN</div><div>A4-0001</div>
            <div>Status</div><div>Expired</div>
            <div>ATC Code/ATCvet Code</div><div>N02BE01</div>
            <div>Product Category</div><div>Drugs</div>
            <div>Manufacturer Name</div><div>Ada Factory</div>
            <div>Approval Date</div><div>2020-01-01</div>
            <div>Expiry Date</div><div>2025-01-01</div>
            """,
            product_id=12,
            source_url="https://greenbook.nafdac.gov.ng/products/details/12",
        )

        self.assertEqual(detail["product_name"], "OLDTABS")
        self.assertEqual(detail["status"], "Expired")
        self.assertEqual(detail["active_ingredients"], [{"name": "Paracetamol", "strength": "500 mg"}])


class IngestionPipelineTests(TestCase):
    def _nafdac_clean(self, source_id, product_id, product_name, status, extra=None):
        """Helper: create a nafdac CleanData row as the scraper would."""
        data = {
            "record_type": "product_detail",
            "product_id": product_id,
            "product_name": product_name,
            "active_ingredients": [{"name": "Paracetamol", "strength": "500 mg"}],
            "status": status,
            "category": "Drugs",
            "nrn": f"A4-{source_id}",
            "source_url": f"https://greenbook.nafdac.gov.ng/products/details/{source_id}",
            **(extra or {}),
        }
        clean = save_clean_record("nafdac", source_id, raw_text=str(data))
        # Simulate accept() storing the structured dict
        clean.data = data
        clean.status = CleanData.STATUS_ACCEPTED
        clean.save(update_fields=["data", "status", "updated_at"])
        return clean

    def test_nafdac_parser_labels_inactive_product_and_suggests_active_alternative(self):
        self._nafdac_clean("1", 1, "Old Para", "Expired")
        self._nafdac_clean("2", 2, "Active Para", "Active")

        products, chunks = parse_nafdac()
        old_product = next(p for p in products if p["product_id"] == 1)
        old_chunk = next(c for c in chunks if c.record_id == "1")

        self.assertFalse(old_product["is_active"])
        self.assertIn("not currently marked active", old_chunk.text)
        self.assertIn("Active Para", old_chunk.text)
        self.assertEqual(DrugChunk.objects.count(), 2)

    def test_source_status_reports_missing_manual_files(self):
        rows = source_status_rows()

        neml_adults = next(row for row in rows if row["source"] == "NEML Adults")
        openfda = next(row for row in rows if row["source"] == "OpenFDA")
        emdex = next(row for row in rows if row["source"] == "EMDEX")
        self.assertEqual(neml_adults["status"], "missing")
        self.assertIn("python manage.py pull_openfda", openfda["command"])
        self.assertEqual(emdex["type"], "Licensed upload")

    def test_source_choices_include_emdex_as_seventh_source(self):
        self.assertEqual(len(SOURCE_CHOICES), 7)
        self.assertIn(("emdex", "EMDEX"), SOURCE_CHOICES)

    def test_parse_data_command_creates_draft_clean_records(self):
        """parse_data writes draft CleanData; ingest_drugs skips non-accepted records."""
        with tempfile.TemporaryDirectory() as tmp:
            with override_settings(MEDIA_ROOT=tmp):
                RawData.objects.create(
                    source="neml",
                    file=SimpleUploadedFile("neml_notes.txt", b"Paracetamol tablet 500 mg"),
                )
                call_command("parse_data", "--source", "neml")

                self.assertTrue(CleanData.objects.filter(source="neml", status=CleanData.STATUS_DRAFT).exists())
                # ingest_drugs should NOT create chunks yet (none accepted)
                call_command("ingest_drugs", "--source", "neml")
                self.assertEqual(DrugChunk.objects.filter(clean_data__source="neml").count(), 0)

    def test_parse_data_skips_uploads_that_already_have_clean_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            with override_settings(MEDIA_ROOT=tmp):
                RawData.objects.create(
                    source="neml",
                    file=SimpleUploadedFile("neml_notes.txt", b"Paracetamol tablet 500 mg"),
                )
                call_command("parse_data", "--source", "neml")
                clean = CleanData.objects.get(source="neml")
                clean.status = CleanData.STATUS_ACCEPTED
                clean.raw_text = "Reviewed text"
                clean.save(update_fields=["status", "raw_text", "updated_at"])

                call_command("parse_data", "--source", "neml")

                clean.refresh_from_db()
                self.assertEqual(clean.status, CleanData.STATUS_ACCEPTED)
                self.assertEqual(clean.raw_text, "Reviewed text")

    def test_ingest_drugs_processes_accepted_clean_records(self):
        """ingest_drugs creates DrugChunk rows from accepted CleanData."""
        with tempfile.TemporaryDirectory() as tmp:
            with override_settings(MEDIA_ROOT=tmp):
                raw = RawData.objects.create(
                    source="neml",
                    file=SimpleUploadedFile("neml_notes.txt", b"Paracetamol tablet 500 mg"),
                )
                call_command("parse_data", "--source", "neml")
                # Accept the draft record
                CleanData.objects.filter(source="neml").update(status=CleanData.STATUS_ACCEPTED)
                call_command("ingest_drugs", "--source", "neml")

                self.assertTrue(DrugChunk.objects.filter(clean_data__source="neml").exists())

    def test_accept_structured_scraper_text_keeps_parser_shape(self):
        data = {
            "record_type": "product_detail",
            "product_id": 7,
            "product_name": "Structured Para",
            "active_ingredients": [{"name": "Paracetamol", "strength": "500 mg"}],
            "status": "Active",
            "category": "Drugs",
        }
        clean = save_clean_record("nafdac", "7", raw_text=json.dumps(data))

        clean.accept()
        products, chunks = parse_nafdac()

        clean.refresh_from_db()
        self.assertEqual(clean.data["record_type"], "product_detail")
        self.assertEqual(products[0]["product_name"], "Structured Para")
        self.assertEqual(len(chunks), 1)
        self.assertEqual(clean.status, CleanData.STATUS_CHUNKED)

    @patch("rxchat.qdrant_service.delete_points")
    def test_reset_to_draft_removes_existing_chunks_and_vectors(self, delete_points):
        clean = save_clean_record("nafdac", "reset-me", raw_text="reset me")
        clean.status = CleanData.STATUS_CHUNKED
        clean.data = {"record_type": "product_detail"}
        clean.save(update_fields=["status", "data", "updated_at"])
        DrugChunk.objects.create(clean_data=clean, chunk_index=1, text="Reset", qdrant_point_id="point-1")

        clean.reset_to_draft()

        self.assertFalse(clean.chunks.exists())
        delete_points.assert_called_once_with(["point-1"])
        clean.refresh_from_db()
        self.assertEqual(clean.status, CleanData.STATUS_DRAFT)
        self.assertEqual(clean.data, {})

    @patch("rxchat.qdrant_service.delete_points")
    def test_clean_data_delete_removes_qdrant_vectors(self, delete_points):
        clean = save_clean_record("nafdac", "delete-me", raw_text="delete me")
        DrugChunk.objects.create(clean_data=clean, chunk_index=1, text="Delete", qdrant_point_id="point-1")

        clean.delete()

        delete_points.assert_called_once_with(["point-1"])

    @patch("rxchat.qdrant_service.delete_points")
    def test_raw_data_delete_cascades_to_clean_data_and_qdrant(self, delete_points):
        with tempfile.TemporaryDirectory() as tmp:
            with override_settings(MEDIA_ROOT=tmp):
                raw = RawData.objects.create(
                    source="neml",
                    file=SimpleUploadedFile("neml_notes.txt", b"Paracetamol tablet 500 mg"),
                )
                clean = save_clean_record("neml", f"upload:{raw.pk}", raw_text="Paracetamol")
                clean.raw = raw
                clean.save(update_fields=["raw"])
                DrugChunk.objects.create(clean_data=clean, chunk_index=1, text="Delete", qdrant_point_id="point-1")

                raw.delete()

        self.assertFalse(CleanData.objects.filter(source="neml", source_id=f"upload:{raw.pk}").exists())
        delete_points.assert_called_once_with(["point-1"])


class QdrantHybridTests(TestCase):
    class FakeQdrantClient:
        def __init__(self):
            self.upserted_points = []
            self.query_kwargs = {}
            self.created_indexes = []

        def get_collection(self, collection_name):
            return {"name": collection_name}

        def create_payload_index(self, **kwargs):
            self.created_indexes.append(kwargs)

        def upsert(self, collection_name, points):
            self.collection_name = collection_name
            self.upserted_points.extend(points)

        def query_points(self, **kwargs):
            self.query_kwargs = kwargs
            return type("Result", (), {"points": []})()

    @override_settings(
        QDRANT_COLLECTION="rxchat",
        QDRANT_INFERENCE_MODEL="intfloat/multilingual-e5-small",
        QDRANT_SPARSE_MODEL="qdrant/bm25",
        QDRANT_DENSE_VECTOR_NAME="dense",
        QDRANT_SPARSE_VECTOR_NAME="sparse",
        QDRANT_VECTOR_SIZE=384,
    )
    @patch("rxchat.qdrant_service._get_client")
    def test_upsert_uses_dense_and_bm25_named_vectors(self, get_client):
        from rxchat.qdrant_service import upsert_drug_chunks

        fake_client = self.FakeQdrantClient()
        get_client.return_value = fake_client
        clean = save_clean_record("nafdac", "vector-test", raw_text="vector test")
        chunk = DrugChunk.objects.create(clean_data=clean, chunk_index=0, text="Paracetamol tablet 500 mg")

        upserted = upsert_drug_chunks([chunk])

        self.assertEqual(upserted, 1)
        self.assertEqual(fake_client.collection_name, "rxchat")
        point = fake_client.upserted_points[0]
        self.assertEqual(set(point.vector.keys()), {"dense", "sparse"})
        self.assertEqual(point.vector["dense"].model, "intfloat/multilingual-e5-small")
        self.assertEqual(point.vector["sparse"].model, "qdrant/bm25")
        chunk.refresh_from_db()
        self.assertTrue(chunk.qdrant_point_id)

    @override_settings(
        QDRANT_COLLECTION="rxchat",
        QDRANT_INFERENCE_MODEL="intfloat/multilingual-e5-small",
        QDRANT_SPARSE_MODEL="qdrant/bm25",
        QDRANT_DENSE_VECTOR_NAME="dense",
        QDRANT_SPARSE_VECTOR_NAME="sparse",
    )
    @patch("rxchat.qdrant_service._get_client")
    def test_retrieve_uses_dense_and_bm25_prefetches(self, get_client):
        from rxchat.qdrant_service import retrieve_context

        fake_client = self.FakeQdrantClient()
        get_client.return_value = fake_client

        results = retrieve_context("paracetamol", top_k=3)

        self.assertEqual(results, [])
        prefetches = fake_client.query_kwargs["prefetch"]
        self.assertEqual(fake_client.query_kwargs["limit"], 3)
        self.assertEqual(prefetches[0].using, "dense")
        self.assertEqual(prefetches[0].query.model, "intfloat/multilingual-e5-small")
        self.assertEqual(prefetches[1].using, "sparse")
        self.assertEqual(prefetches[1].query.model, "qdrant/bm25")


class IngestionAdminTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_superuser(
            username="admin@example.com",
            email="admin@example.com",
            password="password123",
        )
        self.client.force_login(self.user)

    @override_settings(ROOT_URLCONF="config.urls")
    def test_admin_defaults_to_fildah_project_view(self):
        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fildah Admin")
        self.assertContains(response, 'data-admin-project="fildah"')
        self.assertContains(response, 'data-admin-project="rxchat"')
        self.assertContains(response, 'class="app-accounts')
        self.assertContains(response, 'class="app-rxchat')

    @override_settings(ROOT_URLCONF="config.urls")
    def test_admin_rxchat_project_filters_index_to_rxchat(self):
        response = self.client.get("/admin/?project=rxchat")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-admin-project="rxchat"')
        self.assertContains(response, 'class="app-rxchat')
        self.assertContains(response, "Data ingestion")
        self.assertNotContains(response, 'class="app-accounts')

    @override_settings(ROOT_URLCONF="config.urls")
    @patch("rxchat.admin._queue_task")
    def test_admin_ingestion_post_queues_management_command(self, queue_task):
        response = self.client.post(
            "/admin/rxchat/ingestion/",
            {"action": "scrape_nafdac_category", "category": "7"},
        )

        self.assertEqual(response.status_code, 302)
        queue_task.assert_called_once_with("scrape_nafdac", "--category", "7", "--resume")

    @override_settings(ROOT_URLCONF="config.urls")
    @patch("rxchat.admin._queue_task")
    def test_admin_ingestion_upload_creates_raw_data_and_queues_parse(self, queue_task):
        """Upload creates RawData row and queues parse_data (not ingest_drugs directly)."""
        with tempfile.TemporaryDirectory() as tmp:
            with override_settings(MEDIA_ROOT=tmp):
                response = self.client.post(
                    "/admin/rxchat/ingestion/",
                    {
                        "action": "upload_source_file",
                        "source": "neml",
                        "file": SimpleUploadedFile("neml.txt", b"Metformin"),
                    },
                )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(RawData.objects.filter(source="neml").exists())
        queue_task.assert_called_once_with("parse_data", "--source", "neml")

    @override_settings(ROOT_URLCONF="config.urls")
    def test_admin_ingestion_requires_permission(self):
        regular = User.objects.create_user(
            username="regular@example.com",
            email="regular@example.com",
            password="password123",
            is_staff=True,
        )
        self.client.force_login(regular)

        response = self.client.get("/admin/rxchat/ingestion/")

        self.assertEqual(response.status_code, 403)

    @override_settings(ROOT_URLCONF="config.urls")
    def test_admin_clean_data_changelist_is_accessible(self):
        response = self.client.get("/admin/rxchat/cleandata/")

        self.assertEqual(response.status_code, 200)

    @override_settings(ROOT_URLCONF="config.urls")
    def test_admin_raw_data_changelist_is_accessible(self):
        response = self.client.get("/admin/rxchat/rawdata/")

        self.assertEqual(response.status_code, 200)
