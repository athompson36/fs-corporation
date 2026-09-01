# Product requirements and traceability

## Personas

Owner/CEO: chooses objectives, delegates authority, reviews outcomes and overrides decisions. Department head: turns objectives into bounded work, manages a queue and escalates exceptions. Specialist: performs tasks with approved tools. Quality Control: independently inspects product artifacts. Human Resources: oversees development and training. Contractor: fulfills approved provisioning work. Reviewer: verifies outputs independently. Observer: views permitted progress without changing state.

## Requirements

| ID | Requirement | Acceptance condition | Target |
|---|---|---|---|
| R01 | Persistent organization | Departments, roles, assignments and history survive restart | M1/M2 |
| R02 | CEO authority | Authenticated CEO can approve direction, amend policy and pause operations | M1 |
| R03 | Delegated heads | A head can approve/execute only within its action, project, time and budget scope | M1/M3 |
| R04 | Evolving rules | Proposals show before/after diff; stale changes rejected; history and rollback retained | M1 |
| R05 | Mixed models | Department defaults and position overrides work; incompatible routing is rejected | M2 |
| R06 | Real artifacts | Tasks create versioned deliverables with reproducible evidence | M3/M4 |
| R07 | Controlled forks | Work reaches allowed branches; prohibited upstream writes fail before dispatch | M4 |
| R08 | Human collaboration | Human Cursor edits and agent branches coexist with conflict handling | M4 |
| R09 | Market response | A sourced event produces a deduplicated impact brief and scoped next action | M5 |
| R10 | Growth | Accepted work produces one growth credit; replay creates no duplicate credit | M6 |
| R11 | Construction | CEO-approved facilities order can provision a room with a recorded inspection | M6 |
| R12 | Financial visibility | Estimated, reserved and actual costs shown separately from simulated credits | M3/M7 |
| R13 | Company memory | Approved procedures and artifacts retrieved within project/data boundaries | M2/M7 |
| R14 | Owner control | Pause stops new dispatch; revoked grants block queued work; running work is reconciled | M1/M3 |
| R15 | Useful headquarters | Each room opens real tasks, staff, deliverables and relevant decisions | M6 |
| R16 | Auditable completion | Exact artifact accepted by a distinct authorized reviewer; evidence remains linked | M3/M4 |
| R17 | Master Consultant | Scoped adviser submits evidence-backed proposals; cannot self-approve or auto-execute | M1/M3/M7 |
| R18 | Hardware skills | Hardware firmware projects blocked until pertinent employees study approved sources and an independent reviewer certifies the skill | 0.3.1 |
| R19 | Quality Control | Product acceptance requires a passing inspection by Quality Control of the exact artifact; producer and CEO cannot substitute for QC | 0.3.2 |
| R20 | Human Resources | HR oversees development and training; HR or CEO certifies study; learners cannot self-certify | 0.3.2 |
| R21 | Employee development | Hired employees have attributes/backgrounds, recurring documented training, performance goals, reviews and score trends | 0.3.3 |
| R22 | Mobile CEO companion | Owner views company/project stats and acts on decisions, project dispatch, and team feedback from a smartphone over an authenticated private network | 0.3.5/M8 |

## Core journeys

**Enroll a project:** select repository → inspect ownership/access → choose fork strategy → set allowed actions and branches → attach brief → assign departments → run a contained pilot.

**Deliver a project:** submit objective → product scopes outcomes → heads propose plans → approve resources → workers execute → Quality Control inspects the exact artifact → owner/delegated acceptor accepts → archive evidence → growth proposal.

**Amend delegation:** head proposes a responsibility or procedure change → policy diff and cost impact → authorized approver decides → increment policy version → invalidate affected stale approvals → recheck queued work.

**Respond to an event:** collect allowed source → timestamp and normalize → deduplicate → assess relevance and corroboration → head decides within scope or escalates → track resulting work and impact.

## Nonfunctional targets (proposed, not measured)

Durable commands and restart-safe queues; idempotent effects; project isolation; bounded spending and loops; accessible keyboard navigation and reduced motion; configuration export; ability to run locally with mock providers. Establish latency and throughput SLOs after the first real integration benchmark. Do not invent production capacity numbers.

## Not in the initial release

Unrestricted autonomous trading/spending, unsupervised legal sign-off, physical construction, controlling Cursor's GUI, universal provider compatibility, a continuously running agent for every employee, or guaranteed commercial success.

## R17 — Master Consultant

A scoped adviser can review code and company structure, submit evidence-backed improvement proposals, and receive CEO approval/rejection. It cannot approve itself or execute a fix solely because a proposal was accepted. Heuristic scanner and local proposal persistence are implemented in 0.2.0. Authenticated access is M1; live AI review/diagnostics and authorized implementation handoff are M3/M7.

## R18 — Hardware skills

Hardware firmware and board-support projects (ESP32, Raspberry Pi, RockPro64 and similar) are enrolled with a platform catalog. Dispatch of product work is blocked until required skills are certified. Pertinent employees study approved HTTPS documentation; page text cannot amend policy. Live fetch remains fail-closed. Physical fabrication is out of scope. See [20-hardware-skills.md](20-hardware-skills.md).

## R19 — Quality Control

Every product deliverable must receive a Quality Control inspection of the exact artifact hash before CEO/delegated acceptance. Quality Control is a distinct department. The producer cannot inspect their own work. The owner/CEO cannot record the QC verdict. A failing inspection blocks acceptance. Facilities room inspection remains the construction gate. See [21-quality-hr.md](21-quality-hr.md).

## R20 — Human Resources

Human Resources oversees employee development and training. Catalog id `people` is retained. HR Director or Training Specialist (or the CEO) certifies completed study assignments. Learners cannot certify themselves. The development roster lists learning assignments and acquired skills. See [21-quality-hr.md](21-quality-hr.md).

## R21 — Employee development

Hired employees carry configurable attributes and a written background. Pertinent company, department and position skills are assigned as regular training. Overdue training is documented and blocks product dispatch for that employee. Performance goals, independent reviews and score trends are recorded by HR or the CEO. See [22-employee-development.md](22-employee-development.md).
