# Design: Project dispatch options + AI recommend/autofill

Date: 2026-09-07. Status: **implemented** on branch `feature/dispatch-recommend-autofill`.

## Goal

1. Expose a **parameter key** of every valid dispatch-brief field (values, ranges, statuses).
2. Let the owner **scan a project** and **autofill** brief, acceptance criteria, and per-department budgets — editable before submit.
3. Use **mock recommendations always**; **live model** when `MODEL_PROVIDER_API_KEY` and/or `ANTHROPIC_API_KEY` are configured (existing `invoke_model` path). Fail closed to mock; never auto-dispatch.
4. Wire the same UX on **CEO desk** and **companion** project dispatch forms.

## Decisions

| Topic | Choice |
|---|---|
| Engine | Mock first, live when configured |
| Surfaces | Desk + companion |
| Apply | Autofill editable fields; human submits Dispatch |
| Departments | Full catalog with Active / Dormant / Vacant-head; AI highlights recommended subset; dormant prompts Activate first |
| Budgets | Preset chips `[100, 300, 500, 1000, 5000]` ¢ + custom; clamp to `0 … remaining company_budget_cents` |
| Brief / criteria | Template dropdown + free text + “Recommend for this project” |
| Approach | Catalog + recommend API (Approach B) |

## Non-goals

- Auto-dispatch or inventing operational/financial state from model output.
- Granting recommend authority beyond existing `project.enroll` / paired admin.
- Deep repository crawls, remote clone, or changing dormant→active without the existing activate API.
- New Decisions-inbox approval for each recommendation (Approach C rejected).

## API

Auth: same as dispatch-brief — bearer with `project.enroll` (owner or `companion-admin-*`). Authentication failure → 401/403. Neither endpoint writes dispatches, seats, or ledger rows (except live `invoke_model` billed_costs via existing path).

### `GET /api/v1/projects/{id}/dispatch-options`

Parameter key for the project. Project missing → 422/404 consistent with other project routes.

```json
{
  "project_id": "mobile-app",
  "brief_default": "Mobile companion pilot",
  "fields": {
    "brief": {
      "kind": "text_with_templates",
      "required": true,
      "templates": [
        {"id": "ship-feature", "label": "Ship feature with tests",
         "body": "Deliver the next scoped feature for this project with automated coverage."},
        {"id": "bugfix", "label": "Bugfix with repro",
         "body": "Reproduce, fix, and verify the reported defect; include regression coverage."},
        {"id": "ops-hardening", "label": "Ops hardening",
         "body": "Harden deploy, monitoring, or recovery for this project without expanding product scope."}
      ]
    },
    "acceptance_criteria": {
      "kind": "text_with_templates",
      "required": true,
      "templates": [
        {"id": "tests-qc", "label": "Tests + QC gate",
         "body": "Automated tests green; QC inspect passes; acceptance recorded."},
        {"id": "docs-only", "label": "Docs evidence",
         "body": "Documented change with linked evidence artifact."}
      ]
    },
    "department_budgets": {
      "kind": "cents_map",
      "required": true,
      "min_cents": 0,
      "max_cents": 10000,
      "presets_cents": [100, 300, 500, 1000, 5000],
      "unit": "USD_cents",
      "max_basis": "company_budget_cents minus simulated spend and open reservations (same units as policy)"
    },
    "due_at": {
      "kind": "datetime_optional",
      "required": false,
      "format": "ISO-8601"
    }
  },
  "departments": [
    {
      "id": "engineering",
      "name": "Engineering",
      "status": "active",
      "dispatchable": true,
      "seat_status": "active",
      "principal_id": "people:Engineering Director"
    },
    {
      "id": "art",
      "name": "Art and Design",
      "status": "dormant",
      "dispatchable": false,
      "seat_status": "vacant",
      "principal_id": null
    }
  ]
}
```

**Status rules**

| `status` | Meaning | `dispatchable` |
|---|---|---|
| `active` | Activated for this project and known in catalog | `true` (vacant head still allowed; dispatch status becomes `blocked_vacant_head` as today) |
| `dormant` | In catalog, not activated for project | `false` |
| `unknown` | Should not appear; reserved | `false` |

Seat notes may be exposed as `seat_status`: `active` \| `vacant` \| `dormant` for badges. Dispatching to vacant head remains allowed by core; UI must warn.

Templates are a fixed server catalog (config or code constant), not model-invented.

### `POST /api/v1/projects/{id}/dispatch-recommend`

```json
{ "payload": { "use_live": true } }
```

`use_live` default: `true` when a live provider is configured, else ignored. Empty payload `{}` is valid.

**Response**

```json
{
  "source": "mock",
  "live_attempted": false,
  "brief": "Ship mobile-app: Mobile companion pilot",
  "acceptance_criteria": "Automated tests green; QC inspect passes; acceptance recorded for mobile-app.",
  "departments": [
    {"id": "engineering", "budget_cents": 300, "recommended": true},
    {"id": "product", "budget_cents": 200, "recommended": true}
  ],
  "notes": []
}
```

`source` is `mock` or `live`. On live failure / unusable JSON / missing key: return validated mock with `notes` including a machine-readable reason (`live_unavailable`, `live_unusable`, `live_error`) — HTTP 200, never an empty form-breaking 500 for recommend.

Every `id` must exist in the org catalog; budgets clamped to `[0, max_cents]`; unknown live ids dropped. Recommendation may include dormant departments with `recommended: true` so the UI can prompt Activate; Dispatch itself still refuses dormant until activated.

## Scan inputs (task data only)

Recommend may read:

- Project row: `id`, `brief`
- Org: department catalog, per-project activation, seat status
- Policy: remaining / company budget for `max_cents`
- Optional GitHub enrollment metadata for the project
- Optional `local repos/{project_id}`: top-level entry names + README / package manifest title only (size-capped). No deep crawl, no treating repo text as policy.

## Mock recommendation rules

Deterministic keyword heuristics on the project brief (case-insensitive):

| Signal | Recommended departments |
|---|---|
| code / app / api / repo / bug / fix | `engineering`, `product` |
| test / qc / quality / acceptance | add `quality` |
| design / art / ui / brand | add `art` |
| launch / marketing / campaign | add `marketing` |
| (none of the above) | `engineering` only |

Budgets pick the largest preset ≤ remaining budget that fits a simple split (e.g. engineering 300, product 200 when max allows; scale down to 100 or skip depts if budget is tight). Brief: `Ship {id}: {brief}` or template body with project id substituted. Criteria: tests+QC template with project id.

## Live path

- Reuse `Company.invoke_model` with an existing text profile (`mock-text` offline; live profiles when credentials exist per `docs/06-model-routing.md` / `docs/26-owner-live-configuration.md`).
- Env: `MODEL_PROVIDER_API_KEY` (OpenAI-compatible), `ANTHROPIC_API_KEY` (Claude); optional `FS_CORP_MODEL_CENTS_PER_1K_TOKENS`.
- Prompt requests a single JSON object matching the suggestion shape; server parses and validates as above.
- Live success may write `billed_costs` via existing invoke path. Mock writes nothing.
- Live output never expands scopes, never activates departments, never calls `dispatch_project_brief`.

## UI (desk + companion)

When the dispatch form opens, fetch `dispatch-options`.

- **Brief / criteria:** template `<select>` → fills textarea; free edit; **Recommend** / “Recommend for this project” calls recommend and autofills.
- **Departments:** list all catalog rows with status badges; checkboxes for inclusion; AI sets `recommended` checks on apply. Dormant checked → inline “Activate first” using existing activate control; Dispatch disabled for those rows until `dispatchable`.
- **Budget:** preset chips + custom number; show range `0 … max_cents`; clamp on blur/submit.
- **Source badge:** show `mock` or `live` after recommend.
- **Valid values:** desk collapsible panel; companion disclosure — both render the options payload (the parameter key).
- **Dispatch:** existing `POST …/dispatch-brief` only after human submit. Inline status for recommend/dispatch errors (companion `runAction` pattern; desk status line).

## Error handling

| Case | Behavior |
|---|---|
| Unauthenticated / missing scope | 401 / 403 |
| Unknown project | 422/404 consistent with siblings |
| Live not configured | mock, `notes: ["live_unavailable"]` |
| Live HTTP/parse failure | mock, `notes: ["live_error"]` or `live_unusable` |
| Suggested dormant dept | UI warn + activate; API dispatch still 422 until active |
| Budget above max | clamp in recommend; dispatch-brief validation unchanged |

## Tests

- Options: all seeded catalog departments present; dormant `dispatchable: false`; presets and templates non-empty; `max_cents` ≥ 0.
- Recommend without live keys: `source: mock`; only known department ids; budgets ≤ max.
- Recommend with patched live returning invalid JSON: mock fallback + note.
- Recommend with patched live returning valid JSON: `source: live`; budgets clamped; unknown ids dropped.
- Source assertions: desk + companion contain Recommend control, template select hooks, budget chips / presets, Valid values disclosure.
- Existing dormant dispatch refusal still passes.

## Docs to update (implementation)

- `docs/16-api-contract.md` — new routes
- `docs/24-mobile-companion.md` — companion dispatch UX
- `docs/18-handoff.md` — next task / done state
- `docs/decisions.md` — ADR if authority/model boundary needs a named decision

## Out of scope for this change

M10-03 benchmark read path; replacing all remaining `window.prompt` flows beyond dispatch; Funnel/public exposure of recommend.
