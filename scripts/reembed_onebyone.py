#!/usr/bin/env python3
"""Re-embed one chunk at a time - most robust approach."""
import os, sys, time, json
from pathlib import Path

os.environ["CURL_CA_BUNDLE"] = ""
os.environ["REQUESTS_CA_BUNDLE"] = ""
os.environ["SSL_CERT_FILE"] = ""

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import requests
from ticketpilot.retrieval.db.connection import get_db_connection

api_key = ""
base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
with open(Path(__file__).resolve().parent.parent / ".env.local") as f:
    for line in f:
        s = line.strip()
        if s.startswith("EMBEDDING_API_KEY"):
            api_key = s.split("=", 1)[1]
        elif s.startswith("EMBEDDING_BASE_URL"):
            base_url = s.split("=", 1)[1]


def embed_one(text):
    for attempt in range(5):
        try:
            resp = requests.post(
                f"{base_url}/embeddings",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": "text-embedding-v3", "input": [text]},
                timeout=20,
                verify=False,
            )
            data = resp.json()
            return data["data"][0]["embedding"]
        except Exception as e:
            if attempt < 4:
                time.sleep(3 * (attempt + 1))
            else:
                return None


def main():
    with get_db_connection() as conn:
        rows = conn.execute("""
            SELECT id, content FROM knowledge_chunks
            WHERE business_domain NOT IN ('cross_border', 'complaint', 'logistics', 'other', 'product_consulting', 'technical', 'return_exchange')
            ORDER BY id
        """).fetchall()

    total = len(rows)
    print(f"Re-embedding {total} chunks one-by-one", flush=True)

    updated = 0
    failed = 0
    for i, (cid, content) in enumerate(rows):
        emb = embed_one(content)
        if emb:
            emb_str = "[" + ",".join(str(x) for x in emb) + "]"
            with get_db_connection() as conn:
                with conn.transaction():
                    conn.execute("UPDATE knowledge_chunks SET embedding = %s::vector WHERE id = %s", (emb_str, cid))
            updated += 1
        else:
            failed += 1

        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{total}: {updated} ok, {failed} fail", flush=True)
        time.sleep(0.2)

    print(f"Done: {updated} updated, {failed} failed out of {total}", flush=True)


if __name__ == "__main__":
    main()
