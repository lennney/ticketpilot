#!/usr/bin/env python3
"""Seed domestic data using requests (bypasses httpx SSL issues with DashScope)."""
import os, sys, time, hashlib, json
from pathlib import Path

os.environ["CURL_CA_BUNDLE"] = ""
os.environ["REQUESTS_CA_BUNDLE"] = ""
os.environ["SSL_CERT_FILE"] = ""

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import requests
from ticketpilot.retrieval.db.connection import get_db_connection
from ticketpilot.retrieval.schema.knowledge import DocType, BusinessDomain, RiskLevel
from ticketpilot.retrieval.schema.seeds import load_faq_seed_data, load_policy_seed_data, load_case_seed_data
from ticketpilot.retrieval.chunker import chunk_text

# Read config
api_key, base_url = "", "https://dashscope.aliyuncs.com/compatible-mode/v1"
env_path = Path(__file__).resolve().parent.parent / ".env.local"
with open(env_path) as f:
    for line in f:
        s = line.strip()
        if s.startswith("EMBEDDING_API_KEY="):
            api_key = s.split("=", 1)[1]
        elif s.startswith("EMBEDDING_BASE_URL="):
            base_url = s.split("=", 1)[1]

EMBED_DIM = 1024
BATCH_SIZE = 10


def embed_texts(texts):
    """Embed texts using requests with retry."""
    all_embs = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        for attempt in range(5):
            try:
                resp = requests.post(
                    f"{base_url}/embeddings",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": "text-embedding-v3", "input": batch},
                    timeout=30,
                    verify=False,
                )
                data = resp.json()
                items = sorted(data["data"], key=lambda x: x["index"])
                all_embs.extend([item["embedding"] for item in items])
                break
            except Exception as e:
                if attempt < 4:
                    print(f"  [retry {attempt+1}] {e.__class__.__name__}")
                    time.sleep(2 ** attempt)
                else:
                    raise
    return all_embs


def main():
    print(f"API: {base_url}")
    
    # Check current DB state
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT business_domain, COUNT(*) FROM knowledge_chunks GROUP BY business_domain"
        ).fetchall()
        print("Current DB:")
        for d, c in rows:
            print(f"  {d}: {c} chunks")

    # Load seed data
    faqs = load_faq_seed_data()
    policies = load_policy_seed_data()
    cases = load_case_seed_data()
    print(f"\nSeed: {len(faqs)} FAQ, {len(policies)} Policy, {len(cases)} Case")

    # Chunk all docs and collect texts for batch embedding
    print("\nChunking...")
    all_chunk_data = []  # (chunk_tuple_without_embedding, content_text)

    for doc in faqs:
        chunks = chunk_text(
            text=doc.content, doc_id=doc.id, doc_type=DocType.FAQ,
            source_table="knowledge_faq", source_id=doc.id,
            business_domain=doc.business_domain,
        )
        for c in chunks:
            all_chunk_data.append(c)

    for doc in policies:
        chunks = chunk_text(
            text=doc.content, doc_id=doc.id, doc_type=DocType.POLICY,
            source_table="knowledge_policy", source_id=doc.id,
            business_domain=doc.business_domain,
        )
        for c in chunks:
            all_chunk_data.append(c)

    for doc in cases:
        content = f"{doc.issue_summary}\n\n{doc.resolution}"
        chunks = chunk_text(
            text=content, doc_id=doc.id, doc_type=DocType.CASE,
            source_table="knowledge_case", source_id=doc.id,
            business_domain=doc.business_domain, risk_level=doc.risk_level,
        )
        for c in chunks:
            all_chunk_data.append(c)

    print(f"Total chunks: {len(all_chunk_data)}")

    # Batch embed
    print("Embedding...")
    texts = [c.content for c in all_chunk_data]
    embeddings = embed_texts(texts)
    print(f"Embedded {len(embeddings)} texts")

    # Insert
    print("Inserting...")
    inserted = 0
    with get_db_connection() as conn:
        with conn.transaction():
            for chunk, emb in zip(all_chunk_data, embeddings):
                emb_str = "[" + ",".join(str(x) for x in emb) + "]"
                conn.execute(
                    """INSERT INTO knowledge_chunks (
                        id, doc_id, doc_type, source_table, source_id,
                        parent_chunk_id, chunk_level, business_domain,
                        risk_level, content, content_hash, embedding
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector)
                    ON CONFLICT (id) DO NOTHING""",
                    (
                        chunk.id, chunk.doc_id, chunk.doc_type.value,
                        chunk.source_table, chunk.source_id,
                        chunk.parent_chunk_id, chunk.chunk_level.value,
                        chunk.business_domain.value,
                        chunk.risk_level.value if chunk.risk_level else None,
                        chunk.content, chunk.content_hash, emb_str,
                    ),
                )
                inserted += 1

    # Verify
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT business_domain, COUNT(*) FROM knowledge_chunks GROUP BY business_domain ORDER BY COUNT(*) DESC"
        ).fetchall()
        total = sum(c for _, c in rows)
        print(f"\nFinal DB ({total} total chunks):")
        for d, c in rows:
            print(f"  {d}: {c}")


if __name__ == "__main__":
    main()
