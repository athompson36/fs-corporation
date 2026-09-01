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
        raise NotImplementedError("Live repository actions require GitHub App installation and validated action permissions; see docs/08-github-cursor.md")

class MarketFeedAdapter:
    def poll(self, source_id: str) -> list[dict]:
        raise NotImplementedError("No live polling configured; see docs/09-market-intelligence.md")

class LearningAdapter:
    def fetch(self, url: str) -> dict:
        raise NotImplementedError("Live documentation fetch requires an approved source list and the action gateway; see docs/20-hardware-skills.md")
