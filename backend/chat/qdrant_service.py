"""
RxChat Qdrant Service — RAG retrieval using Qdrant Cloud Inference.

Qdrant Cloud Inference handles embedding generation internally.
You pass raw query text; Qdrant embeds it and returns the closest chunks.
No separate OpenAI / embedding API call is needed.

Usage:
    from chat.qdrant_service import retrieve_context

    chunks = retrieve_context("What is the dose of amoxicillin?", top_k=5)
    # chunks → list of {"text": "...", "source": "..."}

Requirements:
    pip install qdrant-client

Environment variables (backend/.env):
    QDRANT_URL       — your Qdrant Cloud cluster URL
    QDRANT_API_KEY   — your Qdrant Cloud API key
    QDRANT_COLLECTION — collection name (default: rxchat_drugs)
    QDRANT_INFERENCE_MODEL — model name for Qdrant Cloud Inference
"""

import logging
from django.conf import settings

logger = logging.getLogger(__name__)

# Lazy-initialised client — created once on first call
_client = None


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


def retrieve_context(query: str, top_k: int = 5) -> list[dict]:
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
    client = _get_client()
    if not client:
        return []

    collection = settings.QDRANT_COLLECTION

    try:
        # Qdrant Cloud Inference: pass the raw query string inside a
        # Document object — the cluster embeds it server-side.
        from qdrant_client.models import Document  # noqa: PLC0415

        inference_model = getattr(settings, "QDRANT_INFERENCE_MODEL", "")
        if not inference_model:
            logger.warning(
                "QDRANT_INFERENCE_MODEL is not set. "
                "RAG context will be skipped for this request."
            )
            return []

        results = client.query_points(
            collection_name=collection,
            query=Document(
                text=query,
                model=inference_model,
            ),  # Qdrant Inference handles embedding
            limit=top_k,
            with_payload=True,
        )

        chunks = []
        for point in results.points:
            payload = point.payload or {}
            chunks.append({
                "text": payload.get("text", ""),
                "source": payload.get("source", "Unknown source"),
            })

        logger.info(
            f"Qdrant retrieved {len(chunks)} chunks for query: "
            f"{query[:60]}..."
        )
        return chunks

    except Exception as e:
        logger.error(f"Qdrant retrieval error: {e}")
        return []
