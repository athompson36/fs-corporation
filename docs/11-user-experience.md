# User experience specification

## Product navigation

CEO desk sidebar grouped as **Home · Work · People · Money · More**, with nested anchors matching the companion domains. Home is hybrid (metrics + Decisions/Consultant first, Headquarters high); Scorecard sits under Work with Projects, Cross-department, Corporate upgrades and People/staffing; People holds Organization and Head inbox; Money is Budget; More holds Intelligence, Diagnostics, Activity and Pairing. Default to meaningful work and decisions, not engine configuration.

## CEO desk

Show active objectives, decisions awaiting attention, blocked projects, actual/reserved/estimated costs and next milestones. Each decision opens evidence, alternatives and the exact action requested. Support approve, edit, reject and request research. An owner pause control states its scope: new dispatch stops, running actions may still need reconciliation.

Company-rule editing presents readable responsibility statements alongside explicit action/resource/limit controls. Show policy diffs, who proposed the change, who can approve it and which queued tasks will be affected. Root-owner restrictions are distinguishable from rules an AI CEO can amend.

## Department view

Mission, head, delegated authority summary, queue, staffing, assigned models, measures, budget and proposed improvements. A head's effective scope should be understandable: permitted projects, action limits and escalation cases. Switching a model offers only compatible profiles and shows benchmark history and data constraints.

## Project view

Brief, acceptance criteria, repository/fork identity, branch policy, departments, work tree, artifacts, CI/review evidence, Quality Control verdict, approvals and timeline. A project can be blocked with a clear missing dependency — including uncertified hardware skills or a missing QC pass — rather than showing simulated progress.

## Headquarters

Readable 2D floor plan plus an isometric projection of the same persisted expansion rooms. Select a room from the list or tiles to open persisted tasks, staff, deliverables, simulated costs and related decisions. Provide a keyboard-accessible list view, reduced motion (isometric rise animation is disabled), text status in addition to color, and zoom that preserves legibility. Room occupancy is not the count of running model requests. Empty HQ draws no invented rooms.

## Intelligence inbox

Sourced findings grouped by project/department. Display source date, observed date, freshness, uncertainty and proposed response. Allow dismiss, request verification, create scoped task or escalate. Corrections should mark affected prior decisions.

## Onboarding

Set company name and owner → choose CEO mode → set root limits → enable initial departments → register available models → enroll one test project → approve first brief → run contained pilot → accept result → preview expansion. Keep model credentials and provider configuration in an administrator flow.

## Design direction

Official visual system: **cosmic restraint** — midnight background, cosmic blue primary, ultraviolet secondary, aurora success, soft-white type, subtle glass cards, clear hierarchy. Syne display type and Manrope body type are shared across companion, desk and welcome. The CEO desk sidebar uses the same five domain groups — **Home · Work · People · Money · More** — with nested always-expanded anchors, hybrid Home (metrics + Decisions/Consultant + HQ), and Scorecard under Work. The companion bottom bar has the matching five domain tabs. Home is the Needs-you queue assembled only from persisted pending decisions and owner-inbox requests, with scope-gated inline actions; Work groups Projects/Corporate/Workers, People opens Organization, Money opens Finance, and More retains the full Decisions/Inbox plus Diagnostics/Settings views. Work's Projects, Corporate and Workers panels and the People organization panel use a local **Browse** default for persisted lists/details and in-row actions, plus **Manage** for create/enroll/configure controls. Projects Browse is a responsive list|detail split (list beside the workspace at ≥720px; stacked on narrow viewports); the detail pane is the full project workspace (brief, GitHub ids, dispatch) with a quiet **Clear selection** control, and the empty detail copy is “Select a project”. Manage remains enroll/assign. Corporate Browse lists use `section-head` titles and `panel-empty` empty states; the Workers **Worker hosts** title sits outside the list card (same pattern as Projects and Corporate Objectives). Organization Browse uses a **Departments** `section-head` above the catalog and keeps Head inbox + inline assign; Manage form titles sit in `section-head` outside each form card. Finance keeps **Overview · Invoices · Adjustments · Periods** without a nested mode switch. Metrics pad real counts (including zero); they never invent occupancy, rooms, or workload. Isometric rooms show small SVG furniture glyphs from persisted `room_type`; photoreal art packs remain deferred.

## Current status

This bundle has a local HTML CEO desk (cosmic-glass shell, five-domain sidebar, 2D plan + isometric projection + room detail from persisted events, plus read lists for projects, departments, people, intelligence, budget and activity) and a mobile-first PWA in `companion/` that reads the same persisted API state. Desk v0.3.67 aligns that sidebar and page order to the companion domains without renaming section ids or adding domain panes. Companion v0.3.70 ships Organization Browse/Manage section-head consistency (Departments catalog title plus Manage form titles outside form cards) on top of the v0.3.69 Corporate/Workers Browse polish and the v0.3.68 Projects Browse list|detail split. Work/People Browse–Manage from v0.3.66 is unchanged in capability; no API contracts, URL sync, Corporate groups or Finance ModeSwitch were added. Hardware skill gaps appear as blocked work, not as animated progress. Custom photoreal room art remains deferred; P4 ships type-based SVG furniture only.
