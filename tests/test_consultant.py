from pathlib import Path
import tempfile
import unittest
from company.core import Company
from company.consultant import ConsultantDesk, review


def proposal():
    return {"title":"Improve review process","finding":"A fixture exposed duplicate reviews",
      "recommendation":"Deduplicate review tasks","evidence":"fixture:test-1; baseline:3 reviews",
      "expected_benefit":"Fewer redundant reviews; measure before and after",
      "implementation_cost_cents":100,"risk":"Missing a review if keys collide",
      "validation_plan":"Test distinct and identical artifact hashes",
      "rollback_plan":"Restore previous scheduler configuration"}


class ConsultantTests(unittest.TestCase):
    def test_scan_finds_code_risks_without_execution(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"company";p.mkdir()
            source="def f(x=[]):\n    try: return x\n    except: pass\nraise RuntimeError('must never execute')\n"
            (p/"example.py").write_text(source)
            result=review(d)
            self.assertEqual({f["rule"] for f in result["findings"]},{"bare-except","mutable-default"})
            self.assertEqual((p/"example.py").read_text(),source)
            self.assertTrue(result["limitations"])

    def test_unroutable_active_department(self):
        import json
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"config";p.mkdir()
            (p/"departments.json").write_text(json.dumps({"departments":[{"id":"art","initially_active":True}]}))
            (p/"models.example.json").write_text(json.dumps({"profiles":{},"departments":{"art":["missing"]}}))
            self.assertEqual(review(d)["findings"][0]["rule"],"unroutable-department")

    def test_proposal_dedup_ceo_only_and_no_execution(self):
        c=Company();self.addCleanup(c.close);desk=ConsultantDesk(c)
        before=c.policy();pid=desk.submit("master-consultant",proposal())
        self.assertEqual(pid,desk.submit("master-consultant",proposal()))
        self.assertEqual(len(desk.list()),1)
        with self.assertRaises(PermissionError):desk.decide("master-consultant",pid,"approved","Looks good")
        desk.decide("human-ceo",pid,"approved","Proceed to a scoped work order")
        self.assertEqual(desk.list()[0]["status"],"approved")
        self.assertEqual(c.policy(),before)
        self.assertEqual(c.status()["tasks"],0)
        self.assertTrue(c.verify_audit())
        with self.assertRaises(ValueError):desk.decide("human-ceo",pid,"approved","Duplicate")

    def test_reject_persists_across_restart(self):
        with tempfile.TemporaryDirectory() as d:
            path=str(Path(d)/"company.db")
            c=Company(path);desk=ConsultantDesk(c)
            pid=desk.submit("master-consultant",proposal())
            desk.decide("human-ceo",pid,"rejected","Benefit not established")
            c.close();c=Company(path);self.addCleanup(c.close)
            self.assertEqual(ConsultantDesk(c).list()[0]["status"],"rejected")

    def test_no_self_approval_or_empty_evidence(self):
        c=Company();self.addCleanup(c.close);desk=ConsultantDesk(c)
        with self.assertRaises(ValueError):desk.submit("consultant",{**proposal(),"evidence":""})
        pid=desk.submit("human-ceo",proposal())
        with self.assertRaises(PermissionError):desk.decide("human-ceo",pid,"approved","Self")
