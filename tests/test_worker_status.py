import os
import tempfile
import unittest
from unittest.mock import patch

from company.worker_status import (
    default_worker_runtime,
    gateway_egress_summary,
    host_has_ipv4,
    resolve_worker_runtime,
    status_summary,
)


class WorkerStatusTests(unittest.TestCase):
    def test_not_ready_without_docker_or_scratch(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("company.worker_status._service_uid", return_value=None):
                with patch("company.worker_status.host_has_ipv4", return_value=False):
                    summary = status_summary()
        self.assertFalse(summary["container_dispatch_ready"])
        self.assertFalse(summary["docker_available"])
        self.assertFalse(summary["scratch_configured"])
        self.assertEqual(summary["default_runtime"], "subprocess")
        self.assertEqual(summary["gateway_egress"]["mode"], "default")
        self.assertFalse(summary["gateway_egress"]["egress_active"])

    def test_ready_when_docker_image_and_scratch_ok(self):
        with tempfile.TemporaryDirectory() as scratch:
            with patch.dict(os.environ, {
                "FS_CORP_WORKER_SCRATCH": scratch,
                "FS_CORP_WORKER_NIC_IP": "192.168.4.101",
            }, clear=False):
                with patch("company.worker_status.shutil.which", return_value="/usr/bin/docker"):
                    with patch("company.worker_status._service_uid", return_value=None):
                        with patch("company.worker_status.subprocess.run") as run:
                            def fake_run(cmd, **kwargs):
                                class Result:
                                    returncode = 0
                                    stdout = "2: eno2    inet 192.168.4.101/22 scope global eno2\n"
                                    stderr = ""
                                if cmd[:3] == ["ip", "-4", "-o"]:
                                    return Result()
                                return Result()
                            run.side_effect = fake_run
                            summary = status_summary()
        self.assertTrue(summary["container_dispatch_ready"])
        self.assertEqual(summary["worker_nic_ip"], "192.168.4.101")
        self.assertTrue(summary["worker_nic_present"])

    def test_host_has_ipv4_parses_ip_output(self):
        with patch("company.worker_status.subprocess.run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = "3: eno2    inet 192.168.4.101/22 brd 192.168.7.255 scope global noprefixroute eno2\n"
            self.assertTrue(host_has_ipv4("192.168.4.101"))
            self.assertFalse(host_has_ipv4("192.168.4.100"))

    def test_gateway_egress_inactive_by_default(self):
        with patch.dict(os.environ, {"FS_CORP_WORKER_NIC_IP": "192.168.4.101"}, clear=False):
            with patch("company.worker_status.host_has_ipv4", return_value=True):
                with patch("company.worker_status._service_uid", return_value=996):
                    with patch("company.worker_status._ip_rule_has_uid_table", return_value=False):
                        with patch("company.worker_status._table_default_src", return_value=None):
                            summary = gateway_egress_summary()
        self.assertEqual(summary["mode"], "default")
        self.assertFalse(summary["egress_active"])
        self.assertTrue(summary["worker_nic_present"])

    def test_gateway_egress_worker_nic_active(self):
        with patch.dict(os.environ, {
            "FS_CORP_GATEWAY_EGRESS": "worker_nic",
            "FS_CORP_WORKER_NIC_IP": "192.168.4.101",
        }, clear=False):
            with patch("company.worker_status.host_has_ipv4", return_value=True):
                with patch("company.worker_status._service_uid", return_value=996):
                    with patch("company.worker_status._ip_rule_has_uid_table", return_value=True):
                        with patch("company.worker_status._table_default_src", return_value="192.168.4.101"):
                            summary = gateway_egress_summary()
        self.assertEqual(summary["mode"], "worker_nic")
        self.assertTrue(summary["egress_active"])
        self.assertTrue(summary["egress_ready"])
        self.assertEqual(summary["egress_source_ip"], "192.168.4.101")

    def test_gateway_egress_worker_nic_not_ready(self):
        with patch.dict(os.environ, {
            "FS_CORP_GATEWAY_EGRESS": "worker_nic",
            "FS_CORP_WORKER_NIC_IP": "192.168.4.101",
        }, clear=False):
            with patch("company.worker_status.host_has_ipv4", return_value=True):
                with patch("company.worker_status._service_uid", return_value=996):
                    with patch("company.worker_status._ip_rule_has_uid_table", return_value=False):
                        with patch("company.worker_status._table_default_src", return_value=None):
                            summary = gateway_egress_summary()
        self.assertFalse(summary["egress_active"])
        self.assertFalse(summary["egress_ready"])
        self.assertIn("policy routing not installed", summary["egress_blockers"])

    def test_resolve_explicit_runtime(self):
        self.assertEqual(resolve_worker_runtime("subprocess"), "subprocess")
        self.assertEqual(resolve_worker_runtime("container"), "container")
        with self.assertRaises(ValueError):
            resolve_worker_runtime("kvm")

    def test_resolve_default_container_fails_closed_when_not_ready(self):
        with patch.dict(os.environ, {"FS_CORP_DEFAULT_WORKER_RUNTIME": "container"}, clear=False):
            with patch("company.worker_status.status_summary", return_value={
                "container_dispatch_ready": False,
                "docker_available": False,
                "image_present": False,
                "scratch_writable": False,
            }):
                with self.assertRaises(NotImplementedError):
                    resolve_worker_runtime(None)

    def test_resolve_default_container_when_ready(self):
        with patch.dict(os.environ, {"FS_CORP_DEFAULT_WORKER_RUNTIME": "container"}, clear=False):
            with patch("company.worker_status.status_summary", return_value={"container_dispatch_ready": True}):
                self.assertEqual(resolve_worker_runtime(None), "container")
                self.assertEqual(default_worker_runtime(), "container")

    def test_api_workers_status(self):
        from company.core import Company
        from company.service import create_app
        from tests.test_core import install, policy

        with tempfile.TemporaryDirectory() as scratch:
            company = Company()
            install(company, policy(company))
            company.register_identity("human-ceo", "owner", "owner-token")
            fake = {
                "container_dispatch_ready": False,
                "default_runtime": "subprocess",
                "gateway_egress": {"mode": "default", "egress_active": False, "egress_table": 101},
            }
            with patch.dict(os.environ, {"FS_CORP_WORKER_SCRATCH": scratch}, clear=False):
                with patch("company.worker_status.shutil.which", return_value=None):
                    with patch("company.worker_status.gateway_egress_summary", return_value=fake["gateway_egress"]):
                        client = __import__("fastapi.testclient", fromlist=["TestClient"]).TestClient(create_app(company))
                        resp = client.get("/api/v1/workers/status", headers={"Authorization": "Bearer owner-token"})
            company.close()
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("container_dispatch_ready", body)
        self.assertIn("default_runtime", body)
        self.assertIn("gateway_egress", body)


if __name__ == "__main__":
    unittest.main()
