# Current handoff

Date: 2026-09-07. Version: **0.3.53**. State: **Companion iPhone integration: server-derived scopes, paired-admin authority, mobile layout**.

## Companion iPhone full integration

The HQ surfaces were visible on the phone but not usable. Both causes are fixed:

- **Scopes are server-derived.** New `GET /api/v1/session` returns `principal_id`, `kind`,
  `access_level` and `scopes` for the bearer token (authentication only, so a read-only device can
  learn it is read-only). `companion/src/App.tsx` hydrates from it on load and on token change,
  which self-heals the native shell and any stale `localStorage`. `companion-native/App.tsx` now
  stores and injects `scopes` and merges instead of overwriting, so it no longer clobbers them.
- **A paired admin phone may act.** `_is_ceo_actor` (owner or `companion-admin-*`) now backs
  `_ceo_or_admin_companion`, `_hr_or_ceo` and `_division_proposer`, plus `approve_policy`,
  `reject_policy`, `respond_owner_request` and `ConsultantDesk.decide`. Root authority stays
  owner-only: pairing issue/list/revoke, revenue, budget periods, policy rollback, model
  assignment, feed enrollment, SLO observations. Recorded as ADR-034.
- **Layout is iPhone-sized.** Five tabs (Home, Projects, Org, Corporate, More) with a segmented
  switcher in More for Decisions, Inbox, Diagnostics and Settings, plus a pending-work badge.
  `input, select, textarea, button` are styled generically at 16px and 44px minimum so number,
  datetime-local and select fields stop being unstyled and stop triggering iOS focus zoom. Safe
  area insets apply on all edges; the switcher wraps to 2×2 at 320px and the tab bar shrinks in
  landscape.
- **Every write reports where it happened.** A shared `runAction` helper drives an inline status
  line per form or list row instead of only the page-top error, which is off-screen when acting
  from a lower section. Insufficient scope now shows the missing scope rather than hiding silently.

## Verification

- `.venv/bin/python -m unittest discover -s tests`: **334 passed**
- `cd companion && npm run build`: passed; `npx tsc --noEmit`: clean
- Browser check against a local paired admin session at 390×844, 320×568 and 844×390: no
  horizontal overflow, no field below 44px/16px, nav labels unclipped, `Scan staffing gaps`
  returned "Scan complete." from a `companion-admin-*` token
- New tests: `/api/v1/session` for admin, read-only and owner; admin staffing scan, division
  proposal, policy decision and owner-inbox response; `companion-user-*` refused; root authority
  still owner-only; desk anchors resolve; five-tab nav, touch CSS and native scope injection

## Next

Deploy with `scripts/deploy_to_fs_dev.sh` plus the remote `run-install.sh`, then re-pair the phone
once so the native session carries scopes. After that, resume M10-03 with a
benchmark-results/model-profile read path or removal, preserving the persisted-evidence rule.
