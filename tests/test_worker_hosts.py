"""Tests for remote worker host registry (P4)."""
from datetime import timedelta
from unittest.mock import patch

from company.core import Company, now
from company.worker_hosts import (
    create_worker_host,
    host_state,
    list_worker_hosts,
    record_worker_host_heartbeat,
    remote_host_status_rows,
    set_worker_host_enabled,
)
from company.worker_status import status_summary
from tests.test_api import owner_client
from tests.test_core import install, policy
import unittest


class WorkerHostsTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)

    def test_create_returns_token_once_and_https_only(self):
        created = create_worker_host(
            self.c, "human-ceo", label="lab-b", base_url="https://workers.example.com"
        )
        self.assertIn("token", created)
        self.assertTrue(created["token"])
        listed = list_worker_hosts(self.c)
        self.assertEqual(len(listed), 1)
        self.assertNotIn("token", listed[0])
        self.assertEqual(listed[0]["state"], "stale")
        with self.assertRaises(ValueError):
            create_worker_host(
                self.c, "human-ceo", label="bad", base_url="http://insecure.example.com"
            )
        with self.assertRaises(PermissionError):
            create_worker_host(
                self.c, "not-ceo", label="x", base_url="https://workers.example.com"
            )

    def test_heartbeat_ready_stale_disabled(self):
        created = create_worker_host(
            self.c, "human-ceo", label="lab-b", base_url="https://workers.example.com/"
        )
        host_id = created["id"]
        token = created["token"]
        with self.assertRaises(PermissionError):
            record_worker_host_heartbeat(self.c, host_id, "wrong-token")
        hb = record_worker_host_heartbeat(
            self.c, host_id, token, meta={"version": "1.0"}
        )
        self.assertEqual(hb["state"], "ready")
        self.assertEqual(hb["last_heartbeat_meta"]["version"], "1.0")
        rows = remote_host_status_rows(self.c)
        self.assertEqual(rows[0]["state"], "ready")
        self.assertNotIn("token", rows[0])
        self.assertNotIn("heartbeat_token_hash", str(rows[0]))

        row = self.c.db.execute(
            "SELECT * FROM worker_hosts WHERE id=?", (host_id,)
        ).fetchone()
        stale_now = now() + timedelta(seconds=500)
        self.assertEqual(host_state(row, ttl_sec=120, now_dt=stale_now), "stale")
        with patch("company.worker_hosts.now", return_value=stale_now):
            listed = list_worker_hosts(self.c)
            self.assertEqual(listed[0]["state"], "stale")

        disabled = set_worker_host_enabled(self.c, "human-ceo", host_id, False)
        self.assertEqual(disabled["state"], "disabled")
        with self.assertRaises(PermissionError):
            record_worker_host_heartbeat(self.c, host_id, token)

    def test_status_summary_includes_remote_hosts_without_token(self):
        created = create_worker_host(
            self.c, "human-ceo", label="edge", base_url="https://edge.example.com"
        )
        record_worker_host_heartbeat(self.c, created["id"], created["token"])
        summary = status_summary(company=self.c)
        self.assertEqual(len(summary["remote_hosts"]), 1)
        self.assertEqual(summary["remote_hosts"][0]["label"], "edge")
        self.assertEqual(summary["remote_hosts"][0]["state"], "ready")
        blob = str(summary)
        self.assertNotIn(created["token"], blob)
        self.assertNotIn("heartbeat_token_hash", blob)


class WorkerHostsHttpTests(unittest.TestCase):
    def setUp(self):
        self.c, self.client = owner_client()
        self.addCleanup(self.c.close)
        self.headers = {"Authorization": "Bearer owner-token"}

    def test_http_create_heartbeat_status(self):
        r = self.client.post(
            "/api/v1/worker-hosts",
            json={"payload": {"label": "lab", "base_url": "https://lab.example.com"}},
            headers={**self.headers, "Idempotency-Key": "wh-1"},
        )
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()["result"]
        token = body["token"]
        host_id = body["id"]
        hb = self.client.post(
            f"/api/v1/worker-hosts/{host_id}/heartbeat",
            json={"meta": {"runtime_ready": True}},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(hb.status_code, 200, hb.text)
        self.assertEqual(hb.json()["state"], "ready")
        status = self.client.get("/api/v1/workers/status", headers=self.headers)
        self.assertEqual(status.status_code, 200)
        remotes = status.json()["remote_hosts"]
        self.assertEqual(len(remotes), 1)
        self.assertEqual(remotes[0]["state"], "ready")
        self.assertNotIn("token", remotes[0])
        listed = self.client.get("/api/v1/worker-hosts", headers=self.headers)
        self.assertEqual(listed.status_code, 200)
        self.assertNotIn("token", listed.json()["hosts"][0])


if __name__ == "__main__":
    unittest.main()
