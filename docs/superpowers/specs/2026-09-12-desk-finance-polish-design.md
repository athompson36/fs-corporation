# Design: Desk Finance polish (pause gate + openRoom)

Date: 2026-09-12. Status: **approved for implementation** (target **v0.3.80**).

## Goal

Close two deferred desk nits from Desk Finance surface (0.3.78): upfront
`company.pause` gating for Finance mutations (not only 403-reactive), and restore
HQ openRoom simulated-spend display without reintroducing the Money-section JSON
dump.

## Owner locks

| Topic | Choice |
|---|---|
| Track | Desk polish (both nits) |
| openRoom | Soften contract to `#budget`-scoped ban; restore simulated + reserved line |
| Pause gate | `GET /api/v1/session` → enable when scopes include `company.pause` |
| Approach | In-place `company/service.py` DESK_HTML JS |
| Version | **0.3.80** |

## Non-goals

- New finance APIs or Alembic.
- Companion FinancePanel / URL changes (beyond version lockstep).
- Desk ModeSwitch / ManageClusters.
- Broader desk session-cache refactor beyond Finance pause detection.

## Fix 1 — Upfront pause gate

1. With a bearer token present, during desk `load()` (or immediately before/after
   `loadFinance()`), `GET /api/v1/session`.
2. Parse `scopes` array; call `setFinanceMutateEnabled(scopes.includes('company.pause'))`.
3. `#finance-scope-notice` remains the muted notice when disabled (existing copy:
   “Mutations require company.pause.”).
4. Remove the unconditional `setFinanceMutateEnabled(true)` at script init (or
   replace with disabled-until-session-known, then apply session result).
5. Keep `postFinanceCommand` 403 → `setFinanceMutateEnabled(false)` as fail-closed
   backup.
6. On session fetch failure: leave mutate disabled (or keep last known state) and
   do not invent scopes — prefer fail closed: `setFinanceMutateEnabled(false)` and
   optional status text only if already showing finance errors.

## Fix 2 — openRoom spend line + scoped contract

Restore in `openRoom` (approx.):

```javascript
'Simulated spend: ' + detail.costs.simulated_spend_cents + '¢ reserved '
  + detail.costs.reserved_cents + '¢',
```

Update `tests/test_desk_finance_surface.py` `test_no_budget_json_dump`:

- Extract the `#budget` section from `DESK_HTML` (substring from
  `id="budget"` through the matching `</section>` for that section).
- Assert that section does **not** contain `budget-json` or `simulated_spend_cents`.
- Do **not** ban `simulated_spend_cents` on the full `DESK_HTML` string.

Keep other desk Finance contracts (Finance rail label, markup ids, helpers,
version) intact modulo version bump.

## Delivery

| Path | Role |
|---|---|
| `company/service.py` | Session-based pause gate; openRoom restore |
| `tests/test_desk_finance_surface.py` | Scoped dump ban; new markers for session/pause; version **0.3.80** |
| `tests/test_companion_finance_url_polish.py` | Soften exact `0.3.79` pin |
| Docs | ADR-062, UX/roadmap/handoff; mark this spec implemented when shipped |
| Versions | `company/__init__.py` + `companion/package.json` → **0.3.80** |

Branch: `feature/desk-finance-polish`.

## Verification

- Source contracts: `#budget` has no dump markers; `DESK_HTML` contains
  `/api/v1/session`, `company.pause`, and openRoom `simulated_spend_cents`.
- Full `unittest discover`; companion build at 0.3.80.
- Manual: owner token → Finance forms enabled; read-only / missing pause →
  disabled + notice; openRoom shows simulated + reserved.

## Follow-ups (deferred)

- Companion one-frame tab URL flash.
- Broader desk use of `/api/v1/session` for other mutate UIs.
