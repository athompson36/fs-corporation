# Security and execution boundaries

## Concrete risks and controls

| Risk | Required control |
|---|---|
| Worker claims to be CEO | Authenticate identities outside requests/prompts; bind service credentials to roles |
| Model expands its own authority | Immutable policies; parent-scope intersection; privileged activation |
| Retrieved page injects instructions | Separate evidence from instructions; deterministic gateway checks |
| Agent-generated code steals credentials | Ephemeral sandbox without root keys, host mounts or Docker socket |
| Cross-project disclosure | Per-project workspaces, memory ACLs and model data policies |
| Replayed approval | Exact payload binding, policy version, expiry and consumed marker |
| Concurrent overspend | Atomic reservations and hierarchical budget checks |
| Unreviewed code reaches production | Branch protections, exact-head checks and separate deployment capability |
| Tampered source evidence | Retained provenance, hashes, verification and independent review |
| Retry duplicates an external effect | Durable idempotency records and remote-state reconciliation |

## Root owner and service identity

Owner identity originates from actual authentication. AI CEO and heads receive separately scoped service principals. Never accept a browser field such as `actor=human-ceo` as proof of authority. Keep owner recovery and service-key rotation independent of model output.

The reference core intentionally trusts its local caller. Anyone able to execute Python or edit its SQLite file can bypass its methods. Its tests prove logical invariants under the intended API; they do not prove adversarial isolation.

## Sandbox requirements before live agents

No privileged containers; no host Docker socket; no home-directory mounts; no root credentials; minimal filesystem mounts; time/CPU/memory/output limits; endpoint egress allowlists; separate project scratch; read-only source inputs where possible; explicit artifact export. Containers alone are not sufficient for hostile code in every deployment; choose stronger isolation according to the workload and threat model.

Separate model inference credentials from repository write credentials. Even authorized code execution must not gain access to the policy store. Block arbitrary model-specified URLs in credentialed clients; validate hosts, redirects and private-address access to prevent SSRF.

## Audit and secrets

Log decision inputs and reason codes, policy versions, artifact hashes, approved targets and external result IDs. Redact secrets and unnecessary private content. Restrict raw prompt/output logs and define retention. The starter's hash chain is tamper-evident only against edits that do not recompute the chain; externally anchored checkpoints are needed for stronger guarantees.

## Release criteria

Authenticated principals; scoped gateway; validated inputs; actual artifact evidence; current-head approval; sandbox boundary tests; budget reservation/reconciliation; revocation and pause behavior; backups and tested restore. A successful mock test is not a substitute for these integration checks.
