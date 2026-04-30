"""Database connection management for retrieval."""

import os
import sys
from contextlib import contextmanager
from typing import Generator, Optional

# Add psycopg_binary.libs to DLL search path on Windows
if sys.platform == "win32":
    import site

    def _add_psycopg_dll_dir():
        """Add psycopg binary libs to DLL search path."""
        for sp in site.getsitepackages():
            psycopg_bin_dir = os.path.join(sp, "psycopg_binary.libs")
            if os.path.exists(psycopg_bin_dir):
                os.add_dll_directory(psycopg_bin_dir)
                # Also add to PATH as fallback
                os.environ["PATH"] = psycopg_bin_dir + os.pathsep + os.environ.get("PATH", "")
                break

    _add_psycopg_dll_dir()

from psycopg import Connection
from psycopg_pool import ConnectionPool

# Database configuration from environment
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "ticketpilot")
DB_USER = os.getenv("DB_USER", "ticketpilot")
DB_PASSWORD = os.getenv("DB_PASSWORD", "ticketpilot")

# Connection pool
_pool: Optional[ConnectionPool] = None


def get_db_pool() -> ConnectionPool:
    """
    Get or create the database connection pool.

    Returns:
        psycopg ConnectionPool instance
    """
    global _pool
    if _pool is None:
        conninfo = (
            f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} "
            f"user={DB_USER} password={DB_PASSWORD}"
        )
        _pool = ConnectionPool(
            conninfo,
            min_size=2,
            max_size=10,
        )
    return _pool


def close_db_pool() -> None:
    """Close the database connection pool."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def get_db_connection() -> Generator[Connection, None, None]:
    """
    Get a database connection from the pool.

    Yields:
        psycopg Connection instance

    Example:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    """
    pool = get_db_pool()
    conn = pool.getconn()
    try:
        yield conn
    finally:
        pool.putconn(conn)


@contextmanager
def get_db_transaction() -> Generator[Connection, None, None]:
    """
    Get a database connection with an active transaction.

    The transaction is committed on success, rolled back on exception.

    Yields:
        psycopg Connection instance with active transaction
    """
    with get_db_connection() as conn:
        with conn.transaction():
            yield conn