"""Tests for ticketpilot.optimizer.git_ops module."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ticketpilot.optimizer.git_ops import (
    commit,
    has_changes,
    revert,
    revert_last_commit,
    run_git,
)


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repository with an initial commit."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path, capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path, capture_output=True, check=True,
    )
    # Make an initial commit so HEAD exists
    (tmp_path / ".gitkeep").write_text("")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "initial", "--allow-empty"],
        cwd=tmp_path, capture_output=True, check=True,
    )
    return tmp_path


class TestRunGit:
    """Tests for run_git helper."""

    def test_run_git_success(self, git_repo: Path) -> None:
        """run_git returns stdout for successful commands."""
        result = run_git("rev-parse", "HEAD", cwd=git_repo)
        assert result  # Should return a SHA
        assert len(result) == 40

    def test_run_git_failure(self, git_repo: Path) -> None:
        """run_git raises RuntimeError for failed commands."""
        with pytest.raises(RuntimeError, match="failed"):
            run_git("status", "--nonexistent-flag", cwd=git_repo)


class TestCommit:
    """Tests for commit function."""

    def test_commit_returns_sha(self, git_repo: Path) -> None:
        """commit returns a valid SHA string."""
        (git_repo / "new_file.txt").write_text("hello")
        sha = commit("test commit", cwd=git_repo)
        assert len(sha) == 40  # Full SHA-1
        assert all(c in "0123456789abcdef" for c in sha)

    def test_commit_stages_changes(self, git_repo: Path) -> None:
        """commit stages all untracked files."""
        (git_repo / "new_file.txt").write_text("hello")
        sha = commit("add file", cwd=git_repo)
        # Verify the file is committed
        result = run_git("show", "--stat", sha, cwd=git_repo)
        assert "new_file.txt" in result


class TestHasChanges:
    """Tests for has_changes function."""

    def test_no_changes(self, git_repo: Path) -> None:
        """has_changes returns False when working tree is clean."""
        assert has_changes(cwd=git_repo) is False

    def test_with_untracked_file(self, git_repo: Path) -> None:
        """has_changes returns True when there are untracked files."""
        (git_repo / "untracked.txt").write_text("new")
        assert has_changes(cwd=git_repo) is True

    def test_with_modified_file(self, git_repo: Path) -> None:
        """has_changes returns True when tracked files are modified."""
        (git_repo / ".gitkeep").write_text("modified")
        assert has_changes(cwd=git_repo) is True


class TestRevert:
    """Tests for revert function."""

    def test_revert_by_sha(self, git_repo: Path) -> None:
        """revert undoes a specific commit (non-conflicting)."""
        # Add a new file in one commit
        (git_repo / "new_feature.txt").write_text("feature")
        sha1 = commit("add feature", cwd=git_repo)

        # Add an unrelated file in the next commit
        (git_repo / "unrelated.txt").write_text("other")
        commit("add unrelated", cwd=git_repo)

        # Revert the first commit — should cleanly remove new_feature.txt
        revert(sha1, cwd=git_repo)

        assert not (git_repo / "new_feature.txt").exists()
        assert (git_repo / "unrelated.txt").exists()


class TestRevertLastCommit:
    """Tests for revert_last_commit function."""

    def test_revert_last_commit_returns_sha(self, git_repo: Path) -> None:
        """revert_last_commit returns the SHA of the undo commit."""
        (git_repo / "feature_a.txt").write_text("a")
        commit("add feature_a", cwd=git_repo)

        (git_repo / "feature_b.txt").write_text("b")
        commit("add feature_b", cwd=git_repo)

        revert_sha = revert_last_commit(cwd=git_repo)

        assert len(revert_sha) == 40
        assert all(c in "0123456789abcdef" for c in revert_sha)

    def test_revert_last_commit_creates_new_commit(self, git_repo: Path) -> None:
        """revert_last_commit creates a new commit that undoes the last one."""
        sha_original = run_git("rev-parse", "HEAD", cwd=git_repo)

        (git_repo / "feature.txt").write_text("content")
        sha_added = commit("add feature", cwd=git_repo)

        revert_sha = revert_last_commit(cwd=git_repo)

        # The revert commit should be different from both
        assert revert_sha != sha_original
        assert revert_sha != sha_added
        # HEAD should now be the revert commit
        head = run_git("rev-parse", "HEAD", cwd=git_repo)
        assert head == revert_sha

    def test_revert_last_commit_undoes_change(self, git_repo: Path) -> None:
        """revert_last_commit actually undoes the last commit's changes."""
        (git_repo / "ephemeral.txt").write_text("will be undone")
        commit("add ephemeral", cwd=git_repo)

        revert_last_commit(cwd=git_repo)

        # The file should no longer exist after the revert
        assert not (git_repo / "ephemeral.txt").exists()

    def test_revert_last_commit_preserves_history(self, git_repo: Path) -> None:
        """revert_last_commit uses git revert (not reset), preserving history."""
        commit("first", cwd=git_repo)
        (git_repo / "file.txt").write_text("second")
        commit("second", cwd=git_repo)

        revert_last_commit(cwd=git_repo)

        # History should show: initial, first, second, Revert "second"
        log = run_git("log", "--oneline", cwd=git_repo)
        lines = log.strip().split("\n")
        assert len(lines) == 4  # initial + first + second + revert
        assert "Revert" in lines[0]  # Most recent is the revert
