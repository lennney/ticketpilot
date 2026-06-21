"""Git operations for the optimizer."""

from __future__ import annotations

import subprocess
from pathlib import Path


def run_git(*args: str, cwd: Path | None = None) -> str:
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git"] + list(args),
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def commit(message: str, cwd: Path | None = None) -> str:
    """Stage all changes and commit. Returns commit SHA."""
    run_git("add", "-A", cwd=cwd)
    run_git("commit", "-m", message, "--allow-empty", cwd=cwd)
    return run_git("rev-parse", "HEAD", cwd=cwd)


def has_changes(cwd: Path | None = None) -> bool:
    """Check if there are uncommitted changes."""
    output = run_git("status", "--porcelain", cwd=cwd)
    return len(output) > 0


def revert(sha: str, cwd: Path | None = None) -> None:
    """Revert a specific commit."""
    run_git("revert", sha, "--no-edit", cwd=cwd)


def revert_last_commit(cwd: Path | None = None) -> str:
    """Revert the last commit (HEAD) by creating a new undo commit.

    Uses ``git revert HEAD --no-edit`` to create a commit that
    undoes the last change while preserving full history. Returns the SHA
    of the revert commit.
    """
    run_git("revert", "HEAD", "--no-edit", cwd=cwd)
    return run_git("rev-parse", "HEAD", cwd=cwd)
