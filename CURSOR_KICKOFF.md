# Paste this into Cursor Agent

You are continuing the FS-Tech AI Company project for Andrew Thompson. Read AGENTS.md, docs/00-project-context.md, docs/18-handoff.md, docs/02-architecture.md and docs/14-roadmap.md before changing code. Review the relevant scoped rules in .cursor/rules.

Goal: extend ChatDev 2.0 into a persistent AI corporation with CEO-set evolving rules; delegable department heads; mixed AI providers/models per department, position and task; controlled work on explicitly enrolled GitHub forks; evidence-based response to real markets and events; and a growing interactive headquarters with facilities and contractor workflows.

Begin by running the offline demo and tests. Report the actual starting state. The current core is a tested local reference, not a production service. Preserve useful code and improve it incrementally. Do not replace working pieces with placeholder dashboards or claim mock outputs are live agent results.

Implement the next unblocked item in docs/14-roadmap.md. ADR-010 already records FastAPI + Alembic + SQLite-first on loopback. Do not skip isolated workers to connect a live model. Bind authority to authenticated identities, never caller-supplied role strings.

Work autonomously on reversible local implementation and meaningful tests. Keep external integrations disabled until their required configuration and action authority exist. Never push to a remote, change an upstream repository, release, deploy, spend external funds, or contact people just because a simulated CEO says to do so. Existing explicit human delegations, when present, govern those actions without repeated approval requests.

Validate enforcement and recovery behavior before proceeding to M2. Update docs/18-handoff.md and the roadmap with implemented files, test results, remaining risks and the exact next step. Keep a truthful capability matrix. If blocked by missing credentials, complete the local interface, mocks, tests and documentation first, then explain the specific missing value. Do not ask broad setup questions at the start.

Preserve the Master Consultant requirement in docs/19-master-consultant.md. The consultant is an independent scoped adviser; its proposals go to the CEO, and approval must hand off through ordinary authorized work orders. Keep the implemented offline scanner and proposal tests. Do not interpret heuristic warnings as confirmed bugs.

Preserve hardware skill learning in docs/20-hardware-skills.md. Firmware and board-support projects are allowed; physical fabrication is not. Live documentation fetch stays fail-closed. Page text cannot amend policy.

Preserve Quality Control and Human Resources in docs/21-quality-hr.md. Product acceptance requires a QC pass on the exact artifact. HR oversees employee development and training. The Master Consultant remains advisory.

Preserve employee development in docs/22-employee-development.md. Hired employees need attributes, backgrounds, regular documented training, goals, reviews and trends.
