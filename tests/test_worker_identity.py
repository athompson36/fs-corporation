"""Worker sprites and editable identity (Corporate HQ Phase 3)."""
from __future__ import annotations

import unittest
from pathlib import Path

from company.core import Company
from company.service import create_app
from tests.test_core import install, policy


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "config" / "departments.json"
SPRITES = ROOT / "config" / "sprite-sets.json"


class WorkerIdentityTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.c.seed_catalog(CATALOG)
        self.c.hire_employee(
            "human-ceo", "ada", "engineering:Developer", "Ada",
            {"curiosity": 9}, "Distributed systems engineer.",
        )
        self.addCleanup(self.c.close)

    def test_sprite_catalog_is_seeded_and_values_are_validated(self):
        self.c.seed_sprite_sets(SPRITES)
        sets = {
            row["id"]: row
            for row in self.c.db.execute("SELECT * FROM sprite_sets ORDER BY id")
        }
        self.assertGreaterEqual(len(sets), 2)
        self.assertIn("default", sets)
        sprite = self.c.set_worker_sprite(
            "people:HR Director", "ada", "default",
            body="round", palette="aurora", accessories={"eyewear": "glasses"},
        )
        self.assertEqual(sprite["accessories"], {"eyewear": "glasses"})
        with self.assertRaisesRegex(ValueError, "palette"):
            self.c.set_worker_sprite(
                "human-ceo", "ada", "default", palette="invented",
            )
        with self.assertRaisesRegex(ValueError, "accessor"):
            self.c.set_worker_sprite(
                "human-ceo", "ada", "default",
                accessories={"eyewear": "crown"},
            )

    def test_profile_updates_require_hr_or_ceo_and_decode_json(self):
        with self.assertRaises(PermissionError):
            self.c.update_worker_profile("stranger", "ada", headline="CTO")
        profile = self.c.update_worker_profile(
            "human-ceo", "ada", headline="Systems builder",
            viewpoint="Prefer evidence over assumptions.",
            strengths=["architecture", "review"], growth_focus="mentoring",
            background="Platform and governance specialist.",
            attributes={"curiosity": 10, "discipline": 9},
        )
        self.assertEqual(profile["strengths"], ["architecture", "review"])
        self.assertEqual(profile["attributes"]["discipline"], 9)
        with self.assertRaisesRegex(ValueError, "strengths"):
            self.c.update_worker_profile(
                "human-ceo", "ada", strengths="architecture",
            )

    def test_worker_card_joins_skills_assignments_and_sprite(self):
        self.c.db.execute(
            "INSERT INTO skills VALUES(?,?,?,?)",
            ("systems", "Systems design", "general", "engineering"),
        )
        self.c.db.execute(
            "INSERT INTO acquired_skills VALUES(?,?,?,?)",
            ("systems", "ada", "source-hash", "2026-09-07T00:00:00+00:00"),
        )
        assignment = self.c.assign_position(
            "human-ceo", "engineering:Developer", "ada",
        )
        self.c.update_worker_profile(
            "human-ceo", "ada", viewpoint="Make state explicit.",
            strengths=["systems"],
        )
        self.c.set_worker_sprite(
            "human-ceo", "ada", "default", body="round", palette="aurora",
        )
        card = self.c.worker_card("ada")
        self.assertEqual(card["identity"]["display_name"], "Ada")
        self.assertEqual(card["strengths"], ["systems"])
        self.assertEqual(card["viewpoint"], "Make state explicit.")
        self.assertEqual(card["skills"][0]["id"], "systems")
        self.assertEqual(card["position_assignments"][0]["id"], assignment["id"])
        self.assertEqual(card["sprite"]["sprite_set"], "default")

    def test_missing_sprite_is_honest_null_and_unknown_worker_is_not_invented(self):
        card = self.c.worker_card("ada")
        self.assertIsNone(card["sprite"])
        self.assertEqual(card["sprite_placeholder"]["kind"], "neutral")
        with self.assertRaisesRegex(ValueError, "Employee not found"):
            self.c.worker_card("invented-worker")

    def test_headquarters_rooms_expose_staff_sprite_or_null(self):
        plan = self.c.create_floorplan("human-ceo", "HQ")
        room = self.c.upsert_floorplan_room(
            "human-ceo", plan["id"], department_id="engineering",
            room_type="engineering-studio", label="Engineering",
            grid_x=0, grid_y=0,
        )
        rendered = next(
            item for item in self.c.headquarters()["rooms"] if item["id"] == room["id"]
        )
        self.assertEqual(rendered["workers"][0]["employee_id"], "ada")
        self.assertIsNone(rendered["workers"][0]["sprite"])


class WorkerIdentityApiTests(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient

        self.c = Company()
        install(self.c, policy(self.c))
        self.c.seed_catalog(CATALOG)
        self.c.hire_employee(
            "human-ceo", "ada", "engineering:Developer", "Ada",
            {}, "Engineer.",
        )
        self.c.register_identity("human-ceo", "owner", "owner-token")
        self.client = TestClient(create_app(self.c))
        self.headers = {"Authorization": "Bearer owner-token"}
        self.addCleanup(self.c.close)

    def command(self, method, path, payload, key):
        return self.client.request(
            method, path,
            headers={**self.headers, "Idempotency-Key": key},
            json={"payload": payload},
        )

    def test_worker_card_and_mutation_routes(self):
        profile = self.command(
            "PATCH", "/api/v1/workers/ada/profile",
            {"headline": "Systems builder", "strengths": ["architecture"]},
            "worker-profile-1",
        )
        self.assertEqual(profile.status_code, 200, profile.text)
        sprite = self.command(
            "POST", "/api/v1/workers/ada/sprite",
            {"sprite_set": "default", "body": "round", "palette": "aurora"},
            "worker-sprite-1",
        )
        self.assertEqual(sprite.status_code, 200, sprite.text)
        card = self.client.get(
            "/api/v1/workers/ada/card", headers=self.headers,
        )
        self.assertEqual(card.status_code, 200, card.text)
        self.assertEqual(card.json()["identity"]["headline"], "Systems builder")
        self.assertEqual(card.json()["sprite"]["palette"], "aurora")

    def test_worker_routes_require_authentication(self):
        self.assertEqual(
            self.client.get("/api/v1/workers/ada/card").status_code, 401,
        )

    def test_desk_and_companion_wire_worker_cards(self):
        desk = self.client.get("/desk").text
        self.assertIn("data-worker-id", desk)
        self.assertIn("openWorkerCard", desk)
        client = (ROOT / "companion" / "src" / "api" / "client.ts").read_text()
        self.assertIn("workerCard(", client)
        self.assertIn("/card`", client)
        self.assertIn("setWorkerSprite(", client)
        self.assertIn("updateWorkerProfile(", client)


if __name__ == "__main__":
    unittest.main()
