# Design: P3 follow-on — benchmark routing + work-order replay ledger

Date: 2026-09-08. Status: **approved** (owner: A then B sequencing; choose_model **best quality**; replay ledger **append-only**).

## Goal

1. Let `choose_model` prefer the highest recorded **quality** benchmark among already-eligible profiles for a role; if no benchmarks apply, keep today’s ordered selection.
2. Persist an append-only **work-order replay ledger** so identical digest replays return the prior outcome without a second effect.

Then proceed to a separate **P4 Scale and presence** design (second host · TailscaleKit · furnished HQ art).

## Non-goals

- Auto-promoting model assignments in Settings.
- Inventing benchmark scores.
- Re-executing ChatDev/live workflows from a work order.
- P4 hardware / TailscaleKit / art in this slice.

## Slice A — Benchmark-aware choose_model

**Behavior**

1. Build the ordered eligible candidate list exactly as today (task → position → department → company; capability + data filters).
2. If `benchmarks` (list of `{role, profile_id, quality, …}`) is provided and `role` is set:
   - Consider only eligible candidates that have at least one row for that `role`.
   - Prefer the candidate with the **maximum** `quality` (latest row per profile if multiple).
   - Tie-break: earlier position in the original eligible order.
3. If no eligible candidate has a benchmark for that role → return the first eligible as today.
4. Return payload includes optional `benchmark_source`: `quality_max` | `order` (and `benchmark_quality` when used).

**Wire-in:** Call sites that have a Company may pass `company.list_benchmark_results(role=…)` and a role string (e.g. position or explicit). Pure `choose_model` stays importable without DB.

## Slice B — Work-order replay ledger

**Table `work_order_replays`** (Alembic `0026`):

| Column | Notes |
|---|---|
| id | PK |
| work_order_id | FK-ish to work_orders.id |
| attempt | int starting at 1 |
| workflow_digest | must match work order |
| status | `authorized` \| `replayed` \| `completed` |
| outcome_json | frozen result body for replay |
| created_at | ISO |
| created_by | actor |

**API / core**

- On `ConsultantDesk.to_work_order` (and any future authorize path): insert attempt 1 `authorized` with empty or handoff outcome stub.
- `Company.replay_work_order(actor, work_order_id, workflow_digest)`:
  - If latest row for that id+digest has `outcome_json` and status in `{authorized, replayed, completed}` with a stored outcome → return it with `replay=True`, append `replayed` row referencing same outcome.
  - If digest mismatches → fail closed.
  - First completion: `complete_work_order_replay(actor, work_order_id, outcome)` stores outcome and status `completed`.
- `GET /api/v1/work-orders/{id}/replays` — `company.read` list attempts.
- Never dispatch ChatDev from this API.

## Testing

- Routing: with two eligible profiles, higher quality wins; with no benches, order wins; restricted data still blocks.
- Replay: authorize → complete → replay returns same outcome; digest mismatch fails; companion/docs optional thin note.

## Docs

- `docs/06-model-routing.md`, api-contract, data-model, handoff, ADR-039.
