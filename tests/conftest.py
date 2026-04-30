"""Pytest configuration — ensures psycopg DLLs are loadable on Windows."""

import os
import site
import sys


def _setup_psycopg_dll_path():
    """Add psycopg binary libs to DLL search path before any imports."""
    if sys.platform != "win32":
        return
    for sp in site.getsitepackages():
        psycopg_bin_dir = os.path.join(sp, "psycopg_binary.libs")
        if os.path.exists(psycopg_bin_dir):
            os.add_dll_directory(psycopg_bin_dir)
            os.environ["PATH"] = (
                psycopg_bin_dir + os.pathsep + os.environ.get("PATH", "")
            )
            break


_setup_psycopg_dll_path()
