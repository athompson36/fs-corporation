# ChatDev integration plan

## Verified baseline

Repository: https://github.com/OpenBMB/ChatDev

Pin: `4fb2db0ea90375ce1059f44fe03ffbd191a7a169` (main branch reference inspected 2026-09-01). Version family: ChatDev 2.0 / DevAll. The legacy virtual software company is maintained separately on `chatdev1.0`. Do not silently move this pin when installing.

Inspection of the pinned `runtime/sdk.py` confirms `run_workflow(yaml_file, *, task_prompt, attachments=None, session_name=None, fn_module=None, variables=None, log_level=None)`. It returns `WorkflowRunResult` containing `final_message` and `meta_info`, including output directory and token usage. Source references are in [17-sources.md](17-sources.md).

The pinned graph configuration defines root `version`, `vars`, `graph`, with graph nodes, edges, start/end and memory. Documentation examples can drift from source. Validate generated workflows against the pinned checkout rather than copying an assumed schema. This archive intentionally does not contain a claimed runnable ChatDev YAML workflow.

## Relationship to this project

The starter is a companion control layer, not a fork of upstream source. Keep ChatDev as a pinned dependency or separate checkout during M2/M3. If later changes require an upstream fork, record them as a small patch set with tests and an upgrade strategy. Do not rebuild ChatDev's workflow engine without a demonstrated gap.

## Obtain upstream in your development environment

These commands are manual setup instructions, not commands run by this package:

```bash
git clone https://github.com/OpenBMB/ChatDev.git upstream/ChatDev
git -C upstream/ChatDev checkout --detach 4fb2db0ea90375ce1059f44fe03ffbd191a7a169
```

Use the pinned repository's own installation instructions and lockfile (`uv sync` for its Python environment). Its frontend is optional for worker integration. Do not install arbitrary latest dependencies into the control-service environment. Follow license/notice requirements for any redistribution.

## Adapter responsibilities

1. Accept an immutable WorkOrder with workflow digest, policy version, approved input artifact references, model assignments, limits and project workspace.
2. Compile approved organization tasks to validated upstream nodes/subgraphs.
3. Validate workflow/config with the pinned upstream parser before dispatch.
4. Start a dedicated restricted process/container with a unique session name and per-task directory.
5. Resolve permitted secrets through the gateway or scoped worker identity; never include root keys in YAML or prompts.
6. Map final output, artifacts, logs and usage to normalized records. A final message is not project acceptance.
7. Emit failure/timeout/cancel events and reconcile incomplete effects.

## Required first integration test

Use a minimal workflow and deterministic mock provider compatible with the pinned schema. Assert input/output, session isolation, usage metadata, cancellation and failure mapping. Verify a tool cannot reach unauthorized filesystem paths, endpoints or credentials. Only after that test passes enable one real text provider for one bounded task.

`company/adapters.py` supplies WorkOrder and a disabled ChatDevAdapter. It has no invocation path to the upstream SDK today. An SDK signature inspection is not end-to-end compatibility testing. Live ChatDev remains untested in this starter.

## Upgrades

Fetch a candidate commit separately; review schema/tool changes, run adapter contract tests, compare output behavior and costs, preserve the old pin, then update lock and migration notes. Never let a model edit the pin in order to bypass a failing validation check.
