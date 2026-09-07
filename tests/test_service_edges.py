"""Service edge contracts from M10-02: bind refusal and SSE cursor frames."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from company.core import Company
from company.service import create_app
from tests.test_core import install, policy


class ServiceEdgeTests(unittest.TestCase):
    def test_refuses_non_loopback_bind_without_allow_remote(self):
        proc = subprocess.run(
            [sys.executable, "-m", "company.service", "--host", "0.0.0.0", "--port", "9"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(Path(__file__).resolve().parents[1]),
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("Refusing to bind a non-loopback address without --allow-remote", proc.stderr)

    def test_events_stream_emits_cursor_frames_without_bodies(self):
        company = Company()
        self.addCleanup(company.close)
        install(company, policy(company))
        company.register_identity("human-ceo", "owner", "owner-token")
        previous = os.environ.get("FS_CORP_SSE_IDLE_SEC")
        os.environ["FS_CORP_SSE_IDLE_SEC"] = "0"
        self.addCleanup(
            lambda: (
                os.environ.__setitem__("FS_CORP_SSE_IDLE_SEC", previous)
                if previous is not None
                else os.environ.pop("FS_CORP_SSE_IDLE_SEC", None)
            )
        )
        client = TestClient(create_app(company))
        with client.stream(
            "GET",
            "/api/v1/events/stream?cursor=0",
            headers={"Authorization": "Bearer owner-token"},
        ) as response:
            self.assertEqual(response.status_code, 200)
            self.assertIn("text/event-stream", response.headers.get("content-type", ""))
            frames = [
                json.loads(line.removeprefix("data: "))
                for line in response.iter_lines()
                if line.startswith("data: ")
            ]
        self.assertTrue(frames, "expected at least one SSE data frame")
        frame = frames[0]
        self.assertEqual(set(frame), {"seq", "kind", "at"})
        self.assertIsInstance(frame["seq"], int)
        self.assertTrue(frame["kind"])


if __name__ == "__main__":
    unittest.main()
