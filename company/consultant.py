"""Read-only heuristic review and durable CEO proposals; no AI calls or fixes."""
import ast
from pathlib import Path
import hashlib
import json
from .core import canonical, digest

IGNORED={".git",".venv",".local","__pycache__","dist","build","upstream","workspaces","artifacts"}


def review(root):
    """Inspect Python syntax and selected organizational/model metadata, never execute files.

    Findings are review candidates, not a proof of bugs or a complete audit.
    Source paths are limited to company/ and explicit configuration files.
    """
    root=Path(root).resolve()
    findings=[]
    def add(rule,target,line,title,evidence,recommendation,source_hash):
        findings.append({"rule":rule,"target":target,"line":line,"title":title,
          "classification":"review_candidate","evidence":evidence,
          "recommendation":recommendation,"source_hash":source_hash})
    for path in sorted((root/"company").rglob("*.py")):
        if path.is_symlink() or not path.resolve().is_relative_to(root):continue
        if any(p in IGNORED for p in path.relative_to(root).parts):continue
        raw=path.read_bytes();sha=hashlib.sha256(raw).hexdigest()
        target=path.relative_to(root).as_posix()
        try: tree=ast.parse(raw,filename=target)
        except SyntaxError as exc:
            add("python-syntax",target,exc.lineno,"Python file cannot be parsed",
                str(exc),"Reproduce with the target interpreter and fix the syntax error.",sha)
            continue
        for node in ast.walk(tree):
            if isinstance(node,ast.ExceptHandler) and node.type is None:
                add("bare-except",target,node.lineno,"Exception handler catches all exception types",
                    "AST contains an except clause without an exception type.",
                    "Check whether cancellation or system-exit signals could be swallowed; narrow the handler where appropriate.",sha)
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                defaults=node.args.defaults+[x for x in node.args.kw_defaults if x is not None]
                if any(isinstance(x,(ast.List,ast.Dict,ast.Set)) for x in defaults):
                    add("mutable-default",target,node.lineno,"Function uses a shared mutable default",
                        f"Function {node.name} has a list/dict/set default expression.",
                        "Determine whether state can leak between calls; if unintended, initialize per call and add a regression test.",sha)
    dept_path=root/"config/departments.json";model_path=root/"config/models.example.json"
    if dept_path.is_file() and model_path.is_file():
        if any(p.is_symlink() or not p.resolve().is_relative_to(root) for p in (dept_path,model_path)):
            raise ValueError("Configuration must be inside the review root")
        departments=json.loads(dept_path.read_text())["departments"]
        models=json.loads(model_path.read_text())
        sha=digest({"departments":departments,"models":models})
        for department in departments:
            if not department["initially_active"]:continue
            candidates=models.get("departments",{}).get(department["id"],[])
            enabled=[key for key in candidates if models["profiles"].get(key,{}).get("enabled")]
            if not enabled:
                add("unroutable-department","config/departments.json",None,
                    f"Active department {department['id']} has no enabled default model",
                    f"Configured routing candidates: {candidates!r}.",
                    "Verify position overrides and workload before assigning an eligible model or marking the department dormant.",sha)
    return {"review_kind":"offline_heuristic","scope":["company/*.py (recursive)","department/model configuration"],
      "findings":findings,"limitations":["Not a comprehensive bug or security audit.",
      "No performance measurements, tests, model inference, live state review or automatic edits.",
      "Absence of findings does not imply the company is correct or efficient."]}


class ConsultantDesk:
    """Local trusted-caller proposal workflow. Production requires authenticated principals."""
    def __init__(self,company):
        self.company=company
        company.db.execute("""CREATE TABLE IF NOT EXISTS consultant_proposals(
          id TEXT PRIMARY KEY, body TEXT NOT NULL, author TEXT NOT NULL,
          status TEXT NOT NULL, approver TEXT, reason TEXT,
          source_hash TEXT, revision_of TEXT)""")

    def submit(self,author,proposal):
        required={"title","finding","recommendation","evidence","expected_benefit",
                  "implementation_cost_cents","risk","validation_plan","rollback_plan"}
        extra=set(proposal)-required
        if extra and extra!={"source_hash"}:
            raise ValueError("Proposal fields must match the documented consultant contract")
        if not required.issubset(proposal):
            raise ValueError("Proposal fields must match the documented consultant contract")
        from .core import money
        money(proposal["implementation_cost_cents"])
        if any(not isinstance(proposal[k],str) or not proposal[k].strip()
               for k in required-{"implementation_cost_cents"}):
            raise ValueError("All narrative fields require nonempty strings")
        if not isinstance(author,str) or not author.strip():raise ValueError("Author required")
        stored={k:proposal[k] for k in required}
        pid=digest({"author":author,"proposal":stored})
        c=self.company
        source_hash=proposal.get("source_hash") or digest(proposal["evidence"])
        with c.tx():
            if not c.db.execute("SELECT 1 FROM consultant_proposals WHERE id=?",(pid,)).fetchone():
                c.db.execute(
                    "INSERT INTO consultant_proposals(id,body,author,status,approver,reason,source_hash,revision_of) VALUES(?,?,?,'pending',NULL,NULL,?,NULL)",
                    (pid,canonical(stored),author,source_hash))
                c._event("consultant.proposal_submitted",{"id":pid,"author":author,"proposal_digest":digest(stored)})
        return pid

    def decide(self,actor,pid,decision,reason,expected_source_hash=None):
        c=self.company;c._ceo(actor)
        if decision not in {"approved","rejected"}:raise ValueError("Decision must be approved or rejected")
        if not isinstance(reason,str) or not reason.strip():raise ValueError("Decision rationale required")
        with c.tx():
            p=c.db.execute("SELECT * FROM consultant_proposals WHERE id=?",(pid,)).fetchone()
            if not p or p["status"]!="pending":raise ValueError("Pending consultant proposal not found")
            if p["author"]==actor:raise PermissionError("Consultant cannot approve its own proposal")
            if expected_source_hash is not None and p["source_hash"] and expected_source_hash!=p["source_hash"]:
                raise ValueError("Stale evidence: revalidate against current source")
            c.db.execute("UPDATE consultant_proposals SET status=?,approver=?,reason=? WHERE id=?",
                         (decision,actor,reason,pid))
            c._event("consultant.proposal_"+decision,{"id":pid,"actor":actor,"reason":reason})
        # Approval is a recorded decision, not repository-write or policy-edit authority.

    def revise(self,author,pid,proposal):
        c=self.company
        old=c.db.execute("SELECT * FROM consultant_proposals WHERE id=?",(pid,)).fetchone()
        if not old:raise ValueError("Consultant proposal not found")
        if old["author"]!=author:raise PermissionError("Only the author may submit a revision")
        new_id=self.submit(author,proposal)
        if new_id==pid:return pid
        with c.tx():
            c.db.execute("UPDATE consultant_proposals SET revision_of=? WHERE id=?",(pid,new_id))
            c._event("consultant.proposal_revised",{"id":new_id,"revision_of":pid,"author":author})
        return new_id

    def to_work_order(self,actor,pid):
        """Record a separately authorized work-order id. Does not dispatch or edit code."""
        c=self.company;c._ceo(actor)
        p=c.db.execute("SELECT * FROM consultant_proposals WHERE id=?",(pid,)).fetchone()
        if not p or p["status"]!="approved":raise ValueError("Approved consultant proposal required")
        body=json.loads(p["body"])
        oid=digest({"consultant_proposal":pid,"task":"handoff"})
        with c.tx():
            if not c.db.execute("SELECT 1 FROM work_orders WHERE id=?",(oid,)).fetchone():
                c.db.execute(
                    "INSERT INTO work_orders VALUES(?,?,?,?,?,?,?)",
                    (oid,pid,c.policy()["version"],digest(body),body["implementation_cost_cents"],
                     canonical({"source":"consultant","proposal_id":pid}),"authorized"))
                c._event("consultant.work_order_authorized",{"work_order_id":oid,"proposal_id":pid})
        return oid

    def list(self):
        return [{**dict(r),"body":json.loads(r["body"])} for r in self.company.db.execute(
            "SELECT * FROM consultant_proposals ORDER BY rowid")]


def main():
    import argparse
    p=argparse.ArgumentParser(description="Read-only offline consultant heuristics; no fixes or model calls")
    p.add_argument("--root",default=".")
    args=p.parse_args()
    print(json.dumps(review(args.root),indent=2))

if __name__=="__main__":main()
