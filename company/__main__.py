import argparse
from datetime import timedelta
import json
from pathlib import Path
from .core import Company, now


def demo(c):
    if c.status()["completions"]:
        return c.status()
    policy={"version":c.policy()["version"]+1,"company_budget_cents":5000,"grants":{}}
    for actor,actions in (("engineering-head",["draft","prepare_pr"]),("contractor",["provision_room"])):
        policy["grants"][actor]={"actions":actions,"projects":["demo-app"],"budget_cents":2000,
          "per_action_cents":500,"expires_at":(now()+timedelta(days=30)).isoformat(),
          "requires_approval":["prepare_pr"] if actor=="engineering-head" else []}
    pid=c.propose_policy("engineering-head",policy,"Demo: delegate app drafting and approved facilities work")
    c.approve_policy("human-ceo",pid)
    output=c.execute_mock(actor="engineering-head",project="demo-app",action="draft",cost=150,task_id="demo-deliverable")
    c.inspect_quality("quality:Quality Inspector",output["id"],output["artifact_hash"],"pass")
    c.accept_project("human-ceo",output["id"],output["artifact_hash"])
    c.approve_expansion("human-ceo","expansion-demo-app")
    c.build_mock("contractor","expansion-demo-app")
    c.ingest_signal(source="https://example.com/demo-platform-announcement",title="Synthetic platform update",
      published_at=now().isoformat(),observed_at=now().isoformat(),summary="Demo fixture only; no real market claim.")
    return c.status()


def main():
    p=argparse.ArgumentParser(description="Offline AI-company reference core; no network or model spend")
    p.add_argument("command",choices=["demo","status","audit","backup","restore"])
    p.add_argument("--db",default=".local/company.db")
    p.add_argument("--dest",default=".local/company.backup.db")
    args=p.parse_args()
    Path(args.db).parent.mkdir(parents=True,exist_ok=True)
    c=Company(args.db)
    try:
        if args.command=="demo": result=demo(c)
        elif args.command=="audit": result={"audit_valid":c.verify_audit()}
        elif args.command=="backup": result={"backup":c.backup(args.dest)}
        elif args.command=="restore": result=c.restore(args.dest)
        else: result=c.status()
        print(json.dumps(result,indent=2))
    finally: c.close()

if __name__=="__main__": main()
