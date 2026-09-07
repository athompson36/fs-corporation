"""Worker ChatDev opt-in (slice 2 Phase A)."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from company.core import Company
from company.worker import ContainerWorkerRuntime, build_worker_envelope, run_isolated_work
from tests.test_core import install, policy


class WorkerChatDevTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.c.enroll_project("human-ceo", "app", "Worker chatdev")
        self.addCleanup(self.c.close)
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        os.environ.pop("CHATDEV_HOME", None)
        os.environ.pop("CHATDEV_ALLOW_CONTROL_PLANE", None)

    def _envelope(self, task_id, *, chatdev=False, digest="mock-workflow"):
        self.c.queue_task("head", "app", "draft", 10, task_id)
        payload = {
            "actor": "head",
            "project": "app",
            "action": "draft",
            "cost": 10,
            "chatdev": chatdev,
            "task_prompt": "hi",
        }
        self.c.db.execute(
            "UPDATE queue SET payload=? WHERE task_id=?",
            (json.dumps(payload), task_id),
        )
        env = build_worker_envelope(self.c, "w1", task_id)
        if digest != "mock-workflow":
            env["workflow_digest"] = digest
        return env

    def test_default_uses_mock(self):
        env = self._envelope("t-mock")

        def request(op, **kw):
            if op == "gateway_check":
                return {"allow": True, "policy_version": self.c.policy()["version"]}
            if op == "store_artifact":
                return {"hash": "a" * 64}
            if op == "execute_mock":
                return {"status": "done"}
            raise AssertionError(op)

        out = run_isolated_work(env, Path(self.scratch.name), request)
        self.assertEqual(out["type"], "done")
        self.assertEqual(out["adapter"]["final_message"], "mock workflow complete")

    def test_chatdev_true_uses_live_when_ready(self):
        env = self._envelope("t-live", chatdev=True)
        live = {
            "final_message": "live-chatdev-output",
            "meta_info": {
                "session_name": "s",
                "usage": {"input_tokens": 0, "output_tokens": 0, "cost_cents": 0},
                "cancelled": False,
                "failed": False,
            },
            "artifact_hash": None,
            "accepted": False,
        }

        def request(op, **kw):
            if op == "gateway_check":
                return {"allow": True, "policy_version": self.c.policy()["version"]}
            if op == "store_artifact":
                content = kw.get("content") or kw.get("content_text", "").encode()
                self.assertIn(b"live-chatdev-output", content)
                return {"hash": "b" * 64}
            if op == "execute_mock":
                return {"status": "done"}
            raise AssertionError(op)

        with patch("company.worker.chatdev_home_ready", return_value=True):
            with patch("company.adapters.ChatDevAdapter.run", return_value=live):
                out = run_isolated_work(env, Path(self.scratch.name), request)
        self.assertEqual(out["type"], "done")
        self.assertEqual(out["adapter"]["final_message"], "live-chatdev-output")

    def test_chatdev_true_not_ready_errors(self):
        env = self._envelope("t-fail", chatdev=True)

        def request(op, **kw):
            if op == "gateway_check":
                return {"allow": True, "policy_version": self.c.policy()["version"]}
            raise AssertionError(f"should not reach {op}")

        with patch("company.worker.chatdev_home_ready", return_value=False):
            out = run_isolated_work(env, Path(self.scratch.name), request)
        self.assertEqual(out["type"], "error")

    def test_container_dispatch_omits_chatdev_allow_env_from_host(self):
        os.environ["CHATDEV_ALLOW_CONTROL_PLANE"] = "1"
        self.addCleanup(lambda: os.environ.pop("CHATDEV_ALLOW_CONTROL_PLANE", None))
        self.c.queue_task("head", "app", "draft", 10, "t-container-env")
        self.c.claim_lease("w1", "t-container-env")
        recorded: dict = {}

        class FakeProc:
            returncode = 0

            def communicate(self, timeout=None):
                return ("", "")

            def poll(self):
                return 0

            def kill(self):
                pass

        def fake_popen(cmd, **kwargs):
            recorded["cmd"] = cmd
            return FakeProc()

        fake_docker = Path(self.scratch.name) / "fake-docker"
        fake_docker.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        fake_docker.chmod(0o755)
        with patch("subprocess.Popen", fake_popen):
            with patch(
                "company.worker.pump_file_gateway",
                return_value={"status": "produced", "id": "t-container-env"},
            ):
                ContainerWorkerRuntime().dispatch(
                    self.c, "w1", "t-container-env", Path(self.scratch.name), docker_path=str(fake_docker))
        cmd_blob = " ".join(recorded["cmd"])
        self.assertNotIn("CHATDEV_ALLOW_CONTROL_PLANE", cmd_blob)


if __name__ == "__main__":
    unittest.main()
