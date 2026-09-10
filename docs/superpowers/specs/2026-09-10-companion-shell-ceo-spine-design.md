# Design: Companion shell + CEO spine (unified brand)

Date: 2026-09-10. Status: **implemented in v0.3.65**.

## Goal

Upgrade the operational UI toward a logically modern layout without a full rewrite.
This release ships the **companion shell + CEO attention spine**, and lightly aligns desk
and `/welcome` to the same brand type. Full visual polish of every Work/People/Money form
and a desk IA rewrite are follow-ups.

## Owner locks

| Topic | Choice |
|---|---|
| Surfaces | C — companion + desk + welcome (phased) |
| First spine | C — Home + Decisions/Inbox daily loop |
| Primary nav | C — collapse to Home · Work · People · Money · More |
| Visual direction | B — unified brand (Syne/Manrope + constellation into ops) |
| Home layout | A — Needs-you queue stack with inline actions |
| Tab content map | A — domain map |
| Delivery | 1 — shell + spine first |

## Non-goals (this release)

- Rewriting every Corporate/Org/Finance form layout.
- Desk sidebar / HQ interaction redesign.
- Rebuilding the `/welcome` hero (already shipped in 0.3.64).
- Native Expo / `companion-native` changes.
- New control-plane APIs or invented metrics/occupancy.
- Tailwind or a third-party component library.

## Information architecture

### Primary tabs

| Tab | Contents |
|---|---|
| **Home** | Needs-you queue (decisions + owner inbox) + status strip; badge = open decisions + inbox count |
| **Work** | Segmented: Projects · Corporate · Workers |
| **People** | Organization (catalog, heads, assignments, worker card, head inbox) |
| **Money** | Existing `FinancePanel` (Overview · Invoices · Adjustments · Periods) |
| **More** | Segmented: Diagnostics · Settings · Decisions · Inbox (full-list overflow) |

### Rules

- Default tab after load remains **Home** (empty queue + status is valid).
- Work / People / Money retain **all current capabilities**; this pass regroups and
  restyles the shell, it does not remove features.
- Scope-gated controls keep inline missing-scope notices (never silently drop a domain).
- Public routes stay: companion `/`, desk `/desk`, marketing `/welcome`.

## Home (Needs-you queue)

Top → bottom:

1. Brand header: FS-Corporation + access badge; quiet constellation wash (not a marketing hero).
2. Offline / error banners (existing semantics).
3. **Needs you** stacked cards from persisted lists only:
   - Decision: kind tag, summary, Approve / Reject when scopes allow (same controls as More → Decisions).
   - Inbox: same fields as today’s Inbox cards (kind · department · subject); Respond when scopes allow.
4. Empty state when both queues are empty (no placeholder fake items).
5. **Status strip**: policy version, paused, simulated spend / reserved, open counts
   (same fields as today’s dashboard card).
6. Pause / Resume / Refresh (scope-gated).

Behavior:

- Reuse existing decide and inbox-respond APIs and form-status pattern.
- **Escalate / create** owner requests stays on More → Inbox (not duplicated on Home).
- Order: all pending decisions (API order), then inbox (API order). No client-invented priority.
- “View all” controls jump to More → Decisions / Inbox.
- Proposed extraction: `HomePanel` component; action helpers stay shared with More screens.

## Visual system

- **Fonts:** self-hosted Syne (display) + Manrope (body), same assets as `/welcome`.
- **Tokens:** keep `assets/cosmic-glass-tokens.css`; add `--font-display`, `--font-body`,
  and a quieter ops `--wash` if needed.
- **Companion:** five-tab bar, Home badge, glass cards, short motion with
  `prefers-reduced-motion` respected; pairing screen uses the same type stack.
- **Desk this pass:** link shared fonts; align heading/body faces only.
- **Welcome this pass:** no hero redesign; keep shared token/font coupling.
- Avoid generic purple-on-white, cream/terracotta, broadsheet density, emoji chrome.

## Architecture / code shape

- Companion remains a Vite React PWA under `companion/`.
- Prefer extracting `HomePanel` (and thin tab shells) from the monolith `App.tsx`
  rather than a big-bang rewrite of every screen.
- Work / People / Money / More wrap existing JSX with segmented switchers where listed.
- No API contract changes expected; auth, pairing, and `GET /api/v1/session` unchanged.

## Failure modes

| Case | Behavior |
|---|---|
| Control unreachable | Existing offline banner + Failed to fetch; do not invent queue items |
| Missing scopes | Disable writes; show missing-scope notice |
| Read-only pairing | Queue visible; approve/respond blocked |
| Empty company | Empty Needs-you + honest zeros in status |

## Verification

- `cd companion && npm run build`
- Manual: pair → Home queue → approve/reject → respond → switch Work/People/Money/More →
  fonts load on companion and desk
- `.venv/bin/python -m unittest discover -s tests` (expect green; no intentional API breaks)
- Post-deploy fs-dev: `/`, `/desk`, `/welcome`, font/static assets 200

## Docs / release

- Update `docs/24-mobile-companion.md` (tab model), `docs/11-user-experience.md` (shell),
  `docs/18-handoff.md`, roadmap, and an ADR for shell + IA.
- Ship as the next patch version after **0.3.64**.

## Follow-ups (explicitly deferred)

1. Deep layout polish inside Work / People / Money forms.
2. Desk information architecture and sidebar alignment to the five domains.
3. Optional further welcome/desk atmospheric tuning beyond fonts.

## Open implementation notes (non-blocking)

- Exact segmented labels and last-selected subtab persistence may mirror today’s
  `lastMoreTab` pattern.
- Version strip above the tab bar remains (ADR-041 / P5).
