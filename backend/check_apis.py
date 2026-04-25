"""
Manual RxChat provider connectivity checks.

Run from backend/ with:
    python check_apis.py

This module is intentionally not named ``test_*.py`` so Django test discovery
does not make live provider calls.
"""

import os

from dotenv import load_dotenv


PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
SKIP = "\033[93m⚡ SKIP\033[0m"
WARN = "\033[93m⚠\033[0m"


def section(title):
    print(f"\n{'─' * 55}")
    print(f"  {title}")
    print(f"{'─' * 55}")


def check_openrouter():
    section("1. OpenRouter  →  openai/gpt-oss-120b:free")

    openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
    openrouter_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    openrouter_model = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-120b:free")

    if not openrouter_key:
        print(f"  {SKIP}  OPENROUTER_API_KEY not set")
        return

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=openrouter_key,
            base_url=openrouter_url,
            timeout=30,
            default_headers={
                "HTTP-Referer": "https://rxchat.dev",
                "X-Title": "RxChat",
            },
        )
        resp = client.chat.completions.create(
            model=openrouter_model,
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            max_tokens=10,
            temperature=0,
        )
        reply = resp.choices[0].message.content.strip()
        print(f"  {PASS}  Response: {reply!r}")
    except Exception as e:
        print(f"  {FAIL}  {e}")


def check_qdrant():
    section("2. Qdrant Cloud  (vector DB + inference)")

    qdrant_url = os.getenv("QDRANT_URL", "")
    qdrant_key = os.getenv("QDRANT_API_KEY", "")
    qdrant_col = os.getenv("QDRANT_COLLECTION", "rxchat_drugs")

    if not qdrant_url or not qdrant_key:
        print(f"  {SKIP}  QDRANT_URL or QDRANT_API_KEY not set")
        return

    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(url=qdrant_url, api_key=qdrant_key)
        collections = [c.name for c in client.get_collections().collections]
        print(f"  {PASS}  Connected  |  Collections: {collections or '(none yet)'}")

        if qdrant_col in collections:
            info = client.get_collection(qdrant_col)
            print(f"  {PASS}  Collection '{qdrant_col}' found  |  {info.points_count} points indexed")
        else:
            print(f"  {WARN}   Collection '{qdrant_col}' not found yet (needs data ingestion)")
    except ImportError:
        print(f"  {FAIL}  qdrant-client not installed — run: pip install qdrant-client")
    except Exception as e:
        print(f"  {FAIL}  {e}")


def main():
    load_dotenv()
    check_openrouter()
    check_qdrant()
    print(f"\n{'─' * 55}\n  Done.\n{'─' * 55}\n")


if __name__ == "__main__":
    main()
