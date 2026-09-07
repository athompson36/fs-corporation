"""P0.2 M10 ops: idempotency prune, model/benchmark reads, learning fetch."""
from __future__ import annotations
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from company.core import Company, now
from company.idempotency_prune import DEFAULT_RETENTION_DAYS, retention_days_from_env
from tests.test_api import owner_client
from tests.test_core import install, policy


class IdempotencyPruneTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)

    def test_default_retention_is_seven_days(self):
        self.assertEqual(DEFAULT_RETENTION_DAYS, 7)
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(retention_days_from_env(), 7)

    def test_prune_deletes_only_old_keys(self):
        old_at = (now() - timedelta(days=10)).isoformat()
        new_at = now().isoformat()
        with self.c.tx():
            self.c.db.execute(
                "INSERT INTO command_idempotency VALUES(?,?,?,?,?,?)",
                ("old-key", "human-ceo", "h1", 200, "{}", old_at),
            )
            self.c.db.execute(
                "INSERT INTO command_idempotency VALUES(?,?,?,?,?,?)",
                ("new-key", "human-ceo", "h2", 200, "{}", new_at),
            )
        out = self.c.prune_idempotency_keys("human-ceo", older_than_days=7)
        self.assertEqual(out["deleted"], 1)
        self.assertEqual(out["older_than_days"], 7)
        keys = {
            r["key"]
            for r in self.c.db.execute("SELECT key FROM command_idempotency")
        }
        self.assertEqual(keys, {"new-key"})

    def test_prune_http(self):
        c, client = owner_client()
        self.addCleanup(c.close)
        old_at = (now() - timedelta(days=30)).isoformat()
        with c.tx():
            c.db.execute(
                "INSERT INTO command_idempotency VALUES(?,?,?,?,?,?)",
                ("stale", "human-ceo", "h", 200, "{}", old_at),
            )
        r = client.post(
            "/api/v1/ops/idempotency/prune",
            json={"payload": {}},
            headers={"Authorization": "Bearer owner-token", "Idempotency-Key": "prune-1"},
        )
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["result"]["deleted"], 1)


class ModelBenchmarkReadTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)
        root = Path(__file__).resolve().parents[1]
        self.c.seed_models(root / "config" / "models.example.json")
        self.fixtures = root / "config" / "benchmarks.example.json"

    def test_list_model_profiles_and_seed_benchmarks(self):
        profiles = self.c.list_model_profiles()
        ids = {p["id"] for p in profiles}
        self.assertIn("mock-text", ids)
        mock = next(p for p in profiles if p["id"] == "mock-text")
        self.assertTrue(mock["enabled"])
        self.assertEqual(mock["body"]["provider"], "mock")
        seeded = self.c.seed_benchmarks(self.fixtures)
        self.assertGreaterEqual(seeded["count"], 2)
        rows = self.c.list_benchmark_results()
        self.assertGreaterEqual(len(rows), 2)
        roles = {r["role"] for r in rows}
        self.assertIn("reviewer", roles)
        self.assertIn("creator", roles)
        filtered = self.c.list_benchmark_results(role="reviewer")
        self.assertTrue(filtered)
        self.assertTrue(all(r["role"] == "reviewer" for r in filtered))

    def test_model_and_benchmark_http(self):
        c, client = owner_client()
        self.addCleanup(c.close)
        root = Path(__file__).resolve().parents[1]
        c.seed_models(root / "config" / "models.example.json")
        c.seed_benchmarks(root / "config" / "benchmarks.example.json")
        h = {"Authorization": "Bearer owner-token"}
        profiles = client.get("/api/v1/model-profiles", headers=h)
        self.assertEqual(profiles.status_code, 200, profiles.text)
        self.assertTrue(any(p["id"] == "mock-text" for p in profiles.json()["profiles"]))
        benches = client.get("/api/v1/benchmarks", headers=h)
        self.assertEqual(benches.status_code, 200, benches.text)
        self.assertGreaterEqual(len(benches.json()["items"]), 2)


class LearningFetchTests(unittest.TestCase):
    def test_allowlisted_fetch_returns_metadata(self):
        from company.adapters import LearningAdapter
        from company.learning_fetch import load_url_prefixes

        prefixes = load_url_prefixes()
        self.assertTrue(any(p.startswith("https://docs.espressif.com/") for p in prefixes))

        class FakeResponse:
            status_code = 200
            text = "<html><head><title>ESP-IDF</title></head><body>Build steps here.</body></html>"
            headers = {"content-type": "text/html"}

            def raise_for_status(self):
                return None

        class FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def get(self, url, headers=None):
                self.url = url
                return FakeResponse()

        with patch("company.learning_fetch.httpx.Client", FakeClient):
            out = LearningAdapter().fetch("https://docs.espressif.com/projects/esp-idf/en/latest/")
        self.assertEqual(out["title"], "ESP-IDF")
        self.assertIn("Build steps", out["summary"])
        self.assertEqual(out["status_code"], 200)

    def test_non_allowlisted_url_denied(self):
        from company.adapters import LearningAdapter
        with self.assertRaises(PermissionError):
            LearningAdapter().fetch("https://evil.example/docs")

    def test_missing_allowlist_file_fails_closed(self):
        from company.learning_fetch import load_url_prefixes
        with patch.dict("os.environ", {"FS_CORP_LEARNING_SOURCES_FILE": "/no/such/learning.json"}, clear=False):
            with self.assertRaises(NotImplementedError):
                load_url_prefixes()


if __name__ == "__main__":
    unittest.main()
