#!/usr/bin/env python3
"""Report which owner live-configuration items are present (never prints secret values)."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CHECKS = (
    ("tier_a", "FS_CORP_PUBLIC_URL", "Public URL for pairing", False),
    ("tier_a", "FS_CORP_LAN_IP", "LAN edge IP", False),
    ("tier_a", "FS_CORP_TAILSCALE_AUTHKEY", "Tailscale auth key (optional)", True),
    ("tier_b_github", "GITHUB_APP_ID", "GitHub App ID", False),
    ("tier_b_github", "GITHUB_INSTALLATION_ID", "GitHub installation ID", False),
    ("tier_b_github", "GITHUB_PRIVATE_KEY_FILE", "GitHub App private key path", False),
    ("tier_b_github", "GITHUB_WEBHOOK_SECRET", "GitHub webhook secret", True),
    ("tier_b_model", "MODEL_PROVIDER_API_KEY", "OpenAI-compatible API key", False),
    ("tier_b_model", "ANTHROPIC_API_KEY", "Anthropic (Claude) API key", False),
    ("tier_b_feed", "FEED_API_KEY", "Feed API key (if required)", True),
    ("tier_c", "VAPID_PUBLIC_KEY", "VAPID public key (optional)", True),
    ("tier_c", "VAPID_PRIVATE_KEY", "VAPID private key (optional)", True),
    ("tier_c", "IMAGE_PROVIDER_API_KEY", "Image provider key (optional)", True),
)


def load_env_file(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.is_file():
        return data
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        data[key.strip()] = value.strip().strip("'\"")
    return data


def file_configured(env: dict[str, str], key: str) -> bool:
    value = (env.get(key) or os.environ.get(key) or "").strip()
    if not value:
        return False
    if key.endswith("_FILE") or key.endswith("_PATH"):
        return Path(value).expanduser().is_file()
    return True


def checklist_summary() -> dict | None:
    path = ROOT / "config" / "owner-live.checklist.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Owner live-configuration status (no secrets printed)")
    parser.add_argument("--env-file", type=Path, help="Additional env file to load (e.g. /etc/fs-corporation/secrets.env)")
    args = parser.parse_args()

    env = dict(os.environ)
    if args.env_file:
        env.update(load_env_file(args.env_file))
    else:
        for candidate in (ROOT / ".env", ROOT / "deploy" / "fs-dev" / "secrets.example.env"):
            if candidate.name == "secrets.example.env":
                continue
            if candidate.is_file():
                env.update(load_env_file(candidate))

    print("FS-Corporation owner live-configuration status\n")
    tiers: dict[str, list[tuple[str, str, bool]]] = {}
    for tier, key, label, optional in CHECKS:
        ok = file_configured(env, key)
        tiers.setdefault(tier, []).append((label, key, ok))
        mark = "ok" if ok else ("skip" if optional else "missing")
        print(f"  [{mark:7}] {label} ({key})")

    checklist = checklist_summary()
    if checklist:
        print("\nChecklist file: config/owner-live.checklist.json")
        for section in ("tier_b_github_pilot", "tier_b_model_v1", "tier_b_feed_v1", "tier_b_worker"):
            block = checklist.get(section, {})
            status = block.get("status", "unknown")
            print(f"  {section}: {status}")
    else:
        print("\nNo config/owner-live.checklist.json — copy from config/owner-live.checklist.template.json")

    required_missing = sum(
        1 for tier, key, label, optional in CHECKS
        if not optional and not file_configured(env, key)
    )
    github_core = all(file_configured(env, k) for k in (
        "GITHUB_APP_ID", "GITHUB_INSTALLATION_ID", "GITHUB_PRIVATE_KEY_FILE"))
    model_ready = file_configured(env, "MODEL_PROVIDER_API_KEY") or file_configured(env, "ANTHROPIC_API_KEY")
    print(f"\nSummary: {required_missing} required env gaps (excludes optional keys)")
    print(f"  GitHub pilot ready: {'yes' if github_core else 'no'}")
    print(f"  Model v1 ready: {'yes' if model_ready else 'no'}")
    print("\nFull checklist: docs/26-owner-live-configuration.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
