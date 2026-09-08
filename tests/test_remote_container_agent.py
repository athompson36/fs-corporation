"""Remote container-on-agent: envelope, gateway relay, renew."""
import os
import tempfile
import unittest
from datetime import timedelta
from unittest.mock import patch

from company.core import Company, now
from company.remote_jobs import (
    claim_job,
    enqueue_remote_job,
    relay_gateway,
    renew_job_lease,
)
from company.worker_hosts import create_worker_host, record_worker_host_heartbeat
from tests.test_api import owner_client
from tests.test_core import install, policy


class ClaimEnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)
        created = create_worker_host(
            self.c, "human-ceo", label="lab", base_url="https://lab.example.com"
        )
        self.host_id = created["id"]
        self.token = created["token"]
        record_worker_host_heartbeat(self.c, self.host_id, self.token)
        self.c.queue_task("head", "app", "draft", 10, "env-t1")

    def test_claim_includes_envelope(self):
        job = enqueue_remote_job(
            self.c, "human-ceo",
            host_id=self.host_id, task_id="env-t1", worker_id="worker-r",
        )
        claimed = claim_job(self.c, self.host_id, self.token, job["id"])
        env = claimed["envelope"]
        self.assertEqual(env["task_id"], "env-t1")
        self.assertEqual(env["worker_id"], f"remote-host:{self.host_id}")
        self.assertIn("payload", env)
        self.assertIn("workflow_digest", env)


class GatewayRelayTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.addCleanup(self.c.close)
        created = create_worker_host(
            self.c, "human-ceo", label="lab", base_url="https://lab.example.com"
        )
        self.host_id = created["id"]
        self.token = created["token"]
        record_worker_host_heartbeat(self.c, self.host_id, self.token)
        self.c.queue_task("head", "app", "draft", 10, "gw-t1")

    def _claimed(self):
        job = enqueue_remote_job(
            self.c,
            "human-ceo",
            host_id=self.host_id,
            task_id="gw-t1",
            worker_id="worker-r",
        )
        return claim_job(self.c, self.host_id, self.token, job["id"])

    def test_gateway_check_allowed_and_renews_lease(self):
        claimed = self._claimed()
        old_expiry = (now() + timedelta(seconds=5)).isoformat()
        with self.c.tx():
            self.c.db.execute(
                "UPDATE remote_worker_jobs SET lease_expires_at=? WHERE id=?",
                (old_expiry, claimed["id"]),
            )
        reply = relay_gateway(
            self.c,
            self.host_id,
            self.token,
            claimed["id"],
            {
                "op": "gateway_check",
                "actor": "head",
                "project": "app",
                "action": "draft",
                "cost": 10,
                "task_id": "gw-t1",
            },
        )
        self.assertTrue(reply.get("allow"))
        row = self.c.db.execute(
            "SELECT lease_expires_at FROM remote_worker_jobs WHERE id=?",
            (claimed["id"],),
        ).fetchone()
        self.assertGreater(row["lease_expires_at"], old_expiry)

    def test_gateway_unknown_op_denied(self):
        claimed = self._claimed()
        with self.assertRaises(PermissionError):
            relay_gateway(
                self.c,
                self.host_id,
                self.token,
                claimed["id"],
                {"op": "delete_database"},
            )

    def test_renew_extends_lease(self):
        claimed = self._claimed()
        before = claimed["lease_expires_at"]
        renewed = renew_job_lease(
            self.c, self.host_id, self.token, claimed["id"]
        )
        self.assertGreaterEqual(renewed["lease_expires_at"], before)

    def test_gateway_rejects_expired_lease(self):
        claimed = self._claimed()
        past = (now() - timedelta(seconds=5)).isoformat()
        with self.c.tx():
            self.c.db.execute(
                "UPDATE remote_worker_jobs SET lease_expires_at=? WHERE id=?",
                (past, claimed["id"]),
            )
        with self.assertRaises(PermissionError):
            relay_gateway(
                self.c,
                self.host_id,
                self.token,
                claimed["id"],
                {
                    "op": "gateway_check",
                    "actor": "head",
                    "project": "app",
                    "action": "draft",
                    "cost": 10,
                    "task_id": "gw-t1",
                },
            )

    def test_store_artifact_uses_control_plane_root(self):
        claimed = self._claimed()
        with tempfile.TemporaryDirectory() as scratch:
            with patch.dict(os.environ, {"FS_CORP_WORKER_SCRATCH": scratch}):
                reply = relay_gateway(
                    self.c,
                    self.host_id,
                    self.token,
                    claimed["id"],
                    {
                        "op": "store_artifact",
                        "producer": "head",
                        "project": "app",
                        "task_id": "gw-t1",
                        "root": "/work",
                        "content_text": "artifact",
                    },
                )
            self.assertIn("hash", reply)
            artifact = self.c.db.execute(
                "SELECT storage_uri FROM artifacts WHERE hash=?", (reply["hash"],)
            ).fetchone()
            self.assertEqual(
                os.path.dirname(artifact["storage_uri"]),
                os.path.join(scratch, "remote-artifacts", "gw-t1"),
            )


class GatewayRelayHttpTests(unittest.TestCase):
    def setUp(self):
        self.c, self.client = owner_client()
        self.addCleanup(self.c.close)
        created = create_worker_host(
            self.c, "human-ceo", label="lab", base_url="https://lab.example.com"
        )
        self.host_id = created["id"]
        self.token = created["token"]
        self.host_headers = {"Authorization": f"Bearer {self.token}"}
        record_worker_host_heartbeat(self.c, self.host_id, self.token)
        self.c.queue_task("head", "app", "draft", 10, "gw-http-t1")
        job = enqueue_remote_job(
            self.c,
            "human-ceo",
            host_id=self.host_id,
            task_id="gw-http-t1",
            worker_id="worker-r",
        )
        claimed = claim_job(self.c, self.host_id, self.token, job["id"])
        self.job_id = claimed["id"]

    def test_http_gateway_and_renew(self):
        gateway = self.client.post(
            f"/api/v1/worker-hosts/{self.host_id}/jobs/{self.job_id}/gateway",
            json={
                "op": "gateway_check",
                "actor": "head",
                "project": "app",
                "action": "draft",
                "cost": 10,
                "task_id": "gw-http-t1",
            },
            headers=self.host_headers,
        )
        self.assertEqual(gateway.status_code, 200, gateway.text)
        self.assertTrue(gateway.json()["allow"])
        renewed = self.client.post(
            f"/api/v1/worker-hosts/{self.host_id}/jobs/{self.job_id}/renew",
            headers=self.host_headers,
        )
        self.assertEqual(renewed.status_code, 200, renewed.text)
        self.assertEqual(renewed.json()["status"], "claimed")

    def test_http_gateway_maps_permission_and_value_errors(self):
        denied = self.client.post(
            f"/api/v1/worker-hosts/{self.host_id}/jobs/{self.job_id}/gateway",
            json={"op": "delete_database"},
            headers=self.host_headers,
        )
        self.assertEqual(denied.status_code, 403, denied.text)
        with patch.object(
            self.c, "gateway_remote_job", side_effect=ValueError("bad gateway")
        ):
            invalid = self.client.post(
                f"/api/v1/worker-hosts/{self.host_id}/jobs/{self.job_id}/gateway",
                json={"op": "gateway_check"},
                headers=self.host_headers,
            )
        self.assertEqual(invalid.status_code, 422, invalid.text)
