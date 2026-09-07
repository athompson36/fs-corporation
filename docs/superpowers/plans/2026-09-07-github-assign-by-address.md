# GitHub Assign by Address Implementation Plan

> **For agentic workers:** TDD task-by-task.

**Goal:** Phone pastes upstream GitHub address; server ensures `owner/repo-corp` and enrolls both.

**Architecture:** Parse + resolve in `github_app` / small helper; `Company.assign_github_by_address`; FastAPI route; companion form.

**Tech Stack:** Python, httpx GitHub App, React companion, unittest.

## Global Constraints

- Fail closed without App credentials
- Same-owner `{name}-corp` sibling (create if missing); upstream pull-only by enrollment ids
- CEO + `project.enroll`; integer repo ids in `github_enrollments`
- No invented UI state

---

### Task 1: Parse + GitHub helpers + core assign — tests first

### Task 2: API route + companion form + docs/version
