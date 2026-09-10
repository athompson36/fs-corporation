import re
import unittest
from pathlib import Path
from unittest.mock import patch
from company import __version__
from company.core import Company, now
from company.service import create_app
from tests.test_api import owner_client
from tests.test_core import install, policy
from tests.test_m1 import PROPOSAL
from company.consultant import ConsultantDesk


class CompanionApiTests(unittest.TestCase):
    def setUp(self):
        self.c, self.client = owner_client()
        self.addCleanup(self.c.close)

    def test_dashboard_projects_and_decisions(self):
        self.c.enroll_project("human-ceo", "mobile-app", "Mobile companion pilot")
        pid = self.c.propose_policy("head", policy(self.c), "mobile test")
        headers = {"Authorization": "Bearer owner-token"}
        dash = self.client.get("/api/v1/dashboard", headers=headers)
        self.assertEqual(dash.status_code, 200)
        body = dash.json()
        self.assertIn("company", body)
        self.assertEqual(body["company"]["paused"], False)
        self.assertTrue(any(p["id"] == "mobile-app" for p in body["projects"]))
        self.assertTrue(any(d["kind"] == "policy" for d in body["pending_decisions"]))
        projects = self.client.get("/api/v1/projects", headers=headers)
        self.assertEqual(projects.status_code, 200)
        self.assertEqual(projects.json()["projects"][0]["id"], "mobile-app")
        detail = self.client.get("/api/v1/projects/mobile-app", headers=headers)
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["brief"], "Mobile companion pilot")
        inbox = self.client.get("/api/v1/decisions/inbox", headers=headers)
        self.assertEqual(inbox.status_code, 200)
        self.assertTrue(inbox.json()["items"])
        self.c.approve_policy("human-ceo", pid)

    def test_dispatch_brief_creates_work_orders(self):
        self.c.seed_catalog(Path(__file__).resolve().parents[1] / "config" / "departments.json")
        self.c.enroll_project("human-ceo", "dash", "Dashboard rollout")
        activated = self.client.post(
            "/api/v1/projects/dash/departments/product/activate",
            json={"payload": {}},
            headers={
                "Authorization": "Bearer owner-token",
                "Idempotency-Key": "activate-product",
            },
        )
        self.assertEqual(activated.status_code, 200, activated.text)
        headers = {"Authorization": "Bearer owner-token", "Idempotency-Key": "dispatch-1"}
        r = self.client.post("/api/v1/projects/dash/dispatch-brief", json={
            "payload": {
                "brief": "Ship CEO mobile stats",
                "department_budgets": {"engineering": 300, "product": 200},
                "acceptance_criteria": "Dashboard API documented",
            }
        }, headers=headers)
        self.assertEqual(r.status_code, 200)
        dispatches = r.json()["result"]["dispatches"]
        self.assertEqual(len(dispatches), 2)
        detail = self.client.get("/api/v1/projects/dash", headers={"Authorization": "Bearer owner-token"})
        self.assertEqual(set(detail.json()["departments"]), {"engineering", "product"})
        events = self.c.db.execute("SELECT kind FROM events WHERE kind='project.dispatched'").fetchall()
        self.assertEqual(len(events), 2)

    def test_companion_dispatch_client_sends_department_budgets(self):
        client_source = (
            Path(__file__).resolve().parents[1] / "companion" / "src" / "api" / "client.ts"
        ).read_text()
        self.assertIn("department_budgets: departmentBudgets", client_source)
        self.assertNotIn("brief, departments, acceptance_criteria, budget_cents", client_source)

    def test_companion_wires_dispatch_recommend(self):
        root = Path(__file__).resolve().parents[1] / "companion" / "src"
        client = (root / "api" / "client.ts").read_text()
        app = (root / "App.tsx").read_text()
        self.assertIn("/dispatch-options", client)
        self.assertIn("/dispatch-recommend", client)
        self.assertIn("dispatchRecommend", client)
        self.assertIn("Recommend for this project", app)
        self.assertIn("dispatch-brief-template", app)
        self.assertIn("Valid values", app)

    def test_companion_wires_company_settings(self):
        root = Path(__file__).resolve().parents[1] / "companion" / "src"
        client = (root / "api" / "client.ts").read_text()
        app = (root / "App.tsx").read_text()
        self.assertIn("/api/v1/settings", client)
        self.assertIn("/api/v1/settings/secrets-status", client)
        self.assertIn("patchCompanySettings", client)
        self.assertIn("Runtime", app)
        self.assertIn("secrets-status", app.lower() or "Secrets")
        self.assertIn("Takes effect after API restart", app)
        self.assertIn("settingDraftDiffers", app)
        self.assertIn("normalizeSettingDraft", app)

    def test_companion_wires_feed_lifecycle(self):
        root = Path(__file__).resolve().parents[1] / "companion" / "src"
        client = (root / "api" / "client.ts").read_text()
        app = (root / "App.tsx").read_text()
        self.assertIn("pauseFeed", client)
        self.assertIn("revokeFeed", client)
        self.assertIn("approveFeed", client)
        self.assertIn("pollFeed", client)
        self.assertIn("modelProfiles", client)
        self.assertIn("<h2>Feeds</h2>", app)
        self.assertIn("<h2>Models</h2>", app)
        self.assertIn("feed-approve-id", app)
        self.assertIn("Watchlist templates stay non-live", app)

    def test_companion_wires_finance(self):
        root = Path(__file__).resolve().parents[1] / "companion" / "src"
        client = (root / "api" / "client.ts").read_text()
        app = (root / "App.tsx").read_text()
        panel = (root / "FinancePanel.tsx").read_text()
        money = (root / "financeMoney.ts").read_text()
        self.assertIn("/api/v1/finance/summary", client)
        self.assertIn("financeBilledCosts", client)
        self.assertIn("financeInvoice", client)
        self.assertIn("createFinanceInvoice", client)
        self.assertIn("postFinanceAdjustment", client)
        self.assertIn("closeFinanceBudgetPeriod", client)
        self.assertIn('["money", "Money"]', app)
        self.assertIn("tab === \"finance\"", app)
        self.assertIn("FinancePanel", app)
        self.assertIn("export function formatUsd", money)
        self.assertIn("Overview", panel)
        self.assertIn("Invoices", panel)
        self.assertIn("Adjustments", panel)
        self.assertIn("Periods", panel)
        self.assertIn("financeBilledCosts", panel)
        self.assertIn("remaining_creditable", panel)
        self.assertIn("confirm(", panel)
        self.assertIn('className="segmented"', panel)
        self.assertIn('role="tablist"', panel)
        self.assertIn('role="tab"', panel)
        self.assertIn("aria-selected={subTab === t}", panel)
        self.assertIn('className={subTab === t ? "active" : ""}', panel)
        self.assertIn("hasToken: boolean", panel)
        self.assertIn("if (!hasToken) return", panel)
        self.assertIn("if (isCancelled()) return", panel)
        self.assertNotIn("scopes: string[]", panel)
        self.assertNotIn("scopes={scopes || []}", app)
        self.assertNotIn("adj-billed", app)

    def test_companion_wires_worker_hosts(self):
        root = Path(__file__).resolve().parents[1] / "companion" / "src"
        client = (root / "api" / "client.ts").read_text()
        app = (root / "App.tsx").read_text()
        panel = (root / "WorkersPanel.tsx").read_text()
        self.assertIn("workerHosts", client)
        self.assertIn("createWorkerHost", client)
        self.assertIn("enableWorkerHost", client)
        self.assertIn("disableWorkerHost", client)
        self.assertIn("deleteWorkerHost", client)
        self.assertIn('["workers", "Workers"]', app)
        self.assertIn("tab === \"workers\"", app)
        self.assertIn("WorkersPanel", app)
        self.assertIn("shown once", panel)
        self.assertIn("confirm(", panel)
        self.assertIn("workerHosts", panel)
        self.assertIn('runAction("worker-host-token-copy"', panel)
        self.assertIn("try {", panel)
        self.assertIn("navigator.clipboard.writeText", panel)
        self.assertIn("document.createRange()", panel)
        self.assertIn('status("worker-host-token-copy")', panel)

    def test_companion_replaces_window_prompt_ops_forms(self):
        app = (
            Path(__file__).resolve().parents[1] / "companion" / "src" / "App.tsx"
        ).read_text()
        self.assertNotIn("window.prompt", app)
        self.assertIn('id="enroll-project-id"', app)
        self.assertIn('id="escalate-department"', app)
        self.assertIn("owner-response-", app)

    def test_desk_surfaces_org_head_inbox_assignment_and_budget_map(self):
        desk_source = (
            Path(__file__).resolve().parents[1] / "company" / "service.py"
        ).read_text()
        self.assertIn('id="org-list"', desk_source)
        self.assertIn("'/api/v1/org'", desk_source)
        self.assertIn("seat.principal_id || 'vacant'", desk_source)
        self.assertIn('id="head-inbox-list"', desk_source)
        self.assertIn("'/api/v1/inbox/head'", desk_source)
        self.assertIn("department_budgets: departmentBudgets", desk_source)
        self.assertIn("'/api/v1/dispatches/' + encodeURIComponent(dispatch.id) + '/assign'", desk_source)

    def test_companion_wires_org_handoff_and_activation_clients(self):
        root = Path(__file__).resolve().parents[1] / "companion" / "src"
        client_source = (root / "api" / "client.ts").read_text()
        app_source = (root / "App.tsx").read_text()
        self.assertIn('"/api/v1/org"', client_source)
        self.assertIn("appointHead(", client_source)
        self.assertIn('"/api/v1/org/heads"', client_source)
        self.assertIn("vacateHead(", client_source)
        self.assertIn("assignPosition(", client_source)
        self.assertIn('"/api/v1/org/assignments"', client_source)
        self.assertIn("releaseAssignment(", client_source)
        self.assertIn('"/api/v1/inbox/head"', client_source)
        self.assertIn("/dispatches/${dispatchId}/assign", client_source)
        self.assertIn("/departments/${departmentId}/activate", client_source)
        self.assertIn('"organization"', app_source)
        self.assertIn('htmlFor="appoint-head-department"', app_source)
        self.assertIn('htmlFor="vacate-head-department"', app_source)
        self.assertIn('htmlFor="assign-position-id"', app_source)
        self.assertIn('htmlFor="release-assignment-id"', app_source)
        self.assertIn("Department budget (¢)", app_source)
        self.assertNotIn("[s.trim(), 500]", app_source)

    def test_desk_surfaces_org_appointment_and_assignment_forms(self):
        desk_source = (
            Path(__file__).resolve().parents[1] / "company" / "service.py"
        ).read_text()
        self.assertIn('id="appoint-head-form"', desk_source)
        self.assertIn('id="vacate-head-form"', desk_source)
        self.assertIn('id="assign-position-form"', desk_source)
        self.assertIn('id="release-assignment-form"', desk_source)
        self.assertIn("'/api/v1/org/heads'", desk_source)
        self.assertIn("'/api/v1/org/assignments'", desk_source)

    def test_desk_and_companion_wire_hq_phase_surfaces(self):
        desk_source = (
            Path(__file__).resolve().parents[1] / "company" / "service.py"
        ).read_text()
        root = Path(__file__).resolve().parents[1] / "companion" / "src"
        client_source = (root / "api" / "client.ts").read_text()
        app_source = (root / "App.tsx").read_text()
        for needle in (
            'id="default-floorplan-btn"',
            "'/api/v1/floorplans/default'",
            'id="create-position-form"',
            "'/api/v1/org/positions'",
            'id="reorder-departments-form"',
            "'/api/v1/org/departments/reorder'",
            'id="cross-dept-create-form"',
            "'/api/v1/cross-department-requests'",
            "'/api/v1/cross-department-requests/' + item.id + '/accept'",
            'id="staffing-scan-btn"',
            "'/api/v1/staffing-proposals/scan'",
            "'/api/v1/promotions/' + promotion.id + '/decision'",
            "'/api/v1/scorecard'",
            "'/api/v1/activity'",
        ):
            self.assertIn(needle, desk_source)
        for needle in (
            "/api/v1/scorecard",
            "/api/v1/objectives",
            '"/api/v1/industry-packs"',
            '"/api/v1/divisions"',
            "/api/v1/promotions",
            '"/api/v1/staffing-proposals/scan"',
            '"/api/v1/cross-department-requests"',
            "/api/v1/activity",
            '"/api/v1/floorplans/default"',
            '"/api/v1/org/departments/reorder"',
            "createPosition(",
            "workerCard(",
        ):
            self.assertIn(needle, client_source)
        for needle in (
            '"corporate"',
            'htmlFor="create-pos-dept"',
            'htmlFor="reorder-items"',
            'htmlFor="worker-lookup-id"',
            'htmlFor="objective-title"',
            'htmlFor="xd-project"',
            "Scan staffing gaps",
            "Create default floorplan",
        ):
            self.assertIn(needle, app_source)

    def test_dashboard_unauthenticated(self):
        self.assertEqual(self.client.get("/api/v1/dashboard").status_code, 401)

    def test_health_no_auth(self):
        r = self.client.get("/api/v1/health")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["version"], __version__)
        self.assertEqual(body["db"], self.c.db_path)

    @patch("company.github_app.github_configured", return_value=True)
    @patch("company.github_app.installation_account_login", return_value="acme")
    @patch("company.github_app.ensure_corp_write_repo")
    @patch("company.github_app.repo_by_full_name")
    def test_github_assign_by_address(self, by_name, ensure_corp, _acct, _cfg):
        by_name.return_value = {"id": 11, "name": "demo", "full_name": "acme/demo", "owner": {"login": "acme"}}
        ensure_corp.return_value = ({"id": 22, "name": "demo-corp", "full_name": "acme/demo-corp"}, True)
        r = self.client.post(
            "/api/v1/projects/demo/github-assign",
            json={"payload": {"upstream": "https://github.com/acme/demo"}},
            headers={"Authorization": "Bearer owner-token", "Idempotency-Key": "gh-assign-1"},
        )
        self.assertEqual(r.status_code, 200)
        result = r.json()["result"]
        self.assertEqual(result["upstream"]["id"], "11")
        self.assertEqual(result["write_repo"]["full_name"], "acme/demo-corp")
        detail = self.client.get("/api/v1/projects/demo", headers={"Authorization": "Bearer owner-token"})
        self.assertEqual(detail.json()["github"]["fork_repo_id"], "22")

    def test_consultant_in_decisions_inbox(self):
        ConsultantDesk(self.c).submit("consultant", PROPOSAL)
        headers = {"Authorization": "Bearer owner-token"}
        items = self.client.get("/api/v1/decisions/inbox", headers=headers).json()["items"]
        self.assertTrue(any(i["kind"] == "consultant" for i in items))

    def test_desk_nav_anchors_resolve_to_sections(self):
        from company.service import DESK_HTML

        anchors = set(re.findall(r'href="#([^"]+)"', DESK_HTML))
        ids = set(re.findall(r'id="([^"]+)"', DESK_HTML))
        self.assertTrue(anchors)
        self.assertEqual(sorted(anchors - ids), [])

    def test_companion_nav_is_five_tabs_with_more_switcher(self):
        app_source = (
            Path(__file__).resolve().parents[1] / "companion" / "src" / "App.tsx"
        ).read_text()
        self.assertIn("const PRIMARY_TABS", app_source)
        self.assertIn("const WORK_TABS", app_source)
        self.assertIn("const MORE_TABS", app_source)
        primary = re.search(r"const PRIMARY_TABS[^=]*= \[(.*?)\];", app_source, re.S).group(1)
        self.assertEqual(len(re.findall(r'\["', primary)), 4)
        self.assertIn('["dashboard", "Home"]', primary)
        self.assertIn('["work", "Work"]', primary)
        self.assertIn('["people", "People"]', primary)
        self.assertIn('["money", "Money"]', primary)
        self.assertNotIn('["workers", "Workers"]', primary)
        self.assertIn('["projects", "Projects"]', app_source)  # inside WORK_TABS
        self.assertIn('tab === "finance"', app_source)
        self.assertNotIn('["finance", "Finance"]', re.search(r"const MORE_TABS[^=]*= \[(.*?)\];", app_source, re.S).group(1))
        self.assertIn("setTab(lastWorkTab)", app_source)
        self.assertIn("setTab(lastMoreTab)", app_source)
        self.assertIn("HomePanel", app_source)

    def test_companion_styles_size_every_field_for_touch(self):
        css = (
            Path(__file__).resolve().parents[1] / "companion" / "src" / "styles.css"
        ).read_text()
        self.assertIn("input, select, textarea, button {", css)
        self.assertIn("font-size: 16px", css)
        self.assertIn("min-height: 44px", css)
        self.assertIn("env(safe-area-inset-bottom)", css)
        narrow = re.search(r"@media \(max-width: 360px\) \{(.*?)\n\}", css, re.S).group(1)
        self.assertIn("white-space: normal", narrow)
        self.assertIn("overflow-wrap: anywhere", narrow)

    def test_remote_worker_runbook_describes_actual_reachability(self):
        runbook = (
            Path(__file__).resolve().parents[1] / "docs" / "25-fs-dev-deployment.md"
        ).read_text()
        self.assertIn("nothing dials `base_url`", runbook)
        self.assertIn("`FS_CORP_CONTROL_URL` must be reachable from the agent host", runbook)
        self.assertNotIn("wh-abc123", runbook)

    def test_native_shell_injects_scopes_without_clobbering(self):
        native = (
            Path(__file__).resolve().parents[1] / "companion-native" / "App.tsx"
        ).read_text()
        self.assertIn("scopes: session.scopes", native)
        self.assertIn("scopes: data.scopes", native)
        self.assertIn("Array.isArray(current.scopes)", native)
        self.assertIn("keyboardDisplayRequiresUserAction={false}", native)

    def test_companion_hydrates_scopes_from_session(self):
        root = Path(__file__).resolve().parents[1] / "companion" / "src"
        self.assertIn('"/api/v1/session"', (root / "api" / "client.ts").read_text())
        self.assertIn("api.session()", (root / "App.tsx").read_text())
        self.assertIn('includes("*")', (root / "scopes.ts").read_text())


class PairedAdminCompanionTests(unittest.TestCase):
    """A paired Admin / CEO mobile device must be able to run what it shows."""

    def setUp(self):
        self.c, self.client = owner_client()
        self.addCleanup(self.c.close)
        self.c.seed_catalog(Path(__file__).resolve().parents[1] / "config" / "departments.json")
        self.c.seed_industry_packs()
        self.token = self._pair("admin")

    def _pair(self, access_level):
        issued = self.c.create_pairing_ticket(
            "human-ceo", "https://192.168.4.100", access_level=access_level)
        return self.c.redeem_pairing_ticket(issued["ticket"])["token"]

    def _headers(self, key, token=None):
        return {"Authorization": f"Bearer {token or self.token}", "Idempotency-Key": key}

    def test_session_reports_principal_and_scopes(self):
        r = self.client.get("/api/v1/session", headers={"Authorization": f"Bearer {self.token}"})
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertTrue(body["principal_id"].startswith("companion-admin-"))
        self.assertEqual(body["access_level"], "admin")
        self.assertEqual(body["kind"], "service")
        self.assertIn("organization.write", body["scopes"])

    def test_session_tells_a_read_only_device_it_is_read_only(self):
        token = self._pair("read_only")
        body = self.client.get(
            "/api/v1/session", headers={"Authorization": f"Bearer {token}"}).json()
        self.assertEqual(body["access_level"], "read_only")
        self.assertNotIn("organization.write", body["scopes"])

    def test_session_requires_authentication(self):
        self.assertEqual(self.client.get("/api/v1/session").status_code, 401)

    def test_owner_session_reports_wildcard_scope(self):
        body = self.client.get(
            "/api/v1/session", headers={"Authorization": "Bearer owner-token"}).json()
        self.assertEqual(body["principal_id"], "human-ceo")
        self.assertIsNone(body["access_level"])
        self.assertEqual(body["scopes"], ["*"])

    def test_admin_companion_can_scan_staffing_and_propose_division(self):
        scan = self.client.post(
            "/api/v1/staffing-proposals/scan",
            json={"payload": {}},
            headers=self._headers("companion-scan"),
        )
        self.assertEqual(scan.status_code, 200, scan.text)
        packs = self.client.get(
            "/api/v1/industry-packs", headers={"Authorization": f"Bearer {self.token}"}).json()
        pack_id = packs["industry_packs"][0]["id"]
        proposed = self.client.post(
            "/api/v1/divisions/proposals",
            json={"payload": {"pack_id": pack_id, "name": "Mobile division", "mode": "minimal"}},
            headers=self._headers("companion-division"),
        )
        self.assertEqual(proposed.status_code, 200, proposed.text)

    def test_admin_companion_can_decide_policy_and_answer_owner_inbox(self):
        pid = self.c.propose_policy("head", policy(self.c), "mobile decision")
        decided = self.client.post(
            f"/api/v1/policy-proposals/{pid}/decision",
            json={"payload": {"decision": "approved", "reason": "Approved from mobile companion"}},
            headers=self._headers("companion-policy"),
        )
        self.assertEqual(decided.status_code, 200, decided.text)
        request = self.c.create_owner_request(
            "human-ceo", "engineering", "escalation", "Need a call", "Approve overtime?")
        answered = self.client.post(
            f"/api/v1/owner-inbox/{request['id']}/respond",
            json={"payload": {"response": "Approved."}},
            headers=self._headers("companion-owner"),
        )
        self.assertEqual(answered.status_code, 200, answered.text)

    def test_lower_pairing_levels_stay_denied(self):
        user_token = self._pair("user")
        denied = self.client.post(
            "/api/v1/staffing-proposals/scan",
            json={"payload": {}},
            headers=self._headers("companion-scan-user", token=user_token),
        )
        self.assertEqual(denied.status_code, 403)
        with self.assertRaises(PermissionError):
            self.c.scan_staffing_gaps("companion-user-abcd1234")
        with self.assertRaises(PermissionError):
            self.c.approve_policy("companion-read_only-abcd1234", "whatever")

    def test_root_authority_stays_owner_only(self):
        for actor_call in (
            lambda: self.c.create_pairing_ticket("companion-admin-abcd1234", "https://x"),
            lambda: self.c.list_paired_devices("companion-admin-abcd1234"),
        ):
            with self.assertRaises(PermissionError):
                actor_call()


if __name__ == "__main__":
    unittest.main()
