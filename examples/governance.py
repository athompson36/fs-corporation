"""Run: python3 -m examples.governance. No persistence, network, or real costs."""
from datetime import timedelta
import json
from pathlib import Path
from company.core import Company, now

c=Company()
try:
    template=Path(__file__).resolve().parents[1]/"config/policy.example.json"
    proposed=json.loads(template.read_text())
    proposed["version"]=c.policy()["version"]+1
    for grant in proposed["grants"].values():
        grant["expires_at"]=(now()+timedelta(days=30)).isoformat()
    pid=c.propose_policy("engineering-head",proposed,"Assign bounded development responsibility")
    c.approve_policy("human-ceo",pid)
    request=dict(actor="engineering-head",project="example-app",action="prepare_pr",cost=100,task_id="example-pr")
    try:c.execute_mock(**request)
    except PermissionError as e:print("Expected denial:",e)
    aid=c.approve_action("human-ceo",**request)
    result=c.execute_mock(**request,approval=aid)
    print("Approved mock result:",json.dumps(result,indent=2))
    print("No actual GitHub pull request was created.")
finally:c.close()
