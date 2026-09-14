# ChatDev-in-Worker Depth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Ship v0.3.90 with opt-in worker-image `uv sync` at the ChatDev pin, `deps_ready` status honesty, CI proof that worker gateway `invoke_model` writes `billed_costs`, and an optional fs-dev smoke that fail-closes without credentials.

**Architecture:** Extend `Dockerfile.worker` ChatDev branch to install `uv` and run `uv sync` (fail build on sync failure); label `org.fs_corporation.chatdev_deps` from `CHATDEV_ENABLE` (sync is mandatory when enable=1); expose `deps_ready` from image inspect; add gateway billed contract test + smoke script; docs/ADR.

**Tech Stack:** Docker/uv, Python company worker gateway, unittest, optional fs-dev smoke script.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-14-chatdev-worker-depth-design.md` (owner-approved).
- Version **0.3.90**. Soften exact `0.3.89` pins to `0\.3\.\d+` where needed.
- Pin remains `4fb2db0ea90375ce1059f44fe03ffbd191a7a169`.
- Default image stays mock-only (`CHATDEV_ENABLE=0`).
- No ChatDev in root `pyproject.toml` / control-plane venv.
- No live Anthropic/OpenAI required for CI green.
- Do not open unrestricted Docker bridge/host.
- Do not commit `local repos/service-department/` or `.vscode/tasks.json`.
- Prefer owner-gated commits; if executing under SDD/owner “execute”, commits are authorized.
- Branch: create `feature/chatdev-worker-depth` from current `main` before Task 1.
- Work **in-place** on the feature branch.

## File map

| Path | Role |
|---|---|
| `deploy/fs-dev/Dockerfile.worker` | `uv` + `uv sync` + deps label when `CHATDEV_ENABLE=1` |
| `company/chatdev_runtime.py` | `LABEL_CHATDEV_DEPS`, `deps_ready` in summary |
| `tests/test_worker_dockerfile_chatdev.py` | Dockerfile contracts for uv sync / deps label |
| `tests/test_chatdev_adapter.py` | Inspect labels include `deps_ready` |
| `tests/test_worker_chatdev_billed.py` (new) | Gateway `invoke_model` → `billed_costs` |
| `scripts/exercise_chatdev_worker_billed.py` | Optional fs-dev smoke |
| Docs + versions | ADR-072, 07/23/25, API contract, README, VERIFICATION, handoff, roadmap |

---

### Task 1: Dockerfile uv sync + deps_ready status

**Files:**
- Modify: `deploy/fs-dev/Dockerfile.worker`
- Modify: `company/chatdev_runtime.py`
- Modify: `tests/test_worker_dockerfile_chatdev.py`
- Modify: `tests/test_chatdev_adapter.py`
- Test: `tests/test_worker_dockerfile_chatdev.py`, `tests/test_chatdev_adapter.py`

**Interfaces:**
- Produces: label `org.fs_corporation.chatdev_deps`; `worker_image_chatdev_summary()` always includes `deps_ready: bool` when summary is non-null

- [x] **Step 1: Create branch**

```bash
cd /Users/andrew/Documents/FS-Tech/fs-corporation
git checkout main
git pull --ff-only
git checkout -b feature/chatdev-worker-depth
```

- [x] **Step 2: Write failing Dockerfile + status tests**

Append to `tests/test_worker_dockerfile_chatdev.py`:

```python
    def test_dockerfile_opt_in_runs_uv_sync(self):
        self.assertIn("uv sync", self.text)
        self.assertIn("org.fs_corporation.chatdev_deps", self.text)

    def test_dockerfile_default_enable_is_zero(self):
        self.assertIn("ARG CHATDEV_ENABLE=0", self.text)
```

Update `tests/test_chatdev_adapter.py` — in `test_worker_image_chatdev_from_inspect_labels`, add deps label to JSON and assert `deps_ready`. Add sibling tests:

```python
    def test_worker_image_chatdev_deps_ready_from_label(self):
        from company.chatdev_runtime import worker_image_chatdev_summary
        labels_json = (
            '{"org.fs_corporation.chatdev_enable":"1",'
            '"org.fs_corporation.chatdev_pin":"' + PINNED_COMMIT + '",'
            '"org.fs_corporation.chatdev_deps":"1"}'
        )
        with patch("company.chatdev_runtime.shutil.which", return_value="/usr/bin/docker"):
            with patch("company.chatdev_runtime.subprocess.run") as run:
                run.return_value = SimpleNamespace(returncode=0, stdout=labels_json)
                summary = worker_image_chatdev_summary()
        self.assertTrue(summary["deps_ready"])

    def test_worker_image_chatdev_deps_ready_false_when_absent(self):
        from company.chatdev_runtime import worker_image_chatdev_summary
        labels_json = (
            '{"org.fs_corporation.chatdev_enable":"1",'
            '"org.fs_corporation.chatdev_pin":"' + PINNED_COMMIT + '"}'
        )
        with patch("company.chatdev_runtime.shutil.which", return_value="/usr/bin/docker"):
            with patch("company.chatdev_runtime.subprocess.run") as run:
                run.return_value = SimpleNamespace(returncode=0, stdout=labels_json)
                summary = worker_image_chatdev_summary()
        self.assertFalse(summary["deps_ready"])
```

Also update existing `test_worker_image_chatdev_from_inspect_labels` to assert `self.assertFalse(summary["deps_ready"])` when deps label is absent (same as sibling), or include `"org.fs_corporation.chatdev_deps":"1"` and `assertTrue`. Prefer keeping the existing test without deps label and asserting `deps_ready is False`, then the new test covers True.

- [x] **Step 3: Run — expect FAIL**

```bash
.venv/bin/python -m unittest tests.test_worker_dockerfile_chatdev tests.test_chatdev_adapter -v
```

Expected: FAIL — `uv sync` / `chatdev_deps` missing from Dockerfile; `deps_ready` KeyError or assertion fail.

- [x] **Step 4: Implement Dockerfile**

Replace `deploy/fs-dev/Dockerfile.worker` ChatDev section so the file is:

```dockerfile
# Build: docker build -f deploy/fs-dev/Dockerfile.worker -t fs-corporation-worker:local .
# Opt-in ChatDev: --build-arg CHATDEV_ENABLE=1
ARG CHATDEV_ENABLE=0
ARG CHATDEV_REF=4fb2db0ea90375ce1059f44fe03ffbd191a7a169

FROM python:3.12-slim

ARG CHATDEV_ENABLE
ARG CHATDEV_REF

WORKDIR /src

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.6.14 /uv /usr/local/bin/uv

COPY pyproject.toml README.md /src/
COPY company /src/company
COPY fixtures /src/fixtures

RUN pip install --no-cache-dir /src

# Opt-in: embed pinned ChatDev source + uv sync (fail closed). Entry point sets CHATDEV_HOME.
RUN if [ "$CHATDEV_ENABLE" = "1" ]; then \
      git clone --depth 1 https://github.com/OpenBMB/ChatDev.git /opt/chatdev \
      && cd /opt/chatdev && git fetch --depth 1 origin "$CHATDEV_REF" && git checkout "$CHATDEV_REF" \
      && test -f /opt/chatdev/runtime/sdk.py \
      && cd /opt/chatdev && uv sync \
      && test -d /opt/chatdev/.venv; \
    fi

LABEL org.fs_corporation.chatdev_enable="${CHATDEV_ENABLE}"
LABEL org.fs_corporation.chatdev_pin="${CHATDEV_REF}"
# After this ship, ENABLE=1 implies deps (uv sync is mandatory). Historical source-only
# images lack this label → deps_ready false.
LABEL org.fs_corporation.chatdev_deps="${CHATDEV_ENABLE}"

COPY deploy/fs-dev/worker-entrypoint.sh /usr/local/bin/worker-entrypoint.sh
RUN chmod +x /usr/local/bin/worker-entrypoint.sh

WORKDIR /work
ENTRYPOINT ["/usr/local/bin/worker-entrypoint.sh"]
```

Note: `worker-entrypoint.sh` already exports `CHATDEV_HOME=/opt/chatdev` when `sdk.py` exists — keep that; do not set a static `ENV CHATDEV_HOME` on the mock image.

- [x] **Step 5: Implement `deps_ready` in `worker_image_chatdev_summary`**

In `company/chatdev_runtime.py`:

```python
LABEL_CHATDEV_ENABLE = "org.fs_corporation.chatdev_enable"
LABEL_CHATDEV_PIN = "org.fs_corporation.chatdev_pin"
LABEL_CHATDEV_DEPS = "org.fs_corporation.chatdev_deps"
```

At end of `worker_image_chatdev_summary`, before `return out`:

```python
    deps_raw = labels.get(LABEL_CHATDEV_DEPS)
    out["deps_ready"] = str(deps_raw).strip() == "1" if deps_raw is not None else False
```

Always set `deps_ready` whenever a summary dict is returned.

- [x] **Step 6: Run — expect PASS**

```bash
.venv/bin/python -m unittest tests.test_worker_dockerfile_chatdev tests.test_chatdev_adapter -v
```

Expected: OK.

- [x] **Step 7: Commit**

```bash
git add deploy/fs-dev/Dockerfile.worker company/chatdev_runtime.py \
  tests/test_worker_dockerfile_chatdev.py tests/test_chatdev_adapter.py
git commit -m "$(cat <<'EOF'
feat(worker): uv sync ChatDev deps in opt-in image

EOF
)"
```

---

### Task 2: Gateway billed contract + smoke script

**Files:**
- Create: `tests/test_worker_chatdev_billed.py`
- Create: `scripts/exercise_chatdev_worker_billed.py`
- Modify: `docs/07-chatdev-integration.md` (status table + smoke)
- Modify: `docs/23-isolated-workers.md` (billed gateway + smoke pointer)
- Modify: `docs/25-fs-dev-deployment.md` (smoke prerequisites)
- Test: `tests/test_worker_chatdev_billed.py`

**Interfaces:**
- Consumes: `SubprocessWorkerRuntime.handle_request(company, msg)` → `company.invoke_model`
- Produces: CI assertion that gateway live invoke writes one `billed_costs` row; smoke exits non-zero without prereqs

- [x] **Step 1: Write failing billed gateway test**

Create `tests/test_worker_chatdev_billed.py` (mirror `tests/test_m10_finance.py` live path through the worker gateway):

```python
"""Worker gateway invoke_model persists billed_costs (ChatDev-in-worker depth)."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from company.core import Company
from company.worker import SubprocessWorkerRuntime
from tests.env_guard import AmbientEnvIsolatedTestCase
from tests.test_core import install, policy


class WorkerChatDevBilledTests(AmbientEnvIsolatedTestCase):
    def setUp(self):
        super().setUp()
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)
        self.registry = {"profiles": {
            "mock-text": {
                "provider": "mock", "enabled": True,
                "capabilities": ["text"], "allowed_data": ["public"],
            },
            "live": {
                "provider": "openai", "enabled": True, "model": "gpt-4o-mini",
                "capabilities": ["text"], "allowed_data": ["public"],
            },
        }}

    def test_gateway_mock_invoke_does_not_write_billed_cost(self):
        before = int(self.c.db.execute("SELECT COUNT(*) FROM billed_costs").fetchone()[0])
        SubprocessWorkerRuntime.handle_request(self.c, {
            "op": "invoke_model",
            "profile_id": "mock-text",
            "prompt": "hello",
            "registry": self.registry,
        })
        after = int(self.c.db.execute("SELECT COUNT(*) FROM billed_costs").fetchone()[0])
        self.assertEqual(after, before)

    @patch("company.model_provider.complete")
    def test_gateway_live_invoke_writes_billed_cost(self, mock_complete):
        mock_complete.return_value = {
            "text": "pilot",
            "profile_id": "live",
            "usage_tokens": 1200,
            "cost_cents": 5,
            "provider": "openai",
            "model": "gpt-4o-mini",
        }
        before = int(self.c.db.execute("SELECT COUNT(*) FROM billed_costs").fetchone()[0])
        with patch.dict("os.environ", {"MODEL_PROVIDER_API_KEY": "test-key"}, clear=False):
            out = SubprocessWorkerRuntime.handle_request(self.c, {
                "op": "invoke_model",
                "profile_id": "live",
                "prompt": "hello",
                "registry": self.registry,
            })
        self.assertEqual(out["usage_tokens"], 1200)
        self.assertEqual(out["cost_cents"], 5)
        after = int(self.c.db.execute("SELECT COUNT(*) FROM billed_costs").fetchone()[0])
        self.assertEqual(after, before + 1)
        row = self.c.db.execute(
            "SELECT amount_cents, usage_tokens, source, profile_id FROM billed_costs "
            "ORDER BY rowid DESC LIMIT 1"
        ).fetchone()
        self.assertEqual(row["amount_cents"], 5)
        self.assertEqual(row["usage_tokens"], 1200)
        self.assertEqual(row["source"], "invoke_model")
        self.assertEqual(row["profile_id"], "live")


if __name__ == "__main__":
    unittest.main()
```

- [x] **Step 2: Run — expect PASS if gateway already wires invoke_model; else FAIL**

```bash
.venv/bin/python -m unittest tests.test_worker_chatdev_billed -v
```

Expected: PASS (gateway already calls `company.invoke_model`). If FAIL, fix only the test message shape — do not invent billed rows in production.

- [x] **Step 3: Write smoke script**

Create `scripts/exercise_chatdev_worker_billed.py`:

```python
#!/usr/bin/env python3
"""Fail-closed fs-dev smoke for ChatDev worker deps + billed gateway path.

Requires (all must be present or exit 2):
  - Docker + FS_CORP_WORKER_IMAGE with org.fs_corporation.chatdev_deps=1
  - FS_CORP_CHATDEV_WORKER_EGRESS=allowlist and ready allowlist/network
  - MODEL_PROVIDER_API_KEY or ANTHROPIC_API_KEY set
  - FS_CORP_DB for local Company invoke (default path used by fs-dev)

Never invents billed_costs rows. Optional --check-only skips the invoke.
"""
from __future__ import annotations

import argparse
import os
import sys


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

    registry = {"profiles": {
        "live": {
            "provider": "openai",
            "enabled": True,
            "model": "gpt-4o-mini",
            "capabilities": ["text"],
            "allowed_data": ["public"],
        },
    }}
    c = Company()
    try:
        before = int(c.db.execute("SELECT COUNT(*) FROM billed_costs").fetchone()[0])
        out = SubprocessWorkerRuntime.handle_request(c, {
            "op": "invoke_model",
            "profile_id": args.profile_id,
            "prompt": "fs-corp chatdev billed smoke",
            "registry": registry,
        })
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
```

Make executable: `chmod +x scripts/exercise_chatdev_worker_billed.py`.

- [x] **Step 4: Document smoke in integration docs**

In `docs/07-chatdev-integration.md` status paragraph, add `deps_ready` to `worker_image_chatdev` fields. Add a short “Billed smoke” subsection pointing at `scripts/exercise_chatdev_worker_billed.py` and the env names above.

In `docs/23-isolated-workers.md`, note that worker gateway `invoke_model` writes `billed_costs` (same as control-plane live invoke) and link the smoke script.

In `docs/25-fs-dev-deployment.md`, add a short bullet under ChatDev/worker: optional smoke requires ChatDev-enabled image with deps, allowlist egress, and model key; never invents billed rows.

- [x] **Step 5: Run unit test again**

```bash
.venv/bin/python -m unittest tests.test_worker_chatdev_billed -v
```

Expected: OK.

- [x] **Step 6: Commit**

```bash
git add tests/test_worker_chatdev_billed.py scripts/exercise_chatdev_worker_billed.py \
  docs/07-chatdev-integration.md docs/23-isolated-workers.md docs/25-fs-dev-deployment.md
git commit -m "$(cat <<'EOF'
test(worker): prove gateway billed costs; add ChatDev billed smoke

EOF
)"
```

---

### Task 3: Version 0.3.90 + docs

**Files:**
- Modify: `company/__init__.py`, `companion/package.json`
- Modify: `docs/decisions.md` (ADR-072)
- Modify: `docs/16-api-contract.md`
- Modify: `README.md`, `VERIFICATION.md`, `docs/18-handoff.md`, `docs/14-roadmap.md`
- Modify: `docs/superpowers/specs/2026-09-14-chatdev-worker-depth-design.md` (status → implemented in v0.3.90)
- Modify: this plan (checkboxes as completed during execution)
- Test: full suite + companion build

**Interfaces:**
- Produces: version **0.3.90**; ADR-072; API note for `deps_ready`

- [x] **Step 1: Bump versions**

Set `company/__init__.py` `__version__` and `companion/package.json` `"version"` to `0.3.90`.

- [x] **Step 2: ADR-072 in `docs/decisions.md`**

Add index row + body:

- Context: Slice 3 embedded ChatDev source without `uv sync`; status lacked deps honesty; billed gateway path unproven for workers.
- Decision: When `CHATDEV_ENABLE=1`, Dockerfile runs `uv sync` (fail closed), labels `org.fs_corporation.chatdev_deps`, status exposes `deps_ready`; CI proves `SubprocessWorkerRuntime.handle_request(invoke_model)` writes `billed_costs`; optional smoke fail-closes without image/egress/key; control-plane still has no ChatDev install.
- Consequences: Rebuild with `FS_CORP_WORKER_CHATDEV=1` required for live ChatDev workers; historical source-only images report `deps_ready: false`.

- [x] **Step 3: API contract**

In `docs/16-api-contract.md` `GET /chatdev/status` row, note `worker_image_chatdev` may include `deps_ready` (bool) from `org.fs_corporation.chatdev_deps`.

- [x] **Step 4: README / VERIFICATION / handoff / roadmap**

- README capability row: ChatDev worker image may include uv-synced deps when opt-in; `deps_ready` on status.
- VERIFICATION: 0.3.90 checklist items for Dockerfile/uv/deps_ready/billed gateway test/smoke.
- Roadmap: mark ChatDev-in-worker depth done at 0.3.90.
- Handoff: version 0.3.90, tip SHA after ship commit, next owner follow-up.

- [x] **Step 5: Mark design implemented**

In design doc header: `Status: **implemented in v0.3.90**.`

- [x] **Step 6: Full suite + companion build**

```bash
.venv/bin/python -m unittest discover -s tests
cd companion && npm run build
```

Expected: all tests OK; companion build OK.

- [x] **Step 7: Commit**

```bash
git add company/__init__.py companion/package.json docs/decisions.md docs/16-api-contract.md \
  README.md VERIFICATION.md docs/18-handoff.md docs/14-roadmap.md \
  docs/superpowers/specs/2026-09-14-chatdev-worker-depth-design.md \
  docs/superpowers/plans/2026-09-14-chatdev-worker-depth.md
git commit -m "$(cat <<'EOF'
docs: ship ChatDev-in-worker depth as 0.3.90

EOF
)"
```

---

## Spec coverage

| Spec item | Task |
|---|---|
| uv sync in opt-in Dockerfile (fail closed) | 1 |
| deps label / deps_ready | 1 |
| Gateway billed contract test | 2 |
| Optional smoke fail-closed | 2 |
| Docs 07 / 23 / 25 | 2 |
| Version 0.3.90 + ADR + API + README/VERIFICATION/handoff/roadmap | 3 |

## Plan self-review

- No TBD/placeholder steps; Task 2 test mirrors `test_m10_finance` through `handle_request`.
- LABEL strategy: `chatdev_deps="${CHATDEV_ENABLE}"` with mandatory `uv sync` when enable=1.
- Smoke never invents billed rows; exits 2 on missing prereqs.
- `CHATDEV_HOME` remains entrypoint-set (mock image stays clean).
