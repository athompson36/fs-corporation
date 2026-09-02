"""External integration contracts. Live adapters intentionally fail closed."""
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class WorkOrder:
    task_id: str
    project_id: str
    policy_version: int
    workflow_digest: str
    max_cost_cents: int
    payload: dict

class WorkflowAdapter(Protocol):
    def run(self, order: WorkOrder) -> dict: ...

class ChatDevAdapter:
    def run(self, order: WorkOrder) -> dict:
        raise NotImplementedError("Live ChatDev execution requires the isolated worker and action gateway; see docs/07-chatdev-integration.md")

class MockChatDevAdapter:
    """Contract double. Does not invoke upstream ChatDev or a live provider."""
    def run(self, order: WorkOrder) -> dict:
        if not order.task_id or not order.workflow_digest:
            raise ValueError("WorkOrder requires task_id and workflow_digest")
        tools=order.payload.get("tools") or []
        allowed={"none","mock_fs"}
        if any(t not in allowed for t in tools):
            raise PermissionError("Unapproved tool")
        return {
            "final_message":"mock workflow complete",
            "meta_info":{
                "session_name":f"company-{order.project_id}-{order.task_id}",
                "usage":{"input_tokens":1,"output_tokens":1,"cost_cents":0},
                "cancelled":False,"failed":False,
            },
            "artifact_hash":None,
            "accepted":False,
        }

    def cancel(self, session_name: str) -> dict:
        return {"session_name":session_name,"cancelled":True}

    def fail(self, order: WorkOrder, reason: str) -> dict:
        return {"task_id":order.task_id,"failed":True,"reason":reason,"accepted":False}

class GitHubAdapter:
    def execute(self, order: WorkOrder) -> dict:
        from . import github_app
        if not github_app.github_configured():
            raise NotImplementedError(
                "Live repository actions require GitHub App installation and validated action permissions; "
                "see docs/08-github-cursor.md")
        operation = order.payload.get("operation")
        repo_id = str(order.payload.get("repo_id") or "")
        branch = order.payload.get("branch") or ""
        if not operation or not repo_id or not branch:
            raise ValueError("GitHub WorkOrder requires operation, repo_id and branch")
        if operation == "open_pr":
            return self._open_pr(order, repo_id, branch)
        if operation in {"push", "prepare_pr"}:
            return self._push(order, repo_id, branch)
        raise ValueError(f"Unsupported GitHub operation: {operation}")

    def _repo(self, repo_id: str) -> dict:
        from . import github_app
        return github_app.repo_by_id(repo_id)

    def _worktree_bytes(self, order: WorkOrder) -> tuple[str, bytes]:
        from pathlib import Path
        worktree = Path(order.payload.get("worktree") or "")
        if worktree.is_dir():
            files = sorted(p for p in worktree.rglob("*") if p.is_file())
            if files:
                primary = files[0]
                rel = primary.relative_to(worktree).as_posix()
                return rel, primary.read_bytes()
        text = f"FS-Corporation pilot task {order.task_id} (project {order.project_id})"
        return f"company/{order.project_id}/{order.task_id}.txt", text.encode()

    def _open_pr(self, order: WorkOrder, repo_id: str, branch: str) -> dict:
        from . import github_app
        repo = self._repo(repo_id)
        owner = repo["owner"]["login"]
        name = repo["name"]
        default = repo.get("default_branch") or "main"
        base_ref = github_app.github_request("GET", f"/repos/{owner}/{name}/git/ref/heads/{default}")
        base_sha = base_ref["object"]["sha"]
        github_app.ensure_branch(owner, name, branch, base_sha)
        rel_path, content = self._worktree_bytes(order)
        github_app.upsert_file(
            owner, name, branch, rel_path, content,
            f"FS-Corporation: {order.project_id}/{order.task_id}")
        pr = github_app.open_pull_request(
            owner, name,
            title=f"[fs-corp] {order.project_id}/{order.task_id}",
            head=branch,
            base=default,
            body="Automated pilot pull request from FS-Corporation.",
        )
        return {
            "status": "applied",
            "remote_id": str(pr.get("number") or pr.get("id")),
            "html_url": pr.get("html_url"),
            "operation": "open_pr",
        }

    def _push(self, order: WorkOrder, repo_id: str, branch: str) -> dict:
        from . import github_app
        repo = self._repo(repo_id)
        owner = repo["owner"]["login"]
        name = repo["name"]
        default = repo.get("default_branch") or "main"
        base_ref = github_app.github_request("GET", f"/repos/{owner}/{name}/git/ref/heads/{default}")
        github_app.ensure_branch(owner, name, branch, base_ref["object"]["sha"])
        rel_path, content = self._worktree_bytes(order)
        result = github_app.upsert_file(
            owner, name, branch, rel_path, content,
            f"FS-Corporation push: {order.project_id}/{order.task_id}")
        return {
            "status": "applied",
            "remote_id": result.get("commit", {}).get("sha"),
            "operation": order.payload.get("operation"),
        }

class MarketFeedAdapter:
    def poll(self, source_id: str, url: str) -> list[dict]:
        from datetime import datetime, timezone
        from .feed_fetch import fetch_feed
        if not url or not url.startswith("https://"):
            raise ValueError("Approved feed source needs an HTTPS URL")
        observed = datetime.now(timezone.utc).isoformat()
        return fetch_feed(url, observed_at=observed)

class LearningAdapter:
    def fetch(self, url: str) -> dict:
        raise NotImplementedError("Live documentation fetch requires an approved source list and the action gateway; see docs/20-hardware-skills.md")

class PushNotificationAdapter:
    def send(self, subscription: dict, payload: dict) -> dict:
        from .push_vapid import send_push
        return send_push(subscription, payload)

class TailscaleAdapter:
    def join(self, payload: dict) -> dict:
        raise NotImplementedError(
            "Live Tailscale node join requires FS_CORP_TAILSCALE_AUTHKEY on the host; see docs/24-mobile-companion.md")
