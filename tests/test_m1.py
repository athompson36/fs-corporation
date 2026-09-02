from datetime import timedelta
import json
import tempfile
from pathlib import Path
import unittest
from company.core import Company, now
from company.consultant import ConsultantDesk
from tests.test_core import install, policy


PROPOSAL = {
    "title": "Improve review process", "finding": "A fixture exposed duplicate reviews",
    "recommendation": "Deduplicate review tasks", "evidence": "fixture:test-1; baseline:3 reviews",
    "expected_benefit": "Fewer redundant reviews; measure before and after",
    "implementation_cost_cents": 100, "risk": "Missing a review if keys collide",
    "validation_plan": "Test distinct and identical artifact hashes",
    "rollback_plan": "Restore previous scheduler configuration",
}


class PolicyLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)

    def test_reject_and_withdraw_preserved(self):
        p = policy(self.c)
        rejected = self.c.propose_policy("head", p, "Reject me")
        self.c.reject_policy("human-ceo", rejected, "Not now")
        self.assertEqual(self.c.db.execute("SELECT status FROM proposals WHERE id=?", (rejected,)).fetchone()[0], "rejected")
        withdrawn = self.c.propose_policy("head", policy(self.c), "Withdraw me")
        self.c.withdraw_policy("head", withdrawn)
        self.assertEqual(self.c.db.execute("SELECT status FROM proposals WHERE id=?", (withdrawn,)).fetchone()[0], "withdrawn")
        with self.assertRaises(PermissionError):
            self.c.reject_policy("head", self.c.propose_policy("head", policy(self.c), "Nope"), "x")

    def test_rollback_is_new_version_and_keeps_history(self):
        before = self.c.policy()["version"]
        events = self.c.status()["events"]
        new_version = self.c.rollback_policy("human-ceo", 1, "Restore initial grants")
        self.assertEqual(new_version, before + 1)
        self.assertEqual(self.c.policy()["grants"], json.loads(
            self.c.db.execute("SELECT body FROM policies WHERE version=1").fetchone()[0])["grants"])
        self.assertGreater(self.c.status()["events"], events)
        self.assertTrue(self.c.db.execute("SELECT 1 FROM policies WHERE version=?", (before,)).fetchone())

    def test_policy_diff_lists_grant_changes(self):
        pid = self.c.propose_policy("head", policy(self.c, 800), "Raise budget")
        diff = self.c.policy_diff(pid)
        self.assertEqual(diff["proposed"]["company_budget_cents"], 800)


class IdentityTests(unittest.TestCase):
    def test_owner_token_and_no_replacement(self):
        c = Company()
        self.addCleanup(c.close)
        c.register_identity("human-ceo", "owner", "secret-owner")
        ident = c.identity_for_token("secret-owner")
        self.assertEqual(ident["kind"], "owner")
        with self.assertRaises(PermissionError):
            c.register_identity("agent-ceo", "owner", "other")
        c.register_identity("consultant", "service", "c-token", ["consultant.read", "consultant.propose"])
        with self.assertRaises(PermissionError):
            c.require_scope(c.identity_for_token("c-token"), "consultant.decide")
        c.require_scope(c.identity_for_token("c-token"), "consultant.propose")

    def test_service_cannot_use_wildcard_scope(self):
        c = Company()
        self.addCleanup(c.close)
        with self.assertRaises(ValueError):
            c.register_identity("head-bot", "service", "t", ["*"])


class DelegationStoryTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        p = policy(self.c)
        p["grants"]["head"]["approval_rights"] = ["draft"]
        install(self.c, p)
        self.addCleanup(self.c.close)

    def test_parent_child_approval_and_revoke_blocks_queue(self):
        did = self.c.create_delegation(
            "head", grantee="specialist", actions=["draft"], projects=["app"],
            budget_cents=200, per_action_cents=200, expires_at=(now() + timedelta(days=1)).isoformat(),
            requires_approval=["draft"])
        with self.assertRaises(PermissionError):
            self.c.execute_mock(actor="specialist", project="app", action="draft", cost=50, task_id="s1")
        aid = self.c.approve_action("head", actor="specialist", project="app", action="draft", cost=50, task_id="s1")
        self.c.execute_mock(actor="specialist", project="app", action="draft", cost=50, task_id="s1", approval=aid)
        with self.assertRaises(PermissionError):
            self.c.approve_policy("head", self.c.propose_policy("head", policy(self.c), "Elevate"))
        with self.assertRaises(PermissionError):
            self.c.execute_mock(actor="specialist", project="app", action="prepare_pr", cost=10, task_id="prx")
        self.c.queue_task("specialist", "app", "draft", 10, "queued-1")
        self.c.revoke_delegation("human-ceo", did)
        with self.assertRaises(PermissionError):
            self.c.dispatch_queued("queued-1")
        self.assertEqual(self.c.db.execute("SELECT status FROM queue WHERE task_id='queued-1'").fetchone()[0], "cancelled")

    def test_child_cannot_exceed_parent_or_cycle_depth(self):
        with self.assertRaises(PermissionError):
            self.c.create_delegation(
                "head", grantee="specialist", actions=["draft"], projects=["app", "other"],
                budget_cents=200, per_action_cents=200, expires_at=(now() + timedelta(days=1)).isoformat())
        did = self.c.create_delegation(
            "head", grantee="specialist", actions=["draft"], projects=["app"],
            budget_cents=200, per_action_cents=200, expires_at=(now() + timedelta(days=1)).isoformat(),
            can_redelegate=True)
        grandchild = self.c.create_delegation(
            "specialist", grantee="intern", actions=["draft"], projects=["app"],
            budget_cents=50, per_action_cents=50, expires_at=(now() + timedelta(days=1)).isoformat(),
            parent_id=did, can_redelegate=True)
        with self.assertRaises(PermissionError):
            self.c.create_delegation(
                "intern", grantee="too-deep", actions=["draft"], projects=["app"],
                budget_cents=10, per_action_cents=10, expires_at=(now() + timedelta(days=1)).isoformat(),
                parent_id=grandchild)


class BackupConsultantTests(unittest.TestCase):
    def test_backup_restore_and_stale_revision(self):
        with tempfile.TemporaryDirectory() as d:
            path = str(Path(d) / "c.db")
            c = Company(path)
            install(c, policy(c))
            desk = ConsultantDesk(c)
            pid = desk.submit("master-consultant", PROPOSAL)
            with self.assertRaises(ValueError):
                desk.decide("human-ceo", pid, "approved", "ok", expected_source_hash="not-the-hash")
            new = desk.revise("master-consultant", pid, {**PROPOSAL, "title": "Revised title"})
            self.assertNotEqual(new, pid)
            self.assertEqual(ConsultantDesk(c).list()[-1]["revision_of"], pid)
            dest = str(Path(d) / "backup.db")
            c.backup(dest)
            c.execute_mock(actor="head", project="app", action="draft", cost=10, task_id="later")
            c.restore(dest)
            self.assertEqual(c.status()["tasks"], 0)
            c.close()


class SchemaMigrationTests(unittest.TestCase):
    def test_alembic_and_core_share_tables(self):
        with tempfile.TemporaryDirectory() as d:
            path = str(Path(d) / "m.db")
            c = Company(path)
            core_tables = {r[0] for r in c.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            c.close()
            from alembic.config import Config
            from alembic import command
            cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
            cfg.set_main_option("sqlalchemy.url", "sqlite:///" + str(Path(d) / "alembic.db"))
            command.upgrade(cfg, "head")
            import sqlite3
            db = sqlite3.connect(str(Path(d) / "alembic.db"))
            migrated = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            db.close()
            required = {"identities", "departments", "positions", "projects", "delegations", "events",
                        "consultant_proposals", "skills", "acquired_skills", "project_capabilities",
                        "learning_assignments", "qc_inspections", "employees", "training_records",
                        "performance_goals", "performance_reviews", "feed_sources", "feed_polls",
                        "push_subscriptions", "push_deliveries", "slo_observations"}
            self.assertTrue(required.issubset(core_tables))
            self.assertTrue(required.issubset(migrated))


if __name__ == "__main__":
    unittest.main()
