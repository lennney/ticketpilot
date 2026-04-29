#!/usr/bin/env python3
"""Ingest knowledge seed data and apply chunking.

This script loads seed data from JSON files, applies parent-child chunking,
and outputs statistics about the generated chunks.

Usage:
    python scripts/ingest_knowledge.py

Note:
    This script does NOT require a database, embeddings, or external services.
    It only performs local chunking operations and outputs statistics.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ticketpilot.retrieval.schema.seeds import load_seed_data
from ticketpilot.retrieval.chunker import chunk_text


def main() -> None:
    """Load seed data and apply chunking."""
    print("=" * 60)
    print("TicketPilot Knowledge Ingestion Script")
    print("=" * 60)
    print()

    # Load seed data
    print("Loading seed data...")
    try:
        faq_docs, policy_docs, case_docs = load_seed_data()
        print(f"  Loaded {len(faq_docs)} FAQ documents")
        print(f"  Loaded {len(policy_docs)} Policy documents")
        print(f"  Loaded {len(case_docs)} Case documents")
        print()
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        print("Please ensure seed data files exist in data/knowledge/")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR loading seed data: {e}")
        sys.exit(1)

    # Process each document type
    all_chunks = []
    stats = {"faq": {"docs": 0, "parent_chunks": 0, "child_chunks": 0}, "policy": {"docs": 0, "parent_chunks": 0, "child_chunks": 0}, "case": {"docs": 0, "parent_chunks": 0, "child_chunks": 0}}

    # Track content hashes for deduplication check
    content_hashes = set()

    # Source table name mapping
    SOURCE_TABLES = {"faq": "knowledge_faq", "policy": "knowledge_policy", "case": "knowledge_case"}

    def process_document(doc, doc_type_str: str):
        """Process a single document and update stats."""
        doc_type_key = doc_type_str.lower()
        source_table = SOURCE_TABLES[doc_type_key]
        stats[doc_type_key]["docs"] += 1

        # Get content for chunking
        # FAQ and Policy have 'content' field, Case has 'issue_summary' + 'resolution'
        if hasattr(doc, "content"):
            content = doc.content
        else:
            # CaseDocument: combine issue_summary and resolution
            content = f"{doc.issue_summary} {doc.resolution}"

        # Apply chunking
        chunks = chunk_text(
            text=content,
            doc_id=doc.id,
            doc_type=doc.doc_type,
            source_table=source_table,
            source_id=doc.id,
            business_domain=doc.business_domain,
            risk_level=getattr(doc, "risk_level", None),
        )

        for chunk in chunks:
            all_chunks.append(chunk)
            content_hashes.add(chunk.content_hash)

            if chunk.chunk_level.value == 1:  # PARENT
                stats[doc_type_key]["parent_chunks"] += 1
            else:  # CHILD
                stats[doc_type_key]["child_chunks"] += 1

    print("Processing FAQ documents...")
    for doc in faq_docs:
        process_document(doc, "faq")

    print("Processing Policy documents...")
    for doc in policy_docs:
        process_document(doc, "policy")

    print("Processing Case documents...")
    for doc in case_docs:
        process_document(doc, "case")

    print()
    print("-" * 60)
    print("CHUNK STATISTICS")
    print("-" * 60)

    total_parents = 0
    total_children = 0

    for doc_type in ["faq", "policy", "case"]:
        s = stats[doc_type]
        total = s["parent_chunks"] + s["child_chunks"]
        total_parents += s["parent_chunks"]
        total_children += s["child_chunks"]
        print(f"  {doc_type.upper()}:")
        print(f"    Documents: {s['docs']}")
        print(f"    Parent chunks: {s['parent_chunks']}")
        print(f"    Child chunks: {s['child_chunks']}")
        print(f"    Total chunks: {total}")
        print()

    print("TOTALS:")
    print(f"  Total documents: {len(faq_docs) + len(policy_docs) + len(case_docs)}")
    print(f"  Total parent chunks: {total_parents}")
    print(f"  Total child chunks: {total_children}")
    print(f"  Total chunks: {len(all_chunks)}")
    print()

    # Check for duplicate content hashes
    print("-" * 60)
    print("CONTENT HASH CHECK")
    print("-" * 60)
    print(f"  Unique content hashes: {len(content_hashes)}")
    print(f"  Total chunks: {len(all_chunks)}")

    if len(content_hashes) < len(all_chunks):
        duplicate_count = len(all_chunks) - len(content_hashes)
        print(f"  WARNING: Found {duplicate_count} duplicate content hashes!")
        print("  (This is expected if documents share common text passages)")
    else:
        print("  No duplicate content hashes found.")
    print()

    print("-" * 60)
    print("INGESTION COMPLETE")
    print("-" * 60)


if __name__ == "__main__":
    main()
