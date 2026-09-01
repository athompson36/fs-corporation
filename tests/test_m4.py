from datetime import timedelta
import unittest
from company.core import Company, now
from tests.test_core import install, policy


class GitHubPilotTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.c.enroll_project("human-ceo", "app", "Pilot fork")
        self.c.enroll_github("human-ceo", "app", "111", "222", ["main"], "company/app/", ["push", "open_pr", "prepare_pr"])
        self.addCleanup(self.c.close)

    def test_denials_and_idempotent_effect(self):
        with self.assertRaises(PermissionError):
            self.c.authorize_github_effect("app", "push", "999", "company/app/t1")
        with self.assertRaises(PermissionError):
            self.c.authorize_github_effect("app", "push", "222", "main")
        with self.assertRaises(PermissionError):
            self.c.authorize_github_effect("app", "push", "222", "random-branch")
        with self.assertRaises(PermissionError):
            self.c.authorize_github_effect("app", "push", "222", "company/app/t1", path=".github/workflows/ci.yml")
        with self.assertRaises(PermissionError):
            self.c.authorize_github_effect("app", "push", "222", "company/app/t1", head_sha="aaa", expected_sha="bbb")
        with self.assertRaises(PermissionError):
            self.c.authorize_github_effect("app", "merge", "222", "company/app/t1")
        self.assertTrue(self.c.authorize_github_effect("app", "push", "222", "company/app/t1"))
        a = self.c.record_github_effect("app", "t1", "open_pr", "222", "company/app/t1")
        b = self.c.record_github_effect("app", "t1", "open_pr", "222", "company/app/t1")
        self.assertEqual(a["id"], b["id"])
        self.assertEqual(self.c.worktree_path("app", "t1"), "workspaces/app/t1")
        self.assertNotEqual(self.c.worktree_path("app", "t1"), "workspaces/human")


if __name__ == "__main__":
    unittest.main()
