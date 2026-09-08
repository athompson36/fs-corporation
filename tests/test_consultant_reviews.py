"""Consultant review cooldown read surface."""
import unittest

from company.core import Company
from tests.test_api import owner_client
from tests.test_core import install, policy


class ConsultantReviewsTests(unittest.TestCase):
    def test_list_after_cooldown(self):
        c = Company()
        install(c, policy(c))
        self.addCleanup(c.close)
        until = c.consultant_cooldown("org_review", hours=1)
        rows = c.list_consultant_reviews()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["trigger_kind"], "org_review")
        self.assertEqual(rows[0]["cooldown_until"], until)

    def test_http_list(self):
        c, client = owner_client()
        self.addCleanup(c.close)
        c.consultant_cooldown("code_review", hours=2)
        r = client.get(
            "/api/v1/consultant/reviews",
            headers={"Authorization": "Bearer owner-token"},
        )
        self.assertEqual(r.status_code, 200, r.text)
        kinds = {row["trigger_kind"] for row in r.json()["reviews"]}
        self.assertIn("code_review", kinds)


if __name__ == "__main__":
    unittest.main()
