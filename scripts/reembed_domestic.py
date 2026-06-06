#!/usr/bin/env python3
"""Re-embed domestic chunks with DashScope via requests (robust version)."""
import os, sys, time
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

BATCH = 5


def embed_batch(texts):
    for attempt in range(5):
        try:
            resp = requests.post(
                f"{base_url}/embeddings",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": "text-embedding-v3", "input": texts},
                timeout=30,
                verify=False,
            )
            data = resp.json()
            items = sorted(data["data"], key=lambda x: x["index"])
            return [item["embedding"] for item in items]
        except Exception as e:
            if attempt < 4:
                time.sleep(2 * (attempt + 1))
            else:
                raise


def main():
    with get_db_connection() as conn:
        rows = conn.execute("""
            SELECT id, content FROM knowledge_chunks
            WHERE business_domain NOT IN ('cross_border', 'complaint', 'logistics', 'other', 'product_consulting', 'technical', 'return_exchange')
            ORDER BY id
        """).fetchall()

    total = len(rows)
    print(f"Re-embedding {total} chunks (batch={BATCH})", flush=True)

    updated = 0
    for i in range(0, total, BATCH):
        batch = rows[i:i + BATCH]
        texts = [r[1] for r in batch]
        ids = [r[0] for r in batch]

        try:
            embs = embed_batch(texts)
            with get_db_connection() as conn:
                with conn.transaction():
                    for cid, emb in zip(ids, embs):
                        emb_str = "[" + ",".join(str(x) for x in emb) + "]"
                        conn.execute("UPDATE knowledge_chunks SET embedding = %s::vector WHERE id = %s", (emb_str, cid))
            updated += len(batch)
        except Exception as e:
            print(f"  FAIL {i//BATCH}: {e.__class__.__name__}", flush=True)

        if (i // BATCH + 1) % 20 == 0:
            print(f"  {updated}/{total}", flush=True)
        time.sleep(0.3)

    print(f"Done: {updated}/{total}", flush=True)


if __name__ == "__main__":
    main()
