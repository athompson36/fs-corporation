"""Alembic-on-startup / schema drift (M10-01)."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from company.core import Company


class AlembicStartupTests(unittest.TestCase):
    def test_company_opens_legacy_file_db_and_adds_missing_columns(self):
        """CREATE TABLE IF NOT EXISTS cannot ALTER; startup must run migrations."""
        with tempfile.TemporaryDirectory() as d:
            path = str(Path(d) / "legacy.db")
            raw = sqlite3.connect(path)
            # Minimal pre-0011 shape: pairing_tickets without access_level, no alembic_version.
            raw.executescript(
                """
                CREATE TABLE settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE policies(version INTEGER PRIMARY KEY, body TEXT NOT NULL);
                CREATE TABLE events(
                  seq INTEGER PRIMARY KEY AUTOINCREMENT,
                  at TEXT NOT NULL, kind TEXT NOT NULL, body TEXT NOT NULL,
                  previous TEXT, hash TEXT NOT NULL, event_id TEXT NOT NULL,
                  schema_version INTEGER NOT NULL, actor_id TEXT, policy_version INTEGER,
                  correlation_id TEXT, project_id TEXT);
                CREATE TABLE pairing_tickets(
                  id TEXT PRIMARY KEY, ticket_hash TEXT NOT NULL, created_by TEXT NOT NULL,
                  created_at TEXT NOT NULL, expires_at TEXT NOT NULL, status TEXT NOT NULL,
                  redeemed_at TEXT, companion_principal TEXT);
                INSERT INTO settings VALUES('ceo', 'human-ceo');
                INSERT INTO settings VALUES('paused', 'false');
                INSERT INTO policies VALUES(1, '{"version":1,"company_budget_cents":10000,"grants":{}}');
                """
            )
            raw.close()

            probe = sqlite3.connect(path)
            cols_before = {row[1] for row in probe.execute("PRAGMA table_info(pairing_tickets)")}
            probe.close()
            self.assertNotIn("access_level", cols_before)

            company = Company(path)
            try:
                cols = {
                    row[1]
                    for row in company.db.execute("PRAGMA table_info(pairing_tickets)").fetchall()
                }
                self.assertIn("access_level", cols)
                version = company.db.execute(
                    "SELECT version_num FROM alembic_version"
                ).fetchone()
                self.assertIsNotNone(version)
                from company.migrate import HEAD_REVISION
                self.assertEqual(version[0], HEAD_REVISION)
            finally:
                company.close()

    def test_memory_company_still_opens(self):
        company = Company()
        self.addCleanup(company.close)
        self.assertEqual(company.ceo, "human-ceo")


if __name__ == "__main__":
    unittest.main()
