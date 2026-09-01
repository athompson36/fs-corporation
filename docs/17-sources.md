# Source references and upstream inspection

Inspected 2026-09-01. These are upstream technical references, not evidence that the full company extension already exists.

- [OpenBMB/ChatDev repository](https://github.com/OpenBMB/ChatDev): project overview, ChatDev 2.0/legacy distinction, developer layout and license.
- [Pinned baseline commit](https://github.com/OpenBMB/ChatDev/commit/4fb2db0ea90375ce1059f44fe03ffbd191a7a169): commit resolved from main during starter creation.
- [Pinned SDK source](https://github.com/OpenBMB/ChatDev/blob/4fb2db0ea90375ce1059f44fe03ffbd191a7a169/runtime/sdk.py): verified run_workflow signature and WorkflowRunResult/WorkflowMetaInfo fields.
- [Pinned graph configuration](https://github.com/OpenBMB/ChatDev/blob/4fb2db0ea90375ce1059f44fe03ffbd191a7a169/entity/configs/graph.py): verified root fields, node/edge references and graph validation.
- [Workflow authoring guide](https://github.com/OpenBMB/ChatDev/blob/main/docs/user_guide/en/workflow_authoring.md): workflow/node/model configuration guidance; resolve the pinned version during integration because main is mutable.
- [Memory guide](https://github.com/OpenBMB/ChatDev/blob/main/docs/user_guide/en/modules/memory.md): memory stores and attachments; guides do not replace an authoritative company database.
- [Pinned license](https://github.com/OpenBMB/ChatDev/blob/4fb2db0ea90375ce1059f44fe03ffbd191a7a169/LICENSE): Apache License 2.0 for upstream ChatDev.

The exact upstream SDK and graph source were inspected through GitHub. An attempted `entity/configs/agent.py` path was not available; graph imports indicate agent configuration is under `entity/configs/node/agent.py`. Do not build an adapter against an assumed path or rely on outdated example filenames. The adapter is intentionally pending a full pinned-schema compatibility test.

The company governance, market response, growth systems and UX in this starter are original proposed extensions grounded in the user's requirements. No current market statistics, provider rankings or pricing claims are supplied.
