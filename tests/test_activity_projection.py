"""Persisted live-activity projection for Corporate HQ Phase 4."""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import unittest

from fastapi.testclient import TestClient

from company.core import Company
from company.service import create_app
from tests.test_core import install, policy


CATALOG = Path(__file__).resolve().parents[1] / "config" / "departments.json"


class ActivityProjectionTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.c.seed_catalog(CATALOG)
        self.c.enroll_project("human-ceo", "app", "Activity projection")
        self.addCleanup(self.c.close)

    def test_reducer_is_idempotent_when_event_is_replayed(self):
        self.c.create_owner_request(
            "human-ceo", "engineering", "feedback", "Choose scope", "Need owner context",
            project_id="app",
        )
        event = self.c.db.execute(
            "SELECT * FROM events WHERE kind='owner.request_created' ORDER BY seq DESC LIMIT 1"
        ).fetchone()

        self.c.apply_activity_from_event(event)
        self.c.apply_activity_from_event(event)

        self.assertEqual(
            1,
            self.c.db.execute(
                "SELECT COUNT(*) FROM activity_sessions WHERE started_event_id=?",
                (event["seq"],),
            ).fetchone()[0],
        )

    def test_activity_session_cannot_exist_without_event(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.c.db.execute(
                """INSERT INTO activity_sessions(
                       id,kind,project_id,department_id,room_id,participants,status,
                       started_event_id,ended_event_id,started_at,ended_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    "orphan", "work", "app", "engineering", None, "[]", "open",
                    999999, None, "2026-09-07T00:00:00+00:00", None,
                ),
            )

    def test_blocked_dispatch_creates_context_request(self):
        dispatch = self.c.dispatch_project_brief(
            "human-ceo", "app", "Build the feature",
            {"engineering": 100}, "Projection tests pass",
        )[0]
        self.assertEqual("blocked_vacant_head", dispatch["status"])

        sessions = self.c.list_activity()["items"]

        self.assertEqual(1, len(sessions))
        self.assertEqual("context_request", sessions[0]["kind"])
        self.assertEqual("engineering", sessions[0]["department_id"])
        self.assertEqual("app", sessions[0]["project_id"])

    def test_close_stale_sessions_closes_terminal_queue_work(self):
        self.c.queue_task("head", "app", "draft", 10, "activity-task")
        self.c.claim_lease("worker-1", "activity-task")
        session = self.c.list_activity()["items"][0]
        self.assertEqual("work", session["kind"])
        self.c.db.execute(
            "UPDATE queue SET status='done' WHERE task_id='activity-task'")

        closed = self.c.close_stale_sessions()

        self.assertEqual(1, closed)
        row = self.c.db.execute(
            "SELECT * FROM activity_sessions WHERE id=?", (session["id"],)
        ).fetchone()
        self.assertEqual("closed", row["status"])
        self.assertIsNotNone(row["ended_at"])


class ActivityProjectionApiTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.c.seed_catalog(CATALOG)
        self.c.enroll_project("human-ceo", "app", "Activity API")
        self.c.default_floorplan_for("human-ceo")
        self.c.register_identity(
            "activity-reader", "service", "activity-token",
            ["company.read", "audit.read"],
        )
        self.client = TestClient(create_app(self.c))
        self.headers = {"Authorization": "Bearer activity-token"}
        self.addCleanup(self.c.close)

    def test_list_activity_api_returns_open_sessions(self):
        self.c.create_owner_request(
            "human-ceo", "engineering", "feedback", "Need input", "Choose direction",
            project_id="app",
        )

        response = self.client.get("/api/v1/activity", headers=self.headers)

        self.assertEqual(200, response.status_code, response.text)
        session = response.json()["items"][0]
        self.assertEqual("context_request", session["kind"])
        self.assertEqual("engineering", session["department_id"])
        self.assertIsInstance(session["participants"], list)
        self.assertTrue(session["room_id"])

    def test_sse_frame_includes_projected_room_when_known(self):
        cursor = self.c.events_page(0, 200)["next_cursor"]
        self.c.create_owner_request(
            "human-ceo", "engineering", "feedback", "Need input", "Choose direction",
            project_id="app",
        )
        import os
        previous = os.environ.get("FS_CORP_SSE_IDLE_SEC")
        os.environ["FS_CORP_SSE_IDLE_SEC"] = "0"
        self.addCleanup(
            lambda: (
                os.environ.__setitem__("FS_CORP_SSE_IDLE_SEC", previous)
                if previous is not None
                else os.environ.pop("FS_CORP_SSE_IDLE_SEC", None)
            )
        )

        with self.client.stream(
            "GET", f"/api/v1/events/stream?cursor={cursor}", headers=self.headers,
        ) as response:
            frames = [
                json.loads(line.removeprefix("data: "))
                for line in response.iter_lines()
                if line.startswith("data: ")
            ]

        frame = next(item for item in frames if item["kind"] == "owner.request_created")
        self.assertEqual("engineering", self.c.list_activity()["items"][0]["department_id"])
        self.assertEqual(self.c.list_activity()["items"][0]["room_id"], frame["room_id"])

    def test_desk_wires_event_stream_activity_polling_and_badges(self):
        response = self.client.get("/desk")
        self.assertEqual(200, response.status_code)
        self.assertIn("setInterval(loadActivity, 10000)", response.text)
        self.assertIn("activity-badge", response.text)
        self.assertIn("prefers-reduced-motion", response.text)


if __name__ == "__main__":
    unittest.main()
