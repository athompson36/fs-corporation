# Remote container whole-branch fix report

Date: 2026-09-08

- Added a remote-specific gateway allowlist limited to `gateway_check`, `execute_mock`, and
  `store_artifact`; remote `invoke_model` is denied before request handling.
- Failed remote completion now releases non-cancelled queue leases back to `queued`, clearing
  lease ownership and expiry so local or isolated dispatch can retry.
- A successful gateway operation returns its reply if the claim is lost before post-operation
  renewal, avoiding an error after committed side effects.
- The agent reports `runtime=remote_container` only when Docker actually started; missing Docker,
  image readiness, and pre-start setup failures remain `remote_agent`.
- Focused verification: `.venv/bin/python -m unittest tests.test_remote_container_agent
  tests.test_remote_worker_jobs` — 33 passed.
- Full-suite verification: `.venv/bin/python -m unittest discover -s tests` — 455 passed.
- Existing untracked `local repos/service-department/` content was preserved and excluded.

## Finance UX whole-branch final fixes

Date: 2026-09-08

- Replaced the Finance action-row sub-navigation with the companion's segmented tab
  pattern, including tab roles, selected state, and active styling.
- Removed the unused `scopes` prop and passed token presence explicitly.
- Finance loading now skips without a token and ignores resolved or rejected requests
  after the panel effect is cleaned up.
- Updated the companion source assertion and `docs/18-handoff.md` with actual evidence.
- Full-suite verification: `.venv/bin/python -m unittest discover -s tests` — 474 passed.
- Companion verification: `cd companion && npm run build` — OK; TypeScript and Vite
  production build completed with 35 modules transformed.
- Existing untracked `local repos/service-department/` content was preserved and excluded.
