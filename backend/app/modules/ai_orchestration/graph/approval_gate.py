from __future__ import annotations

from langgraph.types import interrupt

from app.modules.ai_orchestration.schemas import AgentMessage


def _dump(item):
    return item.model_dump() if hasattr(item, "model_dump") else item


def approval_gate(state: dict) -> dict:
    """Genuinely pauses the graph (via LangGraph's interrupt()) before SOP
    generation, and waits for a real human decision delivered through
    WorkflowService.resume() -> graph.invoke(Command(resume=...), ...).

    This is not cosmetic: graph.invoke() actually returns/raises control back
    to the caller here, and execution only continues on a later, separate
    invoke() call against the same thread_id.
    """
    payload = {
        "type": "opportunity_approval",
        "candidate_opportunities": [_dump(item) for item in state.get("candidate_opportunities", [])],
        "ranked_opportunities": [_dump(item) for item in state.get("ranked_opportunities", [])],
    }
    decision = interrupt(payload)
    decision = decision if isinstance(decision, dict) else {}

    approved = decision.get("decision") == "approve"
    return {
        "human_approval": {
            "decision": decision.get("decision", "reject"),
            "opportunity_id": decision.get("opportunity_id"),
        },
        "approval_status": "approved" if approved else "rejected",
        "agent_messages": [
            AgentMessage(
                sender="approval_gate",
                receiver="supervisor",
                message_type="approval",
                content=f"Human decision: {decision.get('decision', 'reject')}"
                + (f" (opportunity_id={decision.get('opportunity_id')})" if decision.get("opportunity_id") else ""),
            )
        ],
    }
