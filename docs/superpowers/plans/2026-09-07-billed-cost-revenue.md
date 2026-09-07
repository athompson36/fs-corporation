# Billed Cost and Revenue Implementation Plan

> Status: **implemented** (v0.3.48).

**Goal:** Persist honest billed cost and revenue in minor units, separate from simulated credits (M10-03 slice).

**Architecture:** New `billed_costs` / `revenue` tables; live `invoke_model` inserts billed rows; optional token pricing; `status()` exposes separate sums.

**Tech Stack:** Python 3.12+, SQLite, Alembic, unittest.

## Global Constraints

- Integer minor units via `money()`; never store tokens as cents.
- Mock invoke does not write billed rows.
- Do not mix billed/revenue into `simulated_spend_cents`.
- Forward-only Alembic; update `schema.py` and `HEAD_REVISION`.

---

### Task 1: Schema + migration — done

### Task 2: Provider honesty + pricing — done

### Task 3: Persist billed cost on live invoke — done

### Task 4: Revenue writer + status/desk — done
