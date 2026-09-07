"""GitHub assign-by-address: parse upstream URL and enroll same-owner *-corp write repo."""
import unittest
from unittest.mock import patch

import httpx

from company.core import Company
from company.github_app import parse_github_address, ensure_corp_write_repo
from tests.env_guard import AmbientEnvIsolatedTestCase
from tests.test_core import install, policy


class ParseGitHubAddressTests(unittest.TestCase):
    def test_owner_repo(self):
        self.assertEqual(parse_github_address("athompson36/fs-corp-comp"), ("athompson36", "fs-corp-comp"))

    def test_https_url(self):
        self.assertEqual(
            parse_github_address("https://github.com/athompson36/fs-corp-comp"),
            ("athompson36", "fs-corp-comp"),
        )

    def test_git_suffix_and_slash(self):
        self.assertEqual(
            parse_github_address("https://github.com/acme/demo.git/"),
            ("acme", "demo"),
        )

    def test_rejects_garbage(self):
        with self.assertRaises(ValueError):
            parse_github_address("not a repo")
        with self.assertRaises(ValueError):
            parse_github_address("https://gitlab.com/acme/demo")


class AssignGitHubByAddressTests(AmbientEnvIsolatedTestCase):
    def setUp(self):
        super().setUp()
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)

    def test_fail_closed_without_github(self):
        with patch("company.github_app.github_configured", return_value=False):
            with self.assertRaises(NotImplementedError):
                self.c.assign_github_by_address("human-ceo", "pilot", "acme/demo")

    @patch("company.github_app.github_configured", return_value=True)
    @patch("company.github_app.installation_account_login", return_value="acme")
    @patch("company.github_app.ensure_corp_write_repo")
    @patch("company.github_app.repo_by_full_name")
    def test_assign_creates_project_and_enrollment(self, by_name, ensure_corp, _acct, _cfg):
        by_name.return_value = {
            "id": 111, "name": "demo", "full_name": "acme/demo",
            "owner": {"login": "acme"},
        }
        ensure_corp.return_value = (
            {"id": 222, "name": "demo-corp", "full_name": "acme/demo-corp"},
            True,
        )
        out = self.c.assign_github_by_address("human-ceo", "demo", "https://github.com/acme/demo")
        self.assertEqual(out["upstream"]["id"], "111")
        self.assertEqual(out["write_repo"]["id"], "222")
        self.assertTrue(out["created_write_repo"])
        self.assertEqual(out["project_id"], "demo")
        row = self.c.db.execute("SELECT * FROM github_enrollments WHERE project_id='demo'").fetchone()
        self.assertEqual(row["upstream_repo_id"], "111")
        self.assertEqual(row["fork_repo_id"], "222")
        self.assertTrue(self.c.db.execute("SELECT 1 FROM projects WHERE id='demo'").fetchone())

    @patch("company.github_app.github_configured", return_value=True)
    @patch("company.github_app.installation_account_login", return_value="acme")
    @patch("company.github_app.ensure_corp_write_repo")
    @patch("company.github_app.repo_by_full_name")
    def test_companion_admin_can_assign(self, by_name, ensure_corp, _acct, _cfg):
        self.c.register_identity("companion-admin-deadbeef", "service", "admin-tok", ["project.enroll"])
        by_name.return_value = {"id": 1, "name": "x", "full_name": "acme/x", "owner": {"login": "acme"}}
        ensure_corp.return_value = ({"id": 2, "name": "x-corp", "full_name": "acme/x-corp"}, False)
        out = self.c.assign_github_by_address("companion-admin-deadbeef", "x", "acme/x")
        self.assertEqual(out["write_repo"]["full_name"], "acme/x-corp")
        self.assertFalse(out["created_write_repo"])

    @patch("company.github_app.github_configured", return_value=True)
    @patch("company.github_app.installation_account_login", return_value="acme")
    @patch("company.github_app.github_request")
    def test_ensure_corp_reuses_existing(self, request, _acct, _cfg):
        existing = {"id": 9, "name": "demo-corp", "full_name": "acme/demo-corp"}
        request.return_value = existing
        repo, created = ensure_corp_write_repo("acme", "demo")
        self.assertEqual(repo["id"], 9)
        self.assertFalse(created)
        request.assert_called_once()

    @patch("company.github_app.github_configured", return_value=True)
    @patch("company.github_app.installation_account_login", return_value="acme")
    @patch("company.github_app.github_request")
    def test_ensure_corp_creates_when_missing(self, request, _acct, _cfg):
        created = {"id": 10, "name": "demo-corp", "full_name": "acme/demo-corp"}

        def side_effect(method, path, json_body=None, expected=None):
            if method == "GET" and path == "/repos/acme/demo-corp":
                resp = httpx.Response(404, request=httpx.Request("GET", "https://api.github.com"))
                raise httpx.HTTPStatusError("missing", request=resp.request, response=resp)
            if method == "GET" and path == "/orgs/acme":
                resp = httpx.Response(404, request=httpx.Request("GET", "https://api.github.com"))
                raise httpx.HTTPStatusError("not org", request=resp.request, response=resp)
            if method == "POST" and path == "/user/repos":
                return created
            raise AssertionError((method, path, json_body))

        request.side_effect = side_effect
        repo, was_created = ensure_corp_write_repo("acme", "demo")
        self.assertTrue(was_created)
        self.assertEqual(repo["id"], 10)


if __name__ == "__main__":
    unittest.main()
