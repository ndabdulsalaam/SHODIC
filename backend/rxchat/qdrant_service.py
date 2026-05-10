"""
RxChat Qdrant Service — RAG retrieval using Qdrant Cloud Inference.

Qdrant Cloud Inference handles embedding generation internally.
You pass raw query text; Qdrant embeds it and returns the closest chunks.
No separate OpenAI / embedding API call is needed.

Usage:
    from rxchat.qdrant_service import retrieve_context

    chunks = retrieve_context("What is the dose of amoxicillin?", top_k=5)
    # chunks → list of {"text": "...", "source": "..."}

Requirements:
    pip install qdrant-client

    Environment variables (.env or host env):
    QDRANT_URL       — your Qdrant Cloud cluster URL
    QDRANT_API_KEY   — your Qdrant Cloud API key
    QDRANT_COLLECTION — collection name
    QDRANT_INFERENCE_MODEL — dense model, default intfloat/multilingual-e5-small
    QDRANT_SPARSE_MODEL — sparse keyword model, default qdrant/bm25
    QDRANT_DENSE_VECTOR_NAME — dense vector name, default dense
    QDRANT_SPARSE_VECTOR_NAME — sparse vector name, default sparse
"""

import logging
import uuid
from itertools import islice

from django.conf import settings

logger = logging.getLogger(__name__)

# Lazy-initialised client — created once on first call
_client = None


def _collection_setup_hint() -> str:
    return (
        f"Create collection '{settings.QDRANT_COLLECTION}' with dense vector "
        f"'{settings.QDRANT_DENSE_VECTOR_NAME}' size {settings.QDRANT_VECTOR_SIZE} "
        f"distance {settings.QDRANT_DISTANCE} and sparse vector "
        f"'{settings.QDRANT_SPARSE_VECTOR_NAME}' for {settings.QDRANT_SPARSE_MODEL}."
    )


def _chunk_vectors(text: str) -> dict:
    from qdrant_client.models import Document  # noqa: PLC0415

    return {
        settings.QDRANT_DENSE_VECTOR_NAME: Document(text=text, model=settings.QDRANT_INFERENCE_MODEL),
        settings.QDRANT_SPARSE_VECTOR_NAME: Document(text=text, model=settings.QDRANT_SPARSE_MODEL),
    }


def _require_qdrant_settings() -> None:
    if not settings.QDRANT_INFERENCE_MODEL:
        raise RuntimeError("QDRANT_INFERENCE_MODEL is not set.")
    if not settings.QDRANT_SPARSE_MODEL:
        raise RuntimeError("QDRANT_SPARSE_MODEL is not set.")
    if not settings.QDRANT_COLLECTION:
        raise RuntimeError("QDRANT_COLLECTION is not set.")
    if settings.QDRANT_DENSE_VECTOR_NAME == settings.QDRANT_SPARSE_VECTOR_NAME:
        raise RuntimeError("QDRANT_DENSE_VECTOR_NAME and QDRANT_SPARSE_VECTOR_NAME must differ.")
    if settings.QDRANT_VECTOR_SIZE <= 0:
        raise RuntimeError("QDRANT_VECTOR_SIZE must be a positive integer.")


def _qdrant_distance():
    from qdrant_client import models  # noqa: PLC0415

    aliases = {
        "COSINE": "COSINE",
        "DOT": "DOT",
        "EUCLID": "EUCLID",
        "EUCLIDEAN": "EUCLID",
        "MANHATTAN": "MANHATTAN",
    }
    distance_name = aliases.get(str(settings.QDRANT_DISTANCE).strip().upper())
    if not distance_name or not hasattr(models.Distance, distance_name):
        supported = ", ".join(sorted(aliases))
        raise RuntimeError(
            f"Unsupported QDRANT_DISTANCE '{settings.QDRANT_DISTANCE}'. "
            f"Use one of: {supported}."
        )
    return getattr(models.Distance, distance_name)


def collection_config() -> dict:
    """Return the named dense/sparse vector config used for every environment."""
    _require_qdrant_settings()
    from qdrant_client import models  # noqa: PLC0415

    return {
        "vectors_config": {
            settings.QDRANT_DENSE_VECTOR_NAME: models.VectorParams(
                size=settings.QDRANT_VECTOR_SIZE,
                distance=_qdrant_distance(),
            )
        },
        "sparse_vectors_config": {
            settings.QDRANT_SPARSE_VECTOR_NAME: models.SparseVectorParams(),
        },
    }


def active_collection_name() -> str:
    collection = (settings.QDRANT_COLLECTION or "").strip()
    if not collection:
        raise RuntimeError("QDRANT_COLLECTION is not set.")
    return collection


def is_protected_collection(collection_name: str | None = None) -> bool:
    collection = (collection_name or active_collection_name()).lower()
    return "prod" in collection


def collection_exists(collection_name: str | None = None) -> bool:
    client = _get_client()
    if not client:
        raise RuntimeError("Qdrant is not configured. Set QDRANT_URL and QDRANT_API_KEY.")

    collection = collection_name or active_collection_name()
    try:
        client.get_collection(collection)
    except Exception:
        return False
    return True


def ensure_collection() -> bool:
    """Create the active Qdrant collection if missing.

    Returns True when a collection was created and False when it already existed.
    """
    client = _get_client()
    if not client:
        raise RuntimeError("Qdrant is not configured. Set QDRANT_URL and QDRANT_API_KEY.")

    collection = active_collection_name()
    if collection_exists(collection):
        ensure_payload_indexes()
        return False

    client.create_collection(
        collection_name=collection,
        **collection_config(),
    )
    ensure_payload_indexes()
    return True


def reset_collection() -> None:
    """Delete and recreate the active Qdrant collection, with production guards."""
    collection = active_collection_name()
    if is_protected_collection(collection):
        raise RuntimeError(
            f"Refusing to reset protected Qdrant collection '{collection}'."
        )

    client = _get_client()
    if not client:
        raise RuntimeError("Qdrant is not configured. Set QDRANT_URL and QDRANT_API_KEY.")

    if collection_exists(collection):
        client.delete_collection(collection_name=collection)

    client.create_collection(
        collection_name=collection,
        **collection_config(),
    )
    ensure_payload_indexes()


def _iter_batches(items, batch_size: int):
    iterator = items.iterator(chunk_size=batch_size) if hasattr(items, "iterator") else iter(items)
    while True:
        batch = list(islice(iterator, batch_size))
        if not batch:
            break
        yield batch


def _get_client():
    """Return (or initialise) the Qdrant client."""
    global _client
    if _client is not None:
        return _client

    qdrant_url = settings.QDRANT_URL
    qdrant_key = settings.QDRANT_API_KEY

    if not qdrant_url or not qdrant_key:
        logger.warning(
            "Qdrant is not configured (QDRANT_URL or QDRANT_API_KEY missing). "
            "RAG context will be unavailable."
        )
        return None

    try:
        from qdrant_client import QdrantClient  # noqa: PLC0415

        _client = QdrantClient(
            url=qdrant_url,
            api_key=qdrant_key,
            cloud_inference=True,
        )
        logger.info("Qdrant client initialised successfully.")
        return _client

    except ImportError:
        logger.error(
            "qdrant-client is not installed. "
            "Run: pip install qdrant-client"
        )
        return None
    except Exception as e:
        logger.error(f"Failed to initialise Qdrant client: {e}")
        return None


def retrieve_context(query: str, top_k: int = 10) -> list[dict]:
    """Retrieve the most relevant drug-knowledge chunks for a query.

    Uses Qdrant Cloud Inference — the query text is embedded directly
    inside Qdrant using the model configured on the cluster's Inference tab.
    No external embedding API call is made.

    Args:
        query:  The user's question (raw text).
        top_k:  Number of chunks to return (default: 5).

    Returns:
        A list of dicts, each with:
            - ``text``   (str) — the retrieved passage
            - ``source`` (str) — the document / guideline name
        Returns an empty list if Qdrant is unavailable or the query fails.
    """
    if top_k <= 0:
        return []

    client = _get_client()
    if not client:
        return []

    collection = settings.QDRANT_COLLECTION

    try:
        from qdrant_client.models import (  # noqa: PLC0415
            Document,
            Fusion,
            FusionQuery,
            Prefetch,
        )

        if not settings.QDRANT_INFERENCE_MODEL:
            logger.warning(
                "QDRANT_INFERENCE_MODEL is not set. "
                "RAG context will be skipped for this request."
            )
            return []
        if not settings.QDRANT_SPARSE_MODEL:
            logger.warning(
                "QDRANT_SPARSE_MODEL is not set. "
                "Keyword retrieval will be skipped for this request."
            )
            return []

        vector_prefetch = Prefetch(
            query=Document(text=query, model=settings.QDRANT_INFERENCE_MODEL),
            using=settings.QDRANT_DENSE_VECTOR_NAME,
            limit=max(top_k * 2, 10),
        )
        keyword_prefetch = Prefetch(
            query=Document(text=query, model=settings.QDRANT_SPARSE_MODEL),
            using=settings.QDRANT_SPARSE_VECTOR_NAME,
            limit=max(top_k * 2, 10),
        )
        results = client.query_points(
            collection_name=collection,
            prefetch=[vector_prefetch, keyword_prefetch],
            query=FusionQuery(fusion=Fusion.RRF),
            limit=top_k,
            with_payload=True,
        )

        chunks = []
        for point in results.points:
            payload = point.payload or {}
            metadata = payload.get("metadata", {}) or {}
            chunks.append({
                "text": payload.get("text", ""),
                "source": metadata.get("source_label") or payload.get("source", "Unknown source"),
                "status": payload.get("status", ""),
                "is_active": payload.get("is_active", True),
                "metadata": metadata,
            })

        logger.info(
            f"Qdrant retrieved {len(chunks)} chunks for query: "
            f"{query[:60]}..."
        )
        return chunks

    except Exception as e:
        logger.error(f"Qdrant retrieval error: {e}")
        return []


def upsert_chunks(chunks: list, batch_size: int = 64) -> int:
    """Upsert parsed RAG chunks using Qdrant Cloud Inference.

    The target collection must already exist. This keeps vector dimensions and
    distance configuration explicit in Qdrant rather than hidden in app code.
    """
    client = _get_client()
    if not client:
        raise RuntimeError("Qdrant is not configured. Set QDRANT_URL and QDRANT_API_KEY.")

    collection = settings.QDRANT_COLLECTION
    _require_qdrant_settings()

    try:
        client.get_collection(collection)
    except Exception as exc:
        raise RuntimeError(
            f"Qdrant collection '{collection}' does not exist. "
            f"{_collection_setup_hint()}"
        ) from exc

    from qdrant_client.models import PointStruct  # noqa: PLC0415

    total = 0
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]
        points = []
        for chunk in batch:
            chunk_id = getattr(chunk, "id", None) or chunk.get("id")
            text = getattr(chunk, "text", None) or chunk.get("text", "")
            payload = chunk.payload() if hasattr(chunk, "payload") else dict(chunk)
            payload["text"] = text
            points.append(PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, str(chunk_id))),
                vector=_chunk_vectors(text),
                payload=payload,
            ))
        client.upsert(collection_name=collection, points=points)
        total += len(points)
    return total


def ensure_payload_indexes() -> None:
    client = _get_client()
    if not client:
        raise RuntimeError("Qdrant is not configured. Set QDRANT_URL and QDRANT_API_KEY.")

    from qdrant_client.models import (  # noqa: PLC0415
        KeywordIndexParams,
        KeywordIndexType,
        TextIndexParams,
        TextIndexType,
        TokenizerType,
    )

    collection = settings.QDRANT_COLLECTION
    try:
        client.create_payload_index(
            collection_name=collection,
            field_name="text",
            field_schema=TextIndexParams(
                type=TextIndexType.TEXT,
                tokenizer=TokenizerType.WORD,
                lowercase=True,
            ),
        )
    except Exception as exc:
        logger.info("Qdrant text payload index may already exist: %s", exc)
    for field in ["source", "drug_name", "category"]:
        try:
            client.create_payload_index(
                collection_name=collection,
                field_name=field,
                field_schema=KeywordIndexParams(type=KeywordIndexType.KEYWORD),
            )
        except Exception as exc:
            logger.info("Qdrant keyword payload index may already exist for %s: %s", field, exc)


def payload_for_drug_chunk(chunk) -> dict:
    metadata = chunk.metadata or {}
    clean = chunk.clean_data
    return {
        "text": chunk.text,
        "source": clean.source if clean else "",
        "drug_name": metadata.get("drug_name") or metadata.get("product_name") or metadata.get("medicine_name") or "",
        "category": metadata.get("category") or "",
        "chunk_index": chunk.chunk_index,
        "clean_data_id": chunk.clean_data_id,
        "source_url": metadata.get("source_url", ""),
        "source_type": metadata.get("source_type", clean.source if clean else ""),
        "record_id": clean.source_id if clean else "",
        "status": metadata.get("status", "active"),
        "is_active": metadata.get("is_active", True),
        "effective_date": metadata.get("effective_date", ""),
        "updated_at": chunk.updated_at.isoformat(),
        "metadata": metadata,
    }


def point_id_for_chunk(chunk) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"drugchunk:{chunk.pk}"))


def upsert_drug_chunks(chunks, batch_size: int = 64) -> int:
    client = _get_client()
    if not client:
        raise RuntimeError("Qdrant is not configured. Set QDRANT_URL and QDRANT_API_KEY.")

    collection = settings.QDRANT_COLLECTION
    _require_qdrant_settings()

    try:
        client.get_collection(collection)
    except Exception as exc:
        raise RuntimeError(
            f"Qdrant collection '{collection}' does not exist. "
            f"{_collection_setup_hint()}"
        ) from exc

    ensure_payload_indexes()

    from django.utils import timezone  # noqa: PLC0415
    from qdrant_client.models import PointStruct  # noqa: PLC0415

    total = 0
    for batch in _iter_batches(chunks, batch_size):
        points = []
        for chunk in batch:
            point_id = point_id_for_chunk(chunk)
            points.append(PointStruct(
                id=point_id,
                vector=_chunk_vectors(chunk.text),
                payload=payload_for_drug_chunk(chunk),
            ))
            chunk.qdrant_point_id = point_id
            chunk.embedded_at = timezone.now()
        client.upsert(collection_name=collection, points=points)
        for chunk in batch:
            chunk.save(update_fields=["qdrant_point_id", "embedded_at", "updated_at"])
        total += len(points)
    return total


def delete_points(point_ids: list[str]) -> int:
    if not point_ids:
        return 0
    client = _get_client()
    if not client:
        logger.warning("Qdrant is not configured; skipping delete for %s vectors.", len(point_ids))
        return 0
    from qdrant_client.models import PointIdsList  # noqa: PLC0415

    client.delete(
        collection_name=settings.QDRANT_COLLECTION,
        points_selector=PointIdsList(points=point_ids),
    )
    return len(point_ids)
