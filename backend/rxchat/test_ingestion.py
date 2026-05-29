import importlib.util
import tempfile
from pathlib import Path
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from rxchat.ingestion.storage import save_raw_record
from rxchat.ingestion.nafdac_parser import parse_nafdac, products_to_chunks
from rxchat.ingestion.nafdac_scraper import parse_detail_html, parse_listing_html
from rxchat.ingestion.source_status import source_status_rows
from rxchat.models import DrugChunk, RawSourceData, SOURCE_CHOICES, SourceFileUpload


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
    def test_nafdac_parser_labels_inactive_product_and_suggests_active_alternative(self):
        save_raw_record("nafdac", "1", {
            "record_type": "product_detail",
            "product_id": 1,
            "product_name": "Old Para",
            "active_ingredients": [{"name": "Paracetamol", "strength": "500 mg"}],
            "status": "Expired",
            "category": "Drugs",
            "nrn": "A4-OLD",
            "source_url": "https://greenbook.nafdac.gov.ng/products/details/1",
        })
        save_raw_record("nafdac", "2", {
            "record_type": "product_detail",
            "product_id": 2,
            "product_name": "Active Para",
            "active_ingredients": [{"name": "Paracetamol", "strength": "500 mg"}],
            "status": "Active",
            "category": "Drugs",
            "nrn": "A4-ACTIVE",
            "source_url": "https://greenbook.nafdac.gov.ng/products/details/2",
        })

        products, chunks = parse_nafdac()
        old_product = next(product for product in products if product["product_id"] == 1)
        old_chunk = next(chunk for chunk in chunks if chunk.record_id == "1")

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

    def test_ingest_drugs_dry_run_parses_selected_source(self):
        save_raw_record("nafdac", "1", {
            "record_type": "product_detail",
            "product_id": 1,
            "product_name": "Active Drug",
            "active_ingredients": [{"name": "Metformin", "strength": "500 mg"}],
            "status": "Active",
            "category": "Drugs",
        })

        call_command("ingest_drugs", "--source", "nafdac", "--dry-run")

        chunk = DrugChunk.objects.get()
        self.assertEqual(chunk.metadata["source_type"], "nafdac_greenbook")

    def test_manual_upload_dry_run_creates_rows_without_marking_processed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with override_settings(MEDIA_ROOT=tmp):
                upload = SourceFileUpload.objects.create(
                    source="neml",
                    file=SimpleUploadedFile("neml_notes.txt", b"Paracetamol tablet 500 mg"),
                )

                call_command("ingest_drugs", "--source", "neml", "--dry-run")

                upload.refresh_from_db()
                self.assertFalse(upload.processed)
                self.assertTrue(RawSourceData.objects.filter(source="neml", source_id=f"upload:{upload.pk}").exists())
                self.assertTrue(DrugChunk.objects.filter(raw_source__source="neml").exists())

    def test_emdex_upload_dry_run_creates_rows_without_marking_processed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with override_settings(MEDIA_ROOT=tmp):
                upload = SourceFileUpload.objects.create(
                    source="emdex",
                    file=SimpleUploadedFile("emdex_notes.txt", b"Licensed EMDEX monograph text"),
                )

                call_command("ingest_drugs", "--source", "emdex", "--dry-run")

                upload.refresh_from_db()
                self.assertFalse(upload.processed)
                self.assertTrue(RawSourceData.objects.filter(source="emdex", source_id=f"upload:{upload.pk}").exists())
                self.assertTrue(DrugChunk.objects.filter(raw_source__source="emdex").exists())

    @patch("rxchat.management.commands.ingest_drugs.upsert_drug_chunks", return_value=1)
    def test_manual_upload_is_marked_processed_after_qdrant_upsert(self, upsert_chunks):
        with tempfile.TemporaryDirectory() as tmp:
            with override_settings(MEDIA_ROOT=tmp):
                upload = SourceFileUpload.objects.create(
                    source="neml",
                    file=SimpleUploadedFile("neml_notes.txt", b"Paracetamol tablet 500 mg"),
                )

                call_command("ingest_drugs", "--source", "neml")

                upload.refresh_from_db()
                self.assertTrue(upload.processed)
                upsert_chunks.assert_called_once()

    @patch("rxchat.qdrant_service.delete_points")
    def test_raw_source_delete_removes_qdrant_vectors(self, delete_points):
        raw = save_raw_record("nafdac", "delete-me", {"record_type": "product_detail", "product_id": "delete-me"})
        DrugChunk.objects.create(raw_source=raw, chunk_index=1, text="Delete", qdrant_point_id="point-1")

        raw.delete()

        delete_points.assert_called_once_with(["point-1"])

    @patch("rxchat.qdrant_service.delete_points")
    def test_upload_delete_removes_processed_raw_source_and_qdrant_vectors(self, delete_points):
        with tempfile.TemporaryDirectory() as tmp:
            with override_settings(MEDIA_ROOT=tmp):
                upload = SourceFileUpload.objects.create(
                    source="neml",
                    file=SimpleUploadedFile("neml_notes.txt", b"Paracetamol tablet 500 mg"),
                )
                raw = save_raw_record("neml", f"upload:{upload.pk}", {"filename": "neml_notes.txt"})
                DrugChunk.objects.create(raw_source=raw, chunk_index=1, text="Delete", qdrant_point_id="point-1")

                upload.delete()

        self.assertFalse(RawSourceData.objects.filter(source="neml", source_id=f"upload:{upload.pk}").exists())
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
        raw = save_raw_record("nafdac", "vector-test", {"record_type": "product_detail"})
        chunk = DrugChunk.objects.create(raw_source=raw, chunk_index=0, text="Paracetamol tablet 500 mg")

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
    def test_admin_index_shows_rxchat_admin(self):
        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "RxChat Administration")
        self.assertContains(response, 'class="app-rxchat')
        self.assertContains(response, "Upload source files")

    @override_settings(ROOT_URLCONF="config.urls")
    def test_admin_ingestion_page_loads_for_superuser(self):
        response = self.client.get("/admin/rxchat/ingestion/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Data Ingestion")
        self.assertContains(response, "Upload Manual Source")
        self.assertContains(response, "Source Status")

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
    def test_admin_ingestion_upload_creates_source_upload_and_queues_processing(self, queue_task):
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
        self.assertTrue(SourceFileUpload.objects.filter(source="neml").exists())
        queue_task.assert_called_once_with("ingest_drugs", "--source", "neml")

    @override_settings(ROOT_URLCONF="config.urls")
    @patch("rxchat.admin._queue_task")
    def test_admin_source_file_upload_add_queues_processing(self, queue_task):
        with tempfile.TemporaryDirectory() as tmp:
            with override_settings(MEDIA_ROOT=tmp):
                response = self.client.post(
                    "/admin/rxchat/sourcefileupload/add/",
                    {
                        "source": "emdex",
                        "description": "Licensed EMDEX upload",
                        "file": SimpleUploadedFile("emdex.txt", b"EMDEX monograph"),
                        "_save": "Save",
                    },
                )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(SourceFileUpload.objects.filter(source="emdex").exists())
        queue_task.assert_called_once_with("ingest_drugs", "--source", "emdex")

    @override_settings(ROOT_URLCONF="config.urls")
    def test_admin_raw_source_changelist_loads(self):
        response = self.client.get("/admin/rxchat/rawsourcedata/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Select raw data source to change")
        self.assertContains(response, 'id="toolbar"')

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
