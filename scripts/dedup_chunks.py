#!/usr/bin/env python3
"""Remove duplicate knowledge_chunks, preserving parent-child references."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ticketpilot.retrieval.db.connection import get_db_connection

with get_db_connection() as conn:
    before = conn.execute("SELECT COUNT(*) FROM knowledge_chunks").fetchone()[0]
    unique = conn.execute("SELECT COUNT(DISTINCT content) FROM knowledge_chunks").fetchone()[0]
    print(f"Before: {before} chunks ({unique} unique, {before - unique} duplicates)")

    # Step 1: For duplicate child chunks that have parent references,
    #         point them to the surviving parent before deleting duplicates
    with conn.transaction():
        # Find duplicates and which id survives (earliest created_at)
        # Update parent_chunk_id references: point children of doomed parents to the survivor
        conn.execute("""
            WITH ranked AS (
                SELECT id, content,
                    ROW_NUMBER() OVER (PARTITION BY content ORDER BY created_at, id) as rn
                FROM knowledge_chunks
            ),
            survivors AS (
                SELECT content, id as survivor_id FROM ranked WHERE rn = 1
            ),
            doomed AS (
                SELECT id as doomed_id, content FROM ranked WHERE rn > 1
            )
            UPDATE knowledge_chunks kc
            SET parent_chunk_id = s.survivor_id
            FROM doomed d
            JOIN survivors s ON d.content = s.content
            WHERE kc.parent_chunk_id = d.doomed_id
        """)
        print("  Updated parent_chunk_id references")

        # Step 2: Delete duplicates
        deleted = conn.execute("""
            DELETE FROM knowledge_chunks
            WHERE id IN (
                SELECT id FROM (
                    SELECT id, ROW_NUMBER() OVER (PARTITION BY content ORDER BY created_at, id) as rn
                    FROM knowledge_chunks
                ) t WHERE rn > 1
            )
        """).rowcount
        print(f"  Deleted {deleted} duplicates")

    after = conn.execute("SELECT COUNT(*) FROM knowledge_chunks").fetchone()[0]
    print(f"After: {after} chunks")

    rows = conn.execute(
        "SELECT business_domain, COUNT(*) FROM knowledge_chunks GROUP BY business_domain ORDER BY COUNT(*) DESC"
    ).fetchall()
    for r in rows:
        print(f"  {r[0]}: {r[1]}")
