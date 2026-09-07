# ChatDev Adapter Slice 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Optional ChatDev pin inside `fs-corporation-worker` image via build-arg; default image stays mock-only; container dispatch does not leak control-plane ChatDev allow env.

**Architecture:** Conditional Dockerfile layers; Docker label for pin; status/inspect helper; reuse slice-2 `run_isolated_work` selection inside the container.

**Tech Stack:** `deploy/fs-dev/Dockerfile.worker`, `install.sh` build hook, `company/chatdev_runtime.py` / `worker.py`, unittest.

## Global Constraints

- Pin: `4fb2db0ea90375ce1059f44fe03ffbd191a7a169`
- No ChatDev in root `pyproject.toml`
- Default docker build must not require network clone
- Container stays `--network none`
- Do not commit unless user asks
- Version bump to `0.3.40` at end

---

### Task 1: Dockerfile opt-in + contract test

**Files:**
- Modify: `deploy/fs-dev/Dockerfile.worker`
- Create: `tests/test_worker_dockerfile_chatdev.py`

- [ ] **Step 1: Extend Dockerfile**

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

COPY pyproject.toml README.md /src/
COPY company /src/company
COPY fixtures /src/fixtures

RUN pip install --no-cache-dir /src

# Optional: embed pinned ChatDev (source + label). Full uv sync may be added when build network allows.
RUN if [ "$CHATDEV_ENABLE" = "1" ]; then \
      git clone --depth 1 https://github.com/OpenBMB/ChatDev.git /opt/chatdev \
      && cd /opt/chatdev && git fetch --depth 1 origin "$CHATDEV_REF" && git checkout "$CHATDEV_REF" \
      && test -f /opt/chatdev/runtime/sdk.py; \
    else \
      mkdir -p /opt/chatdev && echo "chatdev disabled" > /opt/chatdev/.disabled; \
    fi

ENV CHATDEV_HOME=/opt/chatdev
# Only meaningful when CHATDEV_ENABLE=1; chatdev_home_ready still requires runtime/sdk.py
LABEL org.fs_corporation.chatdev_enable="${CHATDEV_ENABLE}"
LABEL org.fs_corporation.chatdev_pin="${CHATDEV_REF}"

WORKDIR /work
ENTRYPOINT ["python", "-m", "company.worker"]
```

Fix: when `CHATDEV_ENABLE=0`, **do not** set `ENV CHATDEV_HOME=/opt/chatdev` if that would make `chatdev_home_ready` false anyway (missing sdk.py). Prefer:

```dockerfile
RUN if [ "$CHATDEV_ENABLE" = "1" ]; then ...; fi
# Conditionally set ENV only when enabled — use a small script or:
# ENV set in same RUN: echo export >> /etc/profile.d — simpler approach:
```

**Preferred ENV pattern:**

```dockerfile
RUN if [ "$CHATDEV_ENABLE" = "1" ]; then \
      ... clone ... \
      && echo "/opt/chatdev" > /etc/fs-corp-chatdev-home; \
    else \
      echo "" > /etc/fs-corp-chatdev-home; \
    fi
ENV CHATDEV_HOME=
# entrypoint wrapper — YAGNI: instead only set ENV when enabled:
```

Simplest correct approach:

```dockerfile
RUN if [ "$CHATDEV_ENABLE" = "1" ]; then \
      git clone ... /opt/chatdev && git -C /opt/chatdev checkout "$CHATDEV_REF" \
      && echo "CHATDEV_HOME=/opt/chatdev" >> /etc/environment; \
    fi
```

And in worker `main()` or chatdev_runtime, if `CHATDEV_HOME` empty but `/opt/chatdev/runtime/sdk.py` exists, treat as home. **Or** use Dockerfile:

```dockerfile
# Final stage sets ENV only when ARG is 1 — Docker supports:
ENV CHATDEV_HOME=${CHATDEV_ENABLE}
```
That is wrong. Use:

```dockerfile
RUN if [ "$CHATDEV_ENABLE" = "1" ]; then echo /opt/chatdev > /run/chatdev_home; else echo -n > /run/chatdev_home; fi
```

And teach `chatdev_home()` to read `/run/chatdev_home` if env unset — **YAGNI**. Cleanest:

**Two targets documented:** default Dockerfile without ENV; when `CHATDEV_ENABLE=1`, append:

```dockerfile
ENV CHATDEV_HOME=/opt/chatdev
```

Implement with a shell fragment in Dockerfile that writes a tiny `/docker-entrypoint.d` — actually the standard pattern is:

```dockerfile
FROM python:3.12-slim AS base
... install company ...

FROM base AS with-chatdev
ARG CHATDEV_REF=...
RUN git clone ... 
ENV CHATDEV_HOME=/opt/chatdev
LABEL org.fs_corporation.chatdev_enable="1"

FROM base AS final
ARG CHATDEV_ENABLE=0
# Can't easily switch stages on ARG in older docker — use single stage conditional RUN +:
COPY --from=... 
```

**Implement as single-stage conditional RUN +:**

```dockerfile
ENV CHATDEV_HOME=/opt/chatdev
```

only inside the `if` by writing `/usr/local/bin/worker-env.sh` sourced by entrypoint. Change ENTRYPOINT to:

```dockerfile
COPY deploy/fs-dev/worker-entrypoint.sh /usr/local/bin/worker-entrypoint.sh
ENTRYPOINT ["/usr/local/bin/worker-entrypoint.sh"]
```

`worker-entrypoint.sh`:
```bash
#!/bin/sh
if [ -f /opt/chatdev/runtime/sdk.py ]; then
  export CHATDEV_HOME=/opt/chatdev
fi
exec python -m company.worker "$@"
```

Default image: no `/opt/chatdev/runtime/sdk.py` → no export. Enabled build: clone creates sdk → export.

- [ ] **Step 2: Contract test**

```python
def test_dockerfile_has_chatdev_enable_arg():
    text = Path("deploy/fs-dev/Dockerfile.worker").read_text()
    self.assertIn("ARG CHATDEV_ENABLE", text)
    self.assertIn("4fb2db0ea90375ce1059f44fe03ffbd191a7a169", text)
    self.assertIn("worker-entrypoint.sh", text)  # if used
```

- [ ] **Step 3: RED then GREEN** after Dockerfile + entrypoint exist

---

### Task 2: install.sh + container env hygiene

**Files:**
- Modify: `deploy/fs-dev/install.sh` `build_worker_image`
- Modify: `company/worker.py` `ContainerWorkerRuntime.dispatch` — do not forward `CHATDEV_ALLOW_CONTROL_PLANE` from host; optional forward only `CHATDEV_HOME` if host set and image lacks embed
- Create/modify: `deploy/fs-dev/worker-entrypoint.sh`
- Test: assert docker cmd construction strips allow env (unit test with patched Popen recording cmd)

```python
# In dispatch, when building cmd, never add CHATDEV_ALLOW_CONTROL_PLANE from os.environ
# If os.environ.get("CHATDEV_HOME") and want host mount override — out of scope; image embed is enough
```

- [ ] GREEN `tests.test_workers` + new dockerfile/env tests

---

### Task 3: Status label probe + docs + 0.3.40

**Files:**
- `company/chatdev_runtime.py` or `company/worker_status.py` — inspect image labels via `docker image inspect` fail-closed
- Docs: 07, 23, 25, handoff, README, design status implemented
- Version `0.3.40`

```python
def worker_image_chatdev_summary() -> dict:
    # docker image inspect $FS_CORP_WORKER_IMAGE --format labels; return {enabled, pin} or unavailable
```

Wire into `GET /api/v1/chatdev/status` as `worker_image_chatdev: {…}`.

---

## Spec coverage

| Spec | Task |
|---|---|
| Default build mock-only | 1 |
| CHATDEV_ENABLE embeds pin | 1 |
| Slice 2 selection in container | 2 (reuse) |
| No allow env leak | 2 |
| Status/label | 3 |
| Docs / version | 3 |

## Note on ChatDev deps

Slice 3 places source at pin so `chatdev_home_ready` can become true after sdk.py exists. Full ChatDev `uv sync` inside Docker is **best-effort** when build network works; if clone-only, document that model invocation still needs deps + later egress slice. Acceptance is sdk.py present + label + selection path, not Anthropic from `network none`.
