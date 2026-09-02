#!/usr/bin/env python3
"""Verify model provider credentials without printing secrets."""
from __future__ import annotations
import json
import sys

from company.model_provider import anthropic_configured, model_configured, openai_configured, status_summary


def main() -> int:
    if not model_configured():
        print("No model provider configured. Set MODEL_PROVIDER_API_KEY and/or ANTHROPIC_API_KEY.")
        return 1
    summary = status_summary(probe=True)
    print(json.dumps(summary, indent=2))
    openai = summary.get("openai") or {}
    anthropic = summary.get("anthropic") or {}
    ok = False
    if openai_configured():
        ok = ok or bool(openai.get("live"))
    if anthropic_configured():
        ok = ok or bool(anthropic.get("live"))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
