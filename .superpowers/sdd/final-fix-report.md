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
