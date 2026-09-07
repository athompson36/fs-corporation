"""Persisted corporate HQ floorplans and department rooms (Phase 2)."""
from __future__ import annotations

import unittest
from pathlib import Path

from company.core import Company
from tests.test_core import install, policy

CATALOG = Path(__file__).resolve().parents[1] / "config" / "departments.json"


class FloorplanTests(unittest.TestCase):
    def setUp(self):
        self.c = Company()
        install(self.c, policy(self.c))
        self.c.seed_catalog(CATALOG)
        self.addCleanup(self.c.close)

    def test_default_plan_places_one_non_overlapping_room_per_non_retired_department(self):
        plan = self.c.default_floorplan_for("human-ceo")
        departments = list(self.c.db.execute(
            "SELECT id,room_type FROM departments WHERE status!='retired'"))
        self.assertEqual(plan["name"], "Default headquarters")
        self.assertEqual(len(plan["rooms"]), len(departments))
        self.assertEqual(
            {room["department_id"] for room in plan["rooms"]},
            {department["id"] for department in departments},
        )
        occupied = set()
        for room in plan["rooms"]:
            cells = {
                (x, y)
                for x in range(room["grid_x"], room["grid_x"] + room["width"])
                for y in range(room["grid_y"], room["grid_y"] + room["height"])
            }
            self.assertTrue(occupied.isdisjoint(cells))
            occupied.update(cells)

    def test_overlap_is_rejected_without_persisting_room(self):
        plan = self.c.create_floorplan("human-ceo", "HQ")
        self.c.upsert_floorplan_room(
            "human-ceo", plan["id"], department_id="engineering",
            room_type="engineering-studio", label="Engineering",
            grid_x=0, grid_y=0, width=2, height=2, capacity=2,
        )
        with self.assertRaisesRegex(ValueError, "overlap"):
            self.c.upsert_floorplan_room(
                "human-ceo", plan["id"], department_id="art",
                room_type="design-studio", label="Design",
                grid_x=1, grid_y=1, width=1, height=1, capacity=1,
            )
        self.assertEqual(
            self.c.db.execute(
                "SELECT COUNT(*) FROM floorplan_rooms WHERE floorplan_id=?",
                (plan["id"],),
            ).fetchone()[0],
            1,
        )

    def test_unknown_room_type_is_rejected(self):
        plan = self.c.create_floorplan("human-ceo", "HQ")
        with self.assertRaisesRegex(ValueError, "room_type"):
            self.c.upsert_floorplan_room(
                "human-ceo", plan["id"], room_type="invented-room",
                label="Fake", grid_x=0, grid_y=0,
            )

    def test_requirement_gaps_report_missing_and_under_capacity_rooms(self):
        plan = self.c.create_floorplan("human-ceo", "HQ")
        self.c.upsert_floorplan_room(
            "human-ceo", plan["id"], department_id="engineering",
            room_type="engineering-studio", label="Engineering",
            grid_x=0, grid_y=0, capacity=0,
        )
        gaps = self.c.floorplan_status(plan["id"])["unmet_requirements"]
        engineering = next(gap for gap in gaps if gap["department_id"] == "engineering")
        self.assertEqual(engineering["required_room_type"], "engineering-studio")
        self.assertEqual(engineering["min_capacity"], 1)
        self.assertEqual(engineering["actual_capacity"], 0)
        self.assertTrue(any(gap["department_id"] == "art" for gap in gaps))

    def test_expansion_bound_room_cannot_be_removed(self):
        plan = self.c.create_floorplan("human-ceo", "HQ")
        self.c.db.execute(
            "INSERT INTO expansions VALUES(?,?,?,?)",
            ("exp-1", "project-1", "built", "facilities"),
        )
        room = self.c.upsert_floorplan_room(
            "human-ceo", plan["id"], department_id="facilities",
            room_type="construction-office", label="Facilities",
            grid_x=0, grid_y=0, source_expansion_id="exp-1",
        )
        with self.assertRaisesRegex(ValueError, "expansion"):
            self.c.remove_room("human-ceo", room["id"])
        self.assertIsNotNone(self.c.db.execute(
            "SELECT 1 FROM floorplan_rooms WHERE id=?", (room["id"],)).fetchone())

    def test_create_move_remove_emit_events(self):
        plan = self.c.create_floorplan("human-ceo", "HQ")
        room = self.c.upsert_floorplan_room(
            "human-ceo", plan["id"], department_id="executive",
            room_type="boardroom", label="Boardroom", grid_x=0, grid_y=0,
        )
        self.c.move_room("human-ceo", room["id"], 2, 2)
        self.c.remove_room("human-ceo", room["id"])
        kinds = [row[0] for row in self.c.db.execute(
            "SELECT kind FROM events WHERE kind LIKE 'floorplan.%' ORDER BY seq")]
        self.assertEqual(kinds, [
            "floorplan.created", "floorplan.room_upserted",
            "floorplan.room_moved", "floorplan.room_removed",
        ])

    def test_headquarters_uses_persisted_floorplan_rooms_and_keeps_expansions(self):
        plan = self.c.create_floorplan("human-ceo", "HQ")
        room = self.c.upsert_floorplan_room(
            "human-ceo", plan["id"], department_id="executive",
            room_type="boardroom", label="Boardroom", grid_x=0, grid_y=0,
        )
        hq = self.c.headquarters()
        self.assertEqual(hq["source"], "persisted_events")
        self.assertEqual(hq["floorplans"][0]["id"], plan["id"])
        self.assertEqual(hq["rooms"][0]["id"], room["id"])
        self.assertEqual(hq["rooms"][0]["department_name"], "Executive")
        self.assertIn("seat", hq["rooms"][0])
        self.assertEqual(hq["expansions"], [])
        self.assertIn("occupancy_note", hq)
        detail = self.c.room_detail(room["id"])
        self.assertEqual(detail["room"]["room_type"], "boardroom")
        self.assertEqual(detail["departments"][0]["id"], "executive")

    def test_non_ceo_cannot_mutate_floorplans(self):
        with self.assertRaises(PermissionError):
            self.c.create_floorplan("stranger", "HQ")


class FloorplanApiTests(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from company.service import create_app

        self.c = Company()
        install(self.c, policy(self.c))
        self.c.seed_catalog(CATALOG)
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

    def test_floorplan_crud_routes(self):
        created = self.command("POST", "/api/v1/floorplans", {"name": "HQ"}, "fp-1")
        self.assertEqual(created.status_code, 200, created.text)
        plan = created.json()["result"]
        room_response = self.command(
            "POST", f"/api/v1/floorplans/{plan['id']}/rooms",
            {"department_id": "executive", "room_type": "boardroom",
             "label": "Boardroom", "grid_x": 0, "grid_y": 0},
            "room-1",
        )
        self.assertEqual(room_response.status_code, 200, room_response.text)
        room = room_response.json()["result"]
        moved = self.command(
            "PATCH", f"/api/v1/floorplans/{plan['id']}/rooms/{room['id']}",
            {"grid_x": 2, "grid_y": 1}, "room-move-1",
        )
        self.assertEqual(moved.status_code, 200, moved.text)
        self.assertEqual(moved.json()["result"]["grid_x"], 2)
        detail = self.client.get(f"/api/v1/floorplans/{plan['id']}", headers=self.headers)
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertEqual(detail.json()["rooms"][0]["id"], room["id"])
        listed = self.client.get("/api/v1/floorplans", headers=self.headers)
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(listed.json()["floorplans"][0]["id"], plan["id"])
        deleted = self.command(
            "DELETE", f"/api/v1/floorplans/{plan['id']}/rooms/{room['id']}",
            {}, "room-delete-1",
        )
        self.assertEqual(deleted.status_code, 200, deleted.text)

    def test_default_floorplan_route(self):
        response = self.command(
            "POST", "/api/v1/floorplans/default", {}, "fp-default-1")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertGreater(len(response.json()["result"]["rooms"]), 0)

    def test_desk_contains_requirement_warnings(self):
        response = self.client.get("/desk")
        self.assertEqual(response.status_code, 200)
        self.assertIn("unmet-requirements", response.text)


if __name__ == "__main__":
    unittest.main()
