"""
RxChat API connectivity tests.
Run from backend/ with: python test_apis.py
"""

import os
from dotenv import load_dotenv

load_dotenv()

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
SKIP = "\033[93m⚡ SKIP\033[0m"

def section(title):
    print(f"\n{'─'*55}")
    print(f"  {title}")
    print(f"{'─'*55}")


# ─────────────────────────────────────────────────────────
# 1. NVIDIA NIM — DeepSeek v3.2
# ─────────────────────────────────────────────────────────
section("1. NVIDIA NIM  →  deepseek-ai/deepseek-v3.2")

nvidia_key = os.getenv("NVIDIA_API_KEY", "")
nvidia_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")

if not nvidia_key:
    print(f"  {SKIP}  NVIDIA_API_KEY not set")
else:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=nvidia_key, base_url=nvidia_url, timeout=30)
        resp = client.chat.completions.create(
            model="deepseek-ai/deepseek-v3.2",
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            max_tokens=10,
            temperature=0,
        )
        reply = resp.choices[0].message.content.strip()
        print(f"  {PASS}  Response: {reply!r}")
    except Exception as e:
        print(f"  {FAIL}  {e}")


# ─────────────────────────────────────────────────────────
# 2. DeepSeek Direct (fallback)
# ─────────────────────────────────────────────────────────
section("2. DeepSeek Direct API  (fallback LLM)")

deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
deepseek_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

if not deepseek_key:
    print(f"  {SKIP}  DEEPSEEK_API_KEY not set")
else:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=deepseek_key, base_url=deepseek_url, timeout=30)
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            max_tokens=10,
            temperature=0,
        )
        reply = resp.choices[0].message.content.strip()
        print(f"  {PASS}  Response: {reply!r}")
    except Exception as e:
        print(f"  {FAIL}  {e}")


# ─────────────────────────────────────────────────────────
# 3. OpenAI (kept for reference)
# ─────────────────────────────────────────────────────────
section("3. OpenAI API  (reference key — not active in pipeline)")

openai_key = os.getenv("OPENAI_API_KEY", "")

if not openai_key:
    print(f"  {SKIP}  OPENAI_API_KEY not set")
else:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=openai_key, timeout=30)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            max_tokens=10,
            temperature=0,
        )
        reply = resp.choices[0].message.content.strip()
        print(f"  {PASS}  Response: {reply!r}")
    except Exception as e:
        print(f"  {FAIL}  {e}")


# ─────────────────────────────────────────────────────────
# 4. Qdrant Cloud — connection + collections list
# ─────────────────────────────────────────────────────────
section("4. Qdrant Cloud  (vector DB + inference)")

qdrant_url = os.getenv("QDRANT_URL", "")
qdrant_key = os.getenv("QDRANT_API_KEY", "")
qdrant_col = os.getenv("QDRANT_COLLECTION", "rxchat_drugs")

if not qdrant_url or not qdrant_key:
    print(f"  {SKIP}  QDRANT_URL or QDRANT_API_KEY not set")
else:
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(url=qdrant_url, api_key=qdrant_key)

        collections = [c.name for c in client.get_collections().collections]
        print(f"  {PASS}  Connected  |  Collections: {collections or '(none yet)'}")

        if qdrant_col in collections:
            info = client.get_collection(qdrant_col)
            count = info.points_count
            print(f"  {PASS}  Collection '{qdrant_col}' found  |  {count} points indexed")
        else:
            print(f"  \033[93m⚠\033[0m   Collection '{qdrant_col}' not found yet "
                  f"(needs data ingestion — expected at this stage)")

    except ImportError:
        print(f"  {FAIL}  qdrant-client not installed — run: pip install qdrant-client")
    except Exception as e:
        print(f"  {FAIL}  {e}")


print(f"\n{'─'*55}\n  Done.\n{'─'*55}\n")
