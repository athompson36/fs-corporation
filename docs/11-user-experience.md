# User experience specification

## Product navigation

CEO desk; Headquarters; Projects; Departments; People and models; Intelligence; Decisions; Budget; Company rules; Activity. Default to meaningful work and decisions, not engine configuration.

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

Official visual system: **cosmic restraint** — midnight background, cosmic blue primary, ultraviolet secondary, aurora success, soft-white type, subtle glass cards, clear hierarchy. The CEO desk uses a sidebar and metric cards. The companion uses the same tokens with a bottom tab bar. Metrics pad real counts (including zero); they never invent occupancy, rooms, or workload. Furnished isometric interiors remain deferred.

## Current status

This bundle has a local HTML CEO desk (cosmic-glass shell, 2D plan + isometric projection + room detail from persisted events, plus read lists for projects, departments, people, intelligence, budget and activity) and a mobile-first PWA in `companion/` that reads the same persisted API state. Hardware skill gaps appear as blocked work, not as animated progress. Custom furnished room art remains deferred.
