# Project context — authoritative handoff

Created 2026-09-01 from the visible project discussion. Owner: Andrew Thompson. Parent project: FS-Tech. Working name: FS-Tech AI Company; final branding is undecided.

## User requirements, preserved

1. Expand OpenBMB/ChatDev beyond a software team into the departments of a full corporation, including art, marketing and other business functions.
2. Maintain a persistent company that grows as projects are completed.
3. Grow a visible building, including facilities planning and necessary contractors.
4. Designate AI models for departments and individual positions, including a mixture of models.
5. Give the CEO the ability to propose and approve company direction.
6. Delegate specific responsibilities to department heads operating under evolving CEO-defined rules.
7. Give the company controlled access to forks of the user's various GitHub/Cursor projects.
8. Have departments respond to real markets, trends and events.
9. Deliver a comprehensive Cursor starter with documentation, context and rules.

## Working product decisions

Use current ChatDev 2.0 as an orchestration dependency behind an adapter. Preserve the virtual-company idea rather than depending on the legacy UI. The human owner retains root authority. Hybrid CEO is the initial design default; human-only and delegated AI modes remain planned options. The CEO role can delegate approvals as well as execution, bounded by parent authority.

Departments persist as organizational entities while workers start on demand. Model choices belong to profiles, separate from positions and institutional memory. Use different creator/reviewer/arbiter models when useful, with measured evaluation rather than assumed vendor superiority.

Project progress means accepted deliverables with evidence. Growth includes accumulated knowledge, improved procedures, justified staffing and visual expansion. Every accepted project can award visual progress; permanent operating cost requires a capacity case.

The headquarters is virtual. Contractor agents plan and provision software resources and visual space. Real-world building construction or hiring physical contractors is outside this scope.

GitHub holds the shared code history. Cursor is the human development interface; the company does not require remote control of Cursor's desktop. Only explicitly enrolled repositories are available to workers. No actual user repository URLs were provided.

Research creates evidence and proposals. External pages cannot amend policy. Departments may act on findings within their delegated authority, while material exceptions escalate.

## Unresolved choices with sensible defaults

- Branding: use the working name, avoid premature logo work.
- Headquarters presentation: start with an accessible 2D floor plan, then isometric animation.
- Deployment: local development first; later support self-hosted services.
- Models: use mock profiles until exact available IDs, credentials and permitted data classes are configured.
- Budget: demo amounts are synthetic examples, not user authorization to spend.
- GitHub ownership and fork targets: select at onboarding, never infer from unrelated conversations.
- Polling cadence and sources: configurable, disabled until installed and scoped.

## What this bundle actually establishes

A deterministic Python/SQLite reference core tests policy revisions, scoped grants, budget enforcement, approvals, Quality Control inspection, Human Resources training certification, employee hire/training/performance records, acceptance, event persistence, signal records, virtual expansion and hardware skill gating. Documentation defines the larger service and UI. Live external adapters deliberately raise NotImplementedError. This is the starting baseline for Cursor, not a completed implementation of every requirement.

## Added requirements

10. Add an independent master consultant to spot bugs and inefficiencies in company code and organizational structure and submit proposals for CEO approval. Provide scoped read access, evidence-backed findings, configurable model assignment and independent validation of resulting changes. See [19-master-consultant.md](19-master-consultant.md).

11. Support hardware-oriented firmware and board-support projects (ESP32, Raspberry Pi, RockPro64 and similar). If the current skill configuration cannot perform the work, pertinent employees must study approved online documentation before dispatch. Physical fabrication remains out of scope. See [20-hardware-skills.md](20-hardware-skills.md).

12. Add a Quality Control department that independently verifies all product work before the company accepts it. Producers cannot inspect their own output. Engineering in-team QA and the Master Consultant do not replace this gate. See [21-quality-hr.md](21-quality-hr.md).

13. Add a Human Resources department that oversees employee development and training, including certification of completed study. Learners cannot certify themselves. The existing People catalog id is retained. See [21-quality-hr.md](21-quality-hr.md).

14. All employees undergo regular documented training on pertinent skills; HR keeps a reviewable training file; every employee has performance goals, reviews and trending; new employees have configurable attributes and backgrounds. See [22-employee-development.md](22-employee-development.md).
