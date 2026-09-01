"""Run: python3 -m examples.consultant_proposal. Synthetic example; no fixes."""
import json
from company.core import Company
from company.consultant import ConsultantDesk
c=Company()
try:
    desk=ConsultantDesk(c)
    proposal={"title":"Investigate duplicate review jobs (synthetic example)",
      "finding":"Synthetic fixture records three reviews for the same unchanged artifact.",
      "recommendation":"Engineering should investigate deduplication by task and artifact digest.",
      "evidence":"Synthetic fixture only; this is not an observed production defect.",
      "expected_benefit":"Potential reduction in redundant review cost; establish real baseline first.",
      "implementation_cost_cents":100,"risk":"Distinct review criteria could be incorrectly combined.",
      "validation_plan":"Test identical and changed artifact hashes and differing review criteria.",
      "rollback_plan":"Restore prior scheduler behavior if review coverage decreases."}
    pid=desk.submit("master-consultant",proposal)
    desk.decide("human-ceo",pid,"approved","Approve investigation; implementation needs a scoped work order.")
    print(json.dumps(desk.list(),indent=2))
    print("Recorded approval only. No task, code change or policy change was executed.")
finally:c.close()
