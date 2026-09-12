# Empty-List Unknown-Project URL Clear Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gate companion unknown-`?project=` clear on `projectsLoaded` so empty enroll lists clear stale deep links after a successful refresh (v0.3.75).

**Architecture:** Boolean `projectsLoaded` in `App.tsx`, set `true` only on successful refresh that applies `setProjects`. Replace `!projects.length` early-return with `!projectsLoaded` gate. Existing replaceState/serialize unchanged.

**Tech Stack:** React companion, Python unittest source contracts, `npm run build`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-12-empty-list-unknown-project-url-design.md` (owner-approved).
- `projectsLoaded` default `false`; set `true` only after successful `setProjects(...)`.
- Refresh failure: do **not** set `projectsLoaded`; keep boot/`popstate` selection.
- Silent clear only; no toasts; no Manage/Browse URL sync; no new APIs.
- Version **0.3.75**. Do not commit `local repos/service-department/` or `.vscode/tasks.json`.
- Prefer owner-gated commits; if executing under SDD/owner “execute”, commits are authorized.
- Branch: create `feature/empty-list-unknown-project-url` from current `main` before Task 1.
- Keep soft version pins (`0\.3\.\d+`) in older contracts; exact `0.3.75` only in this release’s contract.

## File map

| Path | Role |
|---|---|
| `tests/test_companion_url_sync.py` | Extend contracts for loaded-gate |
| `companion/src/App.tsx` | `projectsLoaded` + clear effect |
| Docs + versions | **0.3.75**, ADR-057 |

---

### Task 1: Failing source contracts

**Files:**
- Modify: `tests/test_companion_url_sync.py`

**Interfaces:**
- Consumes: none
- Produces: RED assertions Tasks 2–3 must satisfy

- [ ] **Step 1: Create branch**

```bash
git checkout main
git pull --ff-only
git checkout -b feature/empty-list-unknown-project-url
```

- [ ] **Step 2: Extend the test module**

Add (or replace the weak unknown-clear coverage with) assertions in `tests/test_companion_url_sync.py`:

```python
    def test_app_unknown_project_clear_gated_on_projects_loaded(self):
        text = (SRC / "App.tsx").read_text()
        self.assertIn("projectsLoaded", text)
        self.assertIn("setProjectsLoaded", text)
        self.assertIn("setProjectsLoaded(true)", text)
        # Gate clear on loaded flag — not empty-list early return alone
        self.assertRegex(
            text,
            r"if\s*\(\s*!projectsLoaded\s*\|\|\s*!selectedProject\s*\)\s*return",
        )
        self.assertNotRegex(
            text,
            r"if\s*\(\s*!selectedProject\s*\|\|\s*!projects\.length\s*\)\s*return",
        )

    def test_version_bump_target_exact(self):
        init = (ROOT / "company" / "__init__.py").read_text()
        self.assertIn('__version__ = "0.3.75"', init)
        pkg = (ROOT / "companion" / "package.json").read_text()
        self.assertIn('"version": "0.3.75"', pkg)
```

Keep existing `test_version_bump_target` soft pin (`0\.3\.\d+`) **or** rename: if both exact and soft exist, soft pin may stay for regression; exact pin is the release gate. Prefer: keep soft pin as `test_version_bump_target` and add `test_version_bump_target_exact` as above.

Update the module docstring to mention v0.3.75.

- [ ] **Step 3: Run — expect FAIL**

Run: `.venv/bin/python -m unittest tests.test_companion_url_sync -v`

Expected: FAIL on `projectsLoaded` / gate regex / exact `0.3.75`.

- [ ] **Step 4: Commit**

```bash
git add tests/test_companion_url_sync.py
git commit -m "$(cat <<'EOF'
test(companion): gate unknown-project clear on projectsLoaded

EOF
)"
```

---

### Task 2: Implement projectsLoaded gate in App

**Files:**
- Modify: `companion/src/App.tsx`

**Interfaces:**
- Produces: `projectsLoaded: boolean` state; clear effect gated as in the spec

- [ ] **Step 1: Add state** near `projects`:

```tsx
const [projects, setProjects] = useState<Record<string, unknown>[]>([]);
const [projectsLoaded, setProjectsLoaded] = useState(false);
```

- [ ] **Step 2: Set loaded on successful refresh**

Inside the successful `try` of `refresh`, immediately after `setProjects(p.projects)`:

```tsx
setProjects(p.projects);
setProjectsLoaded(true);
```

Do **not** call `setProjectsLoaded` in the `catch` path.

- [ ] **Step 3: Replace clear effect**

Replace:

```tsx
useEffect(() => {
  if (!selectedProject || !projects.length) return;
  const known = projects.some((p) => String(p.id) === selectedProject);
  if (!known) setSelectedProject(null);
}, [projects, selectedProject]);
```

With:

```tsx
useEffect(() => {
  if (!projectsLoaded || !selectedProject) return;
  const known = projects.some((p) => String(p.id) === selectedProject);
  if (!known) setSelectedProject(null);
}, [projects, projectsLoaded, selectedProject]);
```

- [ ] **Step 4: Verify App contracts (version may still FAIL)**

```bash
.venv/bin/python -m unittest \
  tests.test_companion_url_sync.CompanionUrlSyncTests.test_app_unknown_project_clear_gated_on_projects_loaded \
  tests.test_companion_url_sync.CompanionUrlSyncTests.test_app_wires_url_sync \
  -v
cd companion && npm run build
```

Expected: loaded-gate + wire tests PASS; exact version may FAIL; build OK.

- [ ] **Step 5: Commit**

```bash
git add companion/src/App.tsx
git commit -m "$(cat <<'EOF'
fix(companion): clear unknown project after projects load

EOF
)"
```

---

### Task 3: Version, docs, handoff

**Files:**
- Modify: `company/__init__.py` → `0.3.75`
- Modify: `companion/package.json` → `0.3.75`
- Modify: `README.md`, `docs/11-user-experience.md`, `docs/14-roadmap.md`, `docs/decisions.md` (ADR-057), `docs/18-handoff.md`
- Modify: spec status → implemented

**Critical:** Explicit paths only. No `git add -A`.

- [ ] **Step 1:** Bump versions to **0.3.75**.

- [ ] **Step 2: ADR-057**

| ADR-057 | 2026-09-12 | Empty-list unknown-project URL clear | Gate unknown `?project=` clear on `projectsLoaded` after successful refresh; failed fetch keeps deep link; silent clear; no new APIs. |

- [ ] **Step 3:** UX / roadmap / handoff / README / mark design spec **implemented in v0.3.75**.

- [ ] **Step 4:** Full suite + companion build.

```bash
.venv/bin/python -m unittest discover -s tests
cd companion && npm run build
```

Expected: all OK; version contracts green.

- [ ] **Step 5: Commit**

```bash
git add company/__init__.py companion/package.json README.md \
  docs/11-user-experience.md docs/14-roadmap.md docs/decisions.md \
  docs/18-handoff.md \
  docs/superpowers/specs/2026-09-12-empty-list-unknown-project-url-design.md
git commit -m "$(cat <<'EOF'
docs: empty-list unknown-project URL clear and release 0.3.75

EOF
)"
```

---

## Spec coverage checklist

| Spec requirement | Task |
|---|---|
| `projectsLoaded` default false | Task 2 |
| Set true only on successful setProjects | Task 2 |
| Failed fetch leaves flag false | Task 2 |
| Clear gated on projectsLoaded (empty list clears) | Tasks 1–2 |
| Silent clear; replaceState unchanged | Task 2 |
| Contracts + 0.3.75 + ADR-057 | Tasks 1 + 3 |
| Non-goals | Global constraints |

## Plan self-review

- Spec coverage: all owner locks mapped to tasks.
- No TBD/TODO placeholders; exact effect bodies and commit paths.
- Explicit `git add` paths; no `git add -A`.
- Soft `0\.3\.\d+` pin retained; exact `0.3.75` in new exact test.
