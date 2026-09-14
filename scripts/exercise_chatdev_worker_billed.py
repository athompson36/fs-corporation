#!/usr/bin/env python3
"""Fail-closed fs-dev smoke for ChatDev worker deps + billed gateway path.

Requires (all must be present or exit 2):
  - Docker + FS_CORP_WORKER_IMAGE with org.fs_corporation.chatdev_deps=1
  - FS_CORP_CHATDEV_WORKER_EGRESS=allowlist and ready allowlist/network
  - MODEL_PROVIDER_API_KEY or ANTHROPIC_API_KEY set

Live invoke (default) also requires FS_CORP_DB. Use --check-only to verify image,
egress, and model key without opening the database or calling invoke_model.

Never invents billed_costs rows. Invoke failures exit 1 with a clear message.
"""
from __future__ import annotations

import argparse
import os
import sys


def _registry_for_keys(profile_id: str) -> dict:
    openai_key = (os.environ.get("MODEL_PROVIDER_API_KEY") or "").strip()
    anthropic_key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if anthropic_key and not openai_key:
        return {"profiles": {
            profile_id: {
                "provider": "anthropic",
                "enabled": True,
                "model": "claude-3-5-haiku-latest",
                "capabilities": ["text"],
                "allowed_data": ["public"],
            },
        }}
    return {"profiles": {
        profile_id: {
            "provider": "openai",
            "enabled": True,
            "model": "gpt-4o-mini",
            "capabilities": ["text"],
            "allowed_data": ["public"],
        },
    }}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only verify prerequisites; do not invoke_model",
    )
    parser.add_argument(
        "--profile-id",
        default="live",
        help="Model profile id for gateway invoke (default: live)",
    )
    args = parser.parse_args()

    from company.chatdev_runtime import status_summary
    from company.core import Company
    from company.worker import SubprocessWorkerRuntime

    status = status_summary()
    img = status.get("worker_image_chatdev") or {}
    missing: list[str] = []
    if not img.get("enabled"):
        missing.append("worker_image_chatdev.enabled (rebuild with CHATDEV_ENABLE=1)")
    if not img.get("deps_ready"):
        missing.append("worker_image_chatdev.deps_ready (uv sync label missing)")
    if not status.get("worker_egress_ready"):
        missing.append(
            "worker_egress_ready (set FS_CORP_CHATDEV_WORKER_EGRESS=allowlist, "
            "FS_CORP_CHATDEV_EGRESS_ALLOWLIST_FILE, FS_CORP_CHATDEV_EGRESS_DOCKER_NETWORK)"
        )
    key_ok = bool(
        (os.environ.get("MODEL_PROVIDER_API_KEY") or "").strip()
        or (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    )
    if not key_ok:
        missing.append("MODEL_PROVIDER_API_KEY or ANTHROPIC_API_KEY")
    if missing:
        print("ChatDev billed smoke prerequisites missing:", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        return 2

    print("prerequisites ok:", {
        "image": img.get("image"),
        "deps_ready": img.get("deps_ready"),
        "worker_egress_ready": status.get("worker_egress_ready"),
    })
    if args.check_only:
        return 0

    db_path = (os.environ.get("FS_CORP_DB") or "").strip()
    if not db_path:
        print("FS_CORP_DB is required for live invoke (omit with --check-only)", file=sys.stderr)
        return 2

    registry = _registry_for_keys(args.profile_id)
    c = Company(db_path)
    try:
        before = int(c.db.execute("SELECT COUNT(*) FROM billed_costs").fetchone()[0])
        try:
            out = SubprocessWorkerRuntime.handle_request(c, {
                "op": "invoke_model",
                "profile_id": args.profile_id,
                "prompt": "fs-corp chatdev billed smoke",
                "registry": registry,
            })
        except Exception as exc:
            print(f"invoke_model failed: {exc}", file=sys.stderr)
            return 1
        after = int(c.db.execute("SELECT COUNT(*) FROM billed_costs").fetchone()[0])
    finally:
        c.close()

    if after != before + 1:
        print(
            f"expected billed_costs +1 (before={before} after={after}); got {out!r}",
            file=sys.stderr,
        )
        return 1
    print("billed gateway ok:", {"usage_tokens": out.get("usage_tokens"), "cost_cents": out.get("cost_cents")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
