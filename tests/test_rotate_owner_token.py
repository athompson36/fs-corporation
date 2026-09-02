import tempfile
import unittest
from pathlib import Path

from company.core import Company
from company.service import bootstrap_owner


class RotateOwnerTokenTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.token_path = Path(self.tmp.name) / "owner.token"
        self.company = Company()
        self.addCleanup(self.company.close)
        self.current = bootstrap_owner(self.company, self.token_path)

    def test_rotate_invalidates_old_and_accepts_new(self):
        new_token = self.company.rotate_owner_token(self.current)
        self.assertNotEqual(new_token, self.current)
        self.assertIsNone(self.company.identity_for_token(self.current))
        ident = self.company.identity_for_token(new_token)
        self.assertIsNotNone(ident)
        self.assertEqual(ident["kind"], "owner")
        self.assertEqual(ident["principal_id"], "human-ceo")
        events = self.company.db.execute(
            "SELECT kind FROM events WHERE kind='identity.owner_token_rotated'"
        ).fetchall()
        self.assertEqual(len(events), 1)

    def test_rotate_rejects_wrong_current_token(self):
        with self.assertRaises(PermissionError):
            self.company.rotate_owner_token("not-the-owner-token")

    def test_rotate_rejects_identical_new_token(self):
        with self.assertRaises(ValueError):
            self.company.rotate_owner_token(self.current, new_token=self.current)

    def test_script_updates_file_and_database(self):
        from scripts.rotate_owner_token import rotate

        # Persist company to a real db path so the script opens the same store.
        db_path = Path(self.tmp.name) / "company.db"
        self.company.close()
        company = Company(str(db_path))
        self.addCleanup(company.close)
        current = bootstrap_owner(company, self.token_path)
        company.close()

        rc = rotate(db_path, self.token_path, print_token=False)
        self.assertEqual(rc, 0)
        new_token = self.token_path.read_text().strip()
        self.assertNotEqual(new_token, current)

        company = Company(str(db_path))
        self.addCleanup(company.close)
        self.assertIsNone(company.identity_for_token(current))
        self.assertIsNotNone(company.identity_for_token(new_token))


if __name__ == "__main__":
    unittest.main()
