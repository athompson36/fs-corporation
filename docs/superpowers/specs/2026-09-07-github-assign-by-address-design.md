# Design: Phone GitHub assign by address (auto `-corp` write repo)

Date: 2026-09-07. Status: **implemented** (v0.3.49).

## Goal

From the CEO companion on a phone, paste a GitHub **upstream** address (`https://github.com/owner/repo` or `owner/repo`). The control plane resolves it, ensures a same-owner write repo named `{repo}-corp`, enrolls both numeric ids on a company project, and treats upstream as the **only pull source**.

## Decisions (locked)

| Topic | Choice |
|---|---|
| Address form | URL or `owner/repo` (option 1) |
| Upstream vs fork | Upstream = pasted (pull only); write target = `{repo}-corp` |
| Fork location | Same owner, name suffix `-corp` |
| True GitHub fork | Not required when same-owner (GitHub disallows forking your own repo). Create sibling repo `{repo}-corp` if missing; reuse if present |
| API | New assign endpoint (approach A); companion form, not `window.prompt` |
| Missing company project | Auto-enroll project id from repo name (slug) with brief from the address |

## API

`POST /api/v1/projects/{project_id}/github-assign`

- Scopes: `project.enroll`; actor must pass CEO check (same as `enroll_github`)
- Body payload: `{ "upstream": "<url or owner/repo>" }` plus optional overrides later
- Behavior:
  1. Fail closed if GitHub App not configured
  2. Parse address → `owner`, `name`
  3. Resolve upstream via `GET /repos/{owner}/{name}` → id
  4. Target `owner/{name}-corp`; `GET` if exists else `POST` create under that owner
  5. If project missing, `enroll_project` with id=`project_id` (caller path id) and brief derived from upstream full_name
  6. `enroll_github(upstream_id, corp_id, protected=["main"], branch_prefix="company/", permitted=["push","open_pr","prepare_pr"])`
- Returns: `{ upstream: {full_name, id}, write_repo: {full_name, id}, project_id, created_write_repo: bool }`

Idempotent: re-assign same upstream + existing `-corp` replaces enrollment row (`INSERT OR REPLACE`).

## Companion UI

Projects tab (when `canEnroll`):

- Fields: Upstream address (required); Project id (default = repo slug after parse, editable)
- Submit “Assign GitHub”
- Show result names/ids; errors from API detail text
- Keep existing enroll/dispatch; this is the GitHub attach path

## Tests

- Parser unit tests (URL, `.git`, `owner/repo`, reject garbage)
- Assign with mocked GitHub: creates `-corp`, enrolls both ids
- Existing `-corp` reused; no second create
- Unconfigured App → NotImplementedError / 501-style mapping already used
- Companion client method + no prompt for this flow

## Out of scope

- Cross-owner true forks; merge permission auto-grant; multi-remote; desk UI duplicate (desk can call same API later)
