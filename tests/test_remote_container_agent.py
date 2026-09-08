"""Remote container-on-agent: envelope, gateway relay, renew."""
import importlib.util
import json
import os
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import MagicMock, call, patch

from company.core import Company, now
from company.remote_jobs import (
    claim_job,
    complete_job,
    enqueue_remote_job,
    relay_gateway,
    renew_job_lease,
)
from company.worker import SubprocessWorkerRuntime
from company.worker_hosts import create_worker_host, record_worker_host_heartbeat
from tests.test_api import owner_client
from tests.test_core import install, policy


AGENT_PATH = Path(__file__).parents[1] / "scripts" / "remote_worker_agent.py"
AGENT_SPEC = importlib.util.spec_from_file_location("remote_worker_agent", AGENT_PATH)
remote_worker_agent = importlib.util.module_from_spec(AGENT_SPEC)
assert AGENT_SPEC.loader is not None
AGENT_SPEC.loader.exec_module(remote_worker_agent)


class RemoteContainerAgentTests(unittest.TestCase):
    def test_runtime_mode_reads_environment(self):
        with patch.dict(
            os.environ, {"FS_CORP_REMOTE_WORKER_RUNTIME": " container "}, clear=False
        ):
            self.assertEqual(remote_worker_agent.runtime_mode(), "container")

    def test_docker_ready_reports_missing_binary(self):
        with patch.object(remote_worker_agent.shutil, "which", return_value=None):
            ready, reason = remote_worker_agent.docker_ready("worker:local")
        self.assertFalse(ready)
        self.assertIn("Docker", reason)

    def test_docker_ready_reports_missing_image(self):
        inspected = MagicMock(return_value=MagicMock(returncode=1, stderr="No such image"))
        with patch.object(remote_worker_agent.subprocess, "run", inspected):
            ready, reason = remote_worker_agent.docker_ready(
                "worker:missing", docker_bin="/usr/bin/docker"
            )
        self.assertFalse(ready)
        self.assertIn("worker:missing", reason)
        inspected.assert_called_once()

    def test_build_docker_cmd_forces_network_none(self):
        with tempfile.TemporaryDirectory() as scratch:
            cmd = remote_worker_agent.build_docker_cmd(
                "/usr/bin/docker", "worker:local", Path(scratch)
            )
        self.assertIn(["--network", "none"], [cmd[i : i + 2] for i in range(len(cmd) - 1)])
        self.assertNotIn("bridge", cmd)
        self.assertIn("fs.corp.runtime=remote_container", cmd)

    def test_pump_remote_gateway_relays_request_and_renews(self):
        with tempfile.TemporaryDirectory() as scratch_name:
            scratch = Path(scratch_name)
            (scratch / "gw-request.json").write_text(
                json.dumps({"type": "request", "op": "gateway_check"}),
                encoding="utf-8",
            )
            (scratch / "result.json").write_text(
                json.dumps({"task_id": "agent-t1"}), encoding="utf-8"
            )
            post_gateway = MagicMock(return_value={"allow": True})
            renew = MagicMock()

            result = remote_worker_agent.pump_remote_gateway(
                scratch, post_gateway, renew, timeout=0.2
            )

            self.assertEqual(result["task_id"], "agent-t1")
            post_gateway.assert_called_once_with(
                {"type": "request", "op": "gateway_check"}
            )
            renew.assert_called_once_with()
            self.assertEqual(
                json.loads((scratch / "gw-response.json").read_text(encoding="utf-8")),
                {"allow": True},
            )

    def test_pump_remote_gateway_detects_dead_process_without_result(self):
        with tempfile.TemporaryDirectory() as scratch_name:
            proc = MagicMock()
            proc.poll.return_value = 7
            proc.communicate.return_value = ("", "worker crashed")

            with self.assertRaisesRegex(
                RuntimeError, "Remote container exited 7: worker crashed"
            ):
                remote_worker_agent.pump_remote_gateway(
                    Path(scratch_name),
                    MagicMock(),
                    MagicMock(),
                    proc=proc,
                    timeout=120,
                )

            proc.poll.assert_called()
            proc.communicate.assert_called_once_with()

    def test_once_default_path_still_mock_completes(self):
        claimed = {"id": "job-1", "task_id": "agent-t1"}
        responses = [
            {},
            {"jobs": [{"id": "job-1", "task_id": "agent-t1"}]},
            claimed,
            {},
        ]
        with patch.object(remote_worker_agent, "request", side_effect=responses) as http:
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("FS_CORP_REMOTE_WORKER_RUNTIME", None)
                handled = remote_worker_agent.once("https://control", "host-1", "token")
        self.assertEqual(handled, 1)
        self.assertEqual(
            http.call_args_list[-1],
            call(
                "POST",
                "https://control/api/v1/worker-hosts/host-1/jobs/job-1/complete",
                "token",
                {
                    "status": "completed",
                    "result": {
                        "type": "remote_mock",
                        "task_id": "agent-t1",
                        "artifact_hint": "remote-mock-agent-t1",
                    },
                },
            ),
        )

    def test_once_container_missing_docker_fails_without_mock(self):
        claimed = {"id": "job-1", "task_id": "agent-t1", "envelope": {}}
        responses = [
            {},
            {"jobs": [{"id": "job-1", "task_id": "agent-t1"}]},
            claimed,
            {},
        ]
        with patch.object(remote_worker_agent, "request", side_effect=responses) as http:
            with patch.object(
                remote_worker_agent,
                "docker_ready",
                return_value=(False, "Docker executable not found"),
            ):
                with patch.dict(
                    os.environ, {"FS_CORP_REMOTE_WORKER_RUNTIME": "container"}
                ):
                    handled = remote_worker_agent.once(
                        "https://control", "host-1", "token"
                    )
        self.assertEqual(handled, 1)
        self.assertEqual(
            http.call_args_list[-1],
            call(
                "POST",
                "https://control/api/v1/worker-hosts/host-1/jobs/job-1/complete",
                "token",
                {
                    "status": "failed",
                    "result": {
                        "error": "Docker executable not found",
                        "type": "remote_container_unready",
                    },
                },
            ),
        )

    def test_once_container_setup_failure_posts_failed_complete(self):
        claimed = {
            "id": "job-1",
            "task_id": "agent-t1",
            "envelope": {"task_id": "agent-t1"},
        }
        responses = [
            {},
            {"jobs": [{"id": "job-1", "task_id": "agent-t1"}]},
            claimed,
            {},
        ]
        with patch.object(remote_worker_agent, "request", side_effect=responses) as http:
            with patch.object(
                remote_worker_agent, "docker_ready", return_value=(True, "")
            ):
                with patch.object(
                    remote_worker_agent.shutil, "which", return_value="/docker"
                ):
                    with patch.object(
                        remote_worker_agent.Path,
                        "write_text",
                        side_effect=OSError("scratch is read-only"),
                    ):
                        with patch.dict(
                            os.environ, {"FS_CORP_REMOTE_WORKER_RUNTIME": "container"}
                        ):
                            handled = remote_worker_agent.once(
                                "https://control", "host-1", "token"
                            )

        self.assertEqual(handled, 1)
        self.assertEqual(
            http.call_args_list[-1],
            call(
                "POST",
                "https://control/api/v1/worker-hosts/host-1/jobs/job-1/complete",
                "token",
                {
                    "status": "failed",
                    "result": {
                        "error": "scratch is read-only",
                        "type": "remote_container_error",
                    },
                },
            ),
        )

    def test_execute_claimed_job_posts_gateway_and_renew(self):
        claimed = {
            "id": "job-1",
            "task_id": "agent-t1",
            "envelope": {"task_id": "agent-t1"},
        }
        container_proc = MagicMock(returncode=0)
        container_proc.communicate.return_value = ("", "")

        def pump(_scratch, post_gateway, renew, *, proc):
            self.assertIs(proc, container_proc)
            self.assertEqual(
                post_gateway({"op": "gateway_check"}), {"allow": True}
            )
            renew()
            return {"task_id": "agent-t1"}

        with patch.object(remote_worker_agent.shutil, "which", return_value="/docker"):
            with patch.object(
                remote_worker_agent.subprocess,
                "Popen",
                return_value=container_proc,
            ):
                with patch.object(
                    remote_worker_agent, "pump_remote_gateway", side_effect=pump
                ):
                    with patch.object(
                        remote_worker_agent,
                        "request",
                        side_effect=[{"allow": True}, {"status": "claimed"}],
                    ) as http:
                        status, result, container_started = remote_worker_agent.execute_claimed_job(
                            "https://control", "host-1", "token", claimed
                        )
        self.assertEqual((status, result), ("completed", {"task_id": "agent-t1"}))
        self.assertTrue(container_started)
        self.assertEqual(
            http.call_args_list,
            [
                call(
                    "POST",
                    "https://control/api/v1/worker-hosts/host-1/jobs/job-1/gateway",
                    "token",
                    {"op": "gateway_check"},
                ),
                call(
                    "POST",
                    "https://control/api/v1/worker-hosts/host-1/jobs/job-1/renew",
                    "token",
                ),
            ],
        )

    def test_execute_claimed_job_returns_failed_when_docker_start_fails(self):
        claimed = {"id": "job-1", "envelope": {"task_id": "agent-t1"}}
        with patch.object(remote_worker_agent.shutil, "which", return_value="/docker"):
            with patch.object(
                remote_worker_agent.subprocess,
                "Popen",
                side_effect=OSError("cannot start docker"),
            ):
                status, result, container_started = remote_worker_agent.execute_claimed_job(
                    "https://control", "host-1", "token", claimed
                )
        self.assertEqual(status, "failed")
        self.assertEqual(result["type"], "remote_container_error")
        self.assertIn("cannot start docker", result["error"])
        self.assertFalse(container_started)


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
        old_expiry = (now() + timedelta(seconds=5)).isoformat()
        with self.c.tx():
            self.c.db.execute(
                "UPDATE remote_worker_jobs SET lease_expires_at=? WHERE id=?",
                (old_expiry, claimed["id"]),
            )
        with self.assertRaises(PermissionError):
            relay_gateway(
                self.c,
                self.host_id,
                self.token,
                claimed["id"],
                {"op": "delete_database"},
            )
        row = self.c.db.execute(
            "SELECT lease_expires_at FROM remote_worker_jobs WHERE id=?",
            (claimed["id"],),
        ).fetchone()
        self.assertEqual(row["lease_expires_at"], old_expiry)

    def test_gateway_invoke_model_denied(self):
        claimed = self._claimed()
        with patch.object(
            SubprocessWorkerRuntime, "handle_request"
        ) as handle_request:
            with self.assertRaises(PermissionError):
                relay_gateway(
                    self.c,
                    self.host_id,
                    self.token,
                    claimed["id"],
                    {"op": "invoke_model"},
                )
        handle_request.assert_not_called()

    def test_gateway_rejects_task_id_mismatch(self):
        claimed = self._claimed()
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
                    "task_id": "gw-other-task",
                },
            )

    def test_gateway_rejects_missing_op_as_invalid(self):
        claimed = self._claimed()
        with self.assertRaises(ValueError):
            relay_gateway(
                self.c,
                self.host_id,
                self.token,
                claimed["id"],
                {},
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

    def test_gateway_returns_reply_if_claim_lost_after_side_effect(self):
        claimed = self._claimed()

        def finish_job_during_request(*_args, **_kwargs):
            with self.c.tx():
                self.c.db.execute(
                    "UPDATE remote_worker_jobs SET status='completed' WHERE id=?",
                    (claimed["id"],),
                )
            return {"stored": True}

        with patch.object(
            SubprocessWorkerRuntime,
            "handle_request",
            side_effect=finish_job_during_request,
        ):
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
                    "content_text": "artifact",
                },
            )
        self.assertEqual(reply, {"stored": True})


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


class CompleteRuntimeTests(unittest.TestCase):
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
        self.c.queue_task("head", "app", "draft", 10, "rt-t1")

    def _claimed_job(self, task_id="rt-t1"):
        job = enqueue_remote_job(
            self.c,
            "human-ceo",
            host_id=self.host_id,
            task_id=task_id,
            worker_id="worker-r",
        )
        return claim_job(self.c, self.host_id, self.token, job["id"])

    def test_complete_with_remote_container_updates_runtime(self):
        claimed = self._claimed_job()
        complete_job(
            self.c,
            self.host_id,
            self.token,
            claimed["id"],
            status="completed",
            result={"ok": True},
            runtime="remote_container",
        )
        run = self.c.db.execute(
            "SELECT runtime FROM worker_runs WHERE task_id=?", ("rt-t1",)
        ).fetchone()
        self.assertEqual(run["runtime"], "remote_container")

    def test_complete_failed_with_remote_container_updates_runtime(self):
        claimed = self._claimed_job()
        complete_job(
            self.c,
            self.host_id,
            self.token,
            claimed["id"],
            status="failed",
            result={"error": "container exit 1"},
            runtime="remote_container",
        )
        run = self.c.db.execute(
            "SELECT status, runtime FROM worker_runs WHERE task_id=?", ("rt-t1",)
        ).fetchone()
        self.assertEqual(run["status"], "failed")
        self.assertEqual(run["runtime"], "remote_container")

    def test_failed_complete_releases_queue_lease_for_redispatch(self):
        claimed = self._claimed_job()
        complete_job(
            self.c,
            self.host_id,
            self.token,
            claimed["id"],
            status="failed",
            result={"error": "container unavailable"},
        )
        queued = self.c.db.execute(
            "SELECT status, lease_owner, lease_until FROM queue WHERE task_id=?",
            ("rt-t1",),
        ).fetchone()
        self.assertEqual(queued["status"], "queued")
        self.assertIsNone(queued["lease_owner"])
        self.assertIsNone(queued["lease_until"])
        self.c.dispatch_queued("rt-t1")
        redispatched = self.c.db.execute(
            "SELECT status FROM queue WHERE task_id=?", ("rt-t1",)
        ).fetchone()
        self.assertEqual(redispatched["status"], "done")

    def test_complete_rejects_invalid_runtime(self):
        claimed = self._claimed_job()
        with self.assertRaises(ValueError):
            complete_job(
                self.c,
                self.host_id,
                self.token,
                claimed["id"],
                status="completed",
                runtime="local_subprocess",
            )

    def test_complete_default_runtime_stays_remote_agent(self):
        claimed = self._claimed_job()
        complete_job(
            self.c,
            self.host_id,
            self.token,
            claimed["id"],
            status="completed",
        )
        run = self.c.db.execute(
            "SELECT runtime FROM worker_runs WHERE task_id=?", ("rt-t1",)
        ).fetchone()
        self.assertEqual(run["runtime"], "remote_agent")


class CompleteRuntimeHttpTests(unittest.TestCase):
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
        self.c.queue_task("head", "app", "draft", 10, "rt-http-t1")
        job = enqueue_remote_job(
            self.c,
            "human-ceo",
            host_id=self.host_id,
            task_id="rt-http-t1",
            worker_id="worker-r",
        )
        claimed = claim_job(self.c, self.host_id, self.token, job["id"])
        self.job_id = claimed["id"]

    def test_http_complete_passes_remote_container_runtime(self):
        done = self.client.post(
            f"/api/v1/worker-hosts/{self.host_id}/jobs/{self.job_id}/complete",
            json={
                "status": "completed",
                "result": {"ok": True},
                "runtime": "remote_container",
            },
            headers=self.host_headers,
        )
        self.assertEqual(done.status_code, 200, done.text)
        run = self.c.db.execute(
            "SELECT runtime FROM worker_runs WHERE task_id=?", ("rt-http-t1",)
        ).fetchone()
        self.assertEqual(run["runtime"], "remote_container")
