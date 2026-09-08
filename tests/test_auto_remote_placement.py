"""Opt-in auto placement onto ready remote worker hosts."""
import json
import unittest

from company.core import Company
from company.worker_hosts import (
    choose_ready_remote_host_id,
    create_worker_host,
    prefer_remote_workers,
    record_worker_host_heartbeat,
)
from tests.test_api import owner_client
from tests.test_core import install, policy


class PlacementHelperTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)

    def test_choose_first_by_label(self):
        b = create_worker_host(
            self.c, "human-ceo", label="bravo", base_url="https://b.example.com"
        )
        a = create_worker_host(
            self.c, "human-ceo", label="alpha", base_url="https://a.example.com"
        )
        record_worker_host_heartbeat(self.c, b["id"], b["token"])
        record_worker_host_heartbeat(self.c, a["id"], a["token"])
        self.assertEqual(choose_ready_remote_host_id(self.c), a["id"])

    def test_prefer_default_false(self):
        self.assertFalse(prefer_remote_workers(self.c))


class AutoPlacementHttpTests(unittest.TestCase):
    def setUp(self):
        self.c, self.client = owner_client()
        self.addCleanup(self.c.close)
        self.headers = {"Authorization": "Bearer owner-token"}
        created = self.client.post(
            "/api/v1/worker-hosts",
            json={"payload": {"label": "lab", "base_url": "https://lab.example.com"}},
            headers={**self.headers, "Idempotency-Key": "auto-h1"},
        )
        self.assertEqual(created.status_code, 200, created.text)
        body = created.json()["result"]
        self.host_id = body["id"]
        self.token = body["token"]
        self.client.post(
            f"/api/v1/worker-hosts/{self.host_id}/heartbeat",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.c.queue_task("head", "app", "draft", 10, "auto-t1")
        self.c.queue_task("head", "app", "draft", 10, "auto-t2")

    def _enable_prefer(self):
        with self.c.tx():
            self.c.db.execute(
                "INSERT OR REPLACE INTO company_settings VALUES(?,?,?,?)",
                (
                    "FS_CORP_PREFER_REMOTE_WORKERS",
                    json.dumps(True),
                    "2026-09-08T00:00:00+00:00",
                    "human-ceo",
                ),
            )

    def test_prefer_on_auto_places(self):
        self._enable_prefer()
        disp = self.client.post(
            "/api/v1/tasks/auto-t1/dispatch-worker",
            json={"payload": {}},
            headers={**self.headers, "Idempotency-Key": "auto-d1"},
        )
        self.assertEqual(disp.status_code, 200, disp.text)
        result = disp.json()["result"]
        self.assertEqual(result["placement"], "auto")
        self.assertEqual(result["worker_host_id"], self.host_id)
        self.assertEqual(result["status"], "queued")

    def test_prefer_on_no_ready_fails(self):
        self._enable_prefer()
        # no heartbeat host
        cold = self.client.post(
            "/api/v1/worker-hosts",
            json={"payload": {"label": "cold", "base_url": "https://cold.example.com"}},
            headers={**self.headers, "Idempotency-Key": "auto-cold"},
        )
        self.assertEqual(cold.status_code, 200)
        # disable the ready lab so none ready
        self.client.post(
            f"/api/v1/worker-hosts/{self.host_id}/disable",
            json={"payload": {}},
            headers={**self.headers, "Idempotency-Key": "auto-dis"},
        )
        self.c.queue_task("head", "app", "draft", 10, "auto-t3")
        disp = self.client.post(
            "/api/v1/tasks/auto-t3/dispatch-worker",
            json={"payload": {}},
            headers={**self.headers, "Idempotency-Key": "auto-fail"},
        )
        self.assertEqual(disp.status_code, 422, disp.text)

    def test_explicit_wins_with_prefer(self):
        self._enable_prefer()
        other = create_worker_host(
            self.c, "human-ceo", label="zzz", base_url="https://zzz.example.com"
        )
        record_worker_host_heartbeat(self.c, other["id"], other["token"])
        disp = self.client.post(
            "/api/v1/tasks/auto-t2/dispatch-worker",
            json={"payload": {"worker_host_id": other["id"]}},
            headers={**self.headers, "Idempotency-Key": "auto-exp"},
        )
        self.assertEqual(disp.status_code, 200, disp.text)
        result = disp.json()["result"]
        self.assertEqual(result["placement"], "explicit")
        self.assertEqual(result["worker_host_id"], other["id"])


if __name__ == "__main__":
    unittest.main()
