"""Deterministic local reference implementation. No network calls or arbitrary code execution.

Actor identifiers are trusted inputs in this local demo. They are NOT authentication.
Production requires authenticated principals and a separate credentialed action gateway.
"""
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import sqlite3
import subprocess
import threading
import uuid
from .schema import (
    COMPANION_SCOPES, GRANT_OPTIONAL, GRANT_REQUIRED, MAX_DELEGATION_DEPTH,
    PAIRING_LEVEL_IDS, POLICY_REQUIRED, SLO_DEFINITIONS, apply_schema,
    pairing_level, pairing_levels_catalog,
)
from .migrate import ensure_migrations, is_ephemeral_path


def now():
    return datetime.now(timezone.utc)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def money(value):
    if type(value) is not int or value < 0:
        raise ValueError("Costs must be nonnegative integer USD cents")
    return value


class _MaterializedCursor:
    """Rows fetched under the company lock so callers can iterate safely."""

    def __init__(self, rows, description, lastrowid, rowcount):
        self._rows = list(rows)
        self.description = description
        self.lastrowid = lastrowid
        self.rowcount = rowcount
        self._i = 0

    def fetchone(self):
        if self._i >= len(self._rows):
            return None
        row = self._rows[self._i]
        self._i += 1
        return row

    def fetchall(self):
        rest = self._rows[self._i:]
        self._i = len(self._rows)
        return rest

    def __iter__(self):
        return iter(self.fetchall())


class _LockedConnection:
    """Serialize all use of one sqlite3 connection across FastAPI worker threads."""

    def __init__(self, conn):
        self._conn = conn
        self._lock = threading.RLock()

    @property
    def lock(self):
        return self._lock

    def execute(self, *args, **kwargs):
        with self._lock:
            cur = self._conn.execute(*args, **kwargs)
            rows = cur.fetchall()
            return _MaterializedCursor(rows, cur.description, cur.lastrowid, cur.rowcount)

    def executescript(self, *args, **kwargs):
        with self._lock:
            return self._conn.executescript(*args, **kwargs)

    def backup(self, target, *args, **kwargs):
        with self._lock:
            return self._conn.backup(target, *args, **kwargs)

    def close(self):
        with self._lock:
            self._conn.close()


class Company:
    def __init__(self, path=":memory:", ceo="human-ceo"):
        self.db_path = str(path)
        raw = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
        raw.row_factory = sqlite3.Row
        raw.execute("PRAGMA foreign_keys=ON")
        raw.execute("PRAGMA busy_timeout=5000")
        apply_schema(raw)
        # Release the connection before Alembic opens its own — holding both deadlocks
        # on file-backed SQLite databases.
        if not is_ephemeral_path(self.db_path):
            raw.close()
            ensure_migrations(self.db_path)
            raw = sqlite3.connect(self.db_path, isolation_level=None, check_same_thread=False)
            raw.row_factory = sqlite3.Row
            raw.execute("PRAGMA foreign_keys=ON")
            raw.execute("PRAGMA busy_timeout=5000")
        self.db = _LockedConnection(raw)
        with self.tx():
            row=self.db.execute("SELECT value FROM settings WHERE key='ceo'").fetchone()
            if row and row[0] != ceo:
                raise ValueError("Existing database CEO differs; identity migration is not implemented")
            if not row:
                self.db.execute("INSERT INTO settings VALUES('ceo',?)",(ceo,))
                self.db.execute("INSERT INTO settings VALUES('paused','false')")
                policy={"version":1,"company_budget_cents":10000,"grants":{}}
                self.db.execute("INSERT INTO policies VALUES(1,?)",(canonical(policy),))
                self._event("company.created", {"ceo":ceo,"policy_version":1})
        self.ceo=ceo

    def close(self):
        self.db.close()

    @contextmanager
    def tx(self):
        # Hold the connection lock for the whole transaction so concurrent
        # FastAPI threadpool requests cannot interleave statements.
        # Nested tx() calls join the outer transaction (savepoint-free reentry)
        # so idempotency records can commit atomically with domain mutations.
        with self.db.lock:
            depth = getattr(self, "_tx_depth", 0)
            if depth == 0:
                self.db._conn.execute("BEGIN IMMEDIATE")
            self._tx_depth = depth + 1
            try:
                yield
                self._tx_depth -= 1
                if self._tx_depth == 0:
                    self.db._conn.execute("COMMIT")
            except BaseException:
                self._tx_depth -= 1
                if self._tx_depth == 0:
                    self.db._conn.execute("ROLLBACK")
                raise

    def _event(self,kind,body,actor_id=None,correlation_id=None,project_id=None):
        row=self.db.execute("SELECT hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        previous=row[0] if row else "0"*64
        at=now().isoformat()
        value={"at":at,"kind":kind,"body":body,"previous":previous}
        policy_version=None
        try:
            policy_version=json.loads(self.db.execute("SELECT body FROM policies ORDER BY version DESC LIMIT 1").fetchone()[0])["version"]
        except Exception:
            policy_version=None
        inserted = self.db.execute(
            "INSERT INTO events(at,kind,body,previous,hash,event_id,schema_version,actor_id,policy_version,correlation_id,project_id) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (at,kind,canonical(body),previous,digest(value),str(uuid.uuid4()),1,actor_id,policy_version,correlation_id,project_id))
        event_row = self.db.execute(
            "SELECT * FROM events WHERE seq=?", (inserted.lastrowid,)).fetchone()
        self.apply_activity_from_event(event_row)

    def _activity_department(self, actor=None, task_id=None):
        if task_id:
            queued = self.db.execute(
                "SELECT actor FROM queue WHERE task_id=?", (task_id,)).fetchone()
            if queued:
                actor = queued["actor"]
            else:
                task = self.db.execute(
                    "SELECT actor FROM tasks WHERE id=?", (task_id,)).fetchone()
                if task:
                    actor = task["actor"]
        if not actor:
            return None
        assignment = self.db.execute(
            """SELECT department_id FROM position_assignments
               WHERE principal_id=? AND status='active'
               ORDER BY assigned_at DESC, id DESC LIMIT 1""",
            (actor,),
        ).fetchone()
        if assignment:
            return assignment["department_id"]
        prefix = str(actor).split(":", 1)[0]
        known = self.db.execute(
            "SELECT id FROM departments WHERE id=?", (prefix,)).fetchone()
        return known["id"] if known else None

    def _activity_room(self, department_id):
        if not department_id:
            return None
        row = self.db.execute(
            """SELECT id FROM floorplan_rooms
               WHERE department_id=? AND status='active'
               ORDER BY created_at, id LIMIT 1""",
            (department_id,),
        ).fetchone()
        return row["id"] if row else None

    @staticmethod
    def _activity_body(event_row):
        keys = event_row.keys()
        body = event_row["body"] if "body" in keys else event_row["event_body"]
        return json.loads(body) if isinstance(body, str) else dict(body)

    def _open_activity_for_task(self, task_id, kind):
        if not task_id:
            return None
        for session in self.db.execute(
                """SELECT activity_sessions.*, events.body AS event_body
                   FROM activity_sessions
                   JOIN events ON events.seq=activity_sessions.started_event_id
                   WHERE activity_sessions.status='open' AND activity_sessions.kind=?""",
                (kind,)):
            source = self._activity_body(session)
            if (source.get("task_id") or source.get("queue_task_id")) == task_id:
                return session
        return None

    def _start_activity(self, event_row, kind, *, project_id=None,
                        department_id=None, participants=None, task_id=None):
        if self._open_activity_for_task(task_id, kind):
            return
        seq = event_row["seq"]
        self.db.execute(
            """INSERT OR IGNORE INTO activity_sessions(
                   id,kind,project_id,department_id,room_id,participants,status,
                   started_event_id,ended_event_id,started_at,ended_at)
               VALUES(?,?,?,?,?,?,'open',?,NULL,?,NULL)""",
            (
                digest({"activity_started_event_id": seq})[:32],
                kind,
                project_id or event_row["project_id"],
                department_id,
                self._activity_room(department_id),
                canonical(sorted({
                    str(participant) for participant in (participants or [])
                    if participant
                })),
                seq,
                event_row["at"],
            ),
        )

    def _close_activity_for_source(self, source_kind, source_id, event_row):
        for session in self.db.execute(
                """SELECT activity_sessions.id, events.body AS event_body
                   FROM activity_sessions
                   JOIN events ON events.seq=activity_sessions.started_event_id
                   WHERE activity_sessions.status='open' AND events.kind=?""",
                (source_kind,)):
            source = self._activity_body(session)
            if (source.get("id") or source.get("run_id")) == source_id:
                self.db.execute(
                    """UPDATE activity_sessions
                       SET status='closed',ended_event_id=?,ended_at=?
                       WHERE id=?""",
                    (event_row["seq"], event_row["at"], session["id"]),
                )

    def _close_activity_for_task(self, task_id, event_row):
        if not task_id:
            return
        for session in self.db.execute(
                """SELECT activity_sessions.id, events.body AS event_body
                   FROM activity_sessions
                   JOIN events ON events.seq=activity_sessions.started_event_id
                   WHERE activity_sessions.status='open'
                     AND activity_sessions.kind IN ('work','review')"""):
            source = self._activity_body(session)
            if (source.get("task_id") or source.get("queue_task_id")) == task_id:
                self.db.execute(
                    """UPDATE activity_sessions
                       SET status='closed',ended_event_id=?,ended_at=?
                       WHERE id=?""",
                    (event_row["seq"], event_row["at"], session["id"]),
                )

    def apply_activity_from_event(self, event_row):
        """Apply one persisted event to the activity projection idempotently."""
        if not event_row:
            raise ValueError("Persisted event required")
        body = self._activity_body(event_row)
        kind = event_row["kind"]

        if kind == "owner.request_responded":
            self._close_activity_for_source(
                "owner.request_created", body.get("id"), event_row)
            return
        if kind == "cross_department.request_accepted":
            self._close_activity_for_source(
                "cross_department.request_created", body.get("id"), event_row)
            return
        if kind == "worker.finished":
            self._close_activity_for_source(
                "worker.started", body.get("run_id"), event_row)
            return
        if kind in {"task.cancelled", "task.worker_completed", "project.accepted"}:
            self._close_activity_for_task(body.get("task_id"), event_row)
            return

        if kind in {"task.leased", "task.started", "worker.started"}:
            task_id = body.get("task_id")
            worker = body.get("worker") or event_row["actor_id"]
            queued = self.db.execute(
                "SELECT project FROM queue WHERE task_id=?", (task_id,)).fetchone()
            self._start_activity(
                event_row, "work",
                project_id=event_row["project_id"] or (
                    queued["project"] if queued else None),
                department_id=self._activity_department(worker, task_id),
                participants=[worker], task_id=task_id,
            )
            return
        if kind == "quality.inspected":
            task_id = body.get("task_id")
            self._start_activity(
                event_row, "review",
                department_id=self._activity_department(event_row["actor_id"]),
                participants=[event_row["actor_id"]], task_id=task_id,
            )
            return
        if kind == "project.dispatch_assigned":
            dispatch = self.db.execute(
                "SELECT department_id FROM project_dispatches WHERE id=?",
                (body.get("dispatch_id"),),
            ).fetchone()
            assignments = [
                row["assignee"] for row in self.db.execute(
                    """SELECT assignee FROM dispatch_assignments
                       WHERE dispatch_id=? AND status='assigned'
                       ORDER BY assigned_at, id""",
                    (body.get("dispatch_id"),),
                )
            ]
            if dispatch:
                self._start_activity(
                    event_row, "meeting" if len(assignments) > 1 else "work",
                    department_id=dispatch["department_id"],
                    participants=assignments or [body.get("assignee")],
                    task_id=body.get("queue_task_id"),
                )
            return
        if kind == "cross_department.request_created":
            self._start_activity(
                event_row, "cross_department",
                department_id=body.get("delivering_department_id"),
                participants=[event_row["actor_id"]],
            )
            return
        if kind == "owner.request_created":
            self._start_activity(
                event_row, "context_request",
                department_id=body.get("department_id"),
                participants=[event_row["actor_id"]],
            )
            return
        if kind == "project.dispatched" and body.get("status") == "blocked_vacant_head":
            self._start_activity(
                event_row, "context_request",
                department_id=body.get("department_id"),
                participants=[event_row["actor_id"]],
            )

    def list_activity(self, status="open"):
        if status not in {"open", "closed"}:
            raise ValueError("Invalid activity status")
        items = []
        for row in self.db.execute(
                """SELECT * FROM activity_sessions
                   WHERE status=? ORDER BY started_at, id""", (status,)):
            item = dict(row)
            item["participants"] = json.loads(item["participants"])
            items.append(item)
        return {"items": items}

    def activity_for_event(self, event_id):
        row = self.db.execute(
            """SELECT * FROM activity_sessions
               WHERE started_event_id=? OR ended_event_id=?
               ORDER BY started_event_id LIMIT 1""",
            (event_id, event_id),
        ).fetchone()
        if not row:
            return None
        item = dict(row)
        item["participants"] = json.loads(item["participants"])
        return item

    def close_stale_sessions(self):
        """Close projected sessions whose persisted source record is terminal."""
        closed = 0
        ended_at = now().isoformat()
        for session in self.db.execute(
                """SELECT activity_sessions.id, activity_sessions.kind,
                          events.kind AS event_kind, events.body AS event_body
                   FROM activity_sessions
                   JOIN events ON events.seq=activity_sessions.started_event_id
                   WHERE activity_sessions.status='open'"""):
            body = self._activity_body(session)
            terminal = False
            task_id = body.get("task_id") or body.get("queue_task_id")
            if task_id:
                queued = self.db.execute(
                    "SELECT status FROM queue WHERE task_id=?", (task_id,)).fetchone()
                task = self.db.execute(
                    "SELECT status FROM tasks WHERE id=?", (task_id,)).fetchone()
                terminal = bool(
                    (queued and queued["status"] in {"done", "cancelled", "failed"})
                    or (task and task["status"] in {"accepted", "cancelled", "failed"})
                )
            if session["event_kind"] == "worker.started":
                run = self.db.execute(
                    "SELECT status FROM worker_runs WHERE id=?",
                    (body.get("run_id"),),
                ).fetchone()
                terminal = bool(run and run["status"] in {"completed", "failed"})
            elif session["event_kind"] == "owner.request_created":
                request = self.db.execute(
                    "SELECT status FROM owner_requests WHERE id=?", (body.get("id"),)
                ).fetchone()
                terminal = bool(request and request["status"] != "open")
            elif session["event_kind"] == "cross_department.request_created":
                request = self.db.execute(
                    "SELECT status FROM cross_department_requests WHERE id=?",
                    (body.get("id"),),
                ).fetchone()
                terminal = bool(request and request["status"] != "pending_acceptance")
            elif (
                    session["event_kind"] == "project.dispatched"
                    and session["kind"] == "context_request"):
                dispatch = self.db.execute(
                    "SELECT status FROM project_dispatches WHERE id=?",
                    (body.get("dispatch_id"),),
                ).fetchone()
                terminal = bool(
                    dispatch and dispatch["status"] != "blocked_vacant_head")
            if terminal:
                self.db.execute(
                    """UPDATE activity_sessions SET status='closed',ended_at=?
                       WHERE id=? AND status='open'""",
                    (ended_at, session["id"]),
                )
                closed += 1
        return closed

    def _ceo(self,actor):
        if actor != self.ceo:
            raise PermissionError("CEO authority required")

    def _is_ceo_actor(self, actor):
        """CEO string or a paired admin companion.

        Lower pairing levels redeem as ``companion-read_only-*`` or
        ``companion-user-*`` and stay outside this predicate.
        """
        return actor == self.ceo or str(actor).startswith("companion-admin-")

    def _ceo_or_admin_companion(self, actor):
        """CEO string or paired admin companion (phone CEO mobile)."""
        if self._is_ceo_actor(actor):
            return
        raise PermissionError("CEO authority required")

    def _is_qc(self,actor):
        return actor=="qc" or str(actor).startswith("quality:")

    def _hr_or_ceo(self,actor):
        if self._is_ceo_actor(actor):return
        if str(actor).startswith("people:"):
            title=actor.split(":",1)[1]
            if title in {"HR Director","People Director","Training Specialist"}:return
        raise PermissionError("HR or CEO authority required")

    def policy(self):
        return json.loads(self.db.execute("SELECT body FROM policies ORDER BY version DESC LIMIT 1").fetchone()[0])

    @staticmethod
    def validate_policy(policy):
        if not POLICY_REQUIRED.issubset(policy) or not set(policy).issubset(POLICY_REQUIRED):
            raise ValueError("Unknown or missing policy fields")
        if type(policy["version"]) is not int or policy["version"] < 1:
            raise ValueError("Invalid version")
        money(policy["company_budget_cents"])
        if not isinstance(policy["grants"],dict):
            raise ValueError("grants must be an object")
        for actor,g in policy["grants"].items():
            if not isinstance(actor,str) or not actor.strip():
                raise ValueError("Invalid actor")
            fields=set(g)
            if not GRANT_REQUIRED.issubset(fields) or not fields.issubset(GRANT_REQUIRED|GRANT_OPTIONAL):
                raise ValueError("Unknown or missing grant fields")
            for key in ("actions","projects","requires_approval"):
                if not isinstance(g[key],list) or any(not isinstance(x,str) or not x or x=="*" for x in g[key]):
                    raise ValueError("Use explicit nonempty string scopes; wildcards are disallowed")
            if "departments" in g and (
                    not isinstance(g["departments"], list)
                    or any(not isinstance(x, str) or not x or x == "*"
                           for x in g["departments"])):
                raise ValueError("Use explicit nonempty string scopes; wildcards are disallowed")
            if not set(g["requires_approval"]).issubset(g["actions"]):
                raise ValueError("Approval actions must belong to the grant")
            if "approval_rights" in g:
                if not isinstance(g["approval_rights"],list) or any(not isinstance(x,str) or not x or x=="*" for x in g["approval_rights"]):
                    raise ValueError("Use explicit nonempty string scopes; wildcards are disallowed")
            money(g["budget_cents"]);money(g["per_action_cents"])
            if g["per_action_cents"] > g["budget_cents"]:
                raise ValueError("Per-action allowance exceeds total grant")
            stamp=datetime.fromisoformat(g["expires_at"])
            if stamp.tzinfo is None:
                raise ValueError("Expiry needs a timezone")

    def propose_policy(self,actor,policy,reason):
        self.validate_policy(policy)
        if not reason.strip():
            raise ValueError("Amendment rationale required")
        with self.tx():
            current=self.policy()
            if policy["version"] != current["version"]+1:
                raise ValueError("Proposal must target the next policy version")
            pid=str(uuid.uuid4())
            self.db.execute("INSERT INTO proposals VALUES(?,?,?,?,?,?)",
                (pid,current["version"],canonical(policy),actor,reason,"pending"))
            self._event("policy.proposed",{"id":pid,"actor":actor,"reason":reason})
            return pid

    def approve_policy(self,actor,pid):
        self._ceo_or_admin_companion(actor)
        with self.tx():
            p=self.db.execute("SELECT * FROM proposals WHERE id=?",(pid,)).fetchone()
            if not p or p["status"] != "pending":
                raise ValueError("Pending proposal not found")
            if p["base"] != self.policy()["version"]:
                raise ValueError("Stale proposal: rebase on current policy")
            body=json.loads(p["body"])
            self.db.execute("INSERT INTO policies VALUES(?,?)",(body["version"],p["body"]))
            self.db.execute("UPDATE proposals SET status='approved' WHERE id=?",(pid,))
            self._event("policy.approved",{"id":pid,"version":body["version"],"actor":actor})

    def pause(self,actor,paused=True):
        if actor != self.ceo and not self.db.execute(
                "SELECT 1 FROM identities WHERE principal_id=? AND kind='service'", (actor,)).fetchone():
            raise PermissionError("CEO authority required")
        with self.tx():
            self.db.execute("UPDATE settings SET value=? WHERE key='paused'",("true" if paused else "false",))
            self._event("company.paused" if paused else "company.resumed",{"actor":actor})

    def _scope(self,actor,project,action,cost,department_id=None):
        money(cost)
        if self.db.execute("SELECT value FROM settings WHERE key='paused'").fetchone()[0]=="true":
            raise PermissionError("Company paused")
        p=self.policy();g=self._effective_grant(actor)
        if not g or action not in g["actions"] or project not in g["projects"]:
            raise PermissionError("No matching delegation")
        if "departments" in g and department_id not in g["departments"]:
            raise PermissionError("No matching department delegation")
        if datetime.fromisoformat(g["expires_at"]) <= now():
            raise PermissionError("Delegation expired")
        spent=self.db.execute("SELECT COALESCE(SUM(cost),0) FROM ledger WHERE actor=?",(actor,)).fetchone()[0]
        reserved=self.db.execute(
            "SELECT COALESCE(SUM(amount_cents),0) FROM reservations WHERE actor=? AND status='reserved'",(actor,)).fetchone()[0]
        total=self.db.execute("SELECT COALESCE(SUM(cost),0) FROM ledger").fetchone()[0]
        total_res=self.db.execute(
            "SELECT COALESCE(SUM(amount_cents),0) FROM reservations WHERE status='reserved'").fetchone()[0]
        if cost>g["per_action_cents"] or spent+reserved+cost>g["budget_cents"] or total+total_res+cost>p["company_budget_cents"]:
            raise PermissionError("Budget exceeded")
        self._check_period_budget(cost)
        return p,g

    def _effective_grant(self,actor,seen=None):
        if seen is None:seen=set()
        if actor in seen:raise PermissionError("Delegation cycle")
        seen.add(actor)
        p=self.policy();g=p["grants"].get(actor)
        if g:
            out=dict(g);out.setdefault("approval_rights",[])
            return out
        row=self.db.execute(
            "SELECT * FROM delegations WHERE grantee=? AND status='active' ORDER BY created_at DESC LIMIT 1",
            (actor,)).fetchone()
        if not row:return None
        parent=self._effective_grant(row["grantor"],seen)
        if parent is None and row["grantor"]!=self.ceo:
            return None
        child={
            "actions":json.loads(row["actions"]),"projects":json.loads(row["projects"]),
            "budget_cents":row["budget_cents"],"per_action_cents":row["per_action_cents"],
            "expires_at":row["expires_at"],"requires_approval":json.loads(row["requires_approval"]),
            "approval_rights":json.loads(row["approval_rights"]),
        }
        if parent:
            child["actions"]=[a for a in child["actions"] if a in parent["actions"]]
            child["projects"]=[x for x in child["projects"] if x in parent["projects"]]
            if "departments" in parent:
                child["departments"]=list(parent["departments"])
            child["budget_cents"]=min(child["budget_cents"],parent["budget_cents"])
            child["per_action_cents"]=min(child["per_action_cents"],parent["per_action_cents"])
            if datetime.fromisoformat(parent["expires_at"]) < datetime.fromisoformat(child["expires_at"]):
                child["expires_at"]=parent["expires_at"]
            child["approval_rights"]=[a for a in child["approval_rights"] if a in parent.get("approval_rights",[])]
        return child

    @staticmethod
    def payload(actor,project,action,cost,task_id):
        return {"actor":actor,"project":project,"action":action,"cost":cost,"task_id":task_id}

    def approve_action(self,approver,*,actor,project,action,cost,task_id):
        with self.tx():
            p,_=self._scope(actor,project,action,cost)
            if approver!=self.ceo:
                g=self._effective_grant(approver)
                if not g or action not in g.get("approval_rights",[]):
                    raise PermissionError("CEO authority required")
                if project not in g["projects"]:
                    raise PermissionError("Approval not in approver project scope")
            aid=str(uuid.uuid4())
            h=digest(self.payload(actor,project,action,cost,task_id))
            self.db.execute("INSERT INTO approvals VALUES(?,?,?,?,0)",
                (aid,h,p["version"],(now()+timedelta(hours=1)).isoformat()))
            self._event("action.approved",{"id":aid,"payload_hash":h,"version":p["version"]},actor_id=approver,project_id=project)
            return aid

    def execute_mock(self,*,actor,project,action,cost,task_id,approval=None):
        """Only deterministic mock actions. Does not execute Git, shell, HTTP or model calls."""
        money(cost)
        if not task_id or not isinstance(task_id,str):
            raise ValueError("Task id required")
        with self.tx():
            existing=self.db.execute("SELECT * FROM tasks WHERE id=?",(task_id,)).fetchone()
            if existing:
                if (existing["actor"],existing["project"],existing["action"],existing["cost"]) != (actor,project,action,cost):
                    raise ValueError("Idempotency key reused with different payload")
                return dict(existing)
            if action not in {"draft","review","prepare_pr"}:
                raise ValueError("Mock executor supports draft, review, prepare_pr only")
            self._require_project_skills(project)
            self._require_employee_training(actor)
            p,g=self._scope(actor,project,action,cost)
            if action in g["requires_approval"]:
                a=self.db.execute("SELECT * FROM approvals WHERE id=?",(approval,)).fetchone()
                h=digest(self.payload(actor,project,action,cost,task_id))
                if not a or a["used"] or a["payload_hash"]!=h or a["version"]!=p["version"] or datetime.fromisoformat(a["expires"])<=now():
                    raise PermissionError("Valid current approval required")
                self.db.execute("UPDATE approvals SET used=1 WHERE id=?",(approval,))
            artifact=digest({"mock":True,"project":project,"task_id":task_id,"action":action})
            self.db.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?)",
                (task_id,actor,project,action,cost,p["version"],"produced",artifact))
            self.db.execute("INSERT INTO ledger VALUES(?,?,?)",(task_id,actor,cost))
            self._event("task.produced",{"task_id":task_id,"artifact_hash":artifact,"mock":True,"cost_cents":cost})
            return dict(self.db.execute("SELECT * FROM tasks WHERE id=?",(task_id,)).fetchone())

    def inspect_quality(self,inspector,task_id,artifact_hash,verdict):
        if verdict not in {"pass","fail"}:raise ValueError("QC verdict must be pass or fail")
        if not self._is_qc(inspector):raise PermissionError("Only Quality Control may inspect work")
        task=self.db.execute("SELECT * FROM tasks WHERE id=?",(task_id,)).fetchone()
        if not task:raise ValueError("Task not found")
        if inspector==task["actor"]:raise PermissionError("Producer cannot inspect own work")
        if task["artifact_hash"]!=artifact_hash:raise ValueError("Inspection evidence does not match artifact")
        with self.tx():
            iid=digest({"task":task_id,"hash":artifact_hash,"inspector":inspector,"at":now().isoformat()})[:24]
            self.db.execute("INSERT INTO qc_inspections VALUES(?,?,?,?,?,?)",
                            (iid,task_id,artifact_hash,inspector,verdict,now().isoformat()))
            self._event("quality.inspected",{"id":iid,"task_id":task_id,"verdict":verdict},
                        actor_id=inspector,project_id=task["project"])
        return {"id":iid,"task_id":task_id,"verdict":verdict}

    def _require_qc_pass(self,task_id,artifact_hash):
        row=self.db.execute(
            "SELECT * FROM qc_inspections WHERE task_id=? AND artifact_hash=? ORDER BY created_at DESC, rowid DESC LIMIT 1",
            (task_id,artifact_hash)).fetchone()
        if not row or row["verdict"]!="pass":
            raise PermissionError("Quality Control must pass the exact artifact before acceptance")

    def accept_project(self,reviewer,task_id,artifact_hash):
        """CEO accepts a particular mock artifact; production requires actual CI/artifact evidence."""
        self._ceo(reviewer)
        with self.tx():
            task=self.db.execute("SELECT * FROM tasks WHERE id=?",(task_id,)).fetchone()
            if not task or task["artifact_hash"]!=artifact_hash:
                raise ValueError("Acceptance evidence does not match artifact")
            if reviewer==task["actor"]:
                raise PermissionError("Creator cannot accept own output")
            if task["action"]!="draft":
                raise ValueError("Only a mock project deliverable can complete a project")
            self._require_qc_pass(task_id,artifact_hash)
            existing=self.db.execute("SELECT * FROM completions WHERE project=?",(task["project"],)).fetchone()
            if existing:
                if existing["task_id"]!=task_id:
                    raise ValueError("Project already completed with another artifact")
                return
            self.db.execute("INSERT INTO completions VALUES(?,?,?,?)",
                (task["project"],task_id,reviewer,artifact_hash))
            self.db.execute("UPDATE tasks SET status='accepted' WHERE id=?",(task_id,))
            self.db.execute("INSERT INTO expansions VALUES(?,?,'proposed',NULL)",
                ("expansion-"+task["project"],task["project"]))
            self._event("project.accepted",{"project":task["project"],"task_id":task_id,"reviewer":reviewer})
            self._event("expansion.proposed",{"source_project":task["project"]})

    def approve_expansion(self,actor,eid):
        self._ceo(actor)
        with self.tx():
            e=self.db.execute("SELECT * FROM expansions WHERE id=?",(eid,)).fetchone()
            if not e or e["status"] not in {"proposed","costed"}:
                raise ValueError("Proposed expansion not found")
            self.db.execute("UPDATE expansions SET status='approved' WHERE id=?",(eid,))
            self._event("expansion.approved",{"id":eid,"actor":actor})

    def build_mock(self,contractor,eid):
        with self.tx():
            e=self.db.execute("SELECT * FROM expansions WHERE id=?",(eid,)).fetchone()
            if not e or e["status"]!="approved":
                raise ValueError("Approved expansion not found")
            self._scope(contractor,e["source_project"],"provision_room",0)
            self.db.execute("UPDATE expansions SET status='built',contractor=? WHERE id=?",(contractor,eid))
            self._event("room.built",{"id":eid,"contractor":contractor,"mock":True})

    def ingest_signal(self,*,source,title,published_at,observed_at,summary):
        from urllib.parse import urlparse
        if urlparse(source).scheme!="https" or not urlparse(source).netloc:
            raise ValueError("Evidence needs an HTTPS source URL")
        pub=datetime.fromisoformat(published_at);seen=datetime.fromisoformat(observed_at)
        if pub.tzinfo is None or seen.tzinfo is None or pub>seen or seen>now()+timedelta(minutes=5):
            raise ValueError("Invalid source timestamps")
        body=dict(source=source,title=title,published_at=published_at,observed_at=observed_at,summary=summary)
        fingerprint=digest({"source":source,"title":title,"published_at":published_at})
        sid=fingerprint[:24]
        status="stale" if now()-pub>timedelta(days=14) else "needs_review"
        with self.tx():
            if not self.db.execute("SELECT 1 FROM signals WHERE fingerprint=?",(fingerprint,)).fetchone():
                self.db.execute("INSERT INTO signals VALUES(?,?,?,?)",(sid,fingerprint,canonical(body),status))
                self._event("signal.ingested",{"id":sid,"status":status,"trusted_instruction":False})
        return sid

    def verify_audit(self):
        previous="0"*64
        for e in self.db.execute("SELECT * FROM events ORDER BY seq"):
            value={"at":e["at"],"kind":e["kind"],"body":json.loads(e["body"]),"previous":previous}
            if e["previous"]!=previous or e["hash"]!=digest(value):
                return False
            previous=e["hash"]
        return True

    def status(self):
        from company.finance import billed_adjustment_cents, billed_gross_cents, billed_net_cents
        counts={table:self.db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("tasks","completions","signals","events")}
        return {"mode":"offline_mock","policy_version":self.policy()["version"],**counts,
            "simulated_spend_cents":self.db.execute("SELECT COALESCE(SUM(cost),0) FROM ledger").fetchone()[0],
            "billed_cost_gross_cents":billed_gross_cents(self),
            "billed_adjustment_cents":billed_adjustment_cents(self),
            "billed_cost_cents":billed_net_cents(self),
            "revenue_cents":self.db.execute(
                "SELECT COALESCE(SUM(amount_cents),0) FROM revenue").fetchone()[0],
            "rooms":1+self.db.execute("SELECT COUNT(*) FROM expansions WHERE status='built'").fetchone()[0],
            "audit_valid":self.verify_audit()}

    def create_invoice(self, actor, period_start, period_end):
        from company.finance import create_invoice
        return create_invoice(self, actor, period_start, period_end)

    def list_invoices(self):
        from company.finance import list_invoices
        return list_invoices(self)

    def get_invoice(self, invoice_id):
        from company.finance import get_invoice
        return get_invoice(self, invoice_id)

    def post_finance_adjustment(self, actor, *, kind, billed_cost_id, reason,
                                amount_cents=None, invoice_id=None):
        from company.finance import post_adjustment
        return post_adjustment(
            self, actor, kind=kind, billed_cost_id=billed_cost_id, reason=reason,
            amount_cents=amount_cents, invoice_id=invoice_id)

    def list_finance_adjustments(self):
        from company.finance import list_adjustments
        return list_adjustments(self)

    def finance_summary(self):
        from company.finance import finance_summary
        return finance_summary(self)

    def list_budget_periods_finance(self):
        from company.finance import list_budget_periods
        return list_budget_periods(self)

    def close_budget_period(self, actor, period_id):
        from company.finance import close_budget_period
        return close_budget_period(self, actor, period_id)

    def create_worker_host(self, actor, *, label, base_url):
        from company.worker_hosts import create_worker_host
        return create_worker_host(self, actor, label=label, base_url=base_url)

    def list_worker_hosts(self):
        from company.worker_hosts import list_worker_hosts
        return list_worker_hosts(self)

    def set_worker_host_enabled(self, actor, host_id, enabled):
        from company.worker_hosts import set_worker_host_enabled
        return set_worker_host_enabled(self, actor, host_id, enabled)

    def delete_worker_host(self, actor, host_id):
        from company.worker_hosts import delete_worker_host
        return delete_worker_host(self, actor, host_id)

    def record_worker_host_heartbeat(self, host_id, token, meta=None):
        from company.worker_hosts import record_worker_host_heartbeat
        return record_worker_host_heartbeat(self, host_id, token, meta=meta)

    def remote_host_status_rows(self):
        from company.worker_hosts import remote_host_status_rows
        return remote_host_status_rows(self)

    def _check_period_budget(self,cost):
        stamp=now().isoformat()
        row=self.db.execute(
            "SELECT * FROM budget_periods WHERE period_start<=? AND period_end>? LIMIT 1",(stamp,stamp)).fetchone()
        if not row:return
        spent=self.db.execute("SELECT COALESCE(SUM(cost),0) FROM ledger").fetchone()[0]
        reserved=self.db.execute(
            "SELECT COALESCE(SUM(amount_cents),0) FROM reservations WHERE status='reserved'").fetchone()[0]
        if spent+reserved+cost>row["limit_cents"]:
            raise PermissionError("Period budget exceeded")

    def _hash_token(self,token):
        return hashlib.sha256(("fs-corporation-identity:"+token).encode()).hexdigest()

    def register_identity(self,principal_id,kind,token,scopes=None):
        if kind not in {"owner","service"}:raise ValueError("Unknown identity kind")
        if not token or not isinstance(token,str):raise ValueError("Token required")
        scopes=scopes or (["*"] if kind=="owner" else [])
        if kind!="owner" and "*" in scopes:raise ValueError("Service principals cannot have wildcard scopes")
        with self.tx():
            existing=self.db.execute("SELECT * FROM identities WHERE kind='owner'").fetchone()
            if kind=="owner" and existing and existing["principal_id"]!=principal_id:
                raise PermissionError("Root owner cannot be replaced by an agent")
            if self.db.execute("SELECT 1 FROM identities WHERE principal_id=?",(principal_id,)).fetchone():
                raise ValueError("Identity already registered")
            self.db.execute("INSERT INTO identities VALUES(?,?,?,?,?)",
                (principal_id,kind,self._hash_token(token),now().isoformat(),canonical(scopes)))
            self._event("identity.registered",{"principal_id":principal_id,"kind":kind},actor_id=principal_id)
        return principal_id

    def identity_for_token(self,token):
        if not token:return None
        row=self.db.execute("SELECT * FROM identities WHERE token_hash=?",(self._hash_token(token),)).fetchone()
        return dict(row) if row else None

    def rotate_owner_token(self, current_token, new_token=None, principal_id="human-ceo"):
        """Replace the owner bearer token. Returns the new plaintext token.

        Updates the identity hash transactionally. The caller must persist the
        new plaintext to the token file; this method never writes the filesystem.
        """
        import secrets
        if not current_token or not isinstance(current_token, str):
            raise ValueError("Current token required")
        ident = self.identity_for_token(current_token)
        if not ident or ident["kind"] != "owner":
            raise PermissionError("Current owner token is invalid")
        if ident["principal_id"] != principal_id:
            raise PermissionError("Root owner cannot be replaced by an agent")
        if new_token is None:
            new_token = secrets.token_urlsafe(32)
        if not new_token or not isinstance(new_token, str):
            raise ValueError("New token required")
        if new_token == current_token:
            raise ValueError("New token must differ from the current token")
        if self.identity_for_token(new_token):
            raise ValueError("New token is already registered")
        with self.tx():
            self.db.execute(
                "UPDATE identities SET token_hash=? WHERE principal_id=? AND kind='owner'",
                (self._hash_token(new_token), principal_id),
            )
            self._event(
                "identity.owner_token_rotated",
                {"principal_id": principal_id},
                actor_id=principal_id,
            )
        return new_token

    def require_scope(self,identity,scope):
        if not identity:raise PermissionError("Unauthenticated")
        if identity["kind"]=="owner":return
        raw=identity.get("scopes")
        if raw is None:
            raise PermissionError("Identity scopes missing")
        scopes=json.loads(raw) if isinstance(raw,str) else list(raw)
        if scope not in scopes:raise PermissionError("Missing scope")

    def reject_policy(self,actor,pid,reason):
        self._ceo_or_admin_companion(actor)
        if not reason or not str(reason).strip():raise ValueError("Decision rationale required")
        with self.tx():
            p=self.db.execute("SELECT * FROM proposals WHERE id=?",(pid,)).fetchone()
            if not p or p["status"]!="pending":raise ValueError("Pending proposal not found")
            self.db.execute("UPDATE proposals SET status='rejected' WHERE id=?",(pid,))
            self._event("policy.rejected",{"id":pid,"actor":actor,"reason":reason},actor_id=actor)

    def withdraw_policy(self,actor,pid):
        with self.tx():
            p=self.db.execute("SELECT * FROM proposals WHERE id=?",(pid,)).fetchone()
            if not p or p["status"]!="pending":raise ValueError("Pending proposal not found")
            if actor!=p["author"] and actor!=self.ceo:raise PermissionError("Only author or CEO may withdraw")
            self.db.execute("UPDATE proposals SET status='withdrawn' WHERE id=?",(pid,))
            self._event("policy.withdrawn",{"id":pid,"actor":actor},actor_id=actor)

    def rollback_policy(self,actor,target_version,reason):
        self._ceo(actor)
        if not reason or not str(reason).strip():raise ValueError("Amendment rationale required")
        with self.tx():
            row=self.db.execute("SELECT * FROM policies WHERE version=?",(target_version,)).fetchone()
            if not row:raise ValueError("Policy version not found")
            current=self.policy()
            restored=json.loads(row["body"])
            restored["version"]=current["version"]+1
            self.validate_policy(restored)
            self.db.execute("INSERT INTO policies VALUES(?,?)",(restored["version"],canonical(restored)))
            self._event("policy.rolled_back",{"from":current["version"],"restored":target_version,"actor":actor,"reason":reason},actor_id=actor)
            return restored["version"]

    def policy_diff(self,pid):
        p=self.db.execute("SELECT * FROM proposals WHERE id=?",(pid,)).fetchone()
        if not p:raise ValueError("Proposal not found")
        current=self.policy()
        proposed=json.loads(p["body"])
        return {"base":p["base"],"current_version":current["version"],"proposed_version":proposed["version"],
                "current":current,"proposed":proposed,
                "grant_added":sorted(set(proposed["grants"])-set(current["grants"])),
                "grant_removed":sorted(set(current["grants"])-set(proposed["grants"]))}

    def create_delegation(self,grantor,*,grantee,actions,projects,budget_cents,per_action_cents,expires_at,
                          requires_approval=None,approval_rights=None,can_redelegate=False,parent_id=None):
        if not grantee or grantee==grantor:raise ValueError("Invalid grantee")
        self._lists(actions,"actions");self._lists(projects,"projects")
        money(budget_cents);money(per_action_cents)
        requires_approval=requires_approval or []
        approval_rights=approval_rights or []
        self._lists(requires_approval,"requires_approval")
        self._lists(approval_rights,"approval_rights")
        stamp=datetime.fromisoformat(expires_at)
        if stamp.tzinfo is None:raise ValueError("Expiry needs a timezone")
        with self.tx():
            parent_row=None
            if parent_id:
                parent_row=self.db.execute("SELECT * FROM delegations WHERE id=?",(parent_id,)).fetchone()
                if not parent_row or parent_row["status"]!="active":raise ValueError("Parent delegation not found")
                if parent_row["grantee"]!=grantor:raise ValueError("Parent grantor mismatch")
                if not parent_row["can_redelegate"]:raise PermissionError("Redelegation is not permitted")
            depth=1;cursor=parent_id
            while cursor:
                depth+=1
                prow=self.db.execute("SELECT parent_id FROM delegations WHERE id=?",(cursor,)).fetchone()
                cursor=prow[0] if prow else None
            if depth>MAX_DELEGATION_DEPTH:raise PermissionError("Redelegation depth exceeded")
            if grantor!=self.ceo:
                g=self._effective_grant(grantor)
                if not g:raise PermissionError("Grantor has no authority")
                if not set(actions).issubset(g["actions"]) or not set(projects).issubset(g["projects"]):
                    raise PermissionError("Child exceeds parent scope")
                if budget_cents>g["budget_cents"] or per_action_cents>g["per_action_cents"]:
                    raise PermissionError("Child exceeds parent budget")
            did=str(uuid.uuid4())
            self.db.execute(
                "INSERT INTO delegations VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (did,grantor,grantee,parent_id,canonical(actions),canonical(projects),budget_cents,per_action_cents,
                 expires_at,canonical(requires_approval),canonical(approval_rights),1 if can_redelegate else 0,
                 "active",now().isoformat()))
            self._event("delegation.created",{"id":did,"grantor":grantor,"grantee":grantee},actor_id=grantor)
            return did

    @staticmethod
    def _lists(values,name):
        if not isinstance(values,list) or any(not isinstance(x,str) or not x or x=="*" for x in values):
            raise ValueError("Use explicit nonempty string scopes; wildcards are disallowed")

    def revoke_delegation(self,actor,did):
        with self.tx():
            row=self.db.execute("SELECT * FROM delegations WHERE id=?",(did,)).fetchone()
            if not row or row["status"]!="active":raise ValueError("Active delegation not found")
            if actor not in {self.ceo,row["grantor"]}:raise PermissionError("Cannot revoke this delegation")
            self.db.execute("UPDATE delegations SET status='revoked' WHERE id=?",(did,))
            children=list(self.db.execute("SELECT id FROM delegations WHERE parent_id=? AND status='active'",(did,)))
            stack=[r["id"] for r in children]
            while stack:
                cid=stack.pop()
                self.db.execute("UPDATE delegations SET status='revoked' WHERE id=?",(cid,))
                stack.extend(r["id"] for r in self.db.execute(
                    "SELECT id FROM delegations WHERE parent_id=? AND status='active'",(cid,)))
            self.db.execute("UPDATE queue SET status='cancelled' WHERE actor=? AND status='queued'",(row["grantee"],))
            self._event("delegation.revoked",{"id":did,"actor":actor},actor_id=actor)

    def queue_task(self,actor,project,action,cost,task_id):
        money(cost)
        with self.tx():
            self._require_project_skills(project)
            self._require_employee_training(actor)
            self._scope(actor,project,action,cost)
            if self.db.execute("SELECT 1 FROM queue WHERE task_id=?",(task_id,)).fetchone():
                row=self.db.execute("SELECT * FROM queue WHERE task_id=?",(task_id,)).fetchone()
                payload=json.loads(row["payload"])
                if (payload["actor"],payload["project"],payload["action"],payload["cost"])!=(actor,project,action,cost):
                    raise ValueError("Idempotency key reused with different payload")
                return dict(row)
            self.db.execute(
                "INSERT INTO queue VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (str(uuid.uuid4()),task_id,actor,project,action,cost,
                 canonical({"actor":actor,"project":project,"action":action,"cost":cost}),
                 None,None,0,"queued"))
            self._event("task.queued",{"task_id":task_id,"actor":actor},actor_id=actor,project_id=project)
            return dict(self.db.execute("SELECT * FROM queue WHERE task_id=?",(task_id,)).fetchone())

    def dispatch_queued(self,task_id,approval=None):
        row=self.db.execute("SELECT * FROM queue WHERE task_id=?",(task_id,)).fetchone()
        if not row:
            raise ValueError("Queued task not found")
        if row["status"]=="cancelled":
            raise PermissionError("Revoked or cancelled work cannot dispatch")
        if row["status"] not in {"queued","leased"}:
            raise ValueError("Queued task not found")
        payload=json.loads(row["payload"])
        result=self.execute_mock(actor=payload["actor"],project=payload["project"],action=payload["action"],
                                 cost=payload["cost"],task_id=task_id,approval=approval)
        with self.tx():
            self.db.execute("UPDATE queue SET status='done' WHERE task_id=?",(task_id,))
        return result

    def dispatch_queued_isolated(self,worker_id,task_id,scratch_root,approval=None,runtime="subprocess",
                                 worker_host_id=None, actor=None, placement="explicit"):
        if worker_host_id:
            from company.remote_jobs import enqueue_remote_job
            return enqueue_remote_job(
                self, actor or worker_id, host_id=worker_host_id, task_id=task_id,
                worker_id=worker_id, placement=placement)
        from .worker import ContainerWorkerRuntime, SubprocessWorkerRuntime
        row=self.db.execute("SELECT * FROM queue WHERE task_id=?",(task_id,)).fetchone()
        if not row:
            raise ValueError("Queued task not found")
        if row["status"]=="cancelled":
            raise PermissionError("Revoked or cancelled work cannot dispatch")
        if row["status"]=="leased" and row["lease_owner"]!=worker_id:
            raise PermissionError("Task is leased to another worker")
        if runtime=="container":
            return ContainerWorkerRuntime().dispatch(self,worker_id,task_id,scratch_root,approval=approval)
        if runtime!="subprocess":
            raise ValueError("Unknown worker runtime")
        return SubprocessWorkerRuntime().dispatch(self,worker_id,task_id,scratch_root,approval=approval)

    def list_remote_host_jobs(self, host_id, token, status="queued"):
        from company.remote_jobs import list_host_jobs
        return list_host_jobs(self, host_id, token, status=status)

    def claim_remote_job(self, host_id, token, job_id):
        from company.remote_jobs import claim_job
        return claim_job(self, host_id, token, job_id)

    def gateway_remote_job(self, host_id, token, job_id, message):
        from company.remote_jobs import relay_gateway
        return relay_gateway(self, host_id, token, job_id, message)

    def renew_remote_job(self, host_id, token, job_id):
        from company.remote_jobs import renew_job_lease
        return renew_job_lease(self, host_id, token, job_id)

    def complete_remote_job(self, host_id, token, job_id, *, status, result=None, runtime=None):
        from company.remote_jobs import complete_job
        return complete_job(
            self, host_id, token, job_id, status=status, result=result, runtime=runtime
        )

    def _start_worker_run(self,worker_id,task_id,runtime,scratch_root):
        rid=str(uuid.uuid4())
        with self.tx():
            self.db.execute(
                "INSERT INTO worker_runs VALUES(?,?,?,?,?,?,?,?)",
                (rid,worker_id,task_id,runtime,scratch_root,"running",now().isoformat(),None))
            self._event("worker.started",{"run_id":rid,"worker":worker_id,"task_id":task_id,"runtime":runtime})
        return rid

    def _finish_worker_run(self,run_id,status):
        if status not in {"completed","failed"}:
            raise ValueError("Invalid worker run status")
        with self.tx():
            self.db.execute("UPDATE worker_runs SET status=?, finished_at=? WHERE id=?",(status,now().isoformat(),run_id))
            self._event("worker.finished",{"run_id":run_id,"status":status})

    def mark_worker_completed(self, run_id, task_id, worker_id, runtime):
        """Finish the run, mark the queue done, and emit completion in one transaction."""
        with self.tx():
            self.db.execute(
                "UPDATE worker_runs SET status=?, finished_at=? WHERE id=?",
                ("completed", now().isoformat(), run_id))
            self._event("worker.finished", {"run_id": run_id, "status": "completed"})
            self.db.execute("UPDATE queue SET status='done' WHERE task_id=?", (task_id,))
            self._event(
                "task.worker_completed",
                {"task_id": task_id, "worker": worker_id, "runtime": runtime})

    def claim_lease(self,worker_id,task_id,seconds=30):
        until=(now()+timedelta(seconds=seconds)).isoformat()
        with self.tx():
            row=self.db.execute("SELECT * FROM queue WHERE task_id=?",(task_id,)).fetchone()
            if not row or row["status"]!="queued":raise ValueError("Task is not available to lease")
            self.db.execute(
                "UPDATE queue SET status='leased',lease_owner=?,lease_until=?,attempts=attempts+1 WHERE task_id=?",
                (worker_id,until,task_id))
            self._event("task.leased",{"task_id":task_id,"worker":worker_id})
        return until

    def cancel_queued(self,actor,task_id):
        self._ceo(actor)
        with self.tx():
            row=self.db.execute("SELECT * FROM queue WHERE task_id=?",(task_id,)).fetchone()
            if not row:raise ValueError("Queued task not found")
            self.db.execute("UPDATE queue SET status='cancelled' WHERE task_id=?",(task_id,))
            self._event("task.cancelled",{"task_id":task_id,"actor":actor},actor_id=actor)

    def outbox_add(self,kind,payload):
        oid=str(uuid.uuid4())
        with self.tx():
            self.db.execute("INSERT INTO outbox VALUES(?,?,?,?,?)",
                            (oid,kind,canonical(payload),"pending",now().isoformat()))
        return oid

    def outbox_pending(self):
        return [dict(r) for r in self.db.execute("SELECT * FROM outbox WHERE status='pending' ORDER BY created_at")]

    def outbox_mark(self,oid,status):
        if status not in {"sent","failed"}:raise ValueError("Invalid outbox status")
        with self.tx():
            self.db.execute("UPDATE outbox SET status=? WHERE id=?",(status,oid))

    def reserve_budget(self,actor,project,action,cost,task_id):
        with self.tx():
            self._scope(actor,project,action,cost)
            if self.db.execute("SELECT 1 FROM reservations WHERE task_id=?",(task_id,)).fetchone():
                row=self.db.execute("SELECT * FROM reservations WHERE task_id=?",(task_id,)).fetchone()
                if row["amount_cents"]!=cost or row["actor"]!=actor:
                    raise ValueError("Idempotency key reused with different payload")
                return dict(row)
            rid=str(uuid.uuid4())
            self.db.execute("INSERT INTO reservations VALUES(?,?,?,?,?,?)",
                            (rid,task_id,actor,cost,"reserved",now().isoformat()))
            self._event("budget.reserved",{"id":rid,"task_id":task_id,"cost":cost},actor_id=actor,project_id=project)
            return dict(self.db.execute("SELECT * FROM reservations WHERE id=?",(rid,)).fetchone())

    def capture_reservation(self,task_id):
        with self.tx():
            row=self.db.execute("SELECT * FROM reservations WHERE task_id=?",(task_id,)).fetchone()
            if not row or row["status"]!="reserved":raise ValueError("Reservation not found")
            self.db.execute("UPDATE reservations SET status='captured' WHERE task_id=?",(task_id,))
            self._event("cost.reconciled",{"task_id":task_id,"amount":row["amount_cents"]})

    def release_reservation(self,task_id):
        with self.tx():
            row=self.db.execute("SELECT * FROM reservations WHERE task_id=?",(task_id,)).fetchone()
            if not row or row["status"]!="reserved":raise ValueError("Reservation not found")
            self.db.execute("UPDATE reservations SET status='released' WHERE task_id=?",(task_id,))
            self._event("budget.released",{"task_id":task_id})

    def store_artifact(self,producer,task_id,project,content,root):
        root=Path(root);root.mkdir(parents=True,exist_ok=True)
        raw=content if isinstance(content,bytes) else content.encode()
        digest_hex=hashlib.sha256(raw).hexdigest()
        path=root/f"{digest_hex}.bin"
        if not path.exists():path.write_bytes(raw)
        with self.tx():
            if not self.db.execute("SELECT 1 FROM artifacts WHERE hash=?",(digest_hex,)).fetchone():
                self.db.execute("INSERT INTO artifacts VALUES(?,?,?,?,?,?,?)",
                    (str(uuid.uuid4()),digest_hex,str(path),producer,task_id,project,now().isoformat()))
                self._event("artifact.created",{"hash":digest_hex,"task_id":task_id},actor_id=producer,project_id=project)
        return digest_hex

    def accept_artifact(self,reviewer,task_id,artifact_hash):
        return self.accept_project(reviewer,task_id,artifact_hash)

    def gateway_check(self,actor,project,action,cost,task_id,target=None):
        """Recheck authority immediately before an external effect. Performs no I/O."""
        p,g=self._scope(actor,project,action,cost)
        if target and target.get("repo_id"):
            self.authorize_github_effect(project,action,target["repo_id"],target.get("branch",""),
                                         head_sha=target.get("head_sha"),expected_sha=target.get("expected_sha"),
                                         path=target.get("path"))
        return {"allow":True,"policy_version":p["version"],"reason":"allow"}

    def invoke_model(self,profile_id,prompt,registry):
        profiles=registry["profiles"]
        if profile_id not in profiles:raise LookupError("Unknown profile")
        profile=profiles[profile_id]
        if not profile.get("enabled"):raise PermissionError("Profile is disabled")
        if not isinstance(prompt,str):raise ValueError("Prompt required")
        provider=profile.get("provider")
        if provider=="mock":
            return {"text":"mock-provider-output","profile_id":profile_id,"cost_cents":0,"provider":"mock"}
        from .model_provider import LIVE_PROVIDERS, complete, _credential_env
        if provider in LIVE_PROVIDERS:
            env_name = _credential_env(profile)
            if not (os.environ.get(env_name) or "").strip():
                raise NotImplementedError(
                    f"Live model requires {env_name} inside the worker boundary; see docs/06-model-routing.md")
            result = complete(
                profile_id,
                profile,
                prompt,
                default_rate=self.effective_setting(
                    "FS_CORP_MODEL_CENTS_PER_1K_TOKENS"
                ),
            )
            usage_tokens = result.get("usage_tokens", 0)
            if type(usage_tokens) is not int or usage_tokens < 0:
                raise ValueError("usage_tokens must be a nonnegative int")
            amount_cents = money(result.get("cost_cents", 0))
            with self.tx():
                bid = str(uuid.uuid4())
                self.db.execute(
                    "INSERT INTO billed_costs VALUES(?,?,?,?,?,?,?,?)",
                    (bid, now().isoformat(), amount_cents, usage_tokens,
                     str(result.get("provider") or provider), profile_id, "invoke_model", None))
                self._event("cost.billed", {
                    "id": bid, "amount_cents": amount_cents, "usage_tokens": usage_tokens,
                    "profile_id": profile_id, "provider": result.get("provider") or provider,
                })
            return result
        raise NotImplementedError(
            f"Live model provider {provider!r} is not configured; "
            f"use provider 'mock', 'openai', 'anthropic', or 'configure-provider' with credentials; "
            "see docs/06-model-routing.md")

    def record_revenue(self, actor, amount_cents, source, note=""):
        self._ceo(actor)
        if not isinstance(source, str) or not source.strip():
            raise ValueError("source required")
        if not isinstance(note, str):
            raise ValueError("note must be a string")
        amount = money(amount_cents)
        with self.tx():
            rid = str(uuid.uuid4())
            self.db.execute(
                "INSERT INTO revenue VALUES(?,?,?,?,?)",
                (rid, now().isoformat(), amount, source.strip(), note))
            self._event("revenue.recorded", {
                "id": rid, "amount_cents": amount, "source": source.strip(),
            }, actor_id=actor)
        return rid

    def seed_catalog(self,departments_path):
        data=json.loads(Path(departments_path).read_text())
        created=updated=preserved=0
        with self.tx():
            for idx, d in enumerate(data["departments"]):
                existing = self.db.execute(
                    "SELECT id, origin, updated_by, name FROM departments WHERE id=?",
                    (d["id"],)).fetchone()
                seat_status = "vacant" if d["initially_active"] else "dormant"
                dept_status = "active" if d["initially_active"] else "dormant"
                if existing and (existing["origin"] == "custom" or existing["updated_by"]):
                    preserved += 1
                else:
                    if existing:
                        updated += 1
                        self.db.execute(
                            """UPDATE departments SET name=?, head_title=?, mission=?, measures=?,
                               room_type=?, initially_active=?, default_model_profile=?, body=?,
                               origin='seed', status=?, display_order=?
                               WHERE id=? AND (updated_by IS NULL OR updated_by='')""",
                            (d["name"], d["head"], d["mission"], canonical(d["measures"]),
                             d["room_type"], 1 if d["initially_active"] else 0,
                             d["default_model_profile"], canonical(d), dept_status, idx, d["id"]))
                    else:
                        created += 1
                        self.db.execute(
                            """INSERT INTO departments(
                                   id,name,head_title,mission,measures,room_type,initially_active,
                                   default_model_profile,body,origin,status,display_order,
                                   parent_department_id,updated_at,updated_by)
                               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (d["id"], d["name"], d["head"], d["mission"], canonical(d["measures"]),
                             d["room_type"], 1 if d["initially_active"] else 0,
                             d["default_model_profile"], canonical(d), "seed", dept_status, idx,
                             None, None, None))
                seat_id = f"seat:{d['id']}"
                seat = self.db.execute(
                    "SELECT id, principal_id, status FROM department_seats WHERE department_id=?",
                    (d["id"],)).fetchone()
                if not seat:
                    self.db.execute(
                        "INSERT INTO department_seats VALUES(?,?,?,?,?,?,?,?)",
                        (seat_id, d["id"], None, d["head"], seat_status, None, None, None))
                elif seat["principal_id"] is None and seat["status"] in {"vacant", "dormant"}:
                    self.db.execute(
                        "UPDATE department_seats SET title=?, status=? WHERE department_id=?",
                        (d["head"], seat_status, d["id"]))
                for pidx, title in enumerate(d["positions"]):
                    pid = f"{d['id']}:{title}"
                    pos = self.db.execute(
                        "SELECT id, status FROM positions WHERE id=?", (pid,)).fetchone()
                    if not pos:
                        self.db.execute(
                            """INSERT INTO positions(id,department_id,title,status,display_order,updated_at)
                               VALUES(?,?,?,?,?,?)""",
                            (pid, d["id"], title, "active", pidx, None))
                    elif pos["status"] != "retired":
                        self.db.execute(
                            """UPDATE positions SET title=?, display_order=? WHERE id=? AND status!='retired'""",
                            (title, pidx, pid))
            requirements_path = Path(departments_path).with_name("room-requirements.json")
            if requirements_path.exists():
                requirements = json.loads(requirements_path.read_text())
                for department_id, requirement in requirements.items():
                    self.db.execute(
                        """INSERT OR REPLACE INTO room_requirements(
                               department_id,required_room_type,min_capacity)
                           SELECT ?,?,? WHERE EXISTS(
                               SELECT 1 FROM departments WHERE id=?)""",
                        (department_id, requirement["required_room_type"],
                         requirement["min_capacity"], department_id))
            self._event("catalog.seeded", {
                "departments": len(data["departments"]),
                "created": created, "updated": updated, "preserved": preserved,
            })

    def _department_row(self, department_id):
        row = self.db.execute("SELECT * FROM departments WHERE id=?", (department_id,)).fetchone()
        if not row:
            raise ValueError("Unknown department")
        return dict(row)

    def _record_department_revision(self, department_id, actor, reason):
        body = self._department_row(department_id)
        version = 1 + (self.db.execute(
            "SELECT COALESCE(MAX(version),0) FROM department_revisions WHERE department_id=?",
            (department_id,)).fetchone()[0])
        rid = str(uuid.uuid4())
        self.db.execute(
            "INSERT INTO department_revisions VALUES(?,?,?,?,?,?,?)",
            (rid, department_id, version, canonical(body), actor, now().isoformat(),
             (reason or "").strip() or "update"))

    def create_department(self, actor, *, department_id, name, head_title, mission, measures,
                          room_type, initially_active, default_model_profile="mock-text",
                          parent_department_id=None, display_order=None):
        self._ceo_or_admin_companion(actor)
        department_id = str(department_id or "").strip()
        if not department_id or not name or not head_title or not mission or not room_type:
            raise ValueError("id, name, head_title, mission and room_type required")
        if not isinstance(measures, list):
            raise ValueError("measures must be a list")
        if parent_department_id and not self.db.execute(
                "SELECT 1 FROM departments WHERE id=?", (parent_department_id,)).fetchone():
            raise ValueError("Unknown parent_department_id")
        if self.db.execute("SELECT 1 FROM departments WHERE id=?", (department_id,)).fetchone():
            raise ValueError("Department already exists")
        status = "active" if initially_active else "dormant"
        seat_status = "vacant" if initially_active else "dormant"
        if display_order is None:
            display_order = 1 + (self.db.execute(
                "SELECT COALESCE(MAX(display_order),-1) FROM departments").fetchone()[0])
        stamp = now().isoformat()
        body = {
            "id": department_id, "name": name, "head": head_title, "mission": mission,
            "measures": measures, "room_type": room_type,
            "initially_active": bool(initially_active),
            "default_model_profile": default_model_profile,
        }
        with self.tx():
            self.db.execute(
                """INSERT INTO departments(
                       id,name,head_title,mission,measures,room_type,initially_active,
                       default_model_profile,body,origin,status,display_order,
                       parent_department_id,updated_at,updated_by)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (department_id, name.strip(), head_title.strip(), mission.strip(),
                 canonical(measures), room_type.strip(), 1 if initially_active else 0,
                 default_model_profile, canonical(body), "custom", status, int(display_order),
                 parent_department_id, stamp, actor))
            self.db.execute(
                "INSERT INTO department_seats VALUES(?,?,?,?,?,?,?,?)",
                (f"seat:{department_id}", department_id, None, head_title.strip(),
                 seat_status, None, None, None))
            self._record_department_revision(department_id, actor, "created")
            self._event("org.department_created", {"id": department_id}, actor_id=actor)
        return self._department_row(department_id)

    def update_department(self, actor, department_id, *, reason="update", **fields):
        self._ceo_or_admin_companion(actor)
        row = self._department_row(department_id)
        if row.get("status") == "retired":
            raise ValueError("Cannot update retired department")
        allowed = {
            "name", "head_title", "mission", "measures", "room_type",
            "initially_active", "default_model_profile", "parent_department_id",
            "display_order", "status",
        }
        unknown = set(fields) - allowed
        if unknown:
            raise ValueError(f"Unknown fields: {sorted(unknown)}")
        if not fields:
            raise ValueError("No fields to update")
        if "parent_department_id" in fields and fields["parent_department_id"]:
            if fields["parent_department_id"] == department_id:
                raise ValueError("Department cannot parent itself")
            if not self.db.execute(
                    "SELECT 1 FROM departments WHERE id=?",
                    (fields["parent_department_id"],)).fetchone():
                raise ValueError("Unknown parent_department_id")
        if "status" in fields and fields["status"] not in {"active", "dormant"}:
            raise ValueError("status must be active or dormant")
        stamp = now().isoformat()
        with self.tx():
            name = fields.get("name", row["name"])
            head_title = fields.get("head_title", row["head_title"])
            mission = fields.get("mission", row["mission"])
            measures = fields.get("measures", json.loads(row["measures"]))
            if not isinstance(measures, list):
                raise ValueError("measures must be a list")
            room_type = fields.get("room_type", row["room_type"])
            initially_active = fields.get(
                "initially_active", bool(row["initially_active"]))
            default_model_profile = fields.get(
                "default_model_profile", row["default_model_profile"])
            parent_department_id = fields.get(
                "parent_department_id", row["parent_department_id"])
            display_order = fields.get("display_order", row["display_order"])
            status = fields.get("status", row["status"])
            body = {
                "id": department_id, "name": name, "head": head_title, "mission": mission,
                "measures": measures, "room_type": room_type,
                "initially_active": bool(initially_active),
                "default_model_profile": default_model_profile,
            }
            self.db.execute(
                """UPDATE departments SET name=?, head_title=?, mission=?, measures=?,
                   room_type=?, initially_active=?, default_model_profile=?, body=?,
                   status=?, display_order=?, parent_department_id=?,
                   updated_at=?, updated_by=? WHERE id=?""",
                (name, head_title, mission, canonical(measures), room_type,
                 1 if initially_active else 0, default_model_profile, canonical(body),
                 status, int(display_order), parent_department_id, stamp, actor,
                 department_id))
            if "head_title" in fields:
                self.db.execute(
                    """UPDATE department_seats SET title=?
                       WHERE department_id=? AND principal_id IS NULL""",
                    (head_title, department_id))
            self._record_department_revision(department_id, actor, reason)
            self._event("org.department_updated", {"id": department_id}, actor_id=actor)
        return self._department_row(department_id)

    def retire_department(self, actor, department_id):
        self._ceo_or_admin_companion(actor)
        self._department_row(department_id)
        seat = self.db.execute(
            "SELECT principal_id, status FROM department_seats WHERE department_id=?",
            (department_id,)).fetchone()
        if seat and seat["status"] == "active" and seat["principal_id"]:
            raise ValueError("Cannot retire department with active seat")
        if self.db.execute(
                """SELECT 1 FROM position_assignments
                   WHERE department_id=? AND status='active'""",
                (department_id,)).fetchone():
            raise ValueError("Cannot retire department with active assignments")
        if self.db.execute(
                """SELECT 1 FROM project_dispatches
                   WHERE department_id=? AND status IN (
                       'queued_for_head','assigned','in_progress','blocked','blocked_vacant_head')""",
                (department_id,)).fetchone():
            raise ValueError("Cannot retire department with open dispatches")
        if self.db.execute(
                """SELECT 1 FROM cross_department_requests
                   WHERE status NOT IN ('accepted','rejected','closed','cancelled')
                     AND (requesting_department_id=? OR delivering_department_id=?)""",
                (department_id, department_id)).fetchone():
            raise ValueError("Cannot retire department with open cross-department requests")
        with self.tx():
            self.db.execute(
                """UPDATE departments SET status='retired', updated_at=?, updated_by=?
                   WHERE id=?""",
                (now().isoformat(), actor, department_id))
            self._record_department_revision(department_id, actor, "retired")
            self._event("org.department_retired", {"id": department_id}, actor_id=actor)
        return self._department_row(department_id)

    def create_position(self, actor, *, department_id, title, display_order=None):
        self._ceo_or_admin_companion(actor)
        dept = self._department_row(department_id)
        if dept.get("status") == "retired":
            raise ValueError("Cannot add position to retired department")
        title = str(title or "").strip()
        if not title:
            raise ValueError("title required")
        position_id = f"{department_id}:{title}"
        if self.db.execute("SELECT 1 FROM positions WHERE id=?", (position_id,)).fetchone():
            raise ValueError("Position already exists")
        if display_order is None:
            display_order = 1 + (self.db.execute(
                "SELECT COALESCE(MAX(display_order),-1) FROM positions WHERE department_id=?",
                (department_id,)).fetchone()[0])
        stamp = now().isoformat()
        with self.tx():
            self.db.execute(
                """INSERT INTO positions(id,department_id,title,status,display_order,updated_at)
                   VALUES(?,?,?,?,?,?)""",
                (position_id, department_id, title, "active", int(display_order), stamp))
            self._event(
                "org.position_created",
                {"id": position_id, "department_id": department_id},
                actor_id=actor,
            )
        return dict(self.db.execute(
            "SELECT * FROM positions WHERE id=?", (position_id,)).fetchone())

    def update_position(self, actor, position_id, *, title=None, display_order=None, status=None):
        self._ceo_or_admin_companion(actor)
        row = self.db.execute("SELECT * FROM positions WHERE id=?", (position_id,)).fetchone()
        if not row:
            raise ValueError("Unknown position")
        if row["status"] == "retired" and status != "active":
            raise ValueError("Cannot update retired position")
        new_title = title.strip() if title is not None else row["title"]
        if not new_title:
            raise ValueError("title required")
        new_id = f"{row['department_id']}:{new_title}"
        new_order = row["display_order"] if display_order is None else int(display_order)
        new_status = status or row["status"]
        if new_status not in {"active", "retired"}:
            raise ValueError("status must be active or retired")
        stamp = now().isoformat()
        with self.tx():
            if new_id != position_id:
                if self.db.execute("SELECT 1 FROM positions WHERE id=?", (new_id,)).fetchone():
                    raise ValueError("Position already exists")
                self.db.execute(
                    """UPDATE position_assignments SET position_id=? WHERE position_id=?""",
                    (new_id, position_id))
                self.db.execute("DELETE FROM positions WHERE id=?", (position_id,))
                self.db.execute(
                    """INSERT INTO positions(id,department_id,title,status,display_order,updated_at)
                       VALUES(?,?,?,?,?,?)""",
                    (new_id, row["department_id"], new_title, new_status, new_order, stamp))
                position_id = new_id
            else:
                self.db.execute(
                    """UPDATE positions SET title=?, display_order=?, status=?, updated_at=?
                       WHERE id=?""",
                    (new_title, new_order, new_status, stamp, position_id))
            self._event("org.position_updated", {"id": position_id}, actor_id=actor)
        return dict(self.db.execute(
            "SELECT * FROM positions WHERE id=?", (position_id,)).fetchone())

    def retire_position(self, actor, position_id):
        return self.update_position(actor, position_id, status="retired")

    def reorder_departments(self, actor, items):
        self._ceo_or_admin_companion(actor)
        if not isinstance(items, list) or not items:
            raise ValueError("items required")
        with self.tx():
            for item in items:
                dept_id = item.get("id")
                order = item.get("display_order")
                if not dept_id or order is None:
                    raise ValueError("id and display_order required")
                if not self.db.execute(
                        "SELECT 1 FROM departments WHERE id=?", (dept_id,)).fetchone():
                    raise ValueError(f"Unknown department {dept_id}")
                self.db.execute(
                    """UPDATE departments SET display_order=?, updated_at=?, updated_by=?
                       WHERE id=?""",
                    (int(order), now().isoformat(), actor, dept_id))
            self._event(
                "org.departments_reordered",
                {"count": len(items)},
                actor_id=actor,
            )
        return self.list_org()

    def appoint_head(self, actor, department_id, principal_id):
        self._ceo_or_admin_companion(actor)
        if not principal_id or not str(principal_id).strip():
            raise ValueError("principal_id required")
        dept = self.db.execute(
            "SELECT id, head_title, status FROM departments WHERE id=?",
            (department_id,),
        ).fetchone()
        if not dept:
            raise ValueError("Unknown department")
        if dept["status"] == "retired":
            raise ValueError("Cannot appoint head for retired department")
        principal_id = str(principal_id).strip()
        with self.tx():
            seat = self.db.execute(
                "SELECT id FROM department_seats WHERE department_id=?",
                (department_id,),
            ).fetchone()
            if not seat:
                raise ValueError("Seat missing; seed catalog first")
            self.db.execute(
                """UPDATE department_seats
                   SET principal_id=?, title=?, status='active', appointed_by=?,
                       appointed_at=?, vacated_at=NULL
                   WHERE department_id=?""",
                (principal_id, dept["head_title"], actor, now().isoformat(), department_id),
            )
            self._event(
                "org.head_appointed",
                {"department_id": department_id, "principal_id": principal_id},
                actor_id=actor,
            )
        return dict(self.db.execute(
            "SELECT * FROM department_seats WHERE department_id=?",
            (department_id,),
        ).fetchone())

    def vacate_head(self, actor, department_id):
        self._ceo_or_admin_companion(actor)
        dept = self.db.execute(
            "SELECT id, initially_active, status FROM departments WHERE id=?",
            (department_id,),
        ).fetchone()
        if not dept:
            raise ValueError("Unknown department")
        with self.tx():
            seat = self.db.execute(
                "SELECT principal_id FROM department_seats WHERE department_id=?",
                (department_id,),
            ).fetchone()
            if not seat:
                raise ValueError("Seat missing; seed catalog first")
            if seat["principal_id"]:
                self.db.execute(
                    "UPDATE queue SET status='cancelled' WHERE actor=? AND status='queued'",
                    (seat["principal_id"],),
                )
            self.db.execute(
                """UPDATE queue SET status='cancelled'
                   WHERE status IN ('queued', 'leased') AND task_id IN (
                       SELECT da.queue_task_id
                       FROM dispatch_assignments da
                       JOIN project_dispatches pd ON pd.id=da.dispatch_id
                       WHERE pd.department_id=? AND da.queue_task_id IS NOT NULL
                   )""",
                (department_id,),
            )
            self.db.execute(
                """UPDATE dispatch_assignments SET status='cancelled'
                   WHERE dispatch_id IN (
                       SELECT id FROM project_dispatches WHERE department_id=?
                   ) AND status='assigned'""",
                (department_id,),
            )
            self.db.execute(
                """UPDATE project_dispatches
                   SET status='blocked_vacant_head', head_principal_id=NULL,
                       head_inbox_at=NULL
                   WHERE department_id=? AND head_principal_id=?
                     AND status='queued_for_head'""",
                (department_id, seat["principal_id"]),
            )
            status = "vacant" if dept["initially_active"] else "dormant"
            self.db.execute(
                """UPDATE department_seats
                   SET principal_id=NULL, status=?, vacated_at=?
                   WHERE department_id=?""",
                (status, now().isoformat(), department_id),
            )
            self._event(
                "org.head_vacated",
                {"department_id": department_id},
                actor_id=actor,
            )
        return dict(self.db.execute(
            "SELECT * FROM department_seats WHERE department_id=?",
            (department_id,),
        ).fetchone())

    def assign_position(self, actor, position_id, principal_id, reports_to_seat_id=None):
        self._ceo_or_admin_companion(actor)
        position = self.db.execute(
            "SELECT id, department_id, status FROM positions WHERE id=?",
            (position_id,),
        ).fetchone()
        if not position:
            raise ValueError("Unknown position")
        if position["status"] == "retired":
            raise ValueError("Cannot assign retired position")
        if not principal_id or not str(principal_id).strip():
            raise ValueError("principal_id required")
        if reports_to_seat_id and not self.db.execute(
                "SELECT id FROM department_seats WHERE id=?",
                (reports_to_seat_id,),
        ).fetchone():
            raise ValueError("Unknown reports_to_seat_id")
        assignment_id = str(uuid.uuid4())
        principal_id = str(principal_id).strip()
        with self.tx():
            self.db.execute(
                """INSERT INTO position_assignments(
                       id, position_id, department_id, principal_id, status,
                       reports_to_seat_id, assigned_by, assigned_at, released_at)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    assignment_id,
                    position_id,
                    position["department_id"],
                    principal_id,
                    "active",
                    reports_to_seat_id,
                    actor,
                    now().isoformat(),
                    None,
                ),
            )
            self._event(
                "org.position_assigned",
                {
                    "id": assignment_id,
                    "position_id": position_id,
                    "principal_id": principal_id,
                },
                actor_id=actor,
            )
        return dict(self.db.execute(
            "SELECT * FROM position_assignments WHERE id=?",
            (assignment_id,),
        ).fetchone())

    def release_position(self, actor, assignment_id):
        self._ceo_or_admin_companion(actor)
        with self.tx():
            assignment = self.db.execute(
                "SELECT id FROM position_assignments WHERE id=? AND status='active'",
                (assignment_id,),
            ).fetchone()
            if not assignment:
                raise ValueError("Active assignment not found")
            self.db.execute(
                """UPDATE position_assignments
                   SET status='released', released_at=?
                   WHERE id=?""",
                (now().isoformat(), assignment_id),
            )
            self._event(
                "org.position_released",
                {"id": assignment_id},
                actor_id=actor,
            )
        return dict(self.db.execute(
            "SELECT * FROM position_assignments WHERE id=?",
            (assignment_id,),
        ).fetchone())

    def list_org(self):
        departments = []
        for department in self.db.execute(
                """SELECT id, name, head_title, mission, room_type, initially_active,
                          origin, status, display_order, parent_department_id,
                          updated_at, updated_by
                   FROM departments
                   WHERE COALESCE(status, 'active') != 'retired'
                   ORDER BY COALESCE(display_order, 0), id"""):
            seat = self.db.execute(
                "SELECT * FROM department_seats WHERE department_id=?",
                (department["id"],),
            ).fetchone()
            assignments = [
                dict(row)
                for row in self.db.execute(
                    """SELECT * FROM position_assignments
                       WHERE department_id=? AND status='active'
                       ORDER BY assigned_at""",
                    (department["id"],),
                )
            ]
            positions = [
                dict(row)
                for row in self.db.execute(
                    """SELECT id, department_id, title, status, display_order
                       FROM positions WHERE department_id=? AND COALESCE(status,'active')!='retired'
                       ORDER BY COALESCE(display_order,0), title""",
                    (department["id"],),
                )
            ]
            departments.append({
                **dict(department),
                "origin": department["origin"] or "seed",
                "status": department["status"] or (
                    "active" if department["initially_active"] else "dormant"),
                "display_order": department["display_order"] or 0,
                "seat": dict(seat) if seat else {
                    "department_id": department["id"],
                    "principal_id": None,
                    "status": "vacant",
                    "title": department["head_title"],
                },
                "assignments": assignments,
                "positions": positions,
            })
        return {"departments": departments}

    def activate_department_for_project(self, actor, project_id, department_id):
        self._ceo_or_admin_companion(actor)
        if not self.db.execute(
                "SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone():
            raise ValueError("Project not found")
        dept = self.db.execute(
            "SELECT id, status FROM departments WHERE id=?", (department_id,)).fetchone()
        if not dept:
            raise ValueError("Unknown department")
        if dept["status"] == "retired":
            raise ValueError("Cannot activate retired department")
        with self.tx():
            self.db.execute(
                """INSERT OR REPLACE INTO project_department_activations
                   (project_id, department_id, activated_by, activated_at)
                   VALUES(?,?,?,?)""",
                (project_id, department_id, actor, now().isoformat()),
            )
            self._event(
                "org.department_activated",
                {"project_id": project_id, "department_id": department_id},
                actor_id=actor,
                project_id=project_id,
            )
        return {"project_id": project_id, "department_id": department_id}

    def department_dispatchable(self, project_id, department_id):
        department = self.db.execute(
            "SELECT initially_active, status FROM departments WHERE id=?",
            (department_id,),
        ).fetchone()
        if not department or department["status"] == "retired":
            return False
        if department["initially_active"]:
            return True
        return bool(self.db.execute(
            """SELECT 1 FROM project_department_activations
               WHERE project_id=? AND department_id=?""",
            (project_id, department_id),
        ).fetchone())

    def seed_models(self,models_path):
        data=json.loads(Path(models_path).read_text())
        with self.tx():
            for pid,body in data.get("profiles",{}).items():
                self.db.execute("INSERT OR REPLACE INTO model_profiles VALUES(?,?,?)",
                                (pid,canonical(body),1 if body.get("enabled") else 0))
            self._event("models.seeded",{"profiles":len(data.get("profiles",{}))})

    def list_model_profiles(self):
        rows = []
        for row in self.db.execute("SELECT id, body, enabled FROM model_profiles ORDER BY id"):
            body = json.loads(row["body"])
            rows.append({
                "id": row["id"],
                "enabled": bool(row["enabled"]),
                "body": body,
            })
        return rows

    def list_benchmark_results(self, role=None):
        if role:
            rows = self.db.execute(
                "SELECT * FROM benchmark_results WHERE role=? ORDER BY recorded_at, id",
                (role,),
            )
        else:
            rows = self.db.execute(
                "SELECT * FROM benchmark_results ORDER BY role, recorded_at, id",
            )
        return [dict(r) for r in rows]

    def choose_model(self, registry, department, position, capability, classification="public",
                     task_assignment=None, company_default=None, role=None):
        from company.routing import choose_model as route
        benches = self.list_benchmark_results(role=role) if role else None
        return route(
            registry, department, position, capability, classification,
            task_assignment=task_assignment, company_default=company_default,
            role=role, benchmarks=benches,
        )

    def list_work_order_replays(self, work_order_id):
        rows = self.db.execute(
            """SELECT * FROM work_order_replays WHERE work_order_id=?
               ORDER BY attempt, created_at""",
            (work_order_id,),
        )
        out = []
        for row in rows:
            item = dict(row)
            item["outcome"] = json.loads(item.pop("outcome_json"))
            out.append(item)
        return out

    def _next_replay_attempt(self, work_order_id):
        row = self.db.execute(
            "SELECT COALESCE(MAX(attempt),0) FROM work_order_replays WHERE work_order_id=?",
            (work_order_id,),
        ).fetchone()
        return int(row[0]) + 1

    def record_work_order_authorized(self, actor, work_order_id, workflow_digest, outcome=None):
        """First ledger row for a newly authorized work order."""
        self._ceo(actor)
        if not self.db.execute("SELECT 1 FROM work_orders WHERE id=?", (work_order_id,)).fetchone():
            raise ValueError("Work order not found")
        existing = self.db.execute(
            "SELECT id FROM work_order_replays WHERE work_order_id=? AND status='authorized'",
            (work_order_id,),
        ).fetchone()
        if existing:
            return dict(self.db.execute(
                "SELECT * FROM work_order_replays WHERE id=?", (existing["id"],)).fetchone())
        rid = str(uuid.uuid4())
        body = outcome if isinstance(outcome, dict) else {"status": "authorized"}
        with self.tx():
            self.db.execute(
                "INSERT INTO work_order_replays VALUES(?,?,?,?,?,?,?,?)",
                (rid, work_order_id, 1, workflow_digest, "authorized",
                 json.dumps(body), now().isoformat(), actor),
            )
            self._event("work_order.replay_authorized", {
                "id": rid, "work_order_id": work_order_id, "attempt": 1,
            }, actor_id=actor)
        return dict(self.db.execute("SELECT * FROM work_order_replays WHERE id=?", (rid,)).fetchone())

    def complete_work_order_outcome(self, actor, work_order_id, outcome):
        """Store a frozen outcome for later identical-digest replay."""
        self._ceo(actor)
        wo = self.db.execute("SELECT * FROM work_orders WHERE id=?", (work_order_id,)).fetchone()
        if not wo:
            raise ValueError("Work order not found")
        if not isinstance(outcome, dict):
            raise ValueError("outcome must be an object")
        attempt = self._next_replay_attempt(work_order_id)
        rid = str(uuid.uuid4())
        with self.tx():
            self.db.execute(
                "INSERT INTO work_order_replays VALUES(?,?,?,?,?,?,?,?)",
                (rid, work_order_id, attempt, wo["workflow_digest"], "completed",
                 json.dumps(outcome), now().isoformat(), actor),
            )
            self._event("work_order.replay_completed", {
                "id": rid, "work_order_id": work_order_id, "attempt": attempt,
            }, actor_id=actor)
        row = dict(self.db.execute("SELECT * FROM work_order_replays WHERE id=?", (rid,)).fetchone())
        row["outcome"] = json.loads(row.pop("outcome_json"))
        return row

    def replay_work_order(self, actor, work_order_id, workflow_digest):
        """Return prior frozen outcome for the same digest; append a replayed row."""
        self._ceo(actor)
        wo = self.db.execute("SELECT * FROM work_orders WHERE id=?", (work_order_id,)).fetchone()
        if not wo:
            raise ValueError("Work order not found")
        if wo["workflow_digest"] != workflow_digest:
            raise PermissionError("Workflow digest mismatch")
        prior = self.db.execute(
            """SELECT * FROM work_order_replays
               WHERE work_order_id=? AND workflow_digest=? AND status IN ('completed','replayed','authorized')
               ORDER BY attempt DESC LIMIT 1""",
            (work_order_id, workflow_digest),
        ).fetchone()
        if not prior:
            raise ValueError("No replayable outcome for work order")
        outcome = json.loads(prior["outcome_json"])
        # Prefer a completed outcome if one exists
        completed = self.db.execute(
            """SELECT * FROM work_order_replays
               WHERE work_order_id=? AND workflow_digest=? AND status='completed'
               ORDER BY attempt DESC LIMIT 1""",
            (work_order_id, workflow_digest),
        ).fetchone()
        if completed:
            outcome = json.loads(completed["outcome_json"])
        attempt = self._next_replay_attempt(work_order_id)
        rid = str(uuid.uuid4())
        with self.tx():
            self.db.execute(
                "INSERT INTO work_order_replays VALUES(?,?,?,?,?,?,?,?)",
                (rid, work_order_id, attempt, workflow_digest, "replayed",
                 json.dumps(outcome), now().isoformat(), actor),
            )
            self._event("work_order.replayed", {
                "id": rid, "work_order_id": work_order_id, "attempt": attempt,
            }, actor_id=actor)
        return {"replay": True, "work_order_id": work_order_id, "attempt": attempt, "outcome": outcome}

    def seed_benchmarks(self, path):
        data = json.loads(Path(path).read_text())
        items = data.get("benchmarks") or []
        ids = []
        for item in items:
            bid = self.record_benchmark(
                item["role"],
                item["profile_id"],
                item["quality"],
                item["latency_ms"],
                item["cost_cents"],
                item["failure_rate"],
            )
            ids.append(bid)
        return {"count": len(ids), "ids": ids}

    def assign_model(self,actor,scope_kind,scope_id,profile_id):
        self._ceo(actor)
        if scope_kind not in {"company","department","position","task"}:raise ValueError("Unknown assignment scope")
        with self.tx():
            version=1+(self.db.execute(
                "SELECT COALESCE(MAX(version),0) FROM model_assignments WHERE scope_kind=? AND scope_id=?",
                (scope_kind,scope_id)).fetchone()[0])
            aid=str(uuid.uuid4())
            self.db.execute("INSERT INTO model_assignments VALUES(?,?,?,?,?,?)",
                            (aid,scope_kind,scope_id,profile_id,version,now().isoformat()))
            self._event("model.assigned",{"id":aid,"scope_kind":scope_kind,"scope_id":scope_id,"profile_id":profile_id},actor_id=actor)
            return aid

    def enroll_project(self,actor,project_id,brief,classification="internal"):
        self._ceo_or_admin_companion(actor)
        if classification not in {"public","internal","restricted"}:raise ValueError("Unknown data classification")
        if not project_id or not brief.strip():raise ValueError("Project id and brief required")
        with self.tx():
            if self.db.execute("SELECT 1 FROM projects WHERE id=?",(project_id,)).fetchone():
                return project_id
            self.db.execute("INSERT INTO projects VALUES(?,?,?,?,?,?,?)",
                            (project_id,brief,classification,None,None,canonical([]),now().isoformat()))
            self._event("project.enrolled",{"id":project_id},actor_id=actor,project_id=project_id)
        return project_id

    def enroll_github(self,actor,project_id,upstream_repo_id,fork_repo_id,protected_branches,branch_prefix,permitted_actions):
        self._ceo_or_admin_companion(actor)
        self._lists(protected_branches,"protected_branches")
        self._lists(permitted_actions,"permitted_actions")
        if not branch_prefix or "*" in branch_prefix:raise ValueError("Explicit branch prefix required")
        with self.tx():
            if not self.db.execute("SELECT 1 FROM projects WHERE id=?",(project_id,)).fetchone():
                raise ValueError("Project must be enrolled first")
            self.db.execute("INSERT OR REPLACE INTO github_enrollments VALUES(?,?,?,?,?,?)",
                (project_id,upstream_repo_id,fork_repo_id,canonical(protected_branches),
                 branch_prefix,canonical(permitted_actions)))
            self._event("github.enrolled",{"project_id":project_id,"fork_repo_id":fork_repo_id},actor_id=actor,project_id=project_id)

    def assign_github_by_address(self, actor, project_id, upstream_address):
        """Paste upstream github.com address; ensure same-owner {repo}-corp; enroll both ids."""
        self._ceo_or_admin_companion(actor)
        from company.github_app import (
            github_configured, parse_github_address, installation_account_login,
            repo_by_full_name, ensure_corp_write_repo,
        )
        if not github_configured():
            raise NotImplementedError(
                "GitHub App is not configured; set GITHUB_APP_ID, GITHUB_INSTALLATION_ID, "
                "and GITHUB_PRIVATE_KEY_FILE")
        if not project_id or not str(project_id).strip():
            raise ValueError("Project id required")
        owner, name = parse_github_address(upstream_address)
        account = installation_account_login()
        if owner.lower() != account.lower():
            raise ValueError(
                f"Upstream owner {owner!r} must match the GitHub App installation account {account!r} "
                "for same-owner -corp write repos")
        upstream = repo_by_full_name(owner, name)
        write_repo, created = ensure_corp_write_repo(owner, name)
        upstream_id = str(upstream.get("id") or "")
        write_id = str(write_repo.get("id") or "")
        if not upstream_id or not write_id:
            raise ValueError("GitHub did not return repository ids")
        brief = f"GitHub {upstream.get('full_name') or f'{owner}/{name}'}"
        self.enroll_project(actor, str(project_id).strip(), brief)
        prefix = f"company/{str(project_id).strip()}/"
        self.enroll_github(
            actor, str(project_id).strip(), upstream_id, write_id,
            ["main"], prefix, ["push", "open_pr", "prepare_pr"])
        return {
            "project_id": str(project_id).strip(),
            "upstream": {
                "id": upstream_id,
                "full_name": upstream.get("full_name") or f"{owner}/{name}",
            },
            "write_repo": {
                "id": write_id,
                "full_name": write_repo.get("full_name") or f"{owner}/{name}-corp",
            },
            "created_write_repo": created,
            "branch_prefix": prefix,
        }

    def worktree_path(self,project_id,task_id):
        return f"workspaces/{project_id}/{task_id}"

    def authorize_github_effect(self,project_id,operation,repo_id,branch,head_sha=None,expected_sha=None,path=None):
        enr=self.db.execute("SELECT * FROM github_enrollments WHERE project_id=?",(project_id,)).fetchone()
        if not enr:raise PermissionError("Repository is not enrolled")
        allowed={enr["upstream_repo_id"],enr["fork_repo_id"]}
        if repo_id not in allowed:raise PermissionError("Unrelated repository")
        protected=json.loads(enr["protected_branches"])
        permitted=json.loads(enr["permitted_actions"])
        writes={"push","open_pr","prepare_pr"}
        if operation in writes and branch in protected:raise PermissionError("Protected branch")
        if operation in writes and not branch.startswith(enr["branch_prefix"]):
            raise PermissionError("Branch prefix not allowed")
        if operation=="merge" and "merge" not in permitted:raise PermissionError("Merge is separately scoped")
        if operation=="deploy" and "deploy" not in permitted:raise PermissionError("Deploy is separately scoped")
        if path and path.startswith(".github/workflows") and "workflow" not in permitted:
            raise PermissionError("Workflow file change is not in scope")
        if expected_sha and head_sha and expected_sha!=head_sha:raise PermissionError("Stale head")
        if operation not in permitted and operation not in writes:
            raise PermissionError("Operation not permitted")
        if operation in writes and not any(x in permitted for x in ("push","open_pr","prepare_pr",operation)):
            raise PermissionError("Operation not permitted")
        return True

    def record_github_effect(self,project_id,task_id,operation,repo_id,branch):
        eid=digest({"repo_id":repo_id,"task_id":task_id,"operation":operation})
        with self.tx():
            existing=self.db.execute("SELECT * FROM github_effects WHERE id=?",(eid,)).fetchone()
            if existing:return dict(existing)
            self.db.execute("INSERT INTO github_effects VALUES(?,?,?,?,?,?,?,?)",
                (eid,project_id,task_id,operation,repo_id,branch,"recorded",None))
            self._event("github.effect_recorded",{"id":eid,"operation":operation},project_id=project_id)
            return dict(self.db.execute("SELECT * FROM github_effects WHERE id=?",(eid,)).fetchone())

    def apply_github_effect(self,project_id,task_id,operation,repo_id,branch,head_sha=None,expected_sha=None,path=None,pr_number=None):
        """Authorize, record, then attempt a live write. Live GitHub stays fail-closed."""
        self.authorize_github_effect(project_id,operation,repo_id,branch,
                                    head_sha=head_sha,expected_sha=expected_sha,path=path)
        row=self.record_github_effect(project_id,task_id,operation,repo_id,branch)
        if row["status"]=="live_unavailable":
            return row
        if operation=="merge" and pr_number is None:
            prior=self.db.execute(
                """SELECT remote_id FROM github_effects
                   WHERE project_id=? AND task_id=? AND operation='open_pr' AND status='applied'
                   ORDER BY rowid DESC LIMIT 1""",
                (project_id,task_id)).fetchone()
            if prior and prior["remote_id"]:
                pr_number=prior["remote_id"]
        from .adapters import GitHubAdapter, WorkOrder
        order=WorkOrder(
            task_id,project_id,self.policy()["version"],"github-effect",0,
            {"operation":operation,"repo_id":repo_id,"branch":branch,
             "head_sha":head_sha,"expected_sha":expected_sha,"path":path,
             "pr_number":pr_number,
             "worktree":self.worktree_path(project_id,task_id)})
        try:
            result = GitHubAdapter().execute(order)
        except NotImplementedError:
            with self.tx():
                self.db.execute("UPDATE github_effects SET status=? WHERE id=?",("live_unavailable",row["id"]))
                self._event("github.effect_live_unavailable",{"id":row["id"],"operation":operation},project_id=project_id)
            return dict(self.db.execute("SELECT * FROM github_effects WHERE id=?",(row["id"],)).fetchone())
        except Exception as exc:
            with self.tx():
                self.db.execute("UPDATE github_effects SET status=? WHERE id=?",("failed",row["id"]))
                self._event("github.effect_failed",{"id":row["id"],"operation":operation,"error":str(exc)},
                            project_id=project_id)
            raise
        remote_id = result.get("remote_id")
        with self.tx():
            self.db.execute(
                "UPDATE github_effects SET status=?, remote_id=? WHERE id=?",
                (result.get("status", "applied"), remote_id, row["id"]))
            self._event("github.effect_applied",
                          {"id": row["id"], "operation": operation, "remote_id": remote_id,
                           "html_url": result.get("html_url")}, project_id=project_id)
        return dict(self.db.execute("SELECT * FROM github_effects WHERE id=?",(row["id"],)).fetchone())

    def ingest_github_webhook(self, event: str, delivery_id: str, payload: dict) -> dict:
        """Persist an allowlisted webhook delivery. Payload is task data, not authority."""
        from .github_webhooks import normalize_event
        if payload.get("_ignored"):
            return {"status": "ignored", "delivery_id": delivery_id, "event": event}
        existing = self.db.execute(
            "SELECT * FROM github_webhook_deliveries WHERE delivery_id=?", (delivery_id,)
        ).fetchone()
        if existing:
            return {
                "status": "duplicate",
                "delivery_id": delivery_id,
                "event": existing["event"],
                "repo_id": existing["repo_id"],
                "summary": existing["summary"],
            }
        normalized = normalize_event(event, payload)
        with self.tx():
            self.db.execute(
                "INSERT INTO github_webhook_deliveries VALUES(?,?,?,?,?,?)",
                (delivery_id, event, normalized.get("repo_id"), normalized["summary"],
                 now().isoformat(), "accepted"),
            )
            self._event(
                "github.webhook_received",
                {
                    "delivery_id": delivery_id,
                    "event": event,
                    "repo_id": normalized.get("repo_id"),
                    "summary": normalized["summary"],
                    "trusted_instruction": False,
                },
            )
        return {
            "status": "accepted",
            "delivery_id": delivery_id,
            "event": event,
            "repo_id": normalized.get("repo_id"),
            "summary": normalized["summary"],
        }

    def create_impact_brief(self,signal_id,project_id,affected_summary,recommended_action,cost_cents,authority):
        money(cost_cents)
        sig=self.db.execute("SELECT * FROM signals WHERE id=?",(signal_id,)).fetchone()
        if not sig:raise ValueError("Signal not found")
        body=json.loads(sig["body"])
        brief={"signal_id":signal_id,"source":body["source"],"published_at":body["published_at"],
               "observed_at":body["observed_at"],"project_id":project_id,"facts":body["summary"],
               "affected_summary":affected_summary,"recommended_action":recommended_action,
               "cost_cents":cost_cents,"required_authority":authority,"auto_publish":False,
               "trusted_instruction":False}
        bid=digest({"signal_id":signal_id})
        with self.tx():
            if self.db.execute("SELECT 1 FROM impact_briefs WHERE signal_id=?",(signal_id,)).fetchone():
                return dict(self.db.execute("SELECT * FROM impact_briefs WHERE signal_id=?",(signal_id,)).fetchone())
            self.db.execute("INSERT INTO impact_briefs VALUES(?,?,?,?,?)",
                            (bid,signal_id,project_id,canonical(brief),"proposed"))
            self._event("intelligence.brief_created",{"id":bid,"signal_id":signal_id},project_id=project_id)
            return dict(self.db.execute("SELECT * FROM impact_briefs WHERE id=?",(bid,)).fetchone())

    def list_impact_briefs(self):
        return [dict(r) for r in self.db.execute(
            "SELECT * FROM impact_briefs ORDER BY id")]

    def correct_signal(self,signal_id,note):
        with self.tx():
            sig=self.db.execute("SELECT * FROM signals WHERE id=?",(signal_id,)).fetchone()
            if not sig:raise ValueError("Signal not found")
            self.db.execute("UPDATE impact_briefs SET status='corrected' WHERE signal_id=?",(signal_id,))
            self._event("intelligence.corrected",{"signal_id":signal_id,"note":note})
        return {"signal_id":signal_id,"status":"corrected","note":note}

    def approve_feed_source(self,actor,source_id,url):
        """CEO-only enrollment of a live feed. Does not poll or fetch."""
        from urllib.parse import urlparse
        self._ceo(actor)
        if not source_id or not str(source_id).strip():
            raise ValueError("Source id required")
        parsed=urlparse(url)
        if parsed.scheme!="https" or not parsed.netloc:
            raise ValueError("Feed source needs an HTTPS URL")
        with self.tx():
            self.db.execute("INSERT OR REPLACE INTO feed_sources VALUES(?,?,?,?,?)",
                            (source_id,url,actor,now().isoformat(),"approved"))
            self._event("feed.source_approved",{"id":source_id,"url":url},actor_id=actor)
        return dict(self.db.execute("SELECT * FROM feed_sources WHERE id=?",(source_id,)).fetchone())

    def pause_feed_source(self,actor,source_id):
        """CEO-only pause; poll fails closed until re-approved."""
        self._ceo(actor)
        with self.tx():
            row=self.db.execute("SELECT * FROM feed_sources WHERE id=?",(source_id,)).fetchone()
            if not row:
                raise ValueError("Feed source not found")
            if row["status"]=="revoked":
                raise ValueError("Revoked feed cannot be paused")
            self.db.execute("UPDATE feed_sources SET status=? WHERE id=?",("paused",source_id))
            self._event("feed.source_paused",{"id":source_id},actor_id=actor)
        return dict(self.db.execute("SELECT * FROM feed_sources WHERE id=?",(source_id,)).fetchone())

    def revoke_feed_source(self,actor,source_id):
        """CEO-only revoke; poll fails closed until re-approved."""
        self._ceo(actor)
        with self.tx():
            row=self.db.execute("SELECT * FROM feed_sources WHERE id=?",(source_id,)).fetchone()
            if not row:
                raise ValueError("Feed source not found")
            self.db.execute("UPDATE feed_sources SET status=? WHERE id=?",("revoked",source_id))
            self._event("feed.source_revoked",{"id":source_id},actor_id=actor)
        return dict(self.db.execute("SELECT * FROM feed_sources WHERE id=?",(source_id,)).fetchone())

    def list_feed_sources(self):
        return [dict(r) for r in self.db.execute("SELECT * FROM feed_sources ORDER BY id")]

    def poll_market_feed(self,source_id,*,actor=None):
        if actor is not None:
            self._ceo(actor)
        """Record a poll attempt for an approved source. Live fetch when adapter succeeds."""
        src=self.db.execute("SELECT * FROM feed_sources WHERE id=? AND status='approved'",(source_id,)).fetchone()
        if not src:
            raise PermissionError("Feed source is not approved")
        pid=digest({"source_id":source_id})
        with self.tx():
            existing=self.db.execute("SELECT * FROM feed_polls WHERE id=?",(pid,)).fetchone()
            if existing:
                row=dict(existing)
            else:
                self.db.execute("INSERT INTO feed_polls VALUES(?,?,?,?)",
                                (pid,source_id,"recorded",now().isoformat()))
                self._event("feed.poll_recorded",{"id":pid,"source_id":source_id})
                row=dict(self.db.execute("SELECT * FROM feed_polls WHERE id=?",(pid,)).fetchone())
        if row["status"] in {"live_unavailable","applied"}:
            return row
        from .adapters import MarketFeedAdapter
        try:
            items=MarketFeedAdapter().poll(source_id, src["url"])
        except NotImplementedError:
            with self.tx():
                self.db.execute("UPDATE feed_polls SET status=? WHERE id=?",("live_unavailable",pid))
                self._event("feed.poll_live_unavailable",{"id":pid,"source_id":source_id})
            return dict(self.db.execute("SELECT * FROM feed_polls WHERE id=?",(pid,)).fetchone())
        except Exception as exc:
            with self.tx():
                self.db.execute("UPDATE feed_polls SET status=? WHERE id=?",("failed",pid))
                self._event("feed.poll_failed",{"id":pid,"source_id":source_id,"error":str(exc)})
            raise
        ingested=0
        for item in items:
            try:
                self.ingest_signal(**item)
                ingested+=1
            except ValueError:
                continue
        with self.tx():
            self.db.execute("UPDATE feed_polls SET status=? WHERE id=?",("applied",pid))
            self._event("feed.poll_applied",{"id":pid,"source_id":source_id,"ingested":ingested})
        out=dict(self.db.execute("SELECT * FROM feed_polls WHERE id=?",(pid,)).fetchone())
        out["ingested"]=ingested
        return out

    def cost_expansion(self,actor,eid,estimate_cents):
        self._ceo(actor)
        money(estimate_cents)
        with self.tx():
            e=self.db.execute("SELECT * FROM expansions WHERE id=?",(eid,)).fetchone()
            if not e or e["status"] not in {"proposed","costed"}:raise ValueError("Expansion not found")
            self.db.execute("UPDATE expansions SET status='costed' WHERE id=?",(eid,))
            self._event("expansion.costed",{"id":eid,"estimate_cents":estimate_cents},actor_id=actor)

    def inspect_expansion(self,inspector,eid,passed=True):
        with self.tx():
            e=self.db.execute("SELECT * FROM expansions WHERE id=?",(eid,)).fetchone()
            if not e:raise ValueError("Expansion not found")
            self._scope(inspector,e["source_project"],"inspect_room",0)
            if not passed:
                if e["status"]=="built":
                    raise ValueError("Cannot fail inspection after room.built without a compensating event")
                self.db.execute("UPDATE expansions SET status='inspection_failed' WHERE id=?",(eid,))
            self._event("expansion.inspected",{"id":eid,"passed":passed,"inspector":inspector},actor_id=inspector)
        return passed

    @staticmethod
    def _validate_industry_pack(body):
        required = {
            "id", "industry", "compliance_notes", "minimal_departments",
            "full_departments", "required_skills", "default_floorplan",
        }
        if set(body) != required:
            raise ValueError("Industry pack has unknown or missing fields")
        if not all(isinstance(body[key], str) and body[key].strip()
                   for key in ("id", "industry", "compliance_notes")):
            raise ValueError("Industry pack id, industry and compliance_notes required")
        department_fields = {
            "id", "name", "head", "mission", "measures", "room_type", "positions",
            "default_model_profile", "initially_active",
        }
        full_ids = set()
        for mode in ("minimal_departments", "full_departments"):
            departments = body[mode]
            if not isinstance(departments, list) or not departments:
                raise ValueError(f"{mode} must be a nonempty list")
            for department in departments:
                if set(department) != department_fields:
                    raise ValueError("Industry pack department has unknown or missing fields")
                if not all(isinstance(department[key], str) and department[key].strip()
                           for key in ("id", "name", "head", "mission", "room_type",
                                       "default_model_profile")):
                    raise ValueError("Industry pack department text fields required")
                if not isinstance(department["measures"], list):
                    raise ValueError("Industry pack measures must be a list")
                if not isinstance(department["positions"], list):
                    raise ValueError("Industry pack positions must be a list")
                if type(department["initially_active"]) is not bool:
                    raise ValueError("Industry pack initially_active must be boolean")
                if mode == "full_departments":
                    full_ids.add(department["id"])
        minimal_ids = {d["id"] for d in body["minimal_departments"]}
        if not minimal_ids.issubset(full_ids):
            raise ValueError("Minimal departments must be included in full departments")
        skill_fields = {"id", "name", "department_id", "platform"}
        for skill in body["required_skills"]:
            if set(skill) != skill_fields or not all(
                    isinstance(skill[key], str) and skill[key].strip()
                    for key in skill_fields):
                raise ValueError("Industry pack skill is invalid")
            if skill["department_id"] not in full_ids:
                raise ValueError("Industry pack skill references unknown department")
        floorplan = body["default_floorplan"]
        if set(floorplan) != {"grid_cols", "grid_rows"}:
            raise ValueError("Industry pack default_floorplan is invalid")
        if any(type(floorplan[key]) is not int or floorplan[key] < 1
               for key in ("grid_cols", "grid_rows")):
            raise ValueError("Industry pack floorplan dimensions must be positive integers")

    def seed_industry_packs(self, path=None):
        directory = Path(path) if path else (
            Path(__file__).resolve().parents[1] / "config" / "industry-packs")
        paths = sorted(directory.glob("*.json"))
        if not paths:
            raise ValueError("No industry packs found")
        packs = []
        for pack_path in paths:
            body = json.loads(pack_path.read_text())
            self._validate_industry_pack(body)
            packs.append(body)
        with self.tx():
            for body in packs:
                self.db.execute(
                    """INSERT INTO industry_packs(id,industry,body,enabled)
                       VALUES(?,?,?,1)
                       ON CONFLICT(id) DO UPDATE SET
                         industry=excluded.industry,body=excluded.body""",
                    (body["id"], body["industry"], canonical(body)),
                )
            self._event("industry_packs.seeded", {"packs": len(packs)})
        return self.list_industry_packs()

    def list_industry_packs(self):
        result = []
        for row in self.db.execute(
                "SELECT * FROM industry_packs ORDER BY industry,id"):
            body = json.loads(row["body"])
            body["enabled"] = bool(row["enabled"])
            result.append(body)
        return {"industry_packs": result}

    def _division_proposer(self, actor):
        if self._is_ceo_actor(actor):
            return
        if actor == "consultant" or str(actor).startswith("consultant:"):
            return
        seat = self.db.execute(
            """SELECT 1 FROM department_seats
               WHERE principal_id=? AND status='active'""", (actor,)).fetchone()
        if seat:
            return
        identity = self.db.execute(
            "SELECT scopes FROM identities WHERE principal_id=?", (actor,)).fetchone()
        if identity and "consultant.propose" in json.loads(identity["scopes"]):
            return
        raise PermissionError("Consultant, seated department head, or CEO authority required")

    def _division(self, division_id):
        row = self.db.execute(
            "SELECT * FROM divisions WHERE id=?", (division_id,)).fetchone()
        if not row:
            raise ValueError("Unknown division")
        return dict(row)

    def propose_division(self, actor, pack_id, name, mode="minimal"):
        self._division_proposer(actor)
        name = str(name or "").strip()
        if not name:
            raise ValueError("name required")
        if mode not in {"minimal", "full"}:
            raise ValueError("mode must be minimal or full")
        pack = self.db.execute(
            "SELECT enabled FROM industry_packs WHERE id=?", (pack_id,)).fetchone()
        if not pack:
            raise ValueError("Unknown industry pack")
        if not pack["enabled"]:
            raise ValueError("Industry pack is disabled")
        division_id = str(uuid.uuid4())
        stamp = now().isoformat()
        with self.tx():
            self.db.execute(
                """INSERT INTO divisions(
                     id,name,industry_pack_id,status,activated_by,activated_at,
                     proposed_by,created_at)
                   VALUES(?,?,?,'proposed',NULL,NULL,?,?)""",
                (division_id, name, pack_id, actor, stamp),
            )
            self.db.execute(
                "INSERT INTO division_activations VALUES(?,?,?,?,?,?)",
                (str(uuid.uuid4()), division_id, "proposed", actor, stamp, mode),
            )
            self._event(
                "division.proposed",
                {"id": division_id, "pack_id": pack_id, "mode": mode},
                actor_id=actor,
            )
        return next(
            item for item in self.list_divisions()["divisions"]
            if item["id"] == division_id)

    def list_divisions(self):
        divisions = []
        for row in self.db.execute(
                "SELECT * FROM divisions ORDER BY created_at,id"):
            result = dict(row)
            mode = self.db.execute(
                """SELECT note FROM division_activations
                   WHERE division_id=? AND action='proposed'
                   ORDER BY at,id LIMIT 1""", (row["id"],)).fetchone()
            result["mode"] = mode["note"] if mode else "minimal"
            result["departments"] = [
                department["department_id"] for department in self.db.execute(
                    """SELECT department_id FROM division_departments
                       WHERE division_id=? ORDER BY department_id""", (row["id"],))
            ]
            result["activations"] = [
                dict(item) for item in self.db.execute(
                    """SELECT id,action,actor,at,note FROM division_activations
                       WHERE division_id=? ORDER BY at,id""", (row["id"],))
            ]
            divisions.append(result)
        return {"divisions": divisions}

    def activate_division(self, actor, division_id):
        self._ceo_or_admin_companion(actor)
        division = self._division(division_id)
        if division["status"] != "proposed":
            raise ValueError("Division is not proposed")
        pack_row = self.db.execute(
            "SELECT body,enabled FROM industry_packs WHERE id=?",
            (division["industry_pack_id"],)).fetchone()
        if not pack_row or not pack_row["enabled"]:
            raise ValueError("Industry pack is unavailable")
        pack = json.loads(pack_row["body"])
        mode_row = self.db.execute(
            """SELECT note FROM division_activations
               WHERE division_id=? AND action='proposed'
               ORDER BY at,id LIMIT 1""", (division_id,)).fetchone()
        mode = mode_row["note"] if mode_row else "minimal"
        departments = pack[f"{mode}_departments"]
        selected_ids = {department["id"] for department in departments}
        stamp = now().isoformat()
        with self.tx():
            for department in departments:
                if not self.db.execute(
                        "SELECT 1 FROM departments WHERE id=?",
                        (department["id"],)).fetchone():
                    self.create_department(
                        actor,
                        department_id=department["id"],
                        name=department["name"],
                        head_title=department["head"],
                        mission=department["mission"],
                        measures=department["measures"],
                        room_type=department["room_type"],
                        initially_active=department["initially_active"],
                        default_model_profile=department["default_model_profile"],
                    )
                for title in department["positions"]:
                    position_id = f"{department['id']}:{title}"
                    if not self.db.execute(
                            "SELECT 1 FROM positions WHERE id=?",
                            (position_id,)).fetchone():
                        self.create_position(
                            actor, department_id=department["id"], title=title)
                self.db.execute(
                    "INSERT INTO division_departments VALUES(?,?)",
                    (division_id, department["id"]),
                )
            heads = {department["id"]: department["head"] for department in departments}
            for skill in pack["required_skills"]:
                if skill["department_id"] not in selected_ids:
                    continue
                self.db.execute(
                    """INSERT INTO skills(id,name,platform,department_id)
                       VALUES(?,?,?,?)
                       ON CONFLICT(id) DO UPDATE SET
                         name=excluded.name,platform=excluded.platform,
                         department_id=excluded.department_id""",
                    (skill["id"], skill["name"], skill["platform"],
                     skill["department_id"]),
                )
                learner = f"{skill['department_id']}:{heads[skill['department_id']]}"
                assignment_id = digest({
                    "project": "company", "skill": skill["id"], "learner": learner,
                })
                self.db.execute(
                    """INSERT OR IGNORE INTO learning_assignments
                       VALUES(?,?,?,?,?,?,?,?,?)""",
                    (assignment_id, "company", skill["id"], learner,
                     skill["department_id"], None, "assigned", None, stamp),
                )
            self.default_floorplan_for(actor, division_id)
            self.db.execute(
                """UPDATE divisions SET status='active',activated_by=?,activated_at=?
                   WHERE id=?""", (actor, stamp, division_id))
            self.db.execute(
                "INSERT INTO division_activations VALUES(?,?,?,?,?,?)",
                (str(uuid.uuid4()), division_id, "activated", actor, stamp, mode),
            )
            self._event(
                "division.activated",
                {"id": division_id, "pack_id": division["industry_pack_id"],
                 "mode": mode, "departments": sorted(selected_ids)},
                actor_id=actor,
            )
        return next(
            item for item in self.list_divisions()["divisions"]
            if item["id"] == division_id)

    def deactivate_division(self, actor, division_id):
        self._ceo_or_admin_companion(actor)
        division = self._division(division_id)
        if division["status"] != "active":
            raise ValueError("Division is not active")
        department_ids = [
            row["department_id"] for row in self.db.execute(
                "SELECT department_id FROM division_departments WHERE division_id=?",
                (division_id,))
        ]
        placeholders = ",".join("?" for _ in department_ids)
        if department_ids and self.db.execute(
                f"""SELECT 1 FROM project_dispatches
                    WHERE department_id IN ({placeholders}) AND status IN (
                      'queued_for_head','assigned','in_progress','blocked',
                      'blocked_vacant_head') LIMIT 1""",
                tuple(department_ids)).fetchone():
            raise ValueError("Cannot deactivate division with open dispatches")
        if department_ids and self.db.execute(
                f"""SELECT 1 FROM cross_department_requests
                    WHERE status NOT IN ('accepted','rejected','closed','cancelled')
                      AND (requesting_department_id IN ({placeholders})
                           OR delivering_department_id IN ({placeholders}))
                    LIMIT 1""",
                tuple(department_ids + department_ids)).fetchone():
            raise ValueError(
                "Cannot deactivate division with open cross-department requests")
        stamp = now().isoformat()
        with self.tx():
            self.db.execute(
                "UPDATE divisions SET status='inactive' WHERE id=?", (division_id,))
            self.db.execute(
                "INSERT INTO division_activations VALUES(?,?,?,?,?,?)",
                (str(uuid.uuid4()), division_id, "deactivated", actor, stamp, None),
            )
            self._event(
                "division.deactivated", {"id": division_id}, actor_id=actor)
        return next(
            item for item in self.list_divisions()["divisions"]
            if item["id"] == division_id)

    def _floorplan(self, floorplan_id):
        row = self.db.execute(
            "SELECT * FROM floorplans WHERE id=?", (floorplan_id,)).fetchone()
        if not row:
            raise LookupError("Floorplan not found")
        return dict(row)

    def _floorplan_room(self, room_id):
        row = self.db.execute(
            "SELECT * FROM floorplan_rooms WHERE id=?", (room_id,)).fetchone()
        if not row:
            raise LookupError("Floorplan room not found")
        return dict(row)

    def _room_with_org(self, room_id):
        row = self.db.execute(
            """SELECT r.*, d.name AS department_name,
                      s.id AS seat_id, s.principal_id AS seat_principal_id,
                      s.title AS seat_title, s.status AS seat_status
               FROM floorplan_rooms r
               LEFT JOIN departments d ON d.id=r.department_id
               LEFT JOIN department_seats s ON s.department_id=r.department_id
               WHERE r.id=?""",
            (room_id,)).fetchone()
        if not row:
            raise LookupError("Floorplan room not found")
        result = dict(row)
        result["seat"] = None if result["seat_id"] is None else {
            "id": result.pop("seat_id"),
            "principal_id": result.pop("seat_principal_id"),
            "title": result.pop("seat_title"),
            "status": result.pop("seat_status"),
        }
        if result["seat"] is None:
            for key in ("seat_id", "seat_principal_id", "seat_title", "seat_status"):
                result.pop(key, None)
        result["workers"] = []
        if result["department_id"]:
            for employee in self.db.execute(
                    """SELECT id,display_name,position_id FROM employees
                       WHERE status='active' AND position_id LIKE ? ORDER BY id""",
                    (f"{result['department_id']}:%",)):
                result["workers"].append({
                    "employee_id": employee["id"],
                    "display_name": employee["display_name"],
                    "position_id": employee["position_id"],
                    "sprite": self._worker_sprite(employee["id"]),
                })
        return result

    def get_floorplan(self, floorplan_id):
        plan = self._floorplan(floorplan_id)
        plan["rooms"] = [
            self._room_with_org(row["id"])
            for row in self.db.execute(
                "SELECT id FROM floorplan_rooms WHERE floorplan_id=? ORDER BY grid_y,grid_x,id",
                (floorplan_id,))
        ]
        plan.update(self.floorplan_status(floorplan_id))
        return plan

    def list_floorplans(self):
        return {
            "floorplans": [
                self.get_floorplan(row["id"])
                for row in self.db.execute(
                    "SELECT id FROM floorplans ORDER BY created_at,id")
            ]
        }

    def create_floorplan(self, actor, name, grid_cols=8, grid_rows=6, division_id=None):
        self._ceo_or_admin_companion(actor)
        name = str(name or "").strip()
        if not name:
            raise ValueError("name required")
        if type(grid_cols) is not int or type(grid_rows) is not int:
            raise ValueError("grid dimensions must be integers")
        if grid_cols < 1 or grid_rows < 1:
            raise ValueError("grid dimensions must be positive")
        floorplan_id = str(uuid.uuid4())
        with self.tx():
            self.db.execute(
                """INSERT INTO floorplans(
                       id,division_id,name,grid_cols,grid_rows,status,created_by,created_at)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (floorplan_id, division_id, name, grid_cols, grid_rows,
                 "active", actor, now().isoformat()))
            self._event(
                "floorplan.created",
                {"id": floorplan_id, "division_id": division_id},
                actor_id=actor,
            )
        return self.get_floorplan(floorplan_id)

    def _validate_room_placement(self, floorplan_id, room_id, grid_x, grid_y, width, height):
        plan = self._floorplan(floorplan_id)
        values = (grid_x, grid_y, width, height)
        if any(type(value) is not int for value in values):
            raise ValueError("room grid values must be integers")
        if grid_x < 0 or grid_y < 0 or width < 1 or height < 1:
            raise ValueError("room grid position and size are invalid")
        if grid_x + width > plan["grid_cols"] or grid_y + height > plan["grid_rows"]:
            raise ValueError("room is outside the floorplan grid")
        overlap = self.db.execute(
            """SELECT id FROM floorplan_rooms
               WHERE floorplan_id=? AND id!=?
                 AND grid_x < ? AND grid_x + width > ?
                 AND grid_y < ? AND grid_y + height > ?
               LIMIT 1""",
            (floorplan_id, room_id or "", grid_x + width, grid_x,
             grid_y + height, grid_y)).fetchone()
        if overlap:
            raise ValueError(f"Room overlap with {overlap['id']}")

    def upsert_floorplan_room(self, actor, floorplan_id, **fields):
        self._ceo_or_admin_companion(actor)
        self._floorplan(floorplan_id)
        allowed = {
            "id", "department_id", "room_type", "label", "grid_x", "grid_y",
            "width", "height", "capacity", "status", "source_expansion_id",
        }
        unknown = set(fields) - allowed
        if unknown:
            raise ValueError(f"Unknown room fields: {sorted(unknown)}")
        room_id = fields.get("id")
        existing = None
        if room_id:
            row = self.db.execute(
                "SELECT * FROM floorplan_rooms WHERE id=?", (room_id,)).fetchone()
            if row:
                existing = dict(row)
                if existing["floorplan_id"] != floorplan_id:
                    raise ValueError("Room belongs to another floorplan")
        if existing is None:
            room_id = room_id or str(uuid.uuid4())
            if self.db.execute(
                    "SELECT 1 FROM floorplan_rooms WHERE id=?", (room_id,)).fetchone():
                raise ValueError("Room id already exists")
        values = {
            "department_id": None,
            "room_type": None,
            "label": None,
            "grid_x": 0,
            "grid_y": 0,
            "width": 1,
            "height": 1,
            "capacity": 1,
            "status": "active",
            "source_expansion_id": None,
        }
        if existing:
            values.update({key: existing[key] for key in values})
        values.update({key: value for key, value in fields.items() if key != "id"})
        department = None
        if values["department_id"] is not None:
            department = self.db.execute(
                "SELECT id,name,room_type FROM departments WHERE id=?",
                (values["department_id"],)).fetchone()
            if not department:
                raise ValueError("Unknown department_id")
        if not values["room_type"] and department:
            values["room_type"] = department["room_type"]
        known_types = {
            row[0] for row in self.db.execute(
                """SELECT room_type FROM departments
                   UNION SELECT required_room_type FROM room_requirements""")
        }
        if values["room_type"] not in known_types:
            raise ValueError("Unknown room_type")
        if not values["label"]:
            values["label"] = department["name"] if department else values["room_type"]
        if type(values["capacity"]) is not int or values["capacity"] < 0:
            raise ValueError("capacity must be a nonnegative integer")
        if values["status"] not in {"active", "planned", "inactive"}:
            raise ValueError("Unknown room status")
        if values["source_expansion_id"] and not self.db.execute(
                "SELECT 1 FROM expansions WHERE id=?",
                (values["source_expansion_id"],)).fetchone():
            raise ValueError("Unknown source_expansion_id")
        self._validate_room_placement(
            floorplan_id, room_id, values["grid_x"], values["grid_y"],
            values["width"], values["height"])
        with self.tx():
            if existing:
                self.db.execute(
                    """UPDATE floorplan_rooms SET
                       department_id=?,room_type=?,label=?,grid_x=?,grid_y=?,
                       width=?,height=?,capacity=?,status=?,source_expansion_id=?
                       WHERE id=?""",
                    tuple(values[key] for key in (
                        "department_id", "room_type", "label", "grid_x", "grid_y",
                        "width", "height", "capacity", "status",
                        "source_expansion_id")) + (room_id,))
            else:
                self.db.execute(
                    """INSERT INTO floorplan_rooms(
                       id,floorplan_id,department_id,room_type,label,grid_x,grid_y,
                       width,height,capacity,status,source_expansion_id,created_by,created_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (room_id, floorplan_id) + tuple(values[key] for key in (
                        "department_id", "room_type", "label", "grid_x", "grid_y",
                        "width", "height", "capacity", "status",
                        "source_expansion_id")) + (actor, now().isoformat()))
            self._event(
                "floorplan.room_upserted",
                {"id": room_id, "floorplan_id": floorplan_id},
                actor_id=actor,
            )
        return self._room_with_org(room_id)

    def move_room(self, actor, room_id, grid_x, grid_y):
        self._ceo_or_admin_companion(actor)
        room = self._floorplan_room(room_id)
        self._validate_room_placement(
            room["floorplan_id"], room_id, grid_x, grid_y,
            room["width"], room["height"])
        with self.tx():
            self.db.execute(
                "UPDATE floorplan_rooms SET grid_x=?,grid_y=? WHERE id=?",
                (grid_x, grid_y, room_id))
            self._event(
                "floorplan.room_moved",
                {"id": room_id, "floorplan_id": room["floorplan_id"],
                 "grid_x": grid_x, "grid_y": grid_y},
                actor_id=actor,
            )
        return self._room_with_org(room_id)

    def remove_room(self, actor, room_id):
        self._ceo_or_admin_companion(actor)
        room = self._floorplan_room(room_id)
        if room["source_expansion_id"]:
            raise ValueError("expansion-bound room cannot be removed")
        with self.tx():
            self.db.execute("DELETE FROM floorplan_rooms WHERE id=?", (room_id,))
            self._event(
                "floorplan.room_removed",
                {"id": room_id, "floorplan_id": room["floorplan_id"]},
                actor_id=actor,
            )
        return {"id": room_id, "removed": True}

    def default_floorplan_for(self, actor, division_id=None):
        if division_id:
            division = self._division(division_id)
            departments = [
                dict(row) for row in self.db.execute(
                    """SELECT d.id,d.name,d.room_type
                       FROM departments d
                       JOIN division_departments dd ON dd.department_id=d.id
                       WHERE dd.division_id=? AND d.status!='retired'
                       ORDER BY d.display_order,d.id""", (division_id,))
            ]
            pack = self.db.execute(
                "SELECT body FROM industry_packs WHERE id=?",
                (division["industry_pack_id"],)).fetchone()
            dimensions = json.loads(pack["body"])["default_floorplan"]
            grid_cols = dimensions["grid_cols"]
            grid_rows = max(
                dimensions["grid_rows"],
                (len(departments) + grid_cols - 1) // grid_cols,
            )
            name = f"{division['name']} headquarters"
        else:
            departments = [
                dict(row) for row in self.db.execute(
                    """SELECT id,name,room_type FROM departments
                       WHERE status!='retired' ORDER BY display_order,id""")
            ]
            grid_cols = 8
            grid_rows = max(6, (len(departments) + grid_cols - 1) // grid_cols)
            name = "Default headquarters"
        plan = self.create_floorplan(
            actor, name, grid_cols, grid_rows, division_id)
        for index, department in enumerate(departments):
            self.upsert_floorplan_room(
                actor, plan["id"],
                department_id=department["id"],
                room_type=department["room_type"],
                label=department["name"],
                grid_x=index % grid_cols,
                grid_y=index // grid_cols,
                width=1, height=1, capacity=1,
            )
        return self.get_floorplan(plan["id"])

    def floorplan_status(self, floorplan_id=None):
        if floorplan_id is None:
            row = self.db.execute(
                "SELECT id FROM floorplans ORDER BY created_at DESC,id DESC LIMIT 1").fetchone()
            if not row:
                return {"floorplan_id": None, "unmet_requirements": [], "compliant": False}
            floorplan_id = row["id"]
        self._floorplan(floorplan_id)
        gaps = []
        for requirement in self.db.execute(
                """SELECT rr.department_id,rr.required_room_type,rr.min_capacity
                   FROM room_requirements rr
                   JOIN departments d ON d.id=rr.department_id
                   WHERE d.status!='retired'
                   ORDER BY d.display_order,d.id,rr.required_room_type"""):
            actual = self.db.execute(
                """SELECT COALESCE(SUM(capacity),0) FROM floorplan_rooms
                   WHERE floorplan_id=? AND department_id=?
                     AND room_type=? AND status='active'""",
                (floorplan_id, requirement["department_id"],
                 requirement["required_room_type"])).fetchone()[0]
            if actual < requirement["min_capacity"]:
                gaps.append({
                    "department_id": requirement["department_id"],
                    "required_room_type": requirement["required_room_type"],
                    "min_capacity": requirement["min_capacity"],
                    "actual_capacity": actual,
                })
        return {
            "floorplan_id": floorplan_id,
            "unmet_requirements": gaps,
            "compliant": not gaps,
        }

    def headquarters(self):
        floorplans = self.list_floorplans()["floorplans"]
        floorplan_rooms = [
            room for plan in floorplans for room in plan["rooms"]
        ]
        expansions = [
            {"id": row["id"], "status": row["status"],
             "source_project": row["source_project"], "contractor": row["contractor"]}
            for row in self.db.execute("SELECT * FROM expansions ORDER BY id")
        ]
        departments = [
            dict(row) for row in self.db.execute(
                "SELECT id,name,initially_active,room_type FROM departments ORDER BY id")
        ]
        rooms = floorplan_rooms if floorplan_rooms else expansions
        room_count = (
            len(floorplan_rooms) if floorplan_rooms
            else 1 + sum(1 for room in expansions if room["status"] == "built")
        )
        status = self.floorplan_status(floorplans[-1]["id"]) if floorplans else {
            "floorplan_id": None, "unmet_requirements": [], "compliant": False}
        return {
            "floorplans": floorplans,
            "rooms": rooms,
            "expansions": expansions,
            "departments": departments,
            "room_count": room_count,
            "unmet_requirements": status["unmet_requirements"],
            "occupancy_note": "Room occupancy is not running model count.",
            "source": "persisted_events",
        }

    def room_detail(self, room_id):
        floor_room = self.db.execute(
            "SELECT 1 FROM floorplan_rooms WHERE id=?", (room_id,)).fetchone()
        if floor_room:
            room = self._room_with_org(room_id)
            departments = []
            staff = []
            if room["department_id"]:
                department = self.db.execute(
                    """SELECT id,name,head_title,mission,room_type,initially_active
                       FROM departments WHERE id=?""",
                    (room["department_id"],)).fetchone()
                if department:
                    departments.append(dict(department))
                staff = [
                    dict(row) for row in self.db.execute(
                        """SELECT id,position_id,display_name,status FROM employees
                           WHERE position_id LIKE ? ORDER BY id""",
                        (f"{room['department_id']}:%",))
                ]
            return {
                "room": room,
                "purpose": room["label"],
                "tasks": [],
                "deliverables": [],
                "queue": [],
                "departments": departments,
                "staff": staff,
                "models": [],
                "decisions": [],
                "costs": {"simulated_spend_cents": 0, "reserved_cents": 0},
                "occupancy_note": "Room occupancy is not running model count.",
            }
        row = self.db.execute("SELECT * FROM expansions WHERE id=?", (room_id,)).fetchone()
        if not row:
            raise LookupError("Room not found")
        room = {"id": row["id"], "status": row["status"], "source_project": row["source_project"],
                "contractor": row["contractor"]}
        project_id = room["source_project"]
        project = self.db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        purpose = project["brief"] if project else f"Expansion for accepted project {project_id}"
        tasks = [dict(r) for r in self.db.execute(
            "SELECT * FROM tasks WHERE project=? ORDER BY rowid", (project_id,))]
        deliverables = [{"id": r["id"], "hash": r["hash"], "task_id": r["task_id"],
                         "producer": r["producer"], "created_at": r["created_at"]}
                        for r in self.db.execute(
                            "SELECT * FROM artifacts WHERE project=? ORDER BY created_at", (project_id,))]
        queue = [dict(r) for r in self.db.execute(
            "SELECT id,task_id,actor,project,action,cost,status FROM queue WHERE project=? ORDER BY id",
            (project_id,))]
        dept_ids = [r[0] for r in self.db.execute(
            "SELECT DISTINCT department_id FROM project_dispatches WHERE project_id=?", (project_id,))]
        known = {r[0] for r in self.db.execute("SELECT id FROM departments")}
        for task in tasks:
            actor = task["actor"]
            prefix = actor.split(":", 1)[0]
            if actor in known and actor not in dept_ids:
                dept_ids.append(actor)
            elif prefix in known and prefix not in dept_ids:
                dept_ids.append(prefix)
        departments = []
        for dept_id in dept_ids:
            d = self.db.execute(
                "SELECT id,name,head_title,mission,room_type,initially_active FROM departments WHERE id=?",
                (dept_id,)).fetchone()
            if d:
                departments.append(dict(d))
        staff = []
        for dept_id in dept_ids:
            for emp in self.db.execute(
                    "SELECT id,position_id,display_name,status FROM employees WHERE position_id LIKE ?",
                    (f"{dept_id}:%",)):
                staff.append(dict(emp))
        models = [dict(r) for r in self.db.execute(
            """SELECT * FROM model_assignments
               WHERE scope_kind='department' AND scope_id IN (SELECT department_id FROM project_dispatches WHERE project_id=?)
               ORDER BY effective_at""",
            (project_id,))]
        spent = self.db.execute(
            "SELECT COALESCE(SUM(cost),0) FROM ledger WHERE task_id IN (SELECT id FROM tasks WHERE project=?)",
            (project_id,)).fetchone()[0]
        reserved = self.db.execute(
            """SELECT COALESCE(SUM(amount_cents),0) FROM reservations
               WHERE status='reserved' AND task_id IN (SELECT id FROM tasks WHERE project=?)""",
            (project_id,)).fetchone()[0]
        decisions = []
        for ev in self.db.execute(
                """SELECT seq,at,kind,body,project_id FROM events
                   WHERE kind IN (
                     'project.accepted','expansion.proposed','expansion.approved',
                     'expansion.inspected','room.built','project.dispatched')
                   ORDER BY seq"""):
            body = json.loads(ev["body"])
            related = (
                ev["project_id"] == project_id
                or body.get("project") == project_id
                or body.get("source_project") == project_id
                or body.get("id") == room_id
            )
            if related:
                decisions.append({"id": ev["seq"], "kind": ev["kind"], "at": ev["at"],
                                  "summary": ev["body"]})
        for item in self.decisions_inbox()["items"]:
            if item.get("project_id") == project_id:
                decisions.append(item)
        return {
            "room": room,
            "purpose": purpose,
            "tasks": tasks,
            "staff": staff,
            "deliverables": deliverables,
            "queue": queue,
            "departments": departments,
            "model_assignments": models,
            "costs": {"simulated_spend_cents": spent, "reserved_cents": reserved},
            "decisions": decisions,
            "occupancy_note": "Room occupancy is not running model count.",
            "source": "persisted_events",
        }

    def put_memory(self,actor,memory_id,body,classification,project_id=None,department_id=None,approved=False):
        if classification not in {"public","internal","restricted"}:raise ValueError("Unknown data classification")
        if approved and actor!=self.ceo:raise PermissionError("CEO authority required")
        with self.tx():
            self.db.execute("INSERT OR REPLACE INTO memories VALUES(?,?,?,?,?,?,?)",
                (memory_id,project_id,department_id,classification,body,1 if approved else 0,actor))
            self._event("memory.stored",{"id":memory_id,"project_id":project_id},actor_id=actor,project_id=project_id)

    def get_memory(self,actor,memory_id,project_id=None):
        row=self.db.execute("SELECT * FROM memories WHERE id=?",(memory_id,)).fetchone()
        if not row:raise LookupError("Memory not found")
        if row["project_id"] and project_id and row["project_id"]!=project_id:
            raise PermissionError("Cross-project memory access denied")
        if row["project_id"] and project_id is None and actor!=self.ceo:
            g=self._effective_grant(actor)
            if not g or row["project_id"] not in g["projects"]:
                raise PermissionError("Cross-project memory access denied")
        return dict(row)

    def set_budget_period(self,actor,scope,period_start,period_end,limit_cents):
        self._ceo(actor)
        money(limit_cents)
        pid=digest({"scope":scope,"period_start":period_start})
        with self.tx():
            self.db.execute("INSERT OR REPLACE INTO budget_periods VALUES(?,?,?,?,?)",
                            (pid,scope,period_start,period_end,limit_cents))
            self._event("budget.period_set",{"id":pid,"limit_cents":limit_cents},actor_id=actor)
        return pid

    def record_benchmark(self,role,profile_id,quality,latency_ms,cost_cents,failure_rate):
        money(cost_cents)
        bid=str(uuid.uuid4())
        with self.tx():
            self.db.execute("INSERT INTO benchmark_results VALUES(?,?,?,?,?,?,?,?)",
                (bid,role,profile_id,quality,latency_ms,cost_cents,failure_rate,now().isoformat()))
        return bid

    def consultant_cooldown(self,trigger_kind,hours=24):
        until=(now()+timedelta(hours=hours)).isoformat()
        with self.tx():
            row=self.db.execute("SELECT * FROM consultant_reviews WHERE trigger_kind=?",(trigger_kind,)).fetchone()
            if row and row["cooldown_until"] and datetime.fromisoformat(row["cooldown_until"])>now():
                raise PermissionError("Consultant review cooldown active")
            rid=row["id"] if row else str(uuid.uuid4())
            if row:
                self.db.execute("UPDATE consultant_reviews SET last_run=?,cooldown_until=? WHERE trigger_kind=?",
                                (now().isoformat(),until,trigger_kind))
            else:
                self.db.execute("INSERT INTO consultant_reviews VALUES(?,?,?,?)",
                                (rid,trigger_kind,now().isoformat(),until))
        return until

    def list_consultant_reviews(self):
        return [dict(r) for r in self.db.execute(
            "SELECT id, trigger_kind, last_run, cooldown_until FROM consultant_reviews ORDER BY trigger_kind")]

    def events_page(self,cursor=0,limit=50,project_id=None):
        limit=min(max(int(limit),1),200)
        if project_id:
            rows=self.db.execute(
                "SELECT * FROM events WHERE seq>? AND (project_id=? OR project_id IS NULL) ORDER BY seq LIMIT ?",
                (cursor,project_id,limit))
        else:
            rows=self.db.execute("SELECT * FROM events WHERE seq>? ORDER BY seq LIMIT ?",(cursor,limit))
        items=[dict(r) for r in rows]
        next_cursor=items[-1]["seq"] if items else cursor
        return {"items":items,"next_cursor":next_cursor}

    def remember_command(self,key,principal_id,request_hash,status_code,response_body):
        with self.tx():
            existing=self.db.execute("SELECT * FROM command_idempotency WHERE key=?",(key,)).fetchone()
            if existing:
                if existing["request_hash"]!=request_hash:
                    raise ValueError("Idempotency key reused with different payload")
                return dict(existing)
            self.db.execute("INSERT INTO command_idempotency VALUES(?,?,?,?,?,?)",
                (key,principal_id,request_hash,status_code,response_body,now().isoformat()))
            return dict(self.db.execute("SELECT * FROM command_idempotency WHERE key=?",(key,)).fetchone())

    def lookup_command(self,key):
        row=self.db.execute("SELECT * FROM command_idempotency WHERE key=?",(key,)).fetchone()
        return dict(row) if row else None

    def run_idempotent(self, key, principal_id, request_hash, work):
        """Run *work* and persist the idempotency record in one transaction.

        *work* is ``() -> (result, status_code, response_body_json)``. On replay, *work*
        is not called. Returns
        ``{"replay": bool, "result": ..., "status_code": int, "response_body": str}``.
        """
        with self.tx():
            existing = self.lookup_command(key)
            if existing:
                if existing["request_hash"] != request_hash:
                    raise ValueError("Idempotency key reused with different payload")
                return {
                    "replay": True,
                    "result": None,
                    "status_code": existing["status_code"],
                    "response_body": existing["response_body"],
                }
            result, status_code, response_body = work()
            self.db.execute(
                "INSERT INTO command_idempotency VALUES(?,?,?,?,?,?)",
                (key, principal_id, request_hash, status_code, response_body, now().isoformat()),
            )
            return {
                "replay": False,
                "result": result,
                "status_code": status_code,
                "response_body": response_body,
            }

    def list_company_settings(self):
        from company.settings_runtime import list_settings
        return {"items": list_settings(self)}

    def patch_company_settings(self, actor, updates):
        self._ceo_or_admin_companion(actor)
        from company.settings_catalog import EDITABLE_KEYS, validate_value
        if not isinstance(updates, dict) or not updates:
            raise ValueError("updates mapping required")
        changed = []
        with self.tx():
            for key, raw in updates.items():
                if key not in EDITABLE_KEYS:
                    raise ValueError(f"Unknown or read-only setting: {key}")
                value = validate_value(key, raw)
                self.db.execute(
                    "INSERT OR REPLACE INTO company_settings VALUES(?,?,?,?)",
                    (key, canonical(value), now().isoformat(), actor),
                )
                changed.append(key)
            self._event("settings.updated", {"keys": changed}, actor_id=actor)
        from company.settings_runtime import effective
        return {"items": [effective(self, key) for key in changed]}

    def reset_company_settings(self, actor, keys=None, all_overlay=False):
        self._ceo_or_admin_companion(actor)
        from company.settings_catalog import EDITABLE_KEYS
        if not isinstance(all_overlay, bool):
            raise ValueError("all_overlay must be boolean")
        if all_overlay and keys is not None:
            raise ValueError("Provide keys or all_overlay, not both")
        if all_overlay:
            changed = None
        else:
            if not isinstance(keys, list) or not keys:
                raise ValueError("keys list or all_overlay=true required")
            changed = []
            for key in keys:
                if not isinstance(key, str):
                    raise ValueError("each key must be a string")
                if key not in EDITABLE_KEYS:
                    raise ValueError(f"Unknown or read-only setting: {key}")
                if key not in changed:
                    changed.append(key)
        with self.tx():
            if changed is None:
                changed = [
                    row["key"]
                    for row in self.db.execute(
                        "SELECT key FROM company_settings ORDER BY key"
                    )
                    if row["key"] in EDITABLE_KEYS
                ]
            for key in changed:
                self.db.execute("DELETE FROM company_settings WHERE key=?", (key,))
            self._event("settings.reset", {"keys": changed}, actor_id=actor)
        from company.settings_runtime import effective
        return {"items": [effective(self, key) for key in changed]}

    def secrets_status(self):
        from company.settings_runtime import secrets_status
        return {"secrets": secrets_status()}

    def effective_setting(self, key):
        from company.settings_runtime import effective
        return effective(self, key)["value"]

    def prune_idempotency_keys(self, actor, older_than_days=None):
        """Delete idempotency rows older than the retention window (default 7 days)."""
        self._ceo_or_admin_companion(actor)
        from company.idempotency_prune import prune_command_idempotency
        days = (
            self.effective_setting("FS_CORP_IDEMPOTENCY_RETENTION_DAYS")
            if older_than_days is None
            else int(older_than_days)
        )
        with self.tx():
            deleted = prune_command_idempotency(self.db, older_than_days=days, now_dt=now())
            self._event(
                "ops.idempotency_pruned",
                {"deleted": deleted, "older_than_days": days},
                actor_id=actor,
            )
        return {"deleted": deleted, "older_than_days": days}

    def _hardware_catalog(self, path=None):
        path=Path(path or Path(__file__).resolve().parents[1]/"config"/"hardware-skills.json")
        return json.loads(path.read_text())

    def _normalize_platform(self, platform, catalog=None):
        catalog=catalog or self._hardware_catalog()
        key=(platform or "").strip().lower().replace("_","-")
        if key in catalog["platforms"]:return key
        alias=catalog.get("aliases",{}).get(key)
        if alias:return alias
        raise ValueError("Unknown hardware platform")

    def seed_hardware_skills(self, path=None):
        catalog=self._hardware_catalog(path)
        with self.tx():
            for sid,body in catalog["skills"].items():
                self.db.execute("INSERT OR REPLACE INTO skills VALUES(?,?,?,?)",
                    (sid,body["name"],body["platform"],body["department_id"]))
            self._event("hardware.skills_seeded",{"skills":len(catalog["skills"])})

    def _require_project_skills(self, project):
        gaps=self.project_skill_gaps(project)
        if gaps:
            raise PermissionError("Skill gap; assigned employees must study approved sources first: "+",".join(gaps))

    def _require_employee_training(self, actor):
        if not self.db.execute("SELECT 1 FROM employees WHERE id=?",(actor,)).fetchone():
            return
        due=self.training_due(actor)
        if due:
            raise PermissionError("Employee training overdue: "+",".join(due))

    def project_skill_gaps(self, project_id):
        row=self.db.execute("SELECT * FROM project_capabilities WHERE project_id=?",(project_id,)).fetchone()
        if not row or row["domain"]!="hardware":return []
        required=json.loads(row["required_skills"])
        held={r["skill_id"] for r in self.db.execute("SELECT DISTINCT skill_id FROM acquired_skills")}
        return [s for s in required if s not in held]

    def enroll_hardware_project(self,actor,project_id,brief,platform,classification="internal"):
        catalog=self._hardware_catalog()
        platform=self._normalize_platform(platform,catalog)
        spec=catalog["platforms"][platform]
        if not self.db.execute("SELECT 1 FROM skills LIMIT 1").fetchone():
            self.seed_hardware_skills()
        self.enroll_project(actor,project_id,brief,classification)
        learning=[]
        with self.tx():
            self.db.execute("INSERT OR REPLACE INTO project_capabilities VALUES(?,?,?,?)",
                (project_id,"hardware",platform,canonical(spec["skills"])))
            self._event("project.hardware_enrolled",{"id":project_id,"platform":platform},actor_id=actor,project_id=project_id)
            for skill_id in spec["skills"]:
                for learner in spec["learners"]:
                    lid=digest({"project":project_id,"skill":skill_id,"learner":learner["learner"]})
                    existing=self.db.execute("SELECT * FROM learning_assignments WHERE id=?",(lid,)).fetchone()
                    if not existing:
                        self.db.execute(
                            "INSERT INTO learning_assignments VALUES(?,?,?,?,?,?,?,?,?)",
                            (lid,project_id,skill_id,learner["learner"],learner["department_id"],None,"assigned",None,now().isoformat()))
                        self._event("skill.learning_assigned",{"id":lid,"skill_id":skill_id,"learner":learner["learner"]},
                                    actor_id=actor,project_id=project_id)
                        existing=self.db.execute("SELECT * FROM learning_assignments WHERE id=?",(lid,)).fetchone()
                    learning.append(dict(existing))
        return {"id":project_id,"domain":"hardware","platform":platform,"gaps":self.project_skill_gaps(project_id),"learning":learning}

    def study_skill(self,learner,assignment_id,source,title,published_at,observed_at,summary):
        row=self.db.execute("SELECT * FROM learning_assignments WHERE id=?",(assignment_id,)).fetchone()
        if not row:raise ValueError("Learning assignment not found")
        if row["learner"]!=learner:raise PermissionError("Only the assigned employee may study this skill")
        sid=self.ingest_signal(source=source,title=title,published_at=published_at,observed_at=observed_at,summary=summary)
        with self.tx():
            self.db.execute("UPDATE learning_assignments SET status='studying',signal_id=?,source=? WHERE id=?",
                            (sid,source,assignment_id))
            if self.db.execute("SELECT 1 FROM employees WHERE id=?",(learner,)).fetchone():
                rid=digest({"assignment":assignment_id,"study":sid})[:24]
                self.db.execute("INSERT OR REPLACE INTO training_records VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (rid,learner,assignment_id,row["skill_id"],source,summary,now().isoformat(),None,None,"studied"))
            self._event("skill.studied",{"id":assignment_id,"learner":learner,"signal_id":sid},actor_id=learner,project_id=row["project_id"])
        return sid

    def certify_skill(self,reviewer,assignment_id):
        row=self.db.execute("SELECT * FROM learning_assignments WHERE id=?",(assignment_id,)).fetchone()
        if not row:raise ValueError("Learning assignment not found")
        if row["status"] not in {"studying","acquired"}:raise ValueError("Study evidence is required before certification")
        if reviewer==row["learner"]:raise PermissionError("Learner cannot certify their own skill")
        self._hr_or_ceo(reviewer)
        with self.tx():
            if row["status"]!="acquired":
                self.db.execute("INSERT OR REPLACE INTO acquired_skills VALUES(?,?,?,?)",
                    (row["skill_id"],row["learner"],row["signal_id"],now().isoformat()))
                self.db.execute("UPDATE learning_assignments SET status='acquired' WHERE id=?",(assignment_id,))
                mem_id=f"skill-{row['skill_id']}-{row['learner']}"
                self.db.execute("INSERT OR REPLACE INTO memories VALUES(?,?,?,?,?,?,?)",
                    (mem_id,row["project_id"],row["department_id"],"internal",
                     f"Acquired {row['skill_id']} from {row['source'] or 'approved source'}",1,reviewer))
                self._event("skill.acquired",{"id":assignment_id,"skill_id":row["skill_id"],"holder":row["learner"]},
                            actor_id=reviewer,project_id=row["project_id"])
                rec=self.db.execute("SELECT * FROM training_records WHERE assignment_id=? ORDER BY studied_at DESC",
                                    (assignment_id,)).fetchone()
                if rec:
                    self.db.execute("UPDATE training_records SET certified_at=?,certifier=?,status='certified' WHERE id=?",
                                    (now().isoformat(),reviewer,rec["id"]))
                elif self.db.execute("SELECT 1 FROM employees WHERE id=?",(row["learner"],)).fetchone():
                    rid=digest({"assignment":assignment_id,"certify":reviewer})[:24]
                    self.db.execute("INSERT INTO training_records VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (rid,row["learner"],assignment_id,row["skill_id"],row["source"],None,None,
                         now().isoformat(),reviewer,"certified"))
        return row["skill_id"]

    def development_roster(self,actor):
        self._hr_or_ceo(actor)
        assignments=[dict(r) for r in self.db.execute("SELECT * FROM learning_assignments ORDER BY created_at")]
        acquired=[dict(r) for r in self.db.execute("SELECT * FROM acquired_skills")]
        return {"assignments":assignments,"acquired":acquired}

    def _development_catalog(self, path=None):
        path=Path(path or Path(__file__).resolve().parents[1]/"config"/"employee-development.json")
        return json.loads(path.read_text())

    def seed_development_skills(self, path=None):
        catalog=self._development_catalog(path)
        skills={}
        for body in catalog.get("company_skills",[]):
            skills[body["id"]]=body
        for sid,body in catalog.get("extra_skills",{}).items():
            skills[sid]=body
        with self.tx():
            for sid,body in skills.items():
                self.db.execute("INSERT OR REPLACE INTO skills VALUES(?,?,?,?)",
                    (sid,body["name"],body.get("platform","hr"),body["department_id"]))
            self._event("hr.skills_seeded",{"skills":len(skills)})

    def _pertinent_skills(self, employee_id):
        catalog=self._development_catalog()
        row=self.db.execute("SELECT * FROM employees WHERE id=?",(employee_id,)).fetchone()
        if not row:raise ValueError("Employee not found")
        skills=[s["id"] for s in catalog.get("company_skills",[])]
        dept=row["position_id"].split(":",1)[0]
        skills.extend(catalog.get("department_skills",{}).get(dept,[]))
        skills.extend(catalog.get("position_skills",{}).get(row["position_id"],[]))
        seen=[]
        for sid in skills:
            if sid not in seen:seen.append(sid)
        return seen

    def training_due(self, employee_id):
        catalog=self._development_catalog()
        interval=timedelta(days=int(catalog.get("training_interval_days",90)))
        held={r["skill_id"]:r["acquired_at"] for r in self.db.execute(
            "SELECT skill_id,acquired_at FROM acquired_skills WHERE holder=?",(employee_id,))}
        due=[]
        for sid in self._pertinent_skills(employee_id):
            acquired=held.get(sid)
            if not acquired:
                due.append(sid);continue
            when=datetime.fromisoformat(acquired)
            if when.tzinfo is None:when=when.replace(tzinfo=now().tzinfo)
            if now()-when>interval:due.append(sid)
        return due

    @staticmethod
    def _career_level(row):
        if not row:
            return None
        result=dict(row)
        result["required_skills"]=json.loads(result["required_skills"])
        result["quality_standard"]=json.loads(result["quality_standard"])
        return result

    def seed_career_ladders(self, path=None):
        path=Path(path) if path else (
            Path(__file__).resolve().parents[1]/"config"/"career-ladders.json")
        catalog=json.loads(path.read_text())
        levels=catalog.get("levels") if isinstance(catalog,dict) else None
        if not isinstance(levels,list) or not levels:
            raise ValueError("Career ladder catalog must contain levels")
        seen=set()
        with self.tx():
            for level in levels:
                required={
                    "id","level_index","title","required_skills",
                    "min_accepted_artifacts","min_review_score","quality_standard"}
                if (
                        not isinstance(level,dict)
                        or not required.issubset(level)
                        or not isinstance(level["id"],str) or not level["id"].strip()
                        or type(level["level_index"]) is not int or level["level_index"]<1
                        or not isinstance(level["title"],str) or not level["title"].strip()
                        or not isinstance(level["required_skills"],list)
                        or any(not isinstance(skill,str) or not skill.strip()
                               for skill in level["required_skills"])
                        or type(level["min_accepted_artifacts"]) is not int
                        or level["min_accepted_artifacts"]<0
                        or type(level["min_review_score"]) is not int
                        or not 0<=level["min_review_score"]<=100
                        or not isinstance(level["quality_standard"],dict)
                        or not level["quality_standard"]):
                    raise ValueError("Invalid career level")
                scope=(level.get("division_id"),level.get("department_id"),
                       level["level_index"])
                if scope in seen or (not scope[0] and not scope[1]):
                    raise ValueError("Career level scope and index must be unique")
                seen.add(scope)
                self.db.execute(
                    """INSERT INTO career_levels(
                         id,division_id,department_id,level_index,title,
                         required_skills,min_accepted_artifacts,min_review_score,
                         quality_standard)
                       VALUES(?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(id) DO UPDATE SET
                         division_id=excluded.division_id,
                         department_id=excluded.department_id,
                         level_index=excluded.level_index,
                         title=excluded.title,
                         required_skills=excluded.required_skills,
                         min_accepted_artifacts=excluded.min_accepted_artifacts,
                         min_review_score=excluded.min_review_score,
                         quality_standard=excluded.quality_standard""",
                    (
                        level["id"],level.get("division_id"),
                        level.get("department_id"),level["level_index"],
                        level["title"].strip(),canonical(level["required_skills"]),
                        level["min_accepted_artifacts"],level["min_review_score"],
                        canonical(level["quality_standard"]),
                    ),
                )
                department=level.get("department_id") or "company"
                for skill_id in level["required_skills"]:
                    self.db.execute(
                        """INSERT OR IGNORE INTO skills(
                             id,name,platform,department_id) VALUES(?,?,?,?)""",
                        (skill_id,skill_id.replace("-"," ").title(),"hr",department),
                    )
            self._event("career_ladders.seeded",{"levels":len(levels)})
        return {"levels":len(levels)}

    def _employee_level_rows(self, employee_id):
        employee=self.db.execute(
            "SELECT * FROM employees WHERE id=?",(employee_id,)).fetchone()
        if not employee:
            raise ValueError("Employee not found")
        department=employee["position_id"].split(":",1)[0]
        levels=list(self.db.execute(
            """SELECT * FROM career_levels
               WHERE department_id=? ORDER BY level_index,id""",(department,)))
        current=self.db.execute(
            """SELECT c.* FROM employee_levels e
               JOIN career_levels c ON c.id=e.level_id
               WHERE e.employee_id=?""",(employee_id,)).fetchone()
        return employee,levels,current

    def employee_ladder(self, employee_id):
        _employee,levels,current=self._employee_level_rows(employee_id)
        current_data=self._career_level(current)
        next_row=None
        if current:
            next_row=next(
                (level for level in levels
                 if level["level_index"]>current["level_index"]),None)
        pending=[self._promotion_record(row) for row in self.db.execute(
            """SELECT * FROM promotion_records
               WHERE employee_id=? AND status='pending'
               ORDER BY created_at,id""",(employee_id,))]
        return {
            "employee_id":employee_id,
            "current_level":current_data,
            "next_level":self._career_level(next_row),
            "levels":[self._career_level(level) for level in levels],
            "pending_promotions":pending,
        }

    def standards_for(self, employee_id):
        _employee,_levels,current=self._employee_level_rows(employee_id)
        return json.loads(current["quality_standard"]) if current else None

    def _evaluate_promotion_to(self, employee_id, target):
        _employee,_levels,current=self._employee_level_rows(employee_id)
        if not current:
            raise ValueError("Employee has no current career level")
        accepted=list(self.db.execute(
            """SELECT DISTINCT t.id,t.artifact_hash
               FROM tasks t LEFT JOIN artifacts a ON a.task_id=t.id
               WHERE t.status='accepted' AND (t.actor=? OR a.producer=?)
               ORDER BY t.id""",(employee_id,employee_id)))
        qc=list(self.db.execute(
            """SELECT DISTINCT q.task_id,q.artifact_hash
               FROM qc_inspections q
               JOIN tasks t ON t.id=q.task_id
               LEFT JOIN artifacts a ON a.task_id=t.id
               WHERE q.verdict='pass' AND q.artifact_hash=t.artifact_hash
                 AND (t.actor=? OR a.producer=?)
               ORDER BY q.task_id""",(employee_id,employee_id)))
        held=sorted(row["skill_id"] for row in self.db.execute(
            "SELECT skill_id FROM acquired_skills WHERE holder=?",(employee_id,)))
        required=json.loads(target["required_skills"])
        missing=[skill for skill in required if skill not in held]
        reviews=list(self.db.execute(
            """SELECT score,created_at FROM performance_reviews
               WHERE employee_id=? ORDER BY created_at,rowid""",(employee_id,)))
        scores=[row["score"] for row in reviews]
        trend="stable"
        if len(scores)>=2:
            if scores[-1]>scores[-2]:trend="improving"
            elif scores[-1]<scores[-2]:trend="declining"
        unmet=[]
        if len(accepted)<target["min_accepted_artifacts"]:
            unmet.append({
                "kind":"accepted_artifacts","actual":len(accepted),
                "required":target["min_accepted_artifacts"]})
        if len(qc)<target["min_accepted_artifacts"]:
            unmet.append({
                "kind":"qc_passes","actual":len(qc),
                "required":target["min_accepted_artifacts"]})
        if missing:
            unmet.append({"kind":"required_skills","missing":missing})
        latest=scores[-1] if scores else None
        if latest is None or latest<target["min_review_score"] or trend=="declining":
            unmet.append({
                "kind":"review_score","actual":latest,
                "required":target["min_review_score"],"trend":trend})
        evidence={
            "accepted_artifacts":len(accepted),
            "artifact_hashes":[row["artifact_hash"] for row in accepted
                               if row["artifact_hash"]],
            "qc_passes":len(qc),
            "qc_artifact_hashes":[row["artifact_hash"] for row in qc
                                  if row["artifact_hash"]],
            "certified_skills":held,
            "review_scores":scores,
            "review_trend":trend,
        }
        return {
            "eligible":not unmet,
            "current_level":self._career_level(current),
            "next_level":self._career_level(target),
            "unmet":unmet,
            "evidence":evidence,
        }

    def evaluate_promotion(self, employee_id):
        _employee,levels,current=self._employee_level_rows(employee_id)
        if not current:
            raise ValueError("Employee has no current career level")
        target=next(
            (level for level in levels
             if level["level_index"]>current["level_index"]),None)
        if not target:
            return {
                "eligible":False,
                "current_level":self._career_level(current),
                "next_level":None,
                "unmet":[{"kind":"max_level"}],
                "evidence":{},
            }
        return self._evaluate_promotion_to(employee_id,target)

    @staticmethod
    def _promotion_record(row):
        result=dict(row)
        result["evidence"]=json.loads(result["evidence"])
        return result

    def list_promotions(self, status=None):
        if status is not None and status not in {"pending","approved","rejected"}:
            raise ValueError("Unknown promotion status")
        sql="SELECT * FROM promotion_records"
        args=()
        if status:
            sql+=" WHERE status=?"
            args=(status,)
        sql+=" ORDER BY created_at,id"
        return {"items":[self._promotion_record(row)
                         for row in self.db.execute(sql,args)]}

    @staticmethod
    def _staffing_proposal(row):
        result=dict(row)
        result["evidence"]=json.loads(result["evidence"])
        return result

    def list_staffing_proposals(self, status=None):
        if status is not None and status not in {"pending","approved","rejected"}:
            raise ValueError("Unknown staffing proposal status")
        sql="SELECT * FROM staffing_proposals"
        args=()
        if status:
            sql+=" WHERE status=?"
            args=(status,)
        sql+=" ORDER BY created_at,id"
        return {"items":[self._staffing_proposal(row)
                         for row in self.db.execute(sql,args)]}

    def create_staffing_proposal(
            self, actor, *, kind, department_id, position_id, rationale,
            evidence, cost_estimate_cents, level_id=None):
        self._hr_or_ceo(actor)
        if kind not in {"hire","reassign","promote","retire_role"}:
            raise ValueError("Unknown staffing proposal kind")
        department_id=str(department_id or "").strip()
        position_id=str(position_id or "").strip()
        rationale=str(rationale or "").strip()
        if not department_id or not self.db.execute(
                "SELECT 1 FROM departments WHERE id=? AND status!='retired'",
                (department_id,)).fetchone():
            raise ValueError("Active department required")
        if not position_id or not position_id.startswith(department_id+":"):
            raise ValueError("Position must belong to the proposal department")
        if not rationale:
            raise ValueError("Staffing rationale required")
        if not isinstance(evidence,dict) or not evidence:
            raise ValueError("Staffing evidence must be a nonempty object")
        money(cost_estimate_cents)
        if level_id is not None and not self.db.execute(
                """SELECT 1 FROM career_levels
                   WHERE id=? AND (department_id=? OR department_id IS NULL)""",
                (level_id,department_id)).fetchone():
            raise ValueError("Unknown career level for department")
        existing=self.db.execute(
            """SELECT * FROM staffing_proposals
               WHERE kind=? AND department_id=? AND position_id=?
                 AND status='pending'""",
            (kind,department_id,position_id)).fetchone()
        if existing:
            return self._staffing_proposal(existing)
        stamp=now().isoformat()
        proposal_id=digest({
            "kind":kind,"department_id":department_id,"position_id":position_id,
            "proposed_by":actor,"created_at":stamp,"evidence":evidence})[:24]
        with self.tx():
            self.db.execute(
                """INSERT INTO staffing_proposals(
                     id,kind,department_id,position_id,level_id,rationale,evidence,
                     cost_estimate_cents,proposed_by,status,approver,decided_at,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?,'pending',NULL,NULL,?)""",
                (proposal_id,kind,department_id,position_id,level_id,rationale,
                 canonical(evidence),cost_estimate_cents,actor,stamp),
            )
            self._event(
                "staffing.proposed",
                {"id":proposal_id,"kind":kind,"department_id":department_id,
                 "position_id":position_id,"evidence_digest":digest(evidence)},
                actor_id=actor,
            )
        return self._staffing_proposal(self.db.execute(
            "SELECT * FROM staffing_proposals WHERE id=?",(proposal_id,)).fetchone())

    def _staffing_position(self, department_id):
        position=self.db.execute(
            """SELECT p.id,COUNT(pa.id) AS active_count
               FROM positions p
               LEFT JOIN position_assignments pa
                 ON pa.position_id=p.id AND pa.status='active'
               WHERE p.department_id=? AND p.status='active'
               GROUP BY p.id ORDER BY active_count,p.display_order,p.id LIMIT 1""",
            (department_id,)).fetchone()
        if position:
            return position["id"]
        department=self.db.execute(
            "SELECT head_title FROM departments WHERE id=?",(department_id,)).fetchone()
        return f"{department_id}:{department['head_title']}"

    def scan_staffing_gaps(self, actor):
        self._hr_or_ceo(actor)
        stamp=now()
        with self.tx():
            cooldown=self.db.execute(
                "SELECT * FROM staffing_scan_cooldown WHERE id='default'").fetchone()
            if cooldown:
                until=datetime.fromisoformat(cooldown["cooldown_until"])
                if until.tzinfo is None:
                    until=until.replace(tzinfo=timezone.utc)
                if stamp<until:
                    raise ValueError(
                        f"Staffing scan cooldown active until {cooldown['cooldown_until']}")

            candidates=[]
            for row in self.db.execute(
                    """SELECT pd.department_id,d.head_title,
                              COUNT(*) AS dispatch_count,
                              GROUP_CONCAT(pd.id) AS dispatch_ids
                       FROM project_dispatches pd
                       JOIN departments d ON d.id=pd.department_id
                       WHERE pd.status='blocked_vacant_head'
                       GROUP BY pd.department_id,d.head_title
                       ORDER BY pd.department_id"""):
                candidates.append({
                    "kind":"hire","department_id":row["department_id"],
                    "position_id":f"{row['department_id']}:{row['head_title']}",
                    "rationale":
                        "Open project dispatches are blocked because the department head is vacant.",
                    "evidence":{
                        "source":"blocked_vacant_head",
                        "dispatch_count":row["dispatch_count"],
                        "dispatch_ids":sorted(row["dispatch_ids"].split(",")),
                    },
                })

            for row in self.db.execute(
                    """SELECT pd.department_id,COUNT(*) AS dispatch_count,
                              GROUP_CONCAT(pd.id) AS dispatch_ids
                       FROM project_dispatches pd
                       WHERE pd.status IN (
                           'queued_for_head','assigned','in_progress','blocked')
                         AND NOT EXISTS (
                           SELECT 1 FROM dispatch_assignments da
                           WHERE da.dispatch_id=pd.id AND da.status='assigned')
                       GROUP BY pd.department_id HAVING COUNT(*)>=3
                       ORDER BY pd.department_id"""):
                candidates.append({
                    "kind":"hire","department_id":row["department_id"],
                    "position_id":self._staffing_position(row["department_id"]),
                    "rationale":
                        "The department has a high open-dispatch queue without active assignments.",
                    "evidence":{
                        "source":"unassigned_dispatch_queue",
                        "queue_depth":row["dispatch_count"],
                        "dispatch_ids":sorted(row["dispatch_ids"].split(",")),
                        "threshold":3,
                    },
                })

            floorplan=self.floorplan_status()
            for gap in floorplan["unmet_requirements"]:
                candidates.append({
                    "kind":"hire","department_id":gap["department_id"],
                    "position_id":self._staffing_position(gap["department_id"]),
                    "rationale":
                        "Persisted headquarters capacity does not meet this department's room requirement.",
                    "evidence":{
                        "source":"unmet_room_requirement",
                        "floorplan_id":floorplan["floorplan_id"],
                        **gap,
                    },
                })

            for employee in self.db.execute(
                    "SELECT id,position_id FROM employees WHERE status='active' ORDER BY id"):
                due=self.training_due(employee["id"])
                if due:
                    candidates.append({
                        "kind":"reassign",
                        "department_id":employee["position_id"].split(":",1)[0],
                        "position_id":employee["position_id"],
                        "rationale":
                            "Overdue pertinent training requires a reviewed reassignment or training plan.",
                        "evidence":{
                            "source":"overdue_training",
                            "employee_id":employee["id"],
                            "overdue_skills":due,
                        },
                    })

            items=[]
            created=0
            seen=set()
            for candidate in candidates:
                key=(candidate["kind"],candidate["department_id"],
                     candidate["position_id"])
                if key in seen:
                    continue
                seen.add(key)
                existing=self.db.execute(
                    """SELECT id FROM staffing_proposals
                       WHERE kind=? AND department_id=? AND position_id=?
                         AND status='pending'""",key).fetchone()
                proposal=self.create_staffing_proposal(
                    actor,**candidate,cost_estimate_cents=0)
                if not existing:
                    created+=1
                items.append(proposal)
            cooldown_until=(stamp+timedelta(minutes=15)).isoformat()
            self.db.execute(
                """INSERT INTO staffing_scan_cooldown(id,last_run,cooldown_until)
                   VALUES('default',?,?)
                   ON CONFLICT(id) DO UPDATE SET
                     last_run=excluded.last_run,
                     cooldown_until=excluded.cooldown_until""",
                (stamp.isoformat(),cooldown_until),
            )
            self._event(
                "staffing.scanned",
                {"created":created,"candidates":len(candidates),
                 "cooldown_until":cooldown_until},
                actor_id=actor,
            )
        return {"items":items,"created":created,"cooldown_until":cooldown_until}

    def decide_staffing_proposal(self, actor, proposal_id, decision):
        self._ceo_or_admin_companion(actor)
        if decision not in {"approved","rejected"}:
            raise ValueError("Staffing decision must be approved or rejected")
        with self.tx():
            proposal=self.db.execute(
                "SELECT * FROM staffing_proposals WHERE id=?",
                (proposal_id,)).fetchone()
            if not proposal:
                raise ValueError("Staffing proposal not found")
            if proposal["status"]!="pending":
                raise ValueError("Staffing proposal is already decided")
            evidence=json.loads(proposal["evidence"])
            if decision=="approved" and proposal["kind"]=="hire":
                required=("employee_id","display_name","background")
                if any(not str(evidence.get(field) or "").strip()
                       for field in required):
                    raise ValueError(
                        "Approved hire evidence requires employee_id, display_name, and background")
            decided_at=now().isoformat()
            self.db.execute(
                """UPDATE staffing_proposals
                   SET status=?,approver=?,decided_at=? WHERE id=?""",
                (decision,actor,decided_at,proposal_id),
            )
            hire=None
            if decision=="approved" and proposal["kind"]=="hire":
                hire=self.hire_employee(
                    actor,evidence["employee_id"],proposal["position_id"],
                    evidence["display_name"],evidence.get("attributes") or {},
                    evidence["background"],
                )
            self._event(
                "staffing.decided",
                {"id":proposal_id,"kind":proposal["kind"],"decision":decision,
                 "employee_id":evidence.get("employee_id") if hire else None},
                actor_id=actor,
            )
        result=self._staffing_proposal(self.db.execute(
            "SELECT * FROM staffing_proposals WHERE id=?",(proposal_id,)).fetchone())
        if hire:
            result["hire"]=hire
        return result

    def propose_promotion(self, actor, employee_id, to_level_id=None):
        self._hr_or_ceo(actor)
        if actor==employee_id:
            raise PermissionError("Employee cannot propose their own promotion")
        _employee,levels,current=self._employee_level_rows(employee_id)
        if not current:
            raise ValueError("Employee has no current career level")
        target=None
        if to_level_id:
            target=next((level for level in levels if level["id"]==to_level_id),None)
            if not target or target["level_index"]<=current["level_index"]:
                raise ValueError("Promotion target must be a higher level in the same ladder")
        else:
            target=next(
                (level for level in levels
                 if level["level_index"]>current["level_index"]),None)
        if not target:
            raise ValueError("No higher career level exists")
        existing=self.db.execute(
            """SELECT * FROM promotion_records
               WHERE employee_id=? AND to_level=? AND status='pending'""",
            (employee_id,target["id"])).fetchone()
        if existing:
            return self._promotion_record(existing)
        evaluation=self._evaluate_promotion_to(employee_id,target)
        stamp=now().isoformat()
        promotion_id=digest({
            "employee":employee_id,"from":current["id"],"to":target["id"],
            "proposed_by":actor,"created_at":stamp})[:24]
        with self.tx():
            self.db.execute(
                """INSERT INTO promotion_records(
                     id,employee_id,from_level,to_level,evidence,proposed_by,
                     approved_by,status,created_at,decided_at)
                   VALUES(?,?,?,?,?,?,NULL,'pending',?,NULL)""",
                (promotion_id,employee_id,current["id"],target["id"],
                 canonical(evaluation),actor,stamp),
            )
            self._event(
                "promotion.proposed",
                {"id":promotion_id,"employee_id":employee_id,
                 "from_level":current["id"],"to_level":target["id"],
                 "eligible":evaluation["eligible"]},
                actor_id=actor,
            )
        return self._promotion_record(self.db.execute(
            "SELECT * FROM promotion_records WHERE id=?",(promotion_id,)).fetchone())

    def decide_promotion(self, actor, promotion_id, decision):
        self._ceo_or_admin_companion(actor)
        if decision not in {"approved","rejected"}:
            raise ValueError("Promotion decision must be approved or rejected")
        promotion=self.db.execute(
            "SELECT * FROM promotion_records WHERE id=?",(promotion_id,)).fetchone()
        if not promotion:
            raise ValueError("Promotion not found")
        if promotion["status"]!="pending":
            raise ValueError("Promotion is already decided")
        current=self.db.execute(
            "SELECT level_id FROM employee_levels WHERE employee_id=?",
            (promotion["employee_id"],)).fetchone()
        if not current or current["level_id"]!=promotion["from_level"]:
            raise ValueError("Promotion evidence is stale")
        target=self.db.execute(
            "SELECT * FROM career_levels WHERE id=?",(promotion["to_level"],)).fetchone()
        stamp=now().isoformat()
        with self.tx():
            self.db.execute(
                """UPDATE promotion_records
                   SET status=?,approved_by=?,decided_at=? WHERE id=?""",
                (decision,actor,stamp,promotion_id),
            )
            training=[]
            if decision=="approved":
                self.db.execute(
                    """INSERT INTO employee_levels(
                         employee_id,level_id,effective_at,set_by) VALUES(?,?,?,?)
                       ON CONFLICT(employee_id) DO UPDATE SET
                         level_id=excluded.level_id,
                         effective_at=excluded.effective_at,
                         set_by=excluded.set_by""",
                    (promotion["employee_id"],target["id"],stamp,actor),
                )
                held={row["skill_id"] for row in self.db.execute(
                    "SELECT skill_id FROM acquired_skills WHERE holder=?",
                    (promotion["employee_id"],))}
                missing=[skill for skill in json.loads(target["required_skills"])
                         if skill not in held]
                training=self._assign_training_skills(
                    promotion["employee_id"],actor,missing)
            self._event(
                "promotion.decided",
                {"id":promotion_id,"employee_id":promotion["employee_id"],
                 "decision":decision,"training_assignments":
                     [item["id"] for item in training]},
                actor_id=actor,
            )
        result=self._promotion_record(self.db.execute(
            "SELECT * FROM promotion_records WHERE id=?",(promotion_id,)).fetchone())
        result["training"]=training
        return result

    def _assign_training_skills(self, employee_id, actor, skills):
        row=self.db.execute(
            "SELECT position_id FROM employees WHERE id=?",(employee_id,)).fetchone()
        if not row:
            raise ValueError("Employee not found")
        dept=row["position_id"].split(":",1)[0]
        created=[]
        with self.tx():
            for skill_id in skills:
                open_row=self.db.execute(
                    """SELECT * FROM learning_assignments
                       WHERE learner=? AND skill_id=?
                         AND status IN ('assigned','studying')""",
                    (employee_id,skill_id)).fetchone()
                if open_row:
                    created.append(dict(open_row))
                    continue
                lid=digest({
                    "employee":employee_id,"skill":skill_id,
                    "cycle":now().isoformat()})
                self.db.execute(
                    "INSERT INTO learning_assignments VALUES(?,?,?,?,?,?,?,?,?)",
                    (lid,"hr-training",skill_id,employee_id,dept,None,
                     "assigned",None,now().isoformat()))
                self._event(
                    "skill.learning_assigned",
                    {"id":lid,"skill_id":skill_id,"learner":employee_id},
                    actor_id=actor,project_id="hr-training")
                created.append(dict(self.db.execute(
                    "SELECT * FROM learning_assignments WHERE id=?",(lid,)).fetchone()))
        return created

    def _assign_training(self, employee_id, actor):
        due=self.training_due(employee_id)
        return self._assign_training_skills(employee_id,actor,due)

    def hire_employee(self,actor,employee_id,position_id,display_name,attributes,background):
        self._hr_or_ceo(actor)
        if not employee_id or not str(employee_id).strip():raise ValueError("Employee id required")
        if not display_name or not str(display_name).strip():raise ValueError("Display name required")
        if not position_id or ":" not in position_id:raise ValueError("Position id must be department:title")
        if not isinstance(attributes,dict):raise ValueError("Attributes must be an object")
        if not background or not str(background).strip():raise ValueError("Background required")
        if self.db.execute("SELECT 1 FROM employees WHERE id=?",(employee_id,)).fetchone():
            raise ValueError("Employee already hired")
        self.seed_development_skills()
        self.seed_career_ladders()
        with self.tx():
            self.db.execute(
                """INSERT INTO employees(
                     id,position_id,display_name,attributes,background,hired_at,status)
                   VALUES(?,?,?,?,?,?,?)""",
                (employee_id,position_id,display_name,canonical(attributes),background.strip(),now().isoformat(),"active"))
            department=position_id.split(":",1)[0]
            entry=self.db.execute(
                """SELECT id FROM career_levels WHERE department_id=?
                   ORDER BY level_index,id LIMIT 1""",(department,)).fetchone()
            if entry:
                self.db.execute(
                    "INSERT INTO employee_levels VALUES(?,?,?,?)",
                    (employee_id,entry["id"],now().isoformat(),actor),
                )
            self._event("employee.hired",{"id":employee_id,"position_id":position_id},actor_id=actor)
        training=self._assign_training(employee_id,actor)
        return {"id":employee_id,"position_id":position_id,"display_name":display_name,
                "attributes":attributes,"background":background.strip(),"training":training,
                "level":self.employee_ladder(employee_id)["current_level"]}

    def employee(self, employee_id):
        row=self.db.execute("SELECT * FROM employees WHERE id=?",(employee_id,)).fetchone()
        if not row:raise ValueError("Employee not found")
        data=dict(row)
        data["attributes"]=json.loads(data["attributes"])
        data["strengths"]=json.loads(data["strengths"]) if data.get("strengths") else []
        return data

    def seed_sprite_sets(self, path=None):
        path = Path(path) if path else (
            Path(__file__).resolve().parents[1] / "config" / "sprite-sets.json")
        catalog = json.loads(path.read_text())
        if not isinstance(catalog, dict) or not catalog:
            raise ValueError("Sprite set catalog must be a nonempty object")
        with self.tx():
            for sprite_id, item in catalog.items():
                if (
                        not isinstance(sprite_id, str) or not sprite_id.strip()
                        or not isinstance(item, dict)
                        or not isinstance(item.get("layers"), dict)
                        or any(
                            not isinstance(values, list)
                            for values in item.get("layers", {}).values())
                        or not isinstance(item.get("allowed_palettes"), list)
                        or not isinstance(item.get("body"), list)):
                    raise ValueError("Invalid sprite set catalog")
                self.db.execute(
                    """INSERT INTO sprite_sets(
                         id,layers,allowed_palettes,body) VALUES(?,?,?,?)
                       ON CONFLICT(id) DO UPDATE SET
                         layers=excluded.layers,
                         allowed_palettes=excluded.allowed_palettes,
                         body=excluded.body""",
                    (
                        sprite_id,
                        canonical(item["layers"]),
                        canonical(item["allowed_palettes"]),
                        canonical(item["body"]),
                    ),
                )
        return {"sprite_sets": sorted(catalog)}

    def _sprite_set(self, sprite_set):
        row = self.db.execute(
            "SELECT * FROM sprite_sets WHERE id=?", (sprite_set,)).fetchone()
        if not row:
            self.seed_sprite_sets()
            row = self.db.execute(
                "SELECT * FROM sprite_sets WHERE id=?", (sprite_set,)).fetchone()
        if not row:
            raise ValueError("Unknown sprite_set")
        result = dict(row)
        for field in ("layers", "allowed_palettes", "body"):
            result[field] = json.loads(result[field])
        return result

    def _worker_sprite(self, employee_id):
        row = self.db.execute(
            "SELECT * FROM worker_sprites WHERE employee_id=?", (employee_id,)).fetchone()
        if not row:
            return None
        result = dict(row)
        result["accessories"] = json.loads(result["accessories"])
        return result

    @staticmethod
    def _validate_sprite_accessories(layers, accessories):
        if accessories is None:
            return {}
        if isinstance(accessories, dict):
            for layer, selected in accessories.items():
                if layer not in layers:
                    raise ValueError(f"Unknown accessory layer: {layer}")
                values = selected if isinstance(selected, list) else [selected]
                if any(value not in layers[layer] for value in values):
                    raise ValueError(f"Invalid accessory for layer: {layer}")
            return accessories
        if isinstance(accessories, list):
            allowed = {
                value for values in layers.values() for value in values
            }
            if any(value not in allowed for value in accessories):
                raise ValueError("Invalid accessory")
            return accessories
        raise ValueError("accessories must be an object or list")

    def set_worker_sprite(
            self, actor, employee_id, sprite_set, body=None, palette=None,
            accessories=None):
        self._hr_or_ceo(actor)
        if not self.db.execute(
                "SELECT 1 FROM employees WHERE id=?", (employee_id,)).fetchone():
            raise ValueError("Employee not found")
        catalog = self._sprite_set(sprite_set)
        if body is not None and body not in catalog["body"]:
            raise ValueError("Invalid body for sprite_set")
        if palette is not None and palette not in catalog["allowed_palettes"]:
            raise ValueError("Invalid palette for sprite_set")
        accessories = self._validate_sprite_accessories(
            catalog["layers"], accessories)
        stamp = now().isoformat()
        with self.tx():
            self.db.execute(
                """INSERT INTO worker_sprites(
                     employee_id,sprite_set,body,palette,accessories,updated_by,updated_at)
                   VALUES(?,?,?,?,?,?,?)
                   ON CONFLICT(employee_id) DO UPDATE SET
                     sprite_set=excluded.sprite_set,body=excluded.body,
                     palette=excluded.palette,accessories=excluded.accessories,
                     updated_by=excluded.updated_by,updated_at=excluded.updated_at""",
                (
                    employee_id, sprite_set, body, palette,
                    canonical(accessories), actor, stamp,
                ),
            )
            self._event(
                "worker.sprite_updated",
                {"employee_id": employee_id, "sprite_set": sprite_set},
                actor_id=actor,
            )
        return self._worker_sprite(employee_id)

    def update_worker_profile(self, actor, employee_id, **fields):
        self._hr_or_ceo(actor)
        allowed = {
            "headline", "viewpoint", "strengths", "growth_focus",
            "background", "attributes",
        }
        unknown = set(fields) - allowed
        if unknown:
            raise ValueError(f"Unknown fields: {sorted(unknown)}")
        if not fields:
            raise ValueError("No fields to update")
        current = self.employee(employee_id)
        if "strengths" in fields:
            strengths = fields["strengths"]
            if (
                    not isinstance(strengths, list)
                    or any(not isinstance(value, str) for value in strengths)):
                raise ValueError("strengths must be a list of strings")
        else:
            strengths = current["strengths"]
        attributes = fields.get("attributes", current["attributes"])
        if not isinstance(attributes, dict):
            raise ValueError("attributes must be an object")
        background = fields.get("background", current["background"])
        if not isinstance(background, str) or not background.strip():
            raise ValueError("background required")
        values = {
            "headline": fields.get("headline", current.get("headline")),
            "viewpoint": fields.get("viewpoint", current.get("viewpoint")),
            "strengths": canonical(strengths),
            "growth_focus": fields.get(
                "growth_focus", current.get("growth_focus")),
            "background": background.strip(),
            "attributes": canonical(attributes),
        }
        for field in ("headline", "viewpoint", "growth_focus"):
            if values[field] is not None and not isinstance(values[field], str):
                raise ValueError(f"{field} must be text or null")
        with self.tx():
            self.db.execute(
                """UPDATE employees SET headline=?,viewpoint=?,strengths=?,
                     growth_focus=?,background=?,attributes=? WHERE id=?""",
                (
                    values["headline"], values["viewpoint"], values["strengths"],
                    values["growth_focus"], values["background"],
                    values["attributes"], employee_id,
                ),
            )
            self._event(
                "worker.profile_updated",
                {"employee_id": employee_id, "fields": sorted(fields)},
                actor_id=actor,
            )
        return self.employee(employee_id)

    def worker_card(self, employee_id):
        identity = self.employee(employee_id)
        skills = [
            {
                "id": row["id"],
                "name": row["name"],
                "platform": row["platform"],
                "department_id": row["department_id"],
                "source_hash": row["source_hash"],
                "acquired_at": row["acquired_at"],
            }
            for row in self.db.execute(
                """SELECT s.*,a.source_hash,a.acquired_at
                   FROM acquired_skills a JOIN skills s ON s.id=a.skill_id
                   WHERE a.holder=? ORDER BY s.name,s.id""",
                (employee_id,),
            )
        ]
        assignments = [
            dict(row) for row in self.db.execute(
                """SELECT pa.*,p.title FROM position_assignments pa
                   JOIN positions p ON p.id=pa.position_id
                   WHERE pa.principal_id=? AND pa.status='active'
                   ORDER BY pa.assigned_at,pa.id""",
                (employee_id,),
            )
        ]
        return {
            "identity": identity,
            "strengths": identity["strengths"],
            "viewpoint": identity.get("viewpoint"),
            "skills": skills,
            "position_assignments": assignments,
            "ladder": self.employee_ladder(employee_id),
            "sprite": self._worker_sprite(employee_id),
            "sprite_placeholder": {
                "kind": "neutral",
                "label": identity["display_name"],
            },
        }

    def schedule_company_training(self,actor):
        self._hr_or_ceo(actor)
        self.seed_development_skills()
        created=[]
        for row in self.db.execute("SELECT id FROM employees WHERE status='active'"):
            created.extend(self._assign_training(row["id"],actor))
        return created

    def training_file(self,actor,employee_id):
        if actor!=employee_id:self._hr_or_ceo(actor)
        if not self.db.execute("SELECT 1 FROM employees WHERE id=?",(employee_id,)).fetchone():
            raise ValueError("Employee not found")
        records=[dict(r) for r in self.db.execute(
            "SELECT * FROM training_records WHERE employee_id=? ORDER BY studied_at, certified_at",(employee_id,))]
        return {"employee_id":employee_id,"records":records,"due":self.training_due(employee_id)}

    def set_performance_goal(self,actor,employee_id,title,target,period):
        self._hr_or_ceo(actor)
        if not self.db.execute("SELECT 1 FROM employees WHERE id=?",(employee_id,)).fetchone():
            raise ValueError("Employee not found")
        if not title or not str(title).strip():raise ValueError("Goal title required")
        if not period or not str(period).strip():raise ValueError("Goal period required")
        if not isinstance(target,int) or isinstance(target,bool) or target<0:
            raise ValueError("Goal target must be a nonnegative integer")
        with self.tx():
            gid=digest({"employee":employee_id,"title":title,"period":period,"at":now().isoformat()})[:24]
            self.db.execute("INSERT INTO performance_goals VALUES(?,?,?,?,?,?,?)",
                (gid,employee_id,title.strip(),target,period.strip(),actor,now().isoformat()))
            self._event("performance.goal_set",{"id":gid,"employee_id":employee_id},actor_id=actor)
        return dict(self.db.execute("SELECT * FROM performance_goals WHERE id=?",(gid,)).fetchone())

    def record_performance_review(self,reviewer,employee_id,score,notes):
        self._hr_or_ceo(reviewer)
        if reviewer==employee_id:raise PermissionError("Employee cannot record their own performance review")
        if not self.db.execute("SELECT 1 FROM employees WHERE id=?",(employee_id,)).fetchone():
            raise ValueError("Employee not found")
        if not isinstance(score,int) or isinstance(score,bool) or score<0 or score>100:
            raise ValueError("Review score must be an integer from 0 to 100")
        if not notes or not str(notes).strip():raise ValueError("Review notes required")
        with self.tx():
            rid=digest({"employee":employee_id,"reviewer":reviewer,"at":now().isoformat()})[:24]
            self.db.execute("INSERT INTO performance_reviews VALUES(?,?,?,?,?,?)",
                (rid,employee_id,reviewer,score,notes.strip(),now().isoformat()))
            self._event("performance.reviewed",{"id":rid,"employee_id":employee_id,"score":score},actor_id=reviewer)
        return dict(self.db.execute("SELECT * FROM performance_reviews WHERE id=?",(rid,)).fetchone())

    def performance_trend(self,actor,employee_id):
        self._hr_or_ceo(actor)
        if not self.db.execute("SELECT 1 FROM employees WHERE id=?",(employee_id,)).fetchone():
            raise ValueError("Employee not found")
        points=[{"at":r["created_at"],"score":r["score"],"reviewer":r["reviewer"]}
                for r in self.db.execute(
                    "SELECT * FROM performance_reviews WHERE employee_id=? ORDER BY created_at, rowid",(employee_id,))]
        direction="stable"
        if len(points)>=2:
            if points[-1]["score"]>points[-2]["score"]:direction="improving"
            elif points[-1]["score"]<points[-2]["score"]:direction="declining"
        goals=[dict(r) for r in self.db.execute(
            "SELECT * FROM performance_goals WHERE employee_id=? ORDER BY created_at",(employee_id,))]
        return {"employee_id":employee_id,"points":points,"direction":direction,"goals":goals}

    @staticmethod
    def _scorecard_timestamp(value, name):
        if isinstance(value, datetime):
            parsed = value
        else:
            try:
                parsed = datetime.fromisoformat(str(value))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{name} must be an ISO-8601 timestamp") from exc
        if parsed.tzinfo is None:
            raise ValueError(f"{name} must include a timezone")
        return parsed

    def _objective_row(self, row):
        result = dict(row)
        result["target"] = json.loads(result["target"])
        return result

    def set_objective(self, actor, title, due_at, target=None, division_id=None):
        self._ceo_or_admin_companion(actor)
        if not title or not str(title).strip():
            raise ValueError("Objective title required")
        due = self._scorecard_timestamp(due_at, "due_at")
        if division_id and not self.db.execute(
                "SELECT 1 FROM divisions WHERE id=?", (division_id,)).fetchone():
            raise ValueError("Division not found")
        if target is None:
            target = {}
        try:
            target_json = canonical(target)
        except (TypeError, ValueError) as exc:
            raise ValueError("Objective target must be JSON serializable") from exc
        objective_id = str(uuid.uuid4())
        created_at = now().isoformat()
        with self.tx():
            self.db.execute(
                """INSERT INTO objectives(
                     id,title,division_id,due_at,target,created_by,status,created_at,closed_at)
                   VALUES(?,?,?,?,?,?,?, ?,NULL)""",
                (objective_id, str(title).strip(), division_id, due.isoformat(),
                 target_json, actor, "open", created_at),
            )
            self._event(
                "objective.created",
                {"id": objective_id, "division_id": division_id, "due_at": due.isoformat()},
                actor_id=actor,
            )
        return self._objective_row(self.db.execute(
            "SELECT * FROM objectives WHERE id=?", (objective_id,)).fetchone())

    def close_objective(self, actor, objective_id):
        self._ceo_or_admin_companion(actor)
        row = self.db.execute(
            "SELECT * FROM objectives WHERE id=?", (objective_id,)).fetchone()
        if not row:
            raise ValueError("Objective not found")
        if row["status"] == "closed":
            raise ValueError("Objective already closed")
        closed_at = now().isoformat()
        with self.tx():
            self.db.execute(
                "UPDATE objectives SET status='closed',closed_at=? WHERE id=?",
                (closed_at, objective_id),
            )
            self._event(
                "objective.closed", {"id": objective_id}, actor_id=actor)
        return self._objective_row(self.db.execute(
            "SELECT * FROM objectives WHERE id=?", (objective_id,)).fetchone())

    def list_objectives(self, status=None):
        if status is not None and status not in {"open", "closed"}:
            raise ValueError("Objective status must be open or closed")
        if status is None:
            rows = self.db.execute(
                "SELECT * FROM objectives ORDER BY due_at,created_at,id")
        else:
            rows = self.db.execute(
                "SELECT * FROM objectives WHERE status=? ORDER BY due_at,created_at,id",
                (status,),
            )
        return {"items": [self._objective_row(row) for row in rows]}

    def compute_scorecard(self, period_start=None, period_end=None):
        start = (
            self._scorecard_timestamp(period_start, "period_start")
            if period_start is not None else None)
        end = (
            self._scorecard_timestamp(period_end, "period_end")
            if period_end is not None else None)
        if start and end and start >= end:
            raise ValueError("period_start must be before period_end")

        def in_period(value):
            stamp = self._scorecard_timestamp(value, "persisted timestamp")
            return (start is None or stamp >= start) and (end is None or stamp < end)

        accepted_task_ids = set()
        for event in self.db.execute(
                "SELECT at,body FROM events WHERE kind='project.accepted' ORDER BY seq"):
            if not in_period(event["at"]):
                continue
            body = json.loads(event["body"])
            task_id = body.get("task_id")
            if task_id and self.db.execute(
                    "SELECT 1 FROM tasks WHERE id=? AND status='accepted'",
                    (task_id,)).fetchone():
                accepted_task_ids.add(task_id)

        verdicts = [
            row["verdict"] for row in self.db.execute(
                "SELECT verdict,created_at FROM qc_inspections ORDER BY created_at,rowid")
            if in_period(row["created_at"]) and row["verdict"] in {"pass", "fail"}
        ]
        qc_pass_rate = (
            round(verdicts.count("pass") / len(verdicts), 4) if verdicts else None)

        terminal_dispatch_statuses = {
            "accepted", "cancelled", "canceled", "closed", "completed", "failed", "rejected",
        }
        instant = now()
        overdue_dispatches = 0
        for row in self.db.execute(
                "SELECT due_at,status FROM project_dispatches WHERE due_at IS NOT NULL"):
            due = self._scorecard_timestamp(row["due_at"], "persisted due_at")
            if due < instant and row["status"] not in terminal_dispatch_statuses:
                overdue_dispatches += 1

        spent = self.db.execute(
            "SELECT COALESCE(SUM(cost),0) FROM ledger").fetchone()[0]
        reserved = self.db.execute(
            """SELECT COALESCE(SUM(amount_cents),0) FROM reservations
               WHERE status='reserved'""").fetchone()[0]
        committed = spent + reserved
        budget_adherence = round(spent / committed, 4) if committed else 1.0

        billed_cost_cents = sum(
            row["amount_cents"] for row in self.db.execute(
                "SELECT recorded_at,amount_cents FROM billed_costs")
            if in_period(row["recorded_at"]))
        revenue_cents = sum(
            row["amount_cents"] for row in self.db.execute(
                "SELECT recorded_at,amount_cents FROM revenue")
            if in_period(row["recorded_at"]))
        metrics = {
            "accepted_artifacts": len(accepted_task_ids),
            "qc_pass_rate": qc_pass_rate,
            "overdue_dispatches": overdue_dispatches,
            "budget_adherence": budget_adherence,
            "billed_cost_cents": billed_cost_cents,
            "revenue_cents": revenue_cents,
        }
        return {
            "period_start": start.isoformat() if start else None,
            "period_end": end.isoformat() if end else None,
            "metrics": metrics,
        }

    def record_scorecard_snapshot(self, period_start=None, period_end=None):
        scorecard = self.compute_scorecard(period_start, period_end)
        snapshot_id = str(uuid.uuid4())
        created_at = now().isoformat()
        with self.tx():
            self.db.execute(
                """INSERT INTO scorecard_snapshots(
                     id,period_start,period_end,metrics,created_at)
                   VALUES(?,?,?,?,?)""",
                (snapshot_id, scorecard["period_start"], scorecard["period_end"],
                 canonical(scorecard["metrics"]), created_at),
            )
            self._event(
                "scorecard.snapshot_recorded",
                {"id": snapshot_id, "period_start": scorecard["period_start"],
                 "period_end": scorecard["period_end"]},
            )
        return {
            "id": snapshot_id,
            **scorecard,
            "created_at": created_at,
        }

    def _is_paused(self):
        return self.db.execute("SELECT value FROM settings WHERE key='paused'").fetchone()[0] == "true"

    def _project_blockers(self, project_id):
        blockers = []
        if self._is_paused():
            blockers.append("company_paused")
        if self.project_skill_gaps(project_id):
            blockers.append("skill_gaps")
        pending_qc = self.db.execute(
            """SELECT 1 FROM tasks t
               LEFT JOIN qc_inspections q ON q.task_id=t.id AND q.verdict='pass'
               WHERE t.project=? AND t.status='produced' AND q.id IS NULL LIMIT 1""",
            (project_id,)).fetchone()
        if pending_qc:
            blockers.append("qc_pending")
        return blockers

    def _project_summary(self, row):
        project_id = row["id"]
        completion = self.db.execute("SELECT 1 FROM completions WHERE project=?", (project_id,)).fetchone()
        open_queue = self.db.execute(
            "SELECT COUNT(*) FROM queue WHERE project=? AND status IN ('queued','leased')",
            (project_id,)).fetchone()[0]
        departments = [r[0] for r in self.db.execute(
            "SELECT department_id FROM project_dispatches WHERE project_id=? ORDER BY created_at",
            (project_id,))]
        return {
            "id": project_id,
            "brief": row["brief"],
            "classification": row["classification"],
            "enrolled_at": row["enrolled_at"],
            "completed": completion is not None,
            "open_queue_count": open_queue,
            "blockers": self._project_blockers(project_id),
            "departments": departments,
        }

    def list_projects(self):
        return [self._project_summary(dict(r)) for r in self.db.execute(
            "SELECT * FROM projects ORDER BY enrolled_at")]

    def list_local_repos(self):
        from company.local_repos import scan_local_repos
        enrolled = {r[0] for r in self.db.execute("SELECT id FROM projects")}
        return scan_local_repos(enrolled_ids=enrolled)

    def project_detail(self, project_id):
        row = self.db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        if not row:
            raise ValueError("Project not found")
        summary = self._project_summary(dict(row))
        tasks = [dict(r) for r in self.db.execute(
            "SELECT * FROM tasks WHERE project=? ORDER BY rowid", (project_id,))]
        timeline = [dict(r) for r in self.db.execute(
            "SELECT seq,at,kind,body FROM events WHERE project_id=? ORDER BY seq DESC LIMIT 30",
            (project_id,))]
        qc = [dict(r) for r in self.db.execute(
            """SELECT q.* FROM qc_inspections q JOIN tasks t ON t.id=q.task_id
               WHERE t.project=? ORDER BY q.created_at DESC""", (project_id,))]
        dispatches = [dict(r) for r in self.db.execute(
            "SELECT * FROM project_dispatches WHERE project_id=? ORDER BY created_at", (project_id,))]
        github = None
        enr = self.db.execute("SELECT * FROM github_enrollments WHERE project_id=?", (project_id,)).fetchone()
        if enr:
            github = {
                "upstream_repo_id": enr["upstream_repo_id"],
                "fork_repo_id": enr["fork_repo_id"],
                "branch_prefix": enr["branch_prefix"],
                "protected_branches": json.loads(enr["protected_branches"]),
                "permitted_actions": json.loads(enr["permitted_actions"]),
            }
        return {**summary, "tasks": tasks, "timeline": timeline,
                "qc_inspections": qc, "dispatches": dispatches,
                "github": github,
                "skill_gaps": self.project_skill_gaps(project_id)}

    def decisions_inbox(self):
        items = []
        for p in self.db.execute("SELECT * FROM proposals WHERE status='pending' ORDER BY rowid"):
            body = json.loads(p["body"])
            items.append({
                "id": p["id"], "kind": "policy",
                "title": f"Policy version {body['version']}",
                "summary": p["reason"], "project_id": None,
                "created_at": None, "evidence_refs": [],
            })
        for p in self.db.execute("SELECT * FROM consultant_proposals WHERE status='pending' ORDER BY rowid"):
            body = json.loads(p["body"])
            items.append({
                "id": p["id"], "kind": "consultant",
                "title": body.get("title", p["id"]),
                "summary": body.get("finding", ""),
                "project_id": None, "created_at": None,
                "evidence_refs": [body.get("evidence", "")[:240]],
            })
        for e in self.db.execute("SELECT * FROM expansions WHERE status IN ('proposed','costed') ORDER BY id"):
            items.append({
                "id": e["id"], "kind": "expansion",
                "title": f"Facilities expansion for {e['source_project']}",
                "summary": e["status"], "project_id": e["source_project"],
                "created_at": None, "evidence_refs": [],
            })
        return {"items": items}

    def ceo_dashboard(self):
        status = self.status()
        reserved = self.db.execute(
            "SELECT COALESCE(SUM(amount_cents),0) FROM reservations WHERE status='reserved'").fetchone()[0]
        dept_queues = []
        for d in self.db.execute("SELECT id,name FROM departments ORDER BY id"):
            cnt = self.db.execute(
                """SELECT COUNT(*) FROM queue
                   WHERE status IN ('queued','leased')
                   AND (actor=? OR actor LIKE ?)""",
                (d["id"], f"{d['id']}:%")).fetchone()[0]
            dept_queues.append({"department_id": d["id"], "name": d["name"], "open_count": cnt})
        return {
            "company": {**status, "paused": self._is_paused(), "reserved_cents": reserved},
            "projects": self.list_projects(),
            "pending_decisions": self.decisions_inbox()["items"],
            "department_queues": dept_queues,
            "owner_inbox_open": self.db.execute(
                "SELECT COUNT(*) FROM owner_requests WHERE status='open'").fetchone()[0],
        }

    def create_owner_request(self, actor, department_id, kind, subject, body, project_id=None):
        if kind not in {"feedback", "escalation", "approval_needed"}:
            raise ValueError("Unknown request kind")
        if not subject or not str(subject).strip():
            raise ValueError("Subject required")
        if not body or not str(body).strip():
            raise ValueError("Body required")
        if actor != self.ceo and not self.db.execute(
                "SELECT 1 FROM identities WHERE principal_id=?", (actor,)).fetchone():
            raise PermissionError("Unknown requester")
        if not self.db.execute("SELECT 1 FROM departments WHERE id=?", (department_id,)).fetchone():
            raise ValueError("Unknown department")
        rid = str(uuid.uuid4())
        with self.tx():
            self.db.execute(
                "INSERT INTO owner_requests VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (rid, project_id, department_id, actor, kind, subject.strip(), body.strip(),
                 "open", None, now().isoformat(), None))
            self._event("owner.request_created", {"id": rid, "kind": kind, "department_id": department_id},
                        actor_id=actor, project_id=project_id)
        row = dict(self.db.execute("SELECT * FROM owner_requests WHERE id=?", (rid,)).fetchone())
        self.notify_push("owner_inbox", subject.strip(), {"request_id": rid})
        return row

    def register_push_subscription(self, actor, endpoint, keys=None):
        """Web Push enrollment for the CEO or a paired companion principal."""
        from urllib.parse import urlparse
        if actor != self.ceo and not self.db.execute(
                "SELECT 1 FROM identities WHERE principal_id=? AND kind='service'", (actor,)).fetchone():
            raise PermissionError("CEO or paired companion required")
        parsed = urlparse(endpoint)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("Push endpoint needs an HTTPS URL")
        sid = digest({"endpoint": endpoint})
        with self.tx():
            self.db.execute("INSERT OR REPLACE INTO push_subscriptions VALUES(?,?,?,?,?,?)",
                            (sid, actor, endpoint, canonical(keys or {}), now().isoformat(), "active"))
            self._event("push.subscription_registered", {"id": sid}, actor_id=actor)
        return dict(self.db.execute("SELECT * FROM push_subscriptions WHERE id=?", (sid,)).fetchone())

    def revoke_push_subscription(self, actor, subscription_id):
        row = self.db.execute("SELECT * FROM push_subscriptions WHERE id=?", (subscription_id,)).fetchone()
        if not row:
            raise ValueError("Push subscription not found")
        if actor != self.ceo and row["principal_id"] != actor:
            raise PermissionError("Cannot revoke another principal's push subscription")
        with self.tx():
            self.db.execute("UPDATE push_subscriptions SET status='revoked' WHERE id=?", (subscription_id,))
            self._event("push.subscription_revoked", {"id": subscription_id}, actor_id=actor)
        return dict(self.db.execute("SELECT * FROM push_subscriptions WHERE id=?", (subscription_id,)).fetchone())

    def list_push_subscriptions(self, actor):
        """Active push subscriptions visible to this principal (no key material)."""
        if actor == self.ceo:
            rows = self.db.execute(
                "SELECT id, principal_id, endpoint, created_at, status FROM push_subscriptions "
                "WHERE status='active' ORDER BY created_at DESC")
        else:
            if not self.db.execute(
                    "SELECT 1 FROM identities WHERE principal_id=? AND kind='service'", (actor,)).fetchone():
                raise PermissionError("CEO or paired companion required")
            rows = self.db.execute(
                "SELECT id, principal_id, endpoint, created_at, status FROM push_subscriptions "
                "WHERE status='active' AND principal_id=? ORDER BY created_at DESC", (actor,))
        return [dict(row) for row in rows]

    def notify_push(self, kind, subject, payload=None):
        """Record a delivery attempt for each active subscription; live send when VAPID is configured."""
        if not subject or not str(subject).strip():
            raise ValueError("Subject required")
        payload = payload or {}
        deliveries = []
        from .adapters import PushNotificationAdapter
        for sub in self.db.execute("SELECT * FROM push_subscriptions WHERE status='active'"):
            did = digest({"subscription_id": sub["id"], "kind": kind, "subject": subject})
            existing = self.db.execute("SELECT * FROM push_deliveries WHERE id=?", (did,)).fetchone()
            if existing:
                deliveries.append(dict(existing))
                continue
            try:
                PushNotificationAdapter().send(
                    {"endpoint": sub["endpoint"], "keys": json.loads(sub["keys"])},
                    {"kind": kind, "subject": subject, **payload})
            except NotImplementedError:
                with self.tx():
                    self.db.execute("INSERT INTO push_deliveries VALUES(?,?,?,?,?,?)",
                                    (did, sub["id"], kind, subject, "live_unavailable", now().isoformat()))
                    self._event("push.delivery_live_unavailable", {"id": did, "kind": kind})
                deliveries.append(dict(self.db.execute("SELECT * FROM push_deliveries WHERE id=?", (did,)).fetchone()))
                continue
            except Exception as exc:
                with self.tx():
                    self.db.execute("INSERT INTO push_deliveries VALUES(?,?,?,?,?,?)",
                                    (did, sub["id"], kind, subject, "failed", now().isoformat()))
                    self._event("push.delivery_failed", {"id": did, "kind": kind, "error": str(exc)})
                deliveries.append(dict(self.db.execute("SELECT * FROM push_deliveries WHERE id=?", (did,)).fetchone()))
                continue
            with self.tx():
                self.db.execute("INSERT INTO push_deliveries VALUES(?,?,?,?,?,?)",
                                (did, sub["id"], kind, subject, "applied", now().isoformat()))
                self._event("push.delivery_applied", {"id": did, "kind": kind})
            deliveries.append(dict(self.db.execute("SELECT * FROM push_deliveries WHERE id=?", (did,)).fetchone()))
        return {"deliveries": deliveries}

    def owner_inbox(self, status=None):
        if status and status not in {"open", "answered", "closed"}:
            raise ValueError("Invalid inbox status")
        if status:
            rows = self.db.execute(
                "SELECT * FROM owner_requests WHERE status=? ORDER BY created_at DESC", (status,))
        else:
            rows = self.db.execute("SELECT * FROM owner_requests ORDER BY created_at DESC")
        return {"items": [dict(r) for r in rows]}

    def respond_owner_request(self, actor, request_id, response, close=True):
        self._ceo_or_admin_companion(actor)
        if not response or not str(response).strip():
            raise ValueError("Response required")
        with self.tx():
            row = self.db.execute("SELECT * FROM owner_requests WHERE id=?", (request_id,)).fetchone()
            if not row:
                raise ValueError("Owner request not found")
            if row["status"] != "open":
                raise ValueError("Request is not open")
            new_status = "closed" if close else "answered"
            self.db.execute(
                "UPDATE owner_requests SET status=?, owner_response=?, responded_at=? WHERE id=?",
                (new_status, response.strip(), now().isoformat(), request_id))
            self._event("owner.request_responded", {"id": request_id, "status": new_status},
                        actor_id=actor, project_id=row["project_id"])
        return dict(self.db.execute("SELECT * FROM owner_requests WHERE id=?", (request_id,)).fetchone())

    def create_cross_dept_request(
            self, actor, *, project_id, requesting_department_id,
            delivering_department_id, budget_owner, due_at,
            acceptance_criteria, escalation_path, budget_cents, subject, brief):
        if not self.db.execute(
                "SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone():
            raise ValueError("Project not found")
        known = {
            row[0] for row in self.db.execute(
                "SELECT id FROM departments WHERE id IN (?,?)",
                (requesting_department_id, delivering_department_id),
            )
        }
        if requesting_department_id not in known:
            raise ValueError(f"Unknown department {requesting_department_id}")
        if delivering_department_id not in known:
            raise ValueError(f"Unknown department {delivering_department_id}")
        if requesting_department_id == delivering_department_id:
            raise ValueError("Cross-department request requires different departments")
        if not self.department_dispatchable(project_id, delivering_department_id):
            raise ValueError(
                f"Department {delivering_department_id} is dormant for this project; activate first")

        is_ceo = actor == self.ceo or str(actor).startswith("companion-admin-")
        if not is_ceo:
            requesting_seat = self.db.execute(
                """SELECT principal_id FROM department_seats
                   WHERE department_id=? AND status='active'""",
                (requesting_department_id,),
            ).fetchone()
            if not requesting_seat or requesting_seat["principal_id"] != actor:
                raise PermissionError("Seated requesting department head required")

        required = {
            "budget_owner": budget_owner,
            "due_at": due_at,
            "acceptance_criteria": acceptance_criteria,
            "escalation_path": escalation_path,
            "subject": subject,
            "brief": brief,
        }
        normalized = {}
        for field, value in required.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} required")
            normalized[field] = value.strip()
        try:
            datetime.fromisoformat(normalized["due_at"].replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("due_at must be an ISO-8601 timestamp") from exc
        money(budget_cents)

        request_id = str(uuid.uuid4())
        created_at = now().isoformat()
        with self.tx():
            self.db.execute(
                """INSERT INTO cross_department_requests(
                       id, project_id, requesting_department_id,
                       delivering_department_id, budget_owner, due_at,
                       acceptance_criteria, escalation_path, budget_cents, status,
                       created_by, created_at, accepted_by, accepted_at, subject, brief)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    request_id, project_id, requesting_department_id,
                    delivering_department_id, normalized["budget_owner"],
                    normalized["due_at"], normalized["acceptance_criteria"],
                    normalized["escalation_path"], budget_cents,
                    "pending_acceptance", actor, created_at, None, None,
                    normalized["subject"], normalized["brief"],
                ),
            )
            self._event(
                "cross_department.request_created",
                {
                    "id": request_id,
                    "requesting_department_id": requesting_department_id,
                    "delivering_department_id": delivering_department_id,
                    "budget_cents": budget_cents,
                    "status": "pending_acceptance",
                },
                actor_id=actor,
                project_id=project_id,
            )
        return dict(self.db.execute(
            "SELECT * FROM cross_department_requests WHERE id=?",
            (request_id,),
        ).fetchone())

    def list_cross_dept_requests(self, actor):
        if actor == self.ceo or str(actor).startswith("companion-admin-"):
            rows = self.db.execute(
                "SELECT * FROM cross_department_requests ORDER BY created_at, id")
        else:
            rows = self.db.execute(
                """SELECT request.*
                   FROM cross_department_requests AS request
                   JOIN department_seats AS seat
                     ON seat.department_id=request.delivering_department_id
                   WHERE seat.status='active' AND seat.principal_id=?
                   ORDER BY request.created_at, request.id""",
                (actor,),
            )
        return {"items": [dict(row) for row in rows]}

    def accept_cross_dept_request(self, actor, request_id):
        request = self.db.execute(
            "SELECT * FROM cross_department_requests WHERE id=?",
            (request_id,),
        ).fetchone()
        if not request:
            raise ValueError("Cross-department request not found")
        if request["status"] != "pending_acceptance":
            raise ValueError("Cross-department request is not pending acceptance")

        is_ceo = actor == self.ceo or str(actor).startswith("companion-admin-")
        if not is_ceo:
            seat = self.db.execute(
                """SELECT principal_id FROM department_seats
                   WHERE department_id=? AND status='active'""",
                (request["delivering_department_id"],),
            ).fetchone()
            if not seat or seat["principal_id"] != actor:
                raise PermissionError("Seated delivering department head required")

        accepted_at = now().isoformat()
        with self.tx():
            current = self.db.execute(
                "SELECT status FROM cross_department_requests WHERE id=?",
                (request_id,),
            ).fetchone()
            if not current or current["status"] != "pending_acceptance":
                raise ValueError("Cross-department request is not pending acceptance")
            self.db.execute(
                """UPDATE cross_department_requests
                   SET status='accepted', accepted_by=?, accepted_at=?
                   WHERE id=?""",
                (actor, accepted_at, request_id),
            )
            self._event(
                "cross_department.request_accepted",
                {"id": request_id, "status": "accepted"},
                actor_id=actor,
                project_id=request["project_id"],
            )
        return dict(self.db.execute(
            "SELECT * FROM cross_department_requests WHERE id=?",
            (request_id,),
        ).fetchone())

    def remaining_dispatch_budget_cents(self):
        from company.dispatch_recommend import remaining_budget_cents
        return remaining_budget_cents(self)

    def dispatch_options(self, project_id):
        from company.dispatch_recommend import build_dispatch_options
        return build_dispatch_options(self, project_id)

    def recommend_dispatch(self, actor, project_id, use_live=True):
        self._ceo_or_admin_companion(actor)
        from company.dispatch_recommend import recommend_with_fallback
        return recommend_with_fallback(self, project_id, use_live=bool(use_live))

    def dispatch_project_brief(self, actor, project_id, brief, department_budgets,
                               acceptance_criteria, due_at=None):
        self._ceo_or_admin_companion(actor)
        if not brief or not str(brief).strip():
            raise ValueError("Brief required")
        if not acceptance_criteria or not str(acceptance_criteria).strip():
            raise ValueError("Acceptance criteria required")
        if not isinstance(department_budgets, dict) or not department_budgets:
            raise ValueError("department_budgets mapping required")
        if not self.db.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone():
            raise ValueError("Project not found")
        known = {r[0] for r in self.db.execute("SELECT id FROM departments")}
        for dept_id, budget_cents in department_budgets.items():
            if dept_id not in known:
                raise ValueError(f"Unknown department {dept_id}")
            money(budget_cents)
            if not self.department_dispatchable(project_id, dept_id):
                raise ValueError(
                    f"Department {dept_id} is dormant for this project; activate first")
        dispatches = []
        with self.tx():
            for dept_id, budget_cents in department_budgets.items():
                dispatch_id = str(uuid.uuid4())
                woid = digest({"dispatch": project_id, "department": dept_id, "at": now().isoformat()})
                task_id = f"dispatch-{project_id}-{dept_id}-{dispatch_id[:8]}"
                payload = {
                    "project_id": project_id, "department_id": dept_id,
                    "brief": brief.strip(), "acceptance_criteria": acceptance_criteria.strip(),
                    "due_at": due_at,
                }
                self.db.execute(
                    "INSERT INTO work_orders VALUES(?,?,?,?,?,?,?)",
                    (woid, task_id, self.policy()["version"], digest(payload), budget_cents,
                     canonical(payload), "authorized"))
                seat = self.db.execute(
                    "SELECT * FROM department_seats WHERE department_id=?",
                    (dept_id,),
                ).fetchone()
                if seat and seat["status"] == "active" and seat["principal_id"]:
                    status = "queued_for_head"
                    head_principal_id = seat["principal_id"]
                    head_inbox_at = now().isoformat()
                else:
                    status = "blocked_vacant_head"
                    head_principal_id = None
                    head_inbox_at = None
                self.db.execute(
                    """INSERT INTO project_dispatches
                       (id, project_id, department_id, work_order_id, brief,
                        acceptance_criteria, budget_cents, due_at, created_at,
                        status, head_principal_id, head_inbox_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (dispatch_id, project_id, dept_id, woid, brief.strip(),
                     acceptance_criteria.strip(), budget_cents, due_at, now().isoformat(),
                     status, head_principal_id, head_inbox_at))
                self._event("project.dispatched",
                              {"dispatch_id": dispatch_id, "department_id": dept_id,
                               "work_order_id": woid, "status": status},
                              actor_id=actor, project_id=project_id)
                dispatches.append({
                    "id": dispatch_id,
                    "department_id": dept_id,
                    "work_order_id": woid,
                    "status": status,
                    "head_principal_id": head_principal_id,
                    "budget_cents": budget_cents,
                })
        return dispatches

    def list_head_inbox(self, actor):
        open_statuses = ("queued_for_head", "blocked_vacant_head", "blocked")
        if actor == self.ceo or str(actor).startswith("companion-admin-"):
            rows = self.db.execute(
                """SELECT * FROM project_dispatches
                   WHERE status IN (?,?,?)
                   ORDER BY created_at, id""",
                open_statuses,
            )
        else:
            rows = self.db.execute(
                """SELECT * FROM project_dispatches
                   WHERE head_principal_id=? AND status IN (?,?,?)
                   ORDER BY created_at, id""",
                (actor, *open_statuses),
            )
        return {"items": [dict(row) for row in rows]}

    def assign_dispatch(self, actor, dispatch_id, assignee, *, action, cost_cents):
        money(cost_cents)
        row = self.db.execute(
            "SELECT * FROM project_dispatches WHERE id=?", (dispatch_id,)).fetchone()
        if not row:
            raise ValueError("Dispatch not found")
        if row["status"] != "queued_for_head":
            raise ValueError("Dispatch is not assignable")
        seat = self.db.execute(
            "SELECT * FROM department_seats WHERE department_id=?",
            (row["department_id"],),
        ).fetchone()
        is_ceo = actor == self.ceo or str(actor).startswith("companion-admin-")
        if not is_ceo:
            if not seat or seat["status"] != "active" or seat["principal_id"] != actor:
                raise PermissionError("Seated head required")
            grant = self._effective_grant(actor)
            departments = grant.get("departments") if grant else None
            if (
                    not isinstance(departments, list)
                    or not departments
                    or row["department_id"] not in departments):
                raise PermissionError("No matching department delegation")
            self._scope(
                actor,
                row["project_id"],
                "work.assign",
                0,
                department_id=row["department_id"],
            )
        rostered = self.db.execute(
            """SELECT 1 FROM position_assignments
               WHERE department_id=? AND principal_id=? AND status='active'""",
            (row["department_id"], assignee),
        ).fetchone()
        assignee_grant = self._effective_grant(assignee)
        contractor = bool(
            assignee_grant and row["project_id"] in assignee_grant["projects"])
        if not rostered and not contractor:
            raise PermissionError(
                "Assignee not on department roster and has no project grant")

        queue_task_id = f"dispatch-assign-{dispatch_id[:8]}-{assignee}"
        queued = self.queue_task(
            assignee, row["project_id"], action, cost_cents, queue_task_id)
        assignment_id = str(uuid.uuid4())
        with self.tx():
            current = self.db.execute(
                "SELECT status FROM project_dispatches WHERE id=?",
                (dispatch_id,),
            ).fetchone()
            if not current or current["status"] != "queued_for_head":
                raise ValueError("Dispatch is not assignable")
            self.db.execute(
                """INSERT INTO dispatch_assignments
                   (id, dispatch_id, assignee, assigned_by, assigned_at,
                    queue_task_id, status)
                   VALUES(?,?,?,?,?,?,?)""",
                (
                    assignment_id, dispatch_id, assignee, actor, now().isoformat(),
                    queued["task_id"], "assigned",
                ),
            )
            self.db.execute(
                "UPDATE project_dispatches SET status='assigned' WHERE id=?",
                (dispatch_id,),
            )
            self._event(
                "project.dispatch_assigned",
                {
                    "dispatch_id": dispatch_id,
                    "assignment_id": assignment_id,
                    "assignee": assignee,
                    "queue_task_id": queued["task_id"],
                },
                actor_id=actor,
                project_id=row["project_id"],
            )
        return dict(self.db.execute(
            "SELECT * FROM project_dispatches WHERE id=?", (dispatch_id,)).fetchone()) | {
                "assignment_id": assignment_id,
                "assignee": assignee,
                "queue_task_id": queued["task_id"],
            }

    def backup(self,dest):
        dest=Path(dest);dest.parent.mkdir(parents=True,exist_ok=True)
        out=sqlite3.connect(str(dest))
        try:
            self.db.backup(out)
        finally:
            out.close()
        return str(dest)

    def list_slos(self):
        latest = {r["slo_id"]: dict(r) for r in self.db.execute(
            """SELECT * FROM slo_observations WHERE id IN (
                 SELECT id FROM slo_observations s1
                 WHERE recorded_at=(SELECT MAX(recorded_at) FROM slo_observations s2 WHERE s2.slo_id=s1.slo_id)
               )""")}
        items = []
        for definition in SLO_DEFINITIONS:
            obs = latest.get(definition["id"])
            items.append({
                **definition,
                "status": "observed" if obs else "unmeasured",
                "value": obs["value"] if obs else None,
                "source": obs["source"] if obs else None,
                "window_start": obs["window_start"] if obs else None,
                "window_end": obs["window_end"] if obs else None,
            })
        return {"items": items}

    def record_slo_observation(self, actor, slo_id, value, source, window_start, window_end):
        """Record a sourced measurement. Does not invent targets or claim SLO met/breached."""
        self._ceo(actor)
        if slo_id not in {d["id"] for d in SLO_DEFINITIONS}:
            raise LookupError("Unknown SLO")
        if not source or not str(source).strip():
            raise ValueError("Observation source required")
        if window_start is None or window_end is None:
            raise ValueError("Observation window required")
        try:
            numeric = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("Observation value must be numeric") from exc
        oid = digest({"slo_id": slo_id, "source": source, "window_start": window_start, "window_end": window_end})
        with self.tx():
            existing = self.db.execute("SELECT * FROM slo_observations WHERE id=?", (oid,)).fetchone()
            if existing:
                return dict(existing) | {"status": "observed"}
            self.db.execute("INSERT INTO slo_observations VALUES(?,?,?,?,?,?,?,?)",
                            (oid, slo_id, numeric, source.strip(), window_start, window_end,
                             now().isoformat(), actor))
            self._event("slo.observed", {"id": oid, "slo_id": slo_id, "source": source.strip()}, actor_id=actor)
        return dict(self.db.execute("SELECT * FROM slo_observations WHERE id=?", (oid,)).fetchone()) | {"status": "observed"}

    def _hash_pairing(self, ticket):
        return hashlib.sha256(("fs-corporation-pairing:" + ticket).encode()).hexdigest()

    def probe_tailscale(self):
        exe = shutil.which("tailscale")
        if not exe:
            return {"cli": "live_unavailable", "ipv4": None}
        try:
            out = subprocess.run([exe, "ip", "-4"], capture_output=True, text=True, timeout=2, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return {"cli": "live_unavailable", "ipv4": None}
        ip = (out.stdout or "").strip().split()
        if out.returncode == 0 and ip:
            return {"cli": "advertised", "ipv4": ip[0]}
        return {"cli": "live_unavailable", "ipv4": None}

    def companion_https_url(self):
        """Prefer Tailscale HTTPS when the node has a tailnet IPv4."""
        env_ip = (os.environ.get("FS_CORP_TAILSCALE_IP") or "").strip()
        probe = self.probe_tailscale()
        ip = env_ip or probe.get("ipv4")
        if ip:
            return f"https://{ip}"
        return None

    def remote_access_status(self, public_url=None):
        configured_url = str(self.effective_setting("FS_CORP_PUBLIC_URL") or "").strip().rstrip("/")
        public = (public_url or configured_url or "").strip().rstrip("/")
        probe = self.probe_tailscale()
        key = os.environ.get("FS_CORP_TAILSCALE_AUTHKEY") or ""
        recommended = configured_url or public
        if not recommended and probe["ipv4"]:
            recommended = f"https://{probe['ipv4']}"
        companion = self.companion_https_url()
        return {
            "vpn": "tailscale",
            "public_url": public or None,
            "recommended_url": recommended,
            "companion_url": companion or recommended,
            "tailnet_ipv4": probe["ipv4"] or (os.environ.get("FS_CORP_TAILSCALE_IP") or "").strip() or None,
            "tailscale_cli": probe["cli"],
            "auth_key_configured": bool(key.strip()),
            "pairing_levels": pairing_levels_catalog(),
        }

    def create_pairing_ticket(self, actor, public_url, access_level="admin", minutes=15):
        self._ceo(actor)
        if access_level not in PAIRING_LEVEL_IDS:
            raise ValueError("Unknown pairing access level")
        level = pairing_level(access_level)
        ticket = secrets.token_urlsafe(24)
        tid = digest({"pair": ticket})[:24]
        exp = (now() + timedelta(minutes=minutes)).isoformat()
        remote = self.remote_access_status(public_url)
        # QR must be redeemable on LAN Wi‑Fi before the phone has joined Tailscale.
        base = remote["recommended_url"] or public_url or ""
        pair_url = f"{base.rstrip('/')}/#fs-pair={ticket}"
        import segno
        qr_svg = segno.make(pair_url, error="m").svg_inline(scale=4)
        with self.tx():
            self.db.execute(
                "INSERT INTO pairing_tickets VALUES(?,?,?,?,?,?,NULL,NULL,?)",
                (tid, self._hash_pairing(ticket), actor, now().isoformat(), exp, "issued", access_level))
            self._event("pairing.issued",
                          {"id": tid, "expires_at": exp, "access_level": access_level}, actor_id=actor)
        return {
            "id": tid,
            "ticket": ticket,
            "pair_url": pair_url,
            "expires_at": exp,
            "access_level": access_level,
            "label": level["label"],
            "qr_svg": qr_svg,
            "remote": remote,
            "contains_owner_token": False,
        }

    def redeem_pairing_ticket(self, ticket):
        if not ticket or not str(ticket).strip():
            raise LookupError("Pairing ticket not found")
        row = self.db.execute(
            "SELECT * FROM pairing_tickets WHERE ticket_hash=?",
            (self._hash_pairing(ticket.strip()),)).fetchone()
        if not row:
            raise LookupError("Pairing ticket not found")
        if row["status"] != "issued":
            raise ValueError("Pairing ticket already used")
        if datetime.fromisoformat(row["expires_at"]) <= now():
            raise ValueError("Pairing ticket expired")
        access_level = row["access_level"] if "access_level" in row.keys() else "admin"
        level = pairing_level(access_level)
        scopes = list(level["scopes"])
        token = secrets.token_urlsafe(32)
        principal = f"companion-{access_level}-{row['id'][:8]}"
        self.register_identity(principal, "service", token, scopes)
        with self.tx():
            self.db.execute(
                "UPDATE pairing_tickets SET status='redeemed', redeemed_at=?, companion_principal=? WHERE id=?",
                (now().isoformat(), principal, row["id"]))
            self._event("pairing.redeemed",
                          {"id": row["id"], "principal_id": principal, "access_level": access_level},
                          actor_id=principal)
        remote = self.remote_access_status()
        key = (os.environ.get("FS_CORP_TAILSCALE_AUTHKEY") or "").strip()
        lan_base = remote["recommended_url"]
        companion = remote.get("companion_url") or lan_base
        result = {
            "token": token,
            "principal_id": principal,
            "base_url": lan_base,
            "companion_url": companion,
            "access_level": access_level,
            "label": level["label"],
            "scopes": scopes,
            "vpn": {
                "provider": "tailscale",
                "status": "configured" if key else "live_unavailable",
                # Both platforms: copy key + open Tailscale; OS forbids silent VPN inject.
                "ios_handoff": "clipboard_open_app" if key else None,
                "android_handoff": "clipboard_open_app" if key else None,
            },
        }
        if key:
            result["tailscale_auth_key"] = key
        return result

    def list_paired_devices(self, actor):
        self._ceo(actor)
        rows = self.db.execute(
            """SELECT id, companion_principal, access_level, redeemed_at, created_by
               FROM pairing_tickets
               WHERE status='redeemed' AND companion_principal IS NOT NULL
               ORDER BY redeemed_at DESC""").fetchall()
        devices = []
        for row in rows:
            principal = row["companion_principal"]
            ident = self.db.execute(
                "SELECT principal_id, kind, created_at, scopes FROM identities WHERE principal_id=?",
                (principal,)).fetchone()
            if not ident:
                continue
            level = row["access_level"] if "access_level" in row.keys() else "admin"
            try:
                label = pairing_level(level)["label"]
            except ValueError:
                label = level
            devices.append({
                "principal_id": principal,
                "ticket_id": row["id"],
                "access_level": level,
                "label": label,
                "redeemed_at": row["redeemed_at"],
                "issued_by": row["created_by"],
                "active": True,
            })
        return devices

    def revoke_paired_device(self, actor, principal_id):
        self._ceo(actor)
        if not principal_id or not str(principal_id).startswith("companion-"):
            raise ValueError("Not a paired companion principal")
        row = self.db.execute("SELECT * FROM identities WHERE principal_id=?", (principal_id,)).fetchone()
        if not row:
            raise LookupError("Paired device not found")
        if row["kind"] != "service":
            raise PermissionError("Only companion service principals may be revoked here")
        with self.tx():
            self.db.execute("DELETE FROM identities WHERE principal_id=?", (principal_id,))
            self._event("pairing.revoked", {"principal_id": principal_id}, actor_id=actor)
        return {"principal_id": principal_id, "status": "revoked"}

    def restore(self,src):
        src=Path(src)
        if not src.is_file():raise ValueError("Backup file not found")
        incoming=sqlite3.connect(str(src))
        try:
            with self.db.lock:
                incoming.backup(self.db._conn)
        finally:
            incoming.close()
        return self.status()
