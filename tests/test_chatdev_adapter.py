"""ChatDevAdapter opt-in runtime — fail-closed; fake SDK in CI."""
from __future__ import annotations
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

from company.adapters import ChatDevAdapter, WorkOrder
from company.core import digest
from company.chatdev_pin import PINNED_COMMIT

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "chatdev" / "minimal_workflow.yaml"


def _digest() -> str:
    return digest({"workflow": FIXTURE.read_bytes().decode()})


class ChatDevAdapterTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(lambda: os.environ.pop("CHATDEV_HOME", None))
        self.addCleanup(lambda: os.environ.pop("CHATDEV_WORKFLOW", None))
        self.addCleanup(lambda: os.environ.pop("CHATDEV_SKIP_PIN_CHECK", None))
        self.addCleanup(lambda: os.environ.pop("CHATDEV_ALLOW_CONTROL_PLANE", None))
        os.environ.pop("CHATDEV_HOME", None)
        os.environ.pop("CHATDEV_WORKFLOW", None)
        os.environ.pop("CHATDEV_SKIP_PIN_CHECK", None)
        os.environ.pop("CHATDEV_ALLOW_CONTROL_PLANE", None)

    def test_fail_closed_without_home(self):
        order = WorkOrder("t1", "p1", 1, _digest(), 10, {"tools": ["none"], "task_prompt": "hi"})
        with self.assertRaises(NotImplementedError):
            ChatDevAdapter().run(order)

    def test_unapproved_tool(self):
        os.environ["CHATDEV_HOME"] = str(ROOT)  # any existing path; will fail later or on tools first
        os.environ["CHATDEV_WORKFLOW"] = str(FIXTURE)
        order = WorkOrder("t1", "p1", 1, _digest(), 10, {"tools": ["shell"], "task_prompt": "hi"})
        with self.assertRaises(PermissionError):
            ChatDevAdapter().run(order, allow_control_plane=True)

    def test_digest_mismatch(self):
        os.environ["CHATDEV_HOME"] = "/tmp/missing-chatdev-home-for-test"
        os.environ["CHATDEV_WORKFLOW"] = str(FIXTURE)
        order = WorkOrder("t1", "p1", 1, "wrong-digest", 10, {"tools": ["none"], "task_prompt": "hi"})
        with self.assertRaises(ValueError):
            ChatDevAdapter().run(order, allow_control_plane=True)

    def test_fake_sdk_normalizes(self):
        os.environ["CHATDEV_HOME"] = str(ROOT / "company")  # path exists; import patched
        os.environ["CHATDEV_WORKFLOW"] = str(FIXTURE)
        fake_result = SimpleNamespace(
            final_message=SimpleNamespace(content="done"),
            meta_info=SimpleNamespace(
                session_name="company-p1-t1",
                token_usage={"input_tokens": 2, "output_tokens": 3},
                output_dir=Path("/tmp/out"),
            ),
        )
        order = WorkOrder("t1", "p1", 1, _digest(), 10, {"tools": ["none"], "task_prompt": "Ship it"})
        with patch("company.chatdev_runtime.load_run_workflow", return_value=lambda *_a, **_kw: fake_result):
            with patch("company.chatdev_runtime.chatdev_home_ready", return_value=True):
                out = ChatDevAdapter().run(order, allow_control_plane=True)
        self.assertFalse(out["accepted"])
        self.assertEqual(out["final_message"], "done")
        self.assertEqual(out["meta_info"]["session_name"], "company-p1-t1")
        self.assertEqual(out["meta_info"]["usage"]["input_tokens"], 2)
        self.assertEqual(out["meta_info"]["usage"]["cost_cents"], 0)
        self.assertFalse(out["meta_info"]["failed"])

    def test_status_probe(self):
        from company.chatdev_runtime import status_summary
        s = status_summary()
        self.assertEqual(s["pin"], PINNED_COMMIT)
        self.assertFalse(s["configured"])
        self.assertFalse(s["pin_verified"])
        self.assertFalse(s["control_plane_allowed"])
        self.assertFalse(s["worker_live_ready"])
        self.assertIn("worker_image_chatdev", s)

    def test_worker_image_chatdev_unavailable_without_docker(self):
        from company.chatdev_runtime import worker_image_chatdev_summary
        with patch("company.chatdev_runtime.shutil.which", return_value=None):
            self.assertIsNone(worker_image_chatdev_summary())

    def test_worker_image_chatdev_inspect_failure(self):
        from company.chatdev_runtime import worker_image_chatdev_summary
        with patch("company.chatdev_runtime.shutil.which", return_value="/usr/bin/docker"):
            with patch("company.chatdev_runtime.subprocess.run") as run:
                run.return_value = SimpleNamespace(returncode=1, stdout="", stderr="missing")
                self.assertIsNone(worker_image_chatdev_summary())

    def test_worker_image_chatdev_from_inspect_labels(self):
        from company.chatdev_runtime import worker_image_chatdev_summary
        labels_json = (
            '{"org.fs_corporation.chatdev_enable":"1",'
            '"org.fs_corporation.chatdev_pin":"4fb2db0ea90375ce1059f44fe03ffbd191a7a169"}'
        )
        with patch("company.chatdev_runtime.shutil.which", return_value="/usr/bin/docker"):
            with patch("company.chatdev_runtime.subprocess.run") as run:
                run.return_value = SimpleNamespace(returncode=0, stdout=labels_json)
                summary = worker_image_chatdev_summary()
        self.assertIsNotNone(summary)
        self.assertTrue(summary["enabled"])
        self.assertEqual(summary["pin"], PINNED_COMMIT)
        self.assertEqual(summary["image"], "fs-corporation-worker:local")
        run.assert_called_once()
        cmd = run.call_args[0][0]
        self.assertEqual(cmd[0], "/usr/bin/docker")
        self.assertEqual(cmd[1:4], ["image", "inspect", "fs-corporation-worker:local"])

    def test_worker_image_chatdev_disabled_label(self):
        from company.chatdev_runtime import worker_image_chatdev_summary
        labels_json = (
            '{"org.fs_corporation.chatdev_enable":"0",'
            '"org.fs_corporation.chatdev_pin":"4fb2db0ea90375ce1059f44fe03ffbd191a7a169"}'
        )
        with patch("company.chatdev_runtime.shutil.which", return_value="/usr/bin/docker"):
            with patch("company.chatdev_runtime.subprocess.run") as run:
                run.return_value = SimpleNamespace(returncode=0, stdout=labels_json)
                summary = worker_image_chatdev_summary()
        self.assertFalse(summary["enabled"])

    def test_pin_mismatch_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / "runtime").mkdir()
            (home / "runtime" / "sdk.py").write_text("# stub\n")
            os.environ["CHATDEV_HOME"] = str(home)
            os.environ["CHATDEV_WORKFLOW"] = str(FIXTURE)
            order = WorkOrder("t1", "p1", 1, _digest(), 10, {"tools": ["none"], "task_prompt": "hi"})
            wrong_head = "0" * 40
            with patch("company.chatdev_runtime.subprocess.run") as run:
                run.return_value = SimpleNamespace(returncode=0, stdout=f"{wrong_head}\n")
                with self.assertRaises(NotImplementedError):
                    ChatDevAdapter().run(order, allow_control_plane=True)

    def test_negative_max_cost_cents(self):
        os.environ["CHATDEV_HOME"] = str(ROOT / "company")
        os.environ["CHATDEV_WORKFLOW"] = str(FIXTURE)
        order = WorkOrder("t1", "p1", 1, _digest(), -1, {"tools": ["none"], "task_prompt": "hi"})
        with self.assertRaises(ValueError):
            ChatDevAdapter().run(order, allow_control_plane=True)

    def test_control_plane_deny_when_home_ready(self):
        os.environ["CHATDEV_HOME"] = str(ROOT / "company")
        os.environ["CHATDEV_WORKFLOW"] = str(FIXTURE)
        order = WorkOrder("t1", "p1", 1, _digest(), 10, {"tools": ["none"], "task_prompt": "hi"})
        with patch("company.chatdev_runtime.chatdev_home_ready", return_value=True):
            with self.assertRaises(NotImplementedError) as ctx:
                ChatDevAdapter().run(order)
        self.assertIn("control plane", str(ctx.exception).lower())

    def test_control_plane_env_escape_hatch(self):
        os.environ["CHATDEV_HOME"] = str(ROOT / "company")
        os.environ["CHATDEV_WORKFLOW"] = str(FIXTURE)
        os.environ["CHATDEV_ALLOW_CONTROL_PLANE"] = "1"
        fake_result = SimpleNamespace(
            final_message=SimpleNamespace(content="desk"),
            meta_info=SimpleNamespace(
                session_name="company-p1-t1",
                token_usage={"input_tokens": 1, "output_tokens": 1},
                output_dir=None,
            ),
        )
        order = WorkOrder("t1", "p1", 1, _digest(), 10, {"tools": ["none"], "task_prompt": "hi"})
        with patch("company.chatdev_runtime.load_run_workflow", return_value=lambda *_a, **_kw: fake_result):
            with patch("company.chatdev_runtime.chatdev_home_ready", return_value=True):
                out = ChatDevAdapter().run(order)
        self.assertEqual(out["final_message"], "desk")

    def test_status_api(self):
        from fastapi.testclient import TestClient
        from company.core import Company
        from company.service import create_app
        from tests.test_core import install, policy
        c = Company()
        install(c, policy(c))
        c.register_identity("human-ceo", "owner", "t")
        self.addCleanup(c.close)
        r = TestClient(create_app(c)).get(
            "/api/v1/chatdev/status", headers={"Authorization": "Bearer t"}
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["pin"], PINNED_COMMIT)
        self.assertIn("worker_image_chatdev", r.json())


if __name__ == "__main__":
    unittest.main()
