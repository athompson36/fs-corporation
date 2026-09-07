# Design: ChatDev adapter slice 1 (opt-in pinned SDK)

Date: 2026-09-07. Status: implemented — plan at `docs/superpowers/plans/2026-09-07-chatdev-adapter-slice1.md`.

## Goal

Make `ChatDevAdapter` able to invoke the pinned ChatDev 2.0 `run_workflow` SDK when the owner opts in, while remaining fail-closed by default. Deliver the **required first integration test** from [docs/07-chatdev-integration.md](../../07-chatdev-integration.md): deterministic mock provider / fake SDK, normalized I/O, no privilege escalation from workflow text.

## Pin

- Upstream: https://github.com/OpenBMB/ChatDev
- Commit: `4fb2db0ea90375ce1059f44fe03ffbd191a7a169`
- Entry: `runtime/sdk.py` → `run_workflow(yaml_file, *, task_prompt, attachments=None, session_name=None, …)` → `WorkflowRunResult(final_message, meta_info)`

## Constraints

- Control-plane venv does **not** install ChatDev or its lockfile.
- No root/owner tokens, DB paths, or policy APIs in ChatDev process inputs.
- Final message is **never** project acceptance (`accepted: false`).
- Signal/workflow text is task data, not authority.
- Workers continue to use `MockChatDevAdapter` until a later slice wires the live adapter behind the gateway.

## Design

### Opt-in

| Env | Meaning |
|---|---|
| `CHATDEV_HOME` | Absolute path to a checkout at the pin (or compatible tree with `runtime/sdk.py`) |
| `CHATDEV_WORKFLOW` | Optional absolute path to workflow YAML; default: package fixture |

Without `CHATDEV_HOME`, if `runtime/sdk.py` is missing, or if `git rev-parse HEAD` does not match the pin, `ChatDevAdapter.run` raises `NotImplementedError` with a pointer to docs/07 (same fail-closed posture as today). Tests may set `CHATDEV_SKIP_PIN_CHECK=1` to bypass pin verification; status then includes `pin_check_skipped`.

### Adapter behavior

1. Validate `WorkOrder` (`task_id`, `workflow_digest`, non-negative int `max_cost_cents`).
2. Enforce tool allowlist: payload `tools` ⊆ `{none, mock_fs}` (same as mock adapter). **This allowlist does not sanitize upstream YAML** — workflow graph contents remain untrusted task data until a later slice validates graphs with the pinned parser before dispatch.
3. Resolve workflow YAML; compute content digest; require `order.workflow_digest` equals that digest (fail closed on mismatch).
4. Import `run_workflow` by adding `CHATDEV_HOME` to `sys.path` only for that call (or load via `importlib` from that root) — never as a permanent package dependency.
5. Call `run_workflow(yaml, task_prompt=…, session_name=f"company-{project}-{task}", …)`.
6. Normalize to:
   ```text
   {
     final_message: str | None,
     meta_info: { session_name, usage: {input_tokens, output_tokens, cost_cents}, output_dir, cancelled, failed },
     artifact_hash: null,
     accepted: false
   }
   ```
7. Cap reported `cost_cents` at `order.max_cost_cents` for the return record (overrun → mark `failed` / raise — prefer raise `PermissionError` so gateway can fail closed).

### Fixture

- `fixtures/chatdev/minimal_workflow.yaml` — minimal graph compatible with the pinned schema (validated against pin when `CHATDEV_HOME` is present; in CI only checksum/shape checks if pin absent).
- Digest of fixture bytes is the expected `workflow_digest` for default tests.

### Tests (`tests/test_chatdev_adapter.py`)

- Fail-closed without `CHATDEV_HOME`.
- Fake `run_workflow` returns a stand-in result → normalized mapping.
- Unapproved tool → `PermissionError`.
- Digest mismatch → `ValueError` / fail closed.
- Mock adapter unchanged; existing `tests/test_m2.py` still passes.

### Status (optional thin)

- `GET /api/v1/chatdev/status` (or field under workers/model status): `{configured, pin, home_set, pin_verified, workflow}` plus optional `pin_check_skipped` — no secrets.

### Production boundary

Slice 1 may invoke the live SDK from the control-plane process when the owner opts in (`CHATDEV_HOME`). **Production must not** — the next slice moves ChatDev execution behind the isolated worker/gateway (restricted process, no control-plane DB). Do not treat slice 1 as permission to run upstream workflows in the API service for real workloads.

## Non-goals (later slices)

- Live Anthropic/OpenAI inside CI
- Installing ChatDev into the worker Docker image
- Compiling company org graphs → YAML
- Full upstream graph schema validation in slice 1 (digest + tool allowlist only)
- Replacing `MockChatDevAdapter` in `company/worker.py` subprocess path
- TailscaleKit / dedicated worker host

## Acceptance

1. Default checkout: `ChatDevAdapter().run(order)` → `NotImplementedError`.
2. With patched SDK: run returns normalized dict, `accepted is False`.
3. Unapproved tool and digest mismatch fail closed.
4. Docs: `07-chatdev-integration.md`, handoff, capability matrix, API contract if status route added.
5. No ChatDev package added to `pyproject.toml`.

## Verify

```bash
.venv/bin/python -m unittest tests.test_chatdev_adapter tests.test_m2 -v
# optional local (owner checkout):
# CHATDEV_HOME=/path/to/ChatDev@4fb2db0 .venv/bin/python -m unittest …
```
