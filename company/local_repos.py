"""Scan local repos/ for company project enroll candidates."""
from __future__ import annotations
import os
import subprocess
from pathlib import Path


def local_repos_root() -> Path:
    env = (os.environ.get("FS_CORP_LOCAL_REPOS_DIR") or "").strip()
    if env:
        return Path(env).expanduser().resolve()
    install = (os.environ.get("FS_CORP_INSTALL_DIR") or "").strip()
    if install:
        return (Path(install) / "local repos").resolve()
    return (Path(__file__).resolve().parents[1] / "local repos").resolve()


def _git_remote(path: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(path), "remote", "get-url", "origin"],
            check=False, capture_output=True, text=True, timeout=5,
        )
        if out.returncode != 0:
            return None
        url = (out.stdout or "").strip()
        return url or None
    except (OSError, subprocess.TimeoutExpired):
        return None


def scan_local_repos(root: Path | None = None, enrolled_ids: set[str] | None = None) -> dict:
    """Return {root, present, candidates[]} without inventing repos."""
    base = root if root is not None else local_repos_root()
    enrolled = enrolled_ids or set()
    if not base.is_dir():
        return {"root": str(base), "present": False, "candidates": []}
    candidates = []
    for child in sorted(base.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        has_git = (child / ".git").exists()
        remote = _git_remote(child) if has_git else None
        cid = child.name
        candidates.append({
            "id": cid,
            "path": str(child.resolve()),
            "has_git": has_git,
            "remote_url": remote,
            "enrolled": cid in enrolled,
        })
    return {"root": str(base), "present": True, "candidates": candidates}
