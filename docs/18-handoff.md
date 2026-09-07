# Current handoff

Date: 2026-09-07. Version: **0.3.51**. State: **cross-department request API on feature branch**.

## Task 7 delivered

- `cross_department_requests` is a separate coordination table added by Alembic
  `0015_cross_dept_work_orders`; immutable execution `work_orders` were not overloaded.
- `Company.create_cross_dept_request` requires an enrolled project, known distinct
  departments, active project delivery department, explicit ownership/schedule/acceptance/
  escalation/budget fields, and a currently seated requesting head unless CEO/admin.
- The current seated delivering head sees requests through the actor-scoped list and may
  accept; a vacancy or wrong department fails closed. CEO/admin may list and accept.
- Create and accept persist `cross_department.request_created` and
  `cross_department.request_accepted` in the same transaction as state changes.
- API-only routes provide POST create, GET actor delivery list, and POST accept under
  `organization.read` / `organization.write`. No UI shipped; version remains 0.3.51.
- Changed behavior files: `company/{schema,migrate,core,service}.py`, Alembic `0015`,
  `tests/test_cross_department_requests.py`, README, and organization/data/roadmap/decision
  documentation.

## Verification

- TDD red: the new focused suite failed with missing command methods and HTTP 404 routes.
- `.venv/bin/python -m unittest tests.test_cross_department_requests`: **8 passed**.
- `.venv/bin/python -m unittest discover -s tests`: **257 passed**.
- `PYTHONPATH=. .venv/bin/alembic heads`: `0015_cross_dept_work_orders (head)`.
- IDE diagnostics: no errors in edited Python/test/migration files.
- `scripts/check_bundle.py` stops only at the pre-existing nested
  `local repos/service-department/README.md` link to missing `./LICENSE`.

## Next implementation

Implement the M10-03 benchmark read path and deterministic role fixtures, or take the next
M10-04 UI item. A future UI may surface cross-department requests, but must project only
persisted request and seat state.
