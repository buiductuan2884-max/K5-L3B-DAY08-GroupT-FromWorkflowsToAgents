"""Remote investigator, A2A style. It owns its sqlite connection and never writes."""

from __future__ import annotations

import copy
from typing import Any

from lab8.db import connect
from lab8.handoff import ALLOWED_FIELDS, CONTRACT_VERSION, READONLY_TOOLS, HandoffError, sanitize
from lab8.runtime import ToolRejected, run_readonly_investigators
from lab8.schemas import Budget

AGENT_CARD = {
    "name": "logix-investigator",
    "version": "1.0.0",
    "skills": ["check_applicable_policy"],
    "auth": {"scheme": "principal_scope_token"},
    "contract_version": CONTRACT_VERSION,
    "tools": sorted(READONLY_TOOLS),
}


class RemoteInvestigator:
    def __init__(self, store_path: str) -> None:
        self.store_path = str(store_path)
        self.cache: dict[str, dict[str, Any]] = {}
        self.computed = 0  # how many times work really ran (idempotency check)

    def handle(self, env: dict[str, Any]) -> dict[str, Any]:
        request_id = env.get("request_id")
        if request_id in self.cache:
            cached = copy.deepcopy(self.cache[request_id])
            cached["correlation_id"] = env.get("correlation_id")
            return cached
        resp = {
            "task_id": env.get("task_id"),
            "correlation_id": env.get("correlation_id"),
            "request_id": request_id,
            "states": ["submitted"],
        }
        try:
            handoff = self._validate(env)
            resp["states"].append("working")
            self.computed += 1
            budget = Budget()
            conn = connect(self.store_path)
            try:
                out = run_readonly_investigators(conn, budget, handoff, principal_id=env["principal_id"])
            finally:
                conn.close()
            resp.update(
                state="completed",
                tools=out["tools"],
                budget={"tool_calls": budget.tool_calls, "cost_estimate": budget.cost_estimate},
            )
        except (HandoffError, ToolRejected, KeyError, TypeError) as exc:
            resp.update(state="failed", error=f"{type(exc).__name__}:{exc}")
        resp["states"].append(resp["state"])
        self.cache[request_id] = copy.deepcopy(resp)
        return resp

    @staticmethod
    def _validate(env: dict[str, Any]) -> dict[str, Any]:
        handoff = env.get("handoff")
        if not isinstance(handoff, dict) or handoff.get("contract_version") != CONTRACT_VERSION:
            raise HandoffError("not a handoff.v1")
        extra = set(handoff) - ALLOWED_FIELDS
        if extra:
            raise HandoffError(f"non-allowlisted fields: {sorted(extra)}")
        if not isinstance(env.get("principal_id"), str) or not env.get("request_id"):
            raise HandoffError("missing principal_id or request_id")
        tools = handoff.get("allowed_tools") or []
        if set(tools) - READONLY_TOOLS:
            raise HandoffError(f"tools not read-only: {sorted(set(tools) - READONLY_TOOLS)}")
        return sanitize(handoff)
