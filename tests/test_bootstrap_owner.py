import tempfile
import unittest
from pathlib import Path

from company.core import Company
from company.service import bootstrap_owner


class BootstrapOwnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.token_path = Path(self.tmp.name) / "owner.token"
        self.company = Company()
        self.addCleanup(self.company.close)

    def test_generates_and_registers_when_absent(self):
        token = bootstrap_owner(self.company, self.token_path)
        self.assertTrue(self.token_path.is_file())
        ident = self.company.identity_for_token(token)
        self.assertIsNotNone(ident)
        self.assertEqual(ident["kind"], "owner")

    def test_registers_token_file_written_before_first_start(self):
        """The fs-dev installer creates owner.token as root before the service runs.

        The identity must still be registered, otherwise every request is 401.
        """
        self.token_path.write_text("provisioned-by-installer\n")

        token = bootstrap_owner(self.company, self.token_path)

        self.assertEqual(token, "provisioned-by-installer")
        ident = self.company.identity_for_token(token)
        self.assertIsNotNone(ident, "pre-created token file must be registered as the owner")
        self.assertEqual(ident["principal_id"], "human-ceo")

    def test_idempotent_across_restarts(self):
        first = bootstrap_owner(self.company, self.token_path)
        second = bootstrap_owner(self.company, self.token_path)
        self.assertEqual(first, second)
        rows = self.company.db.execute("SELECT COUNT(*) FROM identities").fetchone()
        self.assertEqual(rows[0], 1)

    def test_refuses_to_start_when_token_file_does_not_match_owner(self):
        bootstrap_owner(self.company, self.token_path)
        self.token_path.write_text("a-different-token")

        with self.assertRaises(RuntimeError) as ctx:
            bootstrap_owner(self.company, self.token_path)
        self.assertIn("different token", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
