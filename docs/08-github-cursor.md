# GitHub forks and Cursor collaboration

## Project enrollment

The owner explicitly selects each upstream repository and the company-controlled fork/development repository. Store immutable GitHub repository IDs in addition to owner/name strings so renames do not alter authority. Confirm available access, fork policy, private-repository restrictions, license and branch protection. Some organizations prohibit private forks; use an approved development repository or branch strategy instead.

Configure each project independently: upstream, fork, protected branches, allowed branch prefixes, required checks, reviewers, data classification, artifact rules and permitted actions. A repository name mentioned in a document is not enrollment. The template uses OWNER/PROJECT placeholders because actual targets have not been supplied.

## GitHub App permissions

Prefer an installed GitHub App scoped to selected repositories. Begin with metadata/read access. Add only required repository permissions: contents write for approved branches, pull requests write for PR creation, checks/status read for validation. Manage repository settings, workflow files, secrets and organization administration separately; ordinary developers do not need these capabilities.

Mint short-lived installation credentials only inside the action gateway. Do not give workers raw root installation keys. Branch protection should independently enforce human/delegated review and required checks. Permission to push a branch does not grant permission to publish a package, edit Actions workflows, merge upstream or deploy.

## Task workspaces

One worktree or disposable checkout per task, based on an immutable starting commit. Use `company/<project>/<task>` branches. Record base SHA, output SHA, upstream SHA and PR head SHA. Human Cursor work remains on its own branch. Never silently reset or overwrite a human workspace.

Fetch and reconcile upstream changes before review. If conflicts occur, create a conflict-resolution task and rerun checks after resolution. Review approvals apply to the reviewed head SHA; subsequent commits invalidate them. A model may explain a conflict but cannot bypass required checks to finish a task.

## Effect lifecycle

`Company.apply_github_effect` is the local entry point:

1. Authorize: enrolled repo IDs only, protected-branch and prefix checks, stale-head, workflow-file scope, merge/deploy as separate capabilities.
2. Record an idempotent `github_effects` row keyed by repository ID, task ID and operation (`status=recorded`).
3. Attempt `GitHubAdapter.execute`. Until a GitHub App is installed, this raises `NotImplementedError`; the row becomes `live_unavailable` with `remote_id` null. A retry inspects the existing row and does not insert a duplicate.

Prepare changes locally → verify diff and expected target → run tests in a restricted environment → independent review → gateway scope/approval check → `apply_github_effect` → live push/PR only after App credentials exist → record external IDs and commit hashes → merge only under a distinct merge capability.

Do not assume a `live_unavailable` row means a remote write happened. Do not invent a PR number.

## Webhooks

Verify GitHub webhook signatures over raw request bytes using the configured secret. Enforce replay protection, bounded body sizes and event allowlists. Persist delivery IDs and normalize events before queueing. Issue bodies, comments and repository content remain untrusted task data. They cannot grant privileges or supply new credentials.

## Cursor's role

Cursor opens the same repositories and branches for human review and editing. An agent performs Git operations and builds in its own workspace; no desktop automation is required. Keep each enrolled project's local instructions separate from corporate policy. Project instructions can constrain implementation but cannot enlarge granted external access.

## Pilot acceptance

Use a disposable repository with no production secrets. Have the company create a small file change, run checks and open a PR. Demonstrate denial of a protected-branch push, unauthorized repository access, stale-head approval, workflow-file change without scope and cross-project secret access. Test retry after a simulated ambiguous network response.

Live GitHub is not connected by this package. `apply_github_effect` persists `live_unavailable`; the adapter still raises NotImplementedError.
