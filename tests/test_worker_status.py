import os
import tempfile
import unittest
from unittest.mock import patch

from company.worker_status import status_summary


class WorkerStatusTests(unittest.TestCase):
    def test_not_ready_without_docker_or_scratch(self):
        with patch.dict(os.environ, {}, clear=True):
            summary = status_summary()
        self.assertFalse(summary["container_dispatch_ready"])
        self.assertFalse(summary["docker_available"])
        self.assertFalse(summary["scratch_configured"])

    def test_ready_when_docker_image_and_scratch_ok(self):
        with tempfile.TemporaryDirectory() as scratch:
            with patch.dict(os.environ, {
                "FS_CORP_WORKER_SCRATCH": scratch,
                "FS_CORP_WORKER_NIC_IP": "192.168.4.101",
            }, clear=False):
                with patch("company.worker_status.shutil.which", return_value="/usr/bin/docker"):
                    with patch("company.worker_status.subprocess.run") as run:
                        run.return_value.returncode = 0
                        summary = status_summary()
        self.assertTrue(summary["container_dispatch_ready"])
        self.assertEqual(summary["worker_nic_ip"], "192.168.4.101")

    def test_api_workers_status(self):
        from company.core import Company
        from company.service import create_app
        from tests.test_core import install, policy

        with tempfile.TemporaryDirectory() as scratch:
            company = Company()
            install(company, policy(company))
            company.register_identity("human-ceo", "owner", "owner-token")
            with patch.dict(os.environ, {"FS_CORP_WORKER_SCRATCH": scratch}, clear=False):
                client = __import__("fastapi.testclient", fromlist=["TestClient"]).TestClient(create_app(company))
                resp = client.get("/api/v1/workers/status", headers={"Authorization": "Bearer owner-token"})
            company.close()
        self.assertEqual(resp.status_code, 200)
        self.assertIn("container_dispatch_ready", resp.json())


if __name__ == "__main__":
    unittest.main()
