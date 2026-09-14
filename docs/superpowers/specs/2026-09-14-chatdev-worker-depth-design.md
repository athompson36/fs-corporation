# Design: ChatDev-in-worker depth (0.3.90)

Date: 2026-09-14. Status: **approved (pending implement)**.

## Goal

Deepen the opt-in ChatDev worker image: install pinned ChatDev dependencies
(`uv sync`) so the SDK is runnable in-image, expose honest deps readiness on
status, prove billed gateway `invoke_model` → `billed_costs` via contract tests,
and provide an optional fs-dev smoke that fail-closes without credentials.

## Owner locks

| Topic | Choice |
|---|---|
| Intent | Deps in opt-in image **and** prove billed in-container path when egress + model key exist |
| Proof | Contract tests + optional fs-dev smoke (fail-closed if unset) |
| Default image | Stay mock-only; ChatDev+deps only when `CHATDEV_ENABLE=1` / `FS_CORP_WORKER_CHATDEV=1` |
| Approach | `uv sync` at pin in Dockerfile + gateway billed proof |
| Version | **0.3.90** |
| Alembic | None |

## Non-goals

- Baking ChatDev into every default worker build.
- Installing ChatDev into the control-plane venv / root `pyproject.toml`.
- Unrestricted Docker `bridge`/`host` networking.
- Requiring live Anthropic/OpenAI for CI green.
- Changing the ChatDev pin without a separate ADR.
- Stripe / provider invoice CSV work.

## Problem

Slice 3 (0.3.40 / ADR-024) embeds pin **source** + labels when `CHATDEV_ENABLE=1`
but explicitly deferred full dependency install. Operators see `worker_image_chatdev.enabled`
without knowing whether `uv sync` ran. Live billed model calls from containers need
deps + allowlist egress + keys; that path is under-documented and unproven in suite.

## Behavior

### 1. Opt-in image deps

In `deploy/fs-dev/Dockerfile.worker`, when `CHATDEV_ENABLE=1`:

1. Clone/checkout pin `4fb2db0ea90375ce1059f44fe03ffbd191a7a169` to `/opt/chatdev`
   (existing).
2. Install `uv` for the build.
3. `cd /opt/chatdev && uv sync` using the pin’s `pyproject.toml` / `uv.lock`.
4. **Fail the image build** if sync fails (no silent source-only ChatDev image).
5. `ENV CHATDEV_HOME=/opt/chatdev`.
6. Label `org.fs_corporation.chatdev_deps=1` on successful sync (in addition to
   existing `chatdev_enable` / `chatdev_pin` labels).

When `CHATDEV_ENABLE=0`: unchanged mock-only image (no clone, no uv, no deps label
or label `0`).

`install.sh` / `FS_CORP_WORKER_CHATDEV=1` continues to pass `--build-arg CHATDEV_ENABLE=1`.

### 2. Status honesty

Extend `worker_image_chatdev` (from `docker image inspect` labels):

| Field | Meaning |
|---|---|
| `enabled` | `chatdev_enable == 1` (existing) |
| `pin` | Pin label (existing) |
| `deps_ready` | `true` iff `org.fs_corporation.chatdev_deps` is `1` |

Absent/false when mock image or source-only historical images.

Do **not** fold egress into `worker_live_ready`. Keep
`worker_egress_ready` / allowlist fields separate (ADR-037).

### 3. Contract billed proof (CI)

Add/extend tests so an isolated worker path with `chatdev: true` (or equivalent
selection) that exercises gateway `invoke_model` persists a `billed_costs` row
with honest `amount_cents` / `usage_tokens` (mock/fake provider — no live vendor
in CI). Assert no silent mock-success when live ChatDev was requested but not ready
(existing fail-closed behavior preserved).

Dockerfile contract: assert `uv sync` and `chatdev_deps` label appear in the
opt-in branch of `Dockerfile.worker`.

### 4. Optional fs-dev smoke

Add `scripts/exercise_chatdev_worker_billed.py` (name flexible) that:

- Requires ChatDev-enabled worker image with `deps_ready`, egress allowlist ready,
  and model provider key configured (document exact env names in script help).
- Dispatches a bounded worker ChatDev job that triggers billed invoke.
- Exits non-zero with a clear message if any prerequisite is missing (never invents
  a green billed result).

Document in `docs/07-chatdev-integration.md`, `docs/23-isolated-workers.md`,
`docs/25-fs-dev-deployment.md`.

## Packaging

- Bump `company/__init__.py` and `companion/package.json` → **0.3.90**.
- ADR-072.
- API contract note for `worker_image_chatdev.deps_ready`.
- README capability matrix honesty; VERIFICATION; handoff; roadmap.

## Tests / verify

```bash
.venv/bin/python -m unittest discover -s tests
# Dockerfile string contracts for uv sync / deps label
# Optional (owner machine with network):
docker build -f deploy/fs-dev/Dockerfile.worker \
  --build-arg CHATDEV_ENABLE=1 -t fs-corporation-worker:local .
```
