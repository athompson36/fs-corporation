# Design: ChatDev adapter slice 3 (optional ChatDev in worker image)

Date: 2026-09-07. Status: **implemented** (v0.3.40).

## Goal

Optionally bake the pinned ChatDev checkout into `fs-corporation-worker:local` so **container** runtime can run the same live path as subprocess slice 2, without putting ChatDev in the control-plane image or `pyproject.toml`. Default builds remain mock-only.

Builds on [2026-09-07-chatdev-adapter-slice2-design.md](2026-09-07-chatdev-adapter-slice2-design.md).

## Pin (unchanged)

`4fb2db0ea90375ce1059f44fe03ffbd191a7a169`

## Design (approach A)

### Dockerfile (optional stage)

Extend `deploy/fs-dev/Dockerfile.worker`:

1. **Default build** (today): company package only; no ChatDev; image behaves as mock worker.
2. **Opt-in build** via build-arg:
   - `CHATDEV_REF=4fb2db0ea90375ce1059f44fe03ffbd191a7a169` (default the pin)
   - `CHATDEV_ENABLE=1` — when set, clone/copy ChatDev at that commit into `/opt/chatdev` inside the image and set `ENV CHATDEV_HOME=/opt/chatdev`
3. Prefer multi-stage or conditional `RUN` so default CI/fs-dev builds stay thin unless `FS_CORP_WORKER_CHATDEV=1` is set at build time.
4. Do **not** `pip install` ChatDev into the control-plane venv; worker image may install ChatDev’s own deps into the image venv **only when** `CHATDEV_ENABLE=1` (document that this increases image size and build time).
5. If ChatDev’s full dependency install is too heavy for slim, slice 3 may ship **source + pin label only** and keep live execution behind `CHATDEV_HOME` readiness failing closed until deps are present — but the build must still place `runtime/sdk.py` at the pin path so `chatdev_home_ready` can succeed once deps are installed. Prefer documenting a two-step: (a) clone pin into `/opt/chatdev`, (b) `uv sync`/`pip` from ChatDev lockfile when build network is available.

### Runtime wiring

1. Container entrypoint already runs `python -m company.worker` with envelope on scratch — reuse `run_isolated_work` / `_want_live_chatdev` from slice 2.
2. `ContainerWorkerRuntime.dispatch`: when launching `docker run`, if host has `CHATDEV_HOME` **or** image embeds ChatDev, pass through:
   - `-e CHATDEV_HOME=...` only when needed (embedded image already has ENV)
   - Do **not** pass `CHATDEV_ALLOW_CONTROL_PLANE` from the API host env into the container by default; worker path uses `allow_control_plane=True` in-process inside the worker module (already slice 2).
3. `network_mode: none` unchanged — live ChatDev **without** network cannot call external model APIs. Document: container live path is for **offline/fake provider or pre-bundled mock LLM** until a later slice adds controlled egress. Slice 3 acceptance is “image has pin + adapter selection works with patched/fake SDK inside container tests,” not full Anthropic from inside `network none`.

### Build / deploy knobs

| Knob | Where | Effect |
|---|---|---|
| `FS_CORP_WORKER_CHATDEV=1` | `install.sh` / env when building | Passes `--build-arg CHATDEV_ENABLE=1` |
| `CHATDEV_REF` | build-arg | Override pin (must match lock for production) |
| Default | unset | Current mock-only image |

### Status

Extend `GET /api/v1/chatdev/status` and/or workers status:

```text
worker_image_chatdev: bool | null  # null if unknown; true if image inspect finds CHATDEV_HOME or label
```

Optional Docker label `org.fs_corporation.chatdev_pin=<commit>` set at build time for inspect without running a container.

### Tests

1. Unit: Dockerfile / build-arg documentation smoke — or a small parser test that `CHATDEV_ENABLE` build-arg appears in Dockerfile (string/contract test).
2. `tests/test_worker_chatdev.py` (or new): when `FS_CORP_WORKER_IMAGE` points at a fake, skip; with patched container entry using same `_want_live_chatdev` logic — already covered for subprocess; add one test that container dispatch passes no `CHATDEV_ALLOW_CONTROL_PLANE` from parent env.
3. Manual/optional: build with `CHATDEV_ENABLE=1` on a machine with network; `docker run ... printenv CHATDEV_HOME`.

### Non-goals

- Dedicated worker host / TailscaleKit
- Opening Docker network for billed model calls
- Control-plane ChatDev install
- Always-on ChatDev in every fs-dev install (opt-in build only)

## Acceptance

1. Default `docker build -f deploy/fs-dev/Dockerfile.worker` unchanged in behavior (no ChatDev; mock path).
2. With `CHATDEV_ENABLE=1`, image contains `/opt/chatdev/runtime/sdk.py` and `CHATDEV_HOME` ENV (or documented equivalent).
3. Slice 2 worker selection still applies inside the container process.
4. Docs: `23-isolated-workers.md`, `07`, `25`, handoff; version bump.
5. No ChatDev dependency added to root `pyproject.toml`.

## Verify

```bash
docker build -f deploy/fs-dev/Dockerfile.worker -t fs-corporation-worker:local .
# optional:
docker build -f deploy/fs-dev/Dockerfile.worker \
  --build-arg CHATDEV_ENABLE=1 \
  -t fs-corporation-worker:chatdev .
.venv/bin/python -m unittest tests.test_worker_chatdev tests.test_workers -v
```
