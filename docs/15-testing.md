# Testing and definition of done

## Starter commands

```bash
python3 -m unittest discover -s tests -v
python3 scripts/check_bundle.py
python3 -m company demo --db .local/verification.db
python3 -m company status --db .local/verification.db
```

The unit suite covers unknown scopes, self-escalation, stale policy proposals, pause/resume, grant expiry, strict policy fields, cost validation, cumulative spend, idempotency collisions, approval payload/version/expiry, project evidence, duplicate completion, contractor authority, signal freshness/deduplication, audit tampering, disabled live adapters, persistence, concurrent overspend prevention, model data/capability routing, loopback API authentication, parent/child delegation, policy rollback, GitHub denial checks, GitHub effect lifecycle (`apply_github_effect` fail-closed and idempotent), impact briefs, approved-feed poll lifecycle (`poll_market_feed` fail-closed), headquarters replay, memory ACLs, period budgets, hardware skill gaps, learning assignments, independent skill certification, Quality Control inspection before acceptance, Human Resources training authority, employee hire attributes, overdue training gates, documented training files, performance trends, container file-gateway dispatch, and fail-closed Web Push subscription/delivery.

API tests require `pip install -e .`. The demo CLI does not.

## Current evidence limitations

These are deterministic local tests with trusted method callers. They do not exercise authentication, upstream ChatDev execution, provider APIs, GitHub, a browser, real source verification, actual billed costs or a hardened sandbox. Synthetic artifact hashes demonstrate binding logic, not software correctness.

## Future test layers

- Policy: scope intersections, deny precedence, cycles, expired parent, revoked ancestor, delegated approval and policy race conditions.
- Financial: atomic reservation across workers, reconciliation after crash, provider errors that bill, currency/period rules and cap lowering.
- Workflow: adapter schema, malformed outputs, bounded retries, cancellation and artifact mismatch.
- Repository: allowed ref validation, branch protection, exact-head review, signed webhooks, ambiguous write recovery and merge conflicts.
- Intelligence: canonical deduplication, corrections, timestamp anomalies, conflicting sources, prompt injection and access restrictions.
- Hardware skills: unknown platforms, software projects remaining ungated, learner cannot self-certify, page text cannot amend policy, dispatch after certification.
- UI: approval diff clarity, keyboard flow, reduced motion, room-state replay and no fake activity.
- Isolation: filesystem/egress boundaries, secret exposure, project ACLs and unavailable credentials.

## Definition of done

Requirement mapped to an observable acceptance criterion; implementation complete; targeted positive/negative tests pass; effects and failure behavior are visible; documentation and capability status updated; secrets absent; migrations/recovery considered; user-facing outcome demonstrated. External checks not performed must be stated, not marked passed.

CI runs the offline suite and bundle checks on Python 3.12 and 3.13 when pushed to a configured GitHub repository. The packaged local verification is on Python 3.12; the remote CI matrix has not been executed as part of creating this ZIP.

## Consultant checks (0.2.0)

Five additional tests verify static findings without code execution or source edits, active-department routing gaps, deduplicated evidence-bearing proposals, CEO-only decisions, no self-approval, no automatic task/policy effects and persisted rejection. Scanner silence never counts as full audit success.
