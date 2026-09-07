"""Local repos candidates and diagnostics-related coverage."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from company.core import Company
from company.local_repos import scan_local_repos
from tests.test_api import owner_client
from tests.test_core import install, policy


class ScanLocalReposTests(unittest.TestCase):
    def test_missing_root(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "nope"
            out = scan_local_repos(root, enrolled_ids=set())
            self.assertFalse(out["present"])
            self.assertEqual(out["candidates"], [])

    def test_lists_dirs_and_enrolled_flag(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "alpha").mkdir()
            (root / "beta").mkdir()
            (root / ".hidden").mkdir()
            (root / "notes.txt").write_text("x")
            out = scan_local_repos(root, enrolled_ids={"beta"})
            ids = [c["id"] for c in out["candidates"]]
            self.assertEqual(ids, ["alpha", "beta"])
            by_id = {c["id"]: c for c in out["candidates"]}
            self.assertFalse(by_id["alpha"]["enrolled"])
            self.assertTrue(by_id["beta"]["enrolled"])
            self.assertFalse(by_id["alpha"]["has_git"])


class LocalReposApiTests(unittest.TestCase):
    def setUp(self):
        self.c, self.client = owner_client()
        self.addCleanup(self.c.close)

    def test_local_repos_endpoint(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "service-department").mkdir()
            self.c.enroll_project("human-ceo", "other", "already there")
            with patch("company.local_repos.local_repos_root", return_value=root):
                r = self.client.get(
                    "/api/v1/local-repos",
                    headers={"Authorization": "Bearer owner-token"},
                )
            self.assertEqual(r.status_code, 200)
            body = r.json()
            self.assertTrue(body["present"])
            self.assertEqual(len(body["candidates"]), 1)
            self.assertEqual(body["candidates"][0]["id"], "service-department")
            self.assertFalse(body["candidates"][0]["enrolled"])

    def test_local_repos_requires_auth(self):
        self.assertEqual(self.client.get("/api/v1/local-repos").status_code, 401)


if __name__ == "__main__":
    unittest.main()
