# Task 4 report — activation, grant departments, dispatch gates

## Status

Implemented on `feature/org-hierarchy-handoff`.

- Added persistent project department activation and dispatchability checks.
- Replaced the shared dispatch budget with required `department_budgets`.
- Dispatch now records `queued_for_head` only for an active occupied head seat;
  vacant seats produce `blocked_vacant_head`.
- Added optional department-scope validation and inherited restriction for delegated grants.
- Allowed CEO mobile admin principals to appoint/vacate heads, assign/release positions,
  and activate departments; unrelated actors remain denied.
- Added the authenticated, idempotent project-department activation route and updated
  every in-repository dispatch caller.
- Did not implement `assign_dispatch` or a head inbox (Task 5).

## TDD evidence

The new `tests.test_org_roster` cases first failed for the missing activation method,
missing `department_budgets` API, missing department-aware `_scope`, and strict CEO-only
roster methods. After implementation, the targeted modules passed:

```text
Ran 25 tests in 0.903s
OK
```

The complete Python suite passed before commit:

```text
Ran 236 tests in 7.941s
OK
```

IDE lint diagnostics and `git diff --check` passed.

## Concern

`python3 scripts/check_bundle.py` is blocked by a pre-existing untracked nested candidate:
`local repos/service-department/README.md` links to absent `./LICENSE`. Task 4 did not
modify that candidate. The full unit suite still passes.
