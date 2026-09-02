from datetime import timedelta
import json
import tempfile
from pathlib import Path
import unittest
from fastapi.testclient import TestClient
from company.core import Company, now
from company.service import create_app
from tests.test_core import install, policy, qc_pass


def owner_client():
    c = Company()
    install(c, policy(c))
    c.register_identity("human-ceo", "owner", "owner-token")
    c.register_identity("consultant", "service", "c-token", ["consultant.read", "consultant.propose"])
    app = create_app(c)
    client = TestClient(app)
    return c, client


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.c, self.client = owner_client()
        self.addCleanup(self.c.close)

    def test_unauthenticated_and_body_spoof(self):
        self.assertEqual(self.client.get("/api/v1/company").status_code, 401)
        r = self.client.post("/api/v1/company/pause", json={"payload": {"actor": "human-ceo"}},
                             headers={"Authorization": "Bearer c-token"})
        self.assertEqual(r.status_code, 403)

    def test_pause_idempotency_and_events(self):
        headers = {"Authorization": "Bearer owner-token", "Idempotency-Key": "pause-1"}
        a = self.client.post("/api/v1/company/pause", json={"payload": {}}, headers=headers)
        b = self.client.post("/api/v1/company/pause", json={"payload": {}}, headers=headers)
        self.assertEqual(a.status_code, 200)
        self.assertEqual(a.json(), b.json())
        changed = self.client.post("/api/v1/company/pause", json={"payload": {"extra": True}},
                                   headers=headers)
        self.assertEqual(changed.status_code, 409)
        events = self.client.get("/api/v1/events", headers={"Authorization": "Bearer owner-token"})
        self.assertEqual(events.status_code, 200)
        self.assertTrue(events.json()["items"])

    def test_consultant_cannot_decide(self):
        from company.consultant import ConsultantDesk
        from tests.test_m1 import PROPOSAL
        pid = ConsultantDesk(self.c).submit("consultant", PROPOSAL)
        r = self.client.post(f"/api/v1/consultant-proposals/{pid}/decision",
                             json={"payload": {"decision": "approved", "reason": "nope"}},
                             headers={"Authorization": "Bearer c-token"})
        self.assertEqual(r.status_code, 403)

    def test_hardware_project_skills_and_owner_cannot_study_as_employee(self):
        headers = {"Authorization": "Bearer owner-token", "Idempotency-Key": "hw-enroll"}
        enrolled = self.client.post("/api/v1/projects", json={
            "payload": {"id": "badge", "brief": "ESP32 firmware", "platform": "esp32"}
        }, headers=headers)
        self.assertEqual(enrolled.status_code, 200)
        skills = self.client.get("/api/v1/projects/badge/skills",
                                 headers={"Authorization": "Bearer owner-token"})
        self.assertEqual(skills.status_code, 200)
        body = skills.json()
        self.assertEqual(body["capabilities"]["platform"], "esp32")
        self.assertTrue(body["gaps"])
        assignment = body["learning"][0]
        study = self.client.post(
            f"/api/v1/learning/{assignment['id']}/study",
            json={"payload": {
                "source": "https://docs.espressif.com/projects/esp-idf/en/latest/",
                "title": "ESP-IDF",
                "published_at": now().isoformat(),
                "observed_at": now().isoformat(),
                "summary": "build steps",
            }},
            headers={"Authorization": "Bearer owner-token", "Idempotency-Key": "hw-study"})
        self.assertEqual(study.status_code, 403)

    def test_owner_cannot_replace_qc_and_can_read_hr_roster(self):
        t = self.c.execute_mock(actor="head", project="app", action="draft", cost=10, task_id="api-qc")
        inspect = self.client.post(
            "/api/v1/tasks/api-qc/quality-inspect",
            json={"payload": {"artifact_hash": t["artifact_hash"], "verdict": "pass"}},
            headers={"Authorization": "Bearer owner-token", "Idempotency-Key": "qc-1"})
        self.assertEqual(inspect.status_code, 403)
        roster = self.client.get("/api/v1/hr/development", headers={"Authorization": "Bearer owner-token"})
        self.assertEqual(roster.status_code, 200)
        self.assertIn("assignments", roster.json())

    def test_hire_employee_via_api(self):
        hired = self.client.post("/api/v1/employees", json={"payload": {
            "id": "dev-ada", "position_id": "engineering:Developer", "display_name": "Ada",
            "attributes": {"seniority": "mid"}, "background": "Configurable firmware background."
        }}, headers={"Authorization": "Bearer owner-token", "Idempotency-Key": "hire-1"})
        self.assertEqual(hired.status_code, 200)
        self.assertTrue(hired.json()["result"]["training"])
        file = self.client.get("/api/v1/employees/dev-ada/training",
                               headers={"Authorization": "Bearer owner-token"})
        self.assertEqual(file.status_code, 200)
        self.assertIn("due", file.json())

    def test_desk_html_reduced_motion(self):
        page = self.client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertIn("prefers-reduced-motion", page.text)
        self.assertIn("CEO desk", page.text)
        self.assertIn('data-theme="cosmic-glass"', page.text)
        self.assertIn("--midnight:", page.text)
        self.assertIn('id="sidebar"', page.text)
        self.assertIn('id="metric-projects"', page.text)
        self.assertIn('id="iso"', page.text)
        self.assertIn("isometric projection of provisioned rooms", page.text)
        self.assertIn("iso-rise", page.text)
        self.assertIn("data-room-id", page.text)
        hq = self.client.get("/api/v1/headquarters", headers={"Authorization": "Bearer owner-token"})
        self.assertEqual(hq.status_code, 200)
        self.assertIn("occupancy_note", hq.json())
        self.assertEqual(hq.json()["source"], "persisted_events")

    def test_room_detail_api_and_desk_nav(self):
        missing = self.client.get("/api/v1/headquarters/rooms/no-such-room",
                                  headers={"Authorization": "Bearer owner-token"})
        self.assertEqual(missing.status_code, 422)
        t = self.c.execute_mock(actor="head", project="app", action="draft", cost=10, task_id="api-room")
        qc_pass(self.c, t)
        self.c.accept_project("human-ceo", "api-room", t["artifact_hash"])
        self.c.approve_expansion("human-ceo", "expansion-app")
        self.c.build_mock("builder", "expansion-app")
        detail = self.client.get("/api/v1/headquarters/rooms/expansion-app",
                                 headers={"Authorization": "Bearer owner-token"})
        self.assertEqual(detail.status_code, 200)
        body = detail.json()
        self.assertEqual(body["room"]["id"], "expansion-app")
        self.assertEqual([task["id"] for task in body["tasks"]], ["api-room"])
        self.assertNotIn("occupancy", body)
        page = self.client.get("/")
        self.assertIn('id="room-detail"', page.text)
        self.assertIn('href="#projects"', page.text)
        self.assertIn('href="#departments"', page.text)
        self.assertIn('href="#budget"', page.text)
        self.assertIn('href="#activity"', page.text)
        self.assertIn('href="#intelligence"', page.text)
        self.assertIn("/api/v1/headquarters/rooms/", page.text)


if __name__ == "__main__":
    unittest.main()
