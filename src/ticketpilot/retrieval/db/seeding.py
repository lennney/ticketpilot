"""Database seeding for knowledge chunks with embeddings.

Two-layer architecture:
  Source layer: knowledge_faq, knowledge_policy, knowledge_case (separate tables)
  Chunk layer:  knowledge_chunks (unified, with source_table/source_id references)
"""

import uuid
from typing import Optional

from ticketpilot.retrieval.chunker import chunk_text
from ticketpilot.retrieval.db.connection import get_db_connection
from ticketpilot.retrieval.embedding_config import EmbeddingConfig
from ticketpilot.retrieval.providers import create_embedding_provider
from ticketpilot.retrieval.providers.fake_embedding import FakeEmbeddingProvider
from ticketpilot.retrieval.schema.knowledge import (
    BusinessDomain,
    DocType,
    RiskLevel,
)
from ticketpilot.retrieval.schema.seeds import (
    load_case_seed_data,
    load_faq_seed_data,
    load_policy_seed_data,
)

EMBEDDING_DIM = 384

SOURCE_FAQ = "knowledge_faq"
SOURCE_POLICY = "knowledge_policy"
SOURCE_CASE = "knowledge_case"


def _document_to_chunks(
    doc_id: uuid.UUID,
    doc_type: DocType,
    source_table: str,
    source_id: uuid.UUID,
    business_domain: BusinessDomain,
    content: str,
    risk_level: Optional[RiskLevel] = None,
    embedding_provider=None,
) -> list[tuple]:
    """Convert a document to chunk tuples ready for database insertion.

    Args:
        doc_id: Document ID (original document UUID)
        doc_type: Document type (FAQ, POLICY, CASE)
        source_table: Source table name
        source_id: UUID of the source document row
        business_domain: Business domain
        content: Document content
        risk_level: Risk level (for CASE documents)
        embedding_provider: Embedding provider

    Returns:
        List of tuples: (id, doc_id, doc_type, source_table, source_id,
                        parent_chunk_id, chunk_level, business_domain,
                        risk_level, content, content_hash, embedding)
    """
    if embedding_provider is None:
        embedding_provider = FakeEmbeddingProvider()

    chunks = chunk_text(
        text=content,
        doc_id=doc_id,
        doc_type=doc_type,
        source_table=source_table,
        source_id=source_id,
        business_domain=business_domain,
        risk_level=risk_level,
    )

    results = []
    for chunk in chunks:
        embedding = embedding_provider.embed(chunk.content)
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

        results.append((
            chunk.id,
            chunk.doc_id,
            chunk.doc_type.value,
            chunk.source_table,
            chunk.source_id,
            chunk.parent_chunk_id,
            chunk.chunk_level.value,
            chunk.business_domain.value,
            chunk.risk_level.value if chunk.risk_level else None,
            chunk.content,
            chunk.content_hash,
            embedding_str,
        ))

    return results


def _insert_source_documents(conn, clear_existing: bool = False) -> tuple[int, int, int]:
    """Insert seed documents into source tables.

    Args:
        conn: Database connection (must be in a transaction)
        clear_existing: If True, delete existing rows before inserting

    Returns:
        Tuple of (faq_count, policy_count, case_count)
    """
    if clear_existing:
        conn.execute("DELETE FROM knowledge_chunks")
        conn.execute("DELETE FROM knowledge_faq")
        conn.execute("DELETE FROM knowledge_policy")
        conn.execute("DELETE FROM knowledge_case")

    faq_count = 0
    for doc in load_faq_seed_data():
        conn.execute(
            """INSERT INTO knowledge_faq (id, business_domain, title, content, intent_tags)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (id) DO NOTHING""",
            (doc.id, doc.business_domain.value, doc.title, doc.content, doc.intent_tags),
        )
        faq_count += 1

    policy_count = 0
    for doc in load_policy_seed_data():
        conn.execute(
            """INSERT INTO knowledge_policy (id, business_domain, policy_code, title, content, effective_date)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (id) DO NOTHING""",
            (doc.id, doc.business_domain.value, doc.policy_code, doc.title, doc.content, doc.effective_date),
        )
        policy_count += 1

    case_count = 0
    for doc in load_case_seed_data():
        conn.execute(
            """INSERT INTO knowledge_case (id, business_domain, case_id, issue_summary, resolution, risk_level, compensation_amount)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (id) DO NOTHING""",
            (doc.id, doc.business_domain.value, doc.case_id, doc.issue_summary, doc.resolution, doc.risk_level.value, doc.compensation_amount),
        )
        case_count += 1

    return faq_count, policy_count, case_count


def _default_embedding_provider():
    """Create the default embedding provider from environment config."""
    config = EmbeddingConfig()
    return create_embedding_provider(config)


def seed_knowledge_chunks(
    embedding_provider=None,
    clear_existing: bool = False,
) -> dict:
    """Seed source tables and knowledge_chunks from seed data files.

    Two-phase process:
      1. Insert source documents into knowledge_faq/knowledge_policy/knowledge_case
      2. Chunk each document and insert into knowledge_chunks with source refs

    Args:
        embedding_provider: Embedding provider (default: from env config, falls back to FakeEmbeddingProvider)
        clear_existing: If True, delete existing rows before seeding

    Returns:
        Dictionary with seeding statistics
    """
    if embedding_provider is None:
        embedding_provider = _default_embedding_provider()

    all_chunks: list[tuple] = []

    with get_db_connection() as conn:
        with conn.transaction():
            # Phase 1: Insert source documents
            faq_count, policy_count, case_count = _insert_source_documents(conn, clear_existing)

            # Phase 2: Chunk and collect
            for doc in load_faq_seed_data():
                chunks = _document_to_chunks(
                    doc_id=doc.id, doc_type=DocType.FAQ,
                    source_table=SOURCE_FAQ, source_id=doc.id,
                    business_domain=doc.business_domain, content=doc.content,
                    risk_level=None, embedding_provider=embedding_provider,
                )
                all_chunks.extend(chunks)

            for doc in load_policy_seed_data():
                chunks = _document_to_chunks(
                    doc_id=doc.id, doc_type=DocType.POLICY,
                    source_table=SOURCE_POLICY, source_id=doc.id,
                    business_domain=doc.business_domain, content=doc.content,
                    risk_level=None, embedding_provider=embedding_provider,
                )
                all_chunks.extend(chunks)

            for doc in load_case_seed_data():
                content = f"{doc.issue_summary}\n\n{doc.resolution}"
                chunks = _document_to_chunks(
                    doc_id=doc.id, doc_type=DocType.CASE,
                    source_table=SOURCE_CASE, source_id=doc.id,
                    business_domain=doc.business_domain, content=content,
                    risk_level=doc.risk_level, embedding_provider=embedding_provider,
                )
                all_chunks.extend(chunks)

            # Phase 3: Insert chunks
            for chunk in all_chunks:
                conn.execute(
                    """INSERT INTO knowledge_chunks (
                        id, doc_id, doc_type, source_table, source_id,
                        parent_chunk_id, chunk_level, business_domain,
                        risk_level, content, content_hash, embedding
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector
                    )
                    ON CONFLICT (id) DO NOTHING""",
                    chunk,
                )

    return {
        "source_documents": faq_count + policy_count + case_count,
        "faq_documents": faq_count,
        "policy_documents": policy_count,
        "case_documents": case_count,
        "chunks": len(all_chunks),
    }


def get_chunk_count() -> int:
    """Get the current number of chunks in the database."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM knowledge_chunks")
            result = cur.fetchone()
            return result[0] if result else 0


def get_source_counts() -> dict:
    """Get document counts from source tables."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM knowledge_faq")
            faq = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM knowledge_policy")
            policy = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM knowledge_case")
            case = cur.fetchone()[0]
    return {"faq": faq, "policy": policy, "case": case}


def verify_seeding() -> dict:
    """Verify that seeding completed successfully.

    Returns:
        Dictionary with verification results
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Source document counts
            cur.execute("SELECT COUNT(*) FROM knowledge_faq")
            faq = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM knowledge_policy")
            policy = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM knowledge_case")
            case = cur.fetchone()[0]

            # Count by doc type
            cur.execute("""
                SELECT doc_type, COUNT(*) as count
                FROM knowledge_chunks
                GROUP BY doc_type
            """)
            by_type = {row[0]: row[1] for row in cur.fetchall()}

            # Count by chunk level
            cur.execute("""
                SELECT chunk_level, COUNT(*) as count
                FROM knowledge_chunks
                GROUP BY chunk_level
            """)
            by_level = {row[0]: row[1] for row in cur.fetchall()}

            # Count with source refs
            cur.execute("SELECT COUNT(*) FROM knowledge_chunks WHERE source_table IS NOT NULL AND source_id IS NOT NULL")
            with_source_refs = cur.fetchone()[0]

            # Count with embeddings
            cur.execute("SELECT COUNT(*) FROM knowledge_chunks WHERE embedding IS NOT NULL")
            with_embeddings = cur.fetchone()[0]

            total = get_chunk_count()

            return {
                "total": total,
                "source_documents": faq + policy + case,
                "faq_documents": faq,
                "policy_documents": policy,
                "case_documents": case,
                "by_doc_type": by_type,
                "by_chunk_level": by_level,
                "with_source_refs": with_source_refs,
                "with_embeddings": with_embeddings,
                "seeding_complete": total > 0 and with_embeddings == total and with_source_refs == total,
            }
