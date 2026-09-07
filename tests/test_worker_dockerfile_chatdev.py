"""Dockerfile contract: optional ChatDev build-args (slice 3 Task 1)."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "deploy" / "fs-dev" / "Dockerfile.worker"
INSTALL_SH = ROOT / "deploy" / "fs-dev" / "install.sh"
ENV_EXAMPLE = ROOT / "deploy" / "fs-dev" / "env.example"
PIN = "4fb2db0ea90375ce1059f44fe03ffbd191a7a169"


class WorkerDockerfileChatDevTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = DOCKERFILE.read_text()

    def test_dockerfile_has_chatdev_enable_arg(self):
        self.assertIn("ARG CHATDEV_ENABLE", self.text)

    def test_dockerfile_has_pinned_chatdev_ref(self):
        self.assertIn(PIN, self.text)

    def test_dockerfile_uses_worker_entrypoint(self):
        self.assertIn("worker-entrypoint.sh", self.text)

    def test_install_sh_passes_chatdev_build_arg_when_enabled(self):
        text = INSTALL_SH.read_text()
        self.assertIn("FS_CORP_WORKER_CHATDEV", text)
        self.assertIn('CHATDEV_ENABLE=1', text)
        self.assertIn("CHATDEV_REF", text)

    def test_env_example_documents_worker_chatdev_knob(self):
        text = ENV_EXAMPLE.read_text()
        self.assertIn("FS_CORP_WORKER_CHATDEV", text)
        self.assertIn("CHATDEV_REF", text)


if __name__ == "__main__":
    unittest.main()
