# Design: Local repo candidates + Diagnostics (desk & companion)

Date: 2026-09-07. Status: **implemented** (v0.3.50).

## Goal

1. List folders under `local repos/` as **enroll candidates** in Projects (tap to enroll).
2. **Diagnostics** on desk and companion: operator status pack + local-repos enrollment state; fail closed / omit on errors (no invented healthy state).

## Decisions

| Topic | Choice |
|---|---|
| Local repos UX | Candidates list + tap enroll (not auto-enroll) |
| Diagnostics | Status endpoints + local-repos (option 2) |
| Path | `local repos/` under install/repo root; override `FS_CORP_LOCAL_REPOS_DIR` |

## API

`GET /api/v1/local-repos` — scope `company.read`

```json
{
  "root": "/abs/path/local repos",
  "present": true,
  "candidates": [
    {"id": "service-department", "path": "...", "has_git": false, "remote_url": null, "enrolled": false}
  ]
}
```

Missing root → `present: false`, `candidates: []`.

## UI

- Companion: Projects shows Local candidates + Enroll; new Diagnostics tab
- Desk: Projects/activity area shows candidates; Diagnostics section with same fetches

Fetches (parallel, best-effort): health, workers/status, model/status, github/status, push/status, chatdev/status, feeds, slos, local-repos.

## Out of scope

Auto-clone, auto GitHub assign from folder, inventing HQ rooms.
