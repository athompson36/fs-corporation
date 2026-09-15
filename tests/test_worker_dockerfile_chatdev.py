"""Dockerfile contract: optional ChatDev build-args (slice 3 Task 1)."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "deploy" / "fs-dev" / "Dockerfile.worker"
ENTRYPOINT = ROOT / "deploy" / "fs-dev" / "worker-entrypoint.sh"
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

    def test_dockerfile_opt_in_runs_uv_sync(self):
        self.assertIn("uv sync", self.text)
        self.assertIn("org.fs_corporation.chatdev_deps", self.text)

    def test_dockerfile_opt_in_installs_native_build_deps(self):
        # pycairo (ChatDev → xhtml2pdf → svglib) needs gcc + cairo headers on slim.
        self.assertIn("build-essential", self.text)
        self.assertIn("libcairo2-dev", self.text)
        self.assertIn("libcairo2", self.text)

    def test_dockerfile_default_enable_is_zero(self):
        self.assertIn("ARG CHATDEV_ENABLE=0", self.text)

    def test_entrypoint_prepends_chatdev_venv_to_pythonpath(self):
        text = ENTRYPOINT.read_text()
        self.assertIn("/opt/chatdev/.venv", text)
        self.assertIn("PYTHONPATH", text)
        self.assertIn("site-packages", text)
        self.assertIn("exec python -m company.worker", text)


if __name__ == "__main__":
    unittest.main()
