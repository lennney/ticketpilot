"""Database module for retrieval.

This module provides lazy imports to avoid triggering psycopg
imports when the database is not available.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ticketpilot.retrieval.db.connection import (
        close_db_pool,
        get_db_connection,
        get_db_pool,
    )
    from ticketpilot.retrieval.db.seeding import (
        get_chunk_count,
        seed_knowledge_chunks,
        verify_seeding,
    )

__all__ = [
    "get_db_pool",
    "close_db_pool",
    "get_db_connection",
    "seed_knowledge_chunks",
    "get_chunk_count",
    "verify_seeding",
]


def __getattr__(name: str):
    """Lazy import to avoid importing psycopg at module load time."""
    if name == "get_db_pool":
        from ticketpilot.retrieval.db.connection import get_db_pool

        return get_db_pool
    elif name == "close_db_pool":
        from ticketpilot.retrieval.db.connection import close_db_pool

        return close_db_pool
    elif name == "get_db_connection":
        from ticketpilot.retrieval.db.connection import get_db_connection

        return get_db_connection
    elif name == "seed_knowledge_chunks":
        from ticketpilot.retrieval.db.seeding import seed_knowledge_chunks

        return seed_knowledge_chunks
    elif name == "get_chunk_count":
        from ticketpilot.retrieval.db.seeding import get_chunk_count

        return get_chunk_count
    elif name == "verify_seeding":
        from ticketpilot.retrieval.db.seeding import verify_seeding

        return verify_seeding
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
