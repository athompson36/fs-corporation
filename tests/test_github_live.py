import os
import unittest
from unittest.mock import patch

from company.adapters import GitHubAdapter, WorkOrder
from company.core import Company
from tests.test_core import install, policy


class GitHubLiveAdapterTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.c.enroll_project("human-ceo", "app", "Pilot fork")
        self.c.enroll_github("human-ceo", "app", "111", "222", ["main"], "company/app/", ["push", "open_pr"])
        self.addCleanup(self.c.close)

    def test_adapter_fail_closed_without_credentials(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(NotImplementedError):
                GitHubAdapter().execute(WorkOrder(
                    "t1", "app", 1, "github-effect", 0,
                    {"operation": "open_pr", "repo_id": "222", "branch": "company/app/t1"}))

    @patch("company.github_app.github_configured", return_value=True)
    @patch("company.github_app.repo_by_id")
    @patch("company.github_app.github_request")
    @patch("company.github_app.ensure_branch")
    @patch("company.github_app.upsert_file")
    @patch("company.github_app.open_pull_request")
    def test_apply_github_effect_live_open_pr(self, open_pr, upsert, ensure, request, repo_by_id, configured):
        repo_by_id.return_value = {"owner": {"login": "acme"}, "name": "pilot", "default_branch": "main"}
        request.return_value = {"object": {"sha": "base-sha"}}
        open_pr.return_value = {"number": 42, "html_url": "https://github.com/acme/pilot/pull/42", "id": 99}
        result = self.c.apply_github_effect("app", "t1", "open_pr", "222", "company/app/t1")
        self.assertEqual(result["status"], "applied")
        self.assertEqual(result["remote_id"], "42")
        self.assertEqual(self.c.db.execute("SELECT COUNT(*) FROM github_effects WHERE task_id='t1'").fetchone()[0], 1)

    @patch("company.github_app.status_summary")
    def test_status_endpoint(self, summary):
        from fastapi.testclient import TestClient
        from company.service import create_app
        summary.return_value = {"configured": True, "live": True, "app_slug": "fs-corp"}
        self.c.register_identity("human-ceo", "owner", "owner-token")
        client = TestClient(create_app(self.c))
        r = client.get("/api/v1/github/status", headers={"Authorization": "Bearer owner-token"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["live"])


if __name__ == "__main__":
    unittest.main()
