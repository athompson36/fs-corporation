"""Deterministic local reference implementation. No network calls or arbitrary code execution.

Actor identifiers are trusted inputs in this local demo. They are NOT authentication.
Production requires authenticated principals and a separate credentialed action gateway.
"""
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import sqlite3
import uuid
from .schema import GRANT_OPTIONAL, GRANT_REQUIRED, MAX_DELEGATION_DEPTH, POLICY_REQUIRED, apply_schema


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


class Company:
    def __init__(self, path=":memory:", ceo="human-ceo"):
        self.db_path = str(path)
        self.db = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA busy_timeout=5000")
        apply_schema(self.db)
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
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
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
        self.db.execute(
            "INSERT INTO events(at,kind,body,previous,hash,event_id,schema_version,actor_id,policy_version,correlation_id,project_id) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (at,kind,canonical(body),previous,digest(value),str(uuid.uuid4()),1,actor_id,policy_version,correlation_id,project_id))

    def _ceo(self,actor):
        if actor != self.ceo:
            raise PermissionError("CEO authority required")

    def _is_qc(self,actor):
        return actor=="qc" or str(actor).startswith("quality:")

    def _hr_or_ceo(self,actor):
        if actor==self.ceo:return
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
        self._ceo(actor)
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
        self._ceo(actor)
        with self.tx():
            self.db.execute("UPDATE settings SET value=? WHERE key='paused'",("true" if paused else "false",))
            self._event("company.paused" if paused else "company.resumed",{"actor":actor})

    def _scope(self,actor,project,action,cost):
        money(cost)
        if self.db.execute("SELECT value FROM settings WHERE key='paused'").fetchone()[0]=="true":
            raise PermissionError("Company paused")
        p=self.policy();g=self._effective_grant(actor)
        if not g or action not in g["actions"] or project not in g["projects"]:
            raise PermissionError("No matching delegation")
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
        counts={table:self.db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("tasks","completions","signals","events")}
        return {"mode":"offline_mock","policy_version":self.policy()["version"],**counts,
            "simulated_spend_cents":self.db.execute("SELECT COALESCE(SUM(cost),0) FROM ledger").fetchone()[0],
            "rooms":1+self.db.execute("SELECT COUNT(*) FROM expansions WHERE status='built'").fetchone()[0],
            "audit_valid":self.verify_audit()}

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

    def require_scope(self,identity,scope):
        if not identity:raise PermissionError("Unauthenticated")
        scopes=json.loads(identity["scopes"])
        if identity["kind"]=="owner":return
        if scope not in scopes:raise PermissionError("Missing scope")

    def reject_policy(self,actor,pid,reason):
        self._ceo(actor)
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

    def dispatch_queued_isolated(self,worker_id,task_id,scratch_root,approval=None,runtime="subprocess"):
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
        if profile.get("provider")!="mock":
            raise NotImplementedError("Live model requires configured credentials inside the worker boundary; see docs/12-security.md")
        if not isinstance(prompt,str):raise ValueError("Prompt required")
        return {"text":"mock-provider-output","profile_id":profile_id,"cost_cents":0,"provider":"mock"}

    def seed_catalog(self,departments_path):
        data=json.loads(Path(departments_path).read_text())
        with self.tx():
            for d in data["departments"]:
                self.db.execute("INSERT OR REPLACE INTO departments VALUES(?,?,?,?,?,?,?,?,?)",
                    (d["id"],d["name"],d["head"],d["mission"],canonical(d["measures"]),d["room_type"],
                     1 if d["initially_active"] else 0,d["default_model_profile"],canonical(d)))
                for title in d["positions"]:
                    pid=f"{d['id']}:{title}"
                    self.db.execute("INSERT OR REPLACE INTO positions VALUES(?,?,?)",(pid,d["id"],title))
            self._event("catalog.seeded",{"departments":len(data["departments"])})

    def seed_models(self,models_path):
        data=json.loads(Path(models_path).read_text())
        with self.tx():
            for pid,body in data.get("profiles",{}).items():
                self.db.execute("INSERT OR REPLACE INTO model_profiles VALUES(?,?,?)",
                                (pid,canonical(body),1 if body.get("enabled") else 0))
            self._event("models.seeded",{"profiles":len(data.get("profiles",{}))})

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
        self._ceo(actor)
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
        self._ceo(actor)
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

    def apply_github_effect(self,project_id,task_id,operation,repo_id,branch,head_sha=None,expected_sha=None,path=None):
        """Authorize, record, then attempt a live write. Live GitHub stays fail-closed."""
        self.authorize_github_effect(project_id,operation,repo_id,branch,
                                    head_sha=head_sha,expected_sha=expected_sha,path=path)
        row=self.record_github_effect(project_id,task_id,operation,repo_id,branch)
        if row["status"]=="live_unavailable":
            return row
        from .adapters import GitHubAdapter, WorkOrder
        order=WorkOrder(
            task_id,project_id,self.policy()["version"],"github-effect",0,
            {"operation":operation,"repo_id":repo_id,"branch":branch,
             "head_sha":head_sha,"expected_sha":expected_sha,"path":path,
             "worktree":self.worktree_path(project_id,task_id)})
        try:
            GitHubAdapter().execute(order)
        except NotImplementedError:
            with self.tx():
                self.db.execute("UPDATE github_effects SET status=? WHERE id=?",("live_unavailable",row["id"]))
                self._event("github.effect_live_unavailable",{"id":row["id"],"operation":operation},project_id=project_id)
            return dict(self.db.execute("SELECT * FROM github_effects WHERE id=?",(row["id"],)).fetchone())
        raise RuntimeError("Live GitHub adapter returned without applying an effect")

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

    def correct_signal(self,signal_id,note):
        with self.tx():
            sig=self.db.execute("SELECT * FROM signals WHERE id=?",(signal_id,)).fetchone()
            if not sig:raise ValueError("Signal not found")
            self.db.execute("UPDATE impact_briefs SET status='corrected' WHERE signal_id=?",(signal_id,))
            self._event("intelligence.corrected",{"signal_id":signal_id,"note":note})

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

    def poll_market_feed(self,source_id):
        """Record a poll attempt for an approved source. Live fetch stays fail-closed."""
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
        if row["status"]=="live_unavailable":
            return row
        from .adapters import MarketFeedAdapter
        try:
            MarketFeedAdapter().poll(source_id)
        except NotImplementedError:
            with self.tx():
                self.db.execute("UPDATE feed_polls SET status=? WHERE id=?",("live_unavailable",pid))
                self._event("feed.poll_live_unavailable",{"id":pid,"source_id":source_id})
            return dict(self.db.execute("SELECT * FROM feed_polls WHERE id=?",(pid,)).fetchone())
        raise RuntimeError("Live feed adapter returned without poll results")

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

    def headquarters(self):
        rooms=[{"id":r["id"],"status":r["status"],"source_project":r["source_project"],
                "contractor":r["contractor"]} for r in self.db.execute("SELECT * FROM expansions ORDER BY id")]
        depts=[dict(r) for r in self.db.execute("SELECT id,name,initially_active,room_type FROM departments ORDER BY id")]
        return {"rooms":rooms,"departments":depts,"room_count":1+sum(1 for r in rooms if r["status"]=="built"),
                "occupancy_note":"Room occupancy is not running model count.","source":"persisted_events"}

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

    def _assign_training(self, employee_id, actor):
        dept=self.db.execute("SELECT position_id FROM employees WHERE id=?",(employee_id,)).fetchone()["position_id"].split(":",1)[0]
        created=[]
        due=self.training_due(employee_id)
        with self.tx():
            for skill_id in due:
                open_row=self.db.execute(
                    "SELECT * FROM learning_assignments WHERE learner=? AND skill_id=? AND status IN ('assigned','studying')",
                    (employee_id,skill_id)).fetchone()
                if open_row:
                    created.append(dict(open_row));continue
                lid=digest({"employee":employee_id,"skill":skill_id,"cycle":now().isoformat()})
                self.db.execute(
                    "INSERT INTO learning_assignments VALUES(?,?,?,?,?,?,?,?,?)",
                    (lid,"hr-training",skill_id,employee_id,dept,None,"assigned",None,now().isoformat()))
                self._event("skill.learning_assigned",{"id":lid,"skill_id":skill_id,"learner":employee_id},
                            actor_id=actor,project_id="hr-training")
                created.append(dict(self.db.execute("SELECT * FROM learning_assignments WHERE id=?",(lid,)).fetchone()))
        return created

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
        with self.tx():
            self.db.execute("INSERT INTO employees VALUES(?,?,?,?,?,?,?)",
                (employee_id,position_id,display_name,canonical(attributes),background.strip(),now().isoformat(),"active"))
            self._event("employee.hired",{"id":employee_id,"position_id":position_id},actor_id=actor)
        training=self._assign_training(employee_id,actor)
        return {"id":employee_id,"position_id":position_id,"display_name":display_name,
                "attributes":attributes,"background":background.strip(),"training":training}

    def employee(self, employee_id):
        row=self.db.execute("SELECT * FROM employees WHERE id=?",(employee_id,)).fetchone()
        if not row:raise ValueError("Employee not found")
        data=dict(row)
        data["attributes"]=json.loads(data["attributes"])
        return data

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
        return {**summary, "tasks": tasks, "timeline": timeline,
                "qc_inspections": qc, "dispatches": dispatches,
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
        return dict(self.db.execute("SELECT * FROM owner_requests WHERE id=?", (rid,)).fetchone())

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
        self._ceo(actor)
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

    def dispatch_project_brief(self, actor, project_id, brief, departments, acceptance_criteria,
                               budget_cents, due_at=None):
        self._ceo(actor)
        money(budget_cents)
        if not brief or not str(brief).strip():
            raise ValueError("Brief required")
        if not acceptance_criteria or not str(acceptance_criteria).strip():
            raise ValueError("Acceptance criteria required")
        if not isinstance(departments, list) or not departments:
            raise ValueError("At least one department required")
        if not self.db.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone():
            raise ValueError("Project not found")
        known = {r[0] for r in self.db.execute("SELECT id FROM departments")}
        for dept_id in departments:
            if dept_id not in known:
                raise ValueError(f"Unknown department {dept_id}")
        dispatches = []
        with self.tx():
            for dept_id in departments:
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
                self.db.execute(
                    "INSERT INTO project_dispatches VALUES(?,?,?,?,?,?,?,?,?)",
                    (dispatch_id, project_id, dept_id, woid, brief.strip(),
                     acceptance_criteria.strip(), budget_cents, due_at, now().isoformat()))
                self._event("project.dispatched",
                              {"dispatch_id": dispatch_id, "department_id": dept_id, "work_order_id": woid},
                              actor_id=actor, project_id=project_id)
                dispatches.append({"id": dispatch_id, "department_id": dept_id, "work_order_id": woid})
        return dispatches

    def backup(self,dest):
        dest=Path(dest);dest.parent.mkdir(parents=True,exist_ok=True)
        out=sqlite3.connect(str(dest))
        try:
            self.db.backup(out)
        finally:
            out.close()
        return str(dest)

    def restore(self,src):
        src=Path(src)
        if not src.is_file():raise ValueError("Backup file not found")
        incoming=sqlite3.connect(str(src))
        try:
            incoming.backup(self.db)
        finally:
            incoming.close()
        return self.status()
