"""Pytest configuration."""

import os
import shutil
import site
import sys
import tempfile


def _setup_psycopg_dll_path():
    """Copy psycopg DLLs to local temp dir for Windows DLL loader."""
    if sys.platform != "win32":
        return
    for sp in site.getsitepackages():
        d = os.path.join(sp, "psycopg_binary.libs")
        if os.path.exists(d):
            cache_dir = os.path.join(tempfile.gettempdir(), "ticketpilot_dlls")
            os.makedirs(cache_dir, exist_ok=True)
            for f in os.listdir(d):
                src = os.path.join(d, f)
                dst = os.path.join(cache_dir, f)
                if not os.path.exists(dst):
                    shutil.copy2(src, dst)
            os.add_dll_directory(cache_dir)
            os.environ["PATH"] = cache_dir + os.pathsep + os.environ.get("PATH", "")
            break


_setup_psycopg_dll_path()
